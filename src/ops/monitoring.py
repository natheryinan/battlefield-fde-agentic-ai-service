from datetime import datetime
from typing import Any, Dict
from src.utils.logger import get_logger

logger = get_logger(__name__)

def log_mission_event(event: str, payload: Dict[str, Any] | None = None) -> None:
    logger.info("MISSION EVENT: %s | payload=%s", event, payload or {})

def record_metric(name: str, value: float) -> None:
    logger.info("METRIC: %s=%s", name, value)
