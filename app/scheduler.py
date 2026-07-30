import logging
import threading
import time

from app.config import settings
from app.pipeline.run_pipeline import run_pipeline

logger = logging.getLogger(__name__)


def _loop() -> None:
    while True:
        try:
            run_pipeline()
        except Exception:
            logger.exception("Pipeline run failed")
        time.sleep(settings.pipeline_interval_hours * 3600)


def start_scheduler() -> None:
    threading.Thread(target=_loop, daemon=True).start()
