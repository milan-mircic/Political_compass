import re

import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.cluster import AgglomerativeClustering

from app.config import settings
from app.db import get_connection

_MODEL_NAME = "all-MiniLM-L6-v2"
_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


def _first_sentence(text: str) -> str:
    match = re.search(r"[^.!?]*[.!?]", text.strip())
    return match.group(0).strip() if match else text.strip()[:200]


def cluster() -> None:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, title, body, snippet, story_id
            FROM articles
            WHERE published_at >= datetime('now', ?)
            """,
            (f"-{settings.rolling_window_days} days",),
        ).fetchall()

        candidates = []
        for row in rows:
            text_source = row["body"] or row["snippet"] or ""
            if not row["title"] or not text_source:
                continue
            text = f"{row['title']}. {_first_sentence(text_source)}"
            candidates.append((row["id"], row["story_id"], text))

        if len(candidates) < 2:
            return

        texts = [c[2] for c in candidates]
        embeddings = _get_model().encode(texts, normalize_embeddings=True)

        conn.executemany(
            "UPDATE articles SET embedding = ? WHERE id = ?",
            [
                (np.asarray(embedding, dtype=np.float32).tobytes(), article_id)
                for (article_id, _, _), embedding in zip(candidates, embeddings)
            ],
        )

        labels = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=settings.cluster_distance_threshold,
            metric="cosine",
            linkage="average",
        ).fit_predict(embeddings)

        clusters: dict[int, list[tuple[int, int | None]]] = {}
        for (article_id, story_id, _), label in zip(candidates, labels):
            clusters.setdefault(int(label), []).append((article_id, story_id))

        for members in clusters.values():
            existing_story_ids = {sid for _, sid in members if sid is not None}
            if existing_story_ids:
                story_id = min(existing_story_ids)
                conn.execute(
                    "UPDATE stories SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (story_id,),
                )
            else:
                story_id = conn.execute("INSERT INTO stories DEFAULT VALUES").lastrowid

            conn.executemany(
                "UPDATE articles SET story_id = ? WHERE id = ?",
                [(story_id, article_id) for article_id, _ in members],
            )

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    cluster()
