from app.pipeline.aggregate import aggregate_stories
from app.pipeline.cleanup import cleanup_old_data
from app.pipeline.cluster import cluster
from app.pipeline.fetch_bodies import fetch_bodies
from app.pipeline.ingest import ingest
from app.pipeline.sentiment import analyze_sentiment


def run_pipeline() -> None:
    ingest()
    fetch_bodies()
    cluster()
    analyze_sentiment()
    aggregate_stories()
    cleanup_old_data()


if __name__ == "__main__":
    run_pipeline()
