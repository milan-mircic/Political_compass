from google.cloud import language_v1

from app.db import get_connection


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

        client = language_v1.LanguageServiceClient()
        for row in rows:
            text = row["body"] or row["snippet"]
            document = language_v1.Document(content=text, type_=language_v1.Document.Type.PLAIN_TEXT)
            sentiment = client.analyze_sentiment(request={"document": document}).document_sentiment
            conn.execute(
                "UPDATE articles SET sentiment_score = ?, sentiment_magnitude = ? WHERE id = ?",
                (sentiment.score, sentiment.magnitude, row["id"]),
            )
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    analyze_sentiment()
