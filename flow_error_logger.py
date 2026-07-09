from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json


LOG_PATH = Path(__file__).resolve().parent / "flow_last_error.json"


def writeFlowErrorLog(area: str, event: str, message: str, details: str = "") -> Path:
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "area": area,
        "event": event,
        "message": message,
        "details": details,
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.write_text(json.dumps(payload, indent=2))
    return LOG_PATH