import time

from google import genai
from google.genai import errors as genai_errors
from pydantic import BaseModel

from app.config import settings
from app.db import get_connection

_MODEL_NAME = "gemini-flash-lite-latest"
_MAX_EXCERPTS_PER_ORIENTATION = 5
# Free-tier quota for this model is 20 requests/minute; pace calls to stay
# safely under that instead of bursting and relying on retries.
_REQUEST_INTERVAL_SECONDS = 3.5
ORIENTATIONS = ("left", "center", "right")


class StoryAnalysis(BaseModel):
    title: str
    summary: str
    left_framing: str | None = None
    center_framing: str | None = None
    right_framing: str | None = None


def _build_prompt(titles_by_orientation: dict[str, list[str]]) -> str:
    covered = [o for o in ORIENTATIONS if titles_by_orientation.get(o)]
    missing = [o for o in ORIENTATIONS if o not in covered]

    sections = []
    for orientation in covered:
        bullet_list = "\n".join(f"- {t}" for t in titles_by_orientation[orientation])
        sections.append(f"{orientation.upper()} coverage:\n{bullet_list}")

    prompt = (
        "You are analyzing how different news outlets cover the same story. "
        "Below are headlines from articles about one story, grouped by the "
        "political orientation of their publisher.\n\n"
        + "\n\n".join(sections)
        + "\n\nWrite a short, neutral headline (5-12 words) for the underlying event, "
        "and a short, neutral one-paragraph summary of it. "
        f"Then, for each orientation with coverage above ({', '.join(covered)}), write one "
        "or two sentences describing how that orientation frames the story (word choice, "
        "emphasis, what's included or omitted) -- base this only on the provided headlines, "
        "do not speculate."
    )
    if missing:
        prompt += (
            f"\n\nThese orientations have no coverage of this story: {', '.join(missing)}. "
            "Do NOT invent framing for them -- leave their framing fields null."
        )
    return prompt


def aggregate_stories() -> None:
    conn = get_connection()
    try:
        # Only the top N stories (by article count) are ever shown on the
        # frontend -- rank before spending any Gemini calls, not after, so a
        # busy news day doesn't burn quota summarizing stories nobody sees.
        stories = conn.execute(
            """
            SELECT s.id
            FROM stories s
            JOIN articles a ON a.story_id = s.id
            WHERE s.aggregated_at IS NULL OR s.aggregated_at < s.updated_at
            GROUP BY s.id
            ORDER BY COUNT(a.id) DESC
            LIMIT ?
            """,
            (settings.top_stories_limit,),
        ).fetchall()
        if not stories:
            return

        client = genai.Client(api_key=settings.gemini_api_key)

        for story in stories:
            story_id = story["id"]
            rows = conn.execute(
                """
                SELECT s.orientation, s.id AS source_id, a.title, a.sentiment_score
                FROM articles a
                JOIN sources s ON s.id = a.source_id
                WHERE a.story_id = ?
                """,
                (story_id,),
            ).fetchall()
            if not rows:
                continue

            by_orientation: dict[str, list] = {}
            for row in rows:
                by_orientation.setdefault(row["orientation"], []).append(row)

            titles_by_orientation = {
                orientation: [r["title"] for r in members[:_MAX_EXCERPTS_PER_ORIENTATION]]
                for orientation, members in by_orientation.items()
            }

            try:
                response = client.models.generate_content(
                    model=_MODEL_NAME,
                    contents=_build_prompt(titles_by_orientation),
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": StoryAnalysis,
                    },
                )
            except genai_errors.APIError:
                # A transient failure (e.g. model overload or rate limit)
                # on one story shouldn't block the rest; aggregated_at
                # stays NULL so it's retried on the next pipeline run.
                time.sleep(_REQUEST_INTERVAL_SECONDS)
                continue
            time.sleep(_REQUEST_INTERVAL_SECONDS)
            analysis: StoryAnalysis = response.parsed

            conn.execute(
                "UPDATE stories SET title = ?, summary = ?, aggregated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (analysis.title, analysis.summary, story_id),
            )

            framing_by_orientation = {
                "left": analysis.left_framing,
                "center": analysis.center_framing,
                "right": analysis.right_framing,
            }

            for orientation in ORIENTATIONS:
                members = by_orientation.get(orientation, [])
                coverage_count = len({r["source_id"] for r in members})
                scores = [r["sentiment_score"] for r in members if r["sentiment_score"] is not None]
                avg_sentiment = sum(scores) / len(scores) if scores else None
                conn.execute(
                    """
                    INSERT INTO story_ideology_aggregates
                        (story_id, orientation, coverage_count, avg_sentiment, framing)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (story_id, orientation) DO UPDATE SET
                        coverage_count = excluded.coverage_count,
                        avg_sentiment = excluded.avg_sentiment,
                        framing = excluded.framing
                    """,
                    (story_id, orientation, coverage_count, avg_sentiment, framing_by_orientation.get(orientation) or None),
                )

            conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    aggregate_stories()
