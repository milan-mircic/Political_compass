import time

import requests

from app.config import settings
from app.db import get_connection

_API_URL = "https://router.huggingface.co/hf-inference/models/distilbert/distilbert-base-uncased-finetuned-sst-2-english"
_MAX_RETRIES = 3
_MAX_CHARS = 2000


def _score_text(text: str) -> float | None:
    headers = {"Authorization": f"Bearer {settings.hf_api_token}"}
    payload = {"inputs": text[:_MAX_CHARS], "parameters": {"top_k": 2}}

    for attempt in range(_MAX_RETRIES):
        response = requests.post(_API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code == 503:
            time.sleep(min(2**attempt, 10))
            continue
        response.raise_for_status()
        results = response.json()
        if results and isinstance(results[0], list):
            results = results[0]
        scores = {r["label"].upper(): r["score"] for r in results}
        return scores.get("POSITIVE", 0.0) - scores.get("NEGATIVE", 0.0)

    return None


def analyze_sentiment() -> None:
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT id, body, snippet
            FROM articles
            WHERE sentiment_score IS NULL AND (body IS NOT NULL OR snippet IS NOT NULL)
            """
        ).fetchall()

        if not rows:
            return

        for row in rows:
            text = row["body"] or row["snippet"]
            try:
                score = _score_text(text)
            except requests.RequestException:
                continue
            if score is None:
                continue
            conn.execute(
                "UPDATE articles SET sentiment_score = ? WHERE id = ?",
                (score, row["id"]),
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    analyze_sentiment()
