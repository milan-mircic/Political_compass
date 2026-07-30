from app.config import settings
from app.db import get_connection


def cleanup_old_data() -> None:
    conn = get_connection()
    try:
        conn.execute(
            "DELETE FROM articles WHERE published_at < datetime('now', ?)",
            (f"-{settings.rolling_window_days} days",),
        )

        orphaned_story_ids = [
            row["id"]
            for row in conn.execute(
                """
                SELECT id FROM stories
                WHERE id NOT IN (SELECT DISTINCT story_id FROM articles WHERE story_id IS NOT NULL)
                """
            ).fetchall()
        ]

        if orphaned_story_ids:
            placeholders = ",".join("?" * len(orphaned_story_ids))
            conn.execute(
                f"DELETE FROM story_ideology_aggregates WHERE story_id IN ({placeholders})",
                orphaned_story_ids,
            )
            conn.execute(
                f"DELETE FROM stories WHERE id IN ({placeholders})",
                orphaned_story_ids,
            )

        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    cleanup_old_data()
