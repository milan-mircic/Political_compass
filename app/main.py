from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db import get_cursor
from app.scheduler import start_scheduler

APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield


app = FastAPI(title="News Ideology Tracker", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
templates = Jinja2Templates(directory=APP_DIR / "templates")

ORIENTATIONS = ("left", "center", "right")


_SENTIMENT_TEXT = {
    "positive": "Positive",
    "negative": "Negative",
    "neutral": "Neutral",
    "pending": "Sentiment pending",
}


def _sentiment_label(score: float | None) -> str:
    if score is None:
        return "pending"
    if score > 0.25:
        return "positive"
    if score < -0.25:
        return "negative"
    return "neutral"


def _orientation_view(orientation: str, row, panel_size: int) -> dict:
    coverage_count = row["coverage_count"]
    sentiment_label = _sentiment_label(row["avg_sentiment"])
    return {
        "key": orientation,
        "coverage_count": coverage_count,
        "panel_size": panel_size,
        "coverage_pct": round(100 * coverage_count / panel_size) if panel_size else 0,
        "sentiment_label": sentiment_label,
        "sentiment_text": _SENTIMENT_TEXT[sentiment_label],
        "framing": row["framing"],
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    with get_cursor() as cur:
        cur.execute("SELECT orientation, COUNT(*) AS total FROM sources GROUP BY orientation")
        panel_size = {row["orientation"]: row["total"] for row in cur.fetchall()}

        cur.execute(
            """
            SELECT s.id, s.title, s.summary, SUM(sia.coverage_count) AS total_coverage
            FROM stories s
            JOIN story_ideology_aggregates sia ON sia.story_id = s.id
            WHERE s.aggregated_at IS NOT NULL
            GROUP BY s.id
            ORDER BY total_coverage DESC, s.updated_at DESC
            LIMIT 10
            """
        )
        story_rows = cur.fetchall()

        stories = []
        for story_row in story_rows:
            cur.execute(
                "SELECT orientation, coverage_count, avg_sentiment, framing "
                "FROM story_ideology_aggregates WHERE story_id = ?",
                (story_row["id"],),
            )
            aggregates = {row["orientation"]: row for row in cur.fetchall()}
            stories.append(
                {
                    "title": story_row["title"],
                    "summary": story_row["summary"],
                    "orientations": [
                        _orientation_view(orientation, aggregates[orientation], panel_size.get(orientation, 0))
                        for orientation in ORIENTATIONS
                    ],
                }
            )

    return templates.TemplateResponse(request, "index.html", {"stories": stories})


@app.get("/health")
def health():
    return {"status": "ok"}
