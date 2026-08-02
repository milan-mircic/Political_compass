import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Settings:
    db_path: str = os.environ.get("DB_PATH", str(BASE_DIR / "data" / "news.db"))
    newsdata_api_key: str = os.environ.get("NEWSDATA_API_KEY", "")
    hf_api_token: str = os.environ.get("HF_API_TOKEN", "")
    gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
    rolling_window_days: int = int(os.environ.get("ROLLING_WINDOW_DAYS", "7"))
    cluster_distance_threshold: float = float(os.environ.get("CLUSTER_DISTANCE_THRESHOLD", "0.4"))
    pipeline_interval_hours: float = float(os.environ.get("PIPELINE_INTERVAL_HOURS", "6"))


settings = Settings()
