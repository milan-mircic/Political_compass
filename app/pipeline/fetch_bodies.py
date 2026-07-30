import trafilatura

from app.db import get_connection


def fetch_bodies() -> None:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT id, url FROM articles WHERE body IS NULL").fetchall()
        for row in rows:
            downloaded = trafilatura.fetch_url(row["url"])
            body = trafilatura.extract(downloaded) if downloaded else None
            if body:
                conn.execute("UPDATE articles SET body = ? WHERE id = ?", (body, row["id"]))
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    fetch_bodies()
