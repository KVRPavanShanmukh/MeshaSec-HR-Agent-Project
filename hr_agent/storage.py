import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from .models import InterviewReport


SESSIONS_DIR = Path.home() / "Documents" / "AI HR Agent Sessions"


def save_session(report: InterviewReport) -> str:
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(ch for ch in (report.profile.name or "candidate") if ch.isalnum() or ch in (" ", "-", "_")).strip()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = SESSIONS_DIR / f"{safe_name or 'candidate'}_{timestamp}.json"
    path.write_text(json.dumps(asdict(report), indent=2, default=str), encoding="utf-8")
    return str(path)
