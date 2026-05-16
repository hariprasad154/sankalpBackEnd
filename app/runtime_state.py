"""Live automation state (not persisted to Google Sheets)."""
import json
import os
from datetime import datetime

RUNTIME_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "runtime"))
RUNTIME_PATH = os.path.join(RUNTIME_DIR, "runtime_state.json")


def _load_all() -> dict:
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    if not os.path.isfile(RUNTIME_PATH):
        return {}
    with open(RUNTIME_PATH, encoding="utf-8") as f:
        try:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}


def _save_all(data: dict) -> None:
    os.makedirs(RUNTIME_DIR, exist_ok=True)
    with open(RUNTIME_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def recover_stale_runtime() -> None:
    """After backend restart: clear running flags (worker process is gone)."""
    data = _load_all()
    changed = False
    for username, row in data.items():
        if isinstance(row, dict) and row.get("running"):
            row["running"] = False
            row["last_log"] = row.get("last_log") or "Runtime recovered after server restart"
            data[username] = row
            changed = True
    if changed:
        _save_all(data)


def _today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _ensure_daily_row(row: dict) -> dict:
    """Reset applied_today when the calendar day changes."""
    row = dict(row)
    if row.get("applied_date") != _today_key():
        row["applied_date"] = _today_key()
        row["applied_today"] = 0
    return row


def get_user_state(username: str) -> dict:
    data = _load_all()
    row = dict(data.get(username, {}))
    row = _ensure_daily_row(row)
    if data.get(username) != row:
        data[username] = row
        _save_all(data)
    return row


def patch_user(username: str, **fields) -> dict:
    data = _load_all()
    row = _ensure_daily_row(dict(data.get(username, {})))
    for key, value in fields.items():
        if value is not None:
            row[key] = value
    data[username] = row
    _save_all(data)
    return row


def set_running(username: str, running: bool) -> None:
    patch_user(username, running=running)
    if not running:
        patch_user(username, current_job="")


def set_current_job(username: str, job_title: str) -> None:
    patch_user(username, current_job=(job_title or "")[:500], last_error="")


def record_log(username: str, message: str) -> None:
    patch_user(username, last_log=(message or "")[:240])


def record_error(username: str, error: str) -> None:
    msg = (error or "Unknown error")[:240]
    patch_user(username, last_error=msg[:500], last_log=msg)


def record_apply_success(username: str, job_title: str = "", company: str = "") -> None:
    row = get_user_state(username)
    count = int(row.get("applied_today", 0) or 0) + 1
    now = datetime.now().strftime("%Y-%m-%d %I:%M %p")
    title = (job_title or "").strip()
    co = (company or "").strip()
    msg = f"Applied {title}" if title else "Applied successfully"
    patch_user(
        username,
        applied_today=count,
        last_apply_time=now,
        last_log=msg[:240],
        current_job=title[:500],
        current_company=co[:255],
        last_error="",
    )


def build_dashboard_state(username: str) -> dict:
    from app.automation_service import automation_running
    from app.services import sheets_service as sheets

    rt = get_user_state(username)
    sheet_stats = sheets.dashboard_stats(username)
    proc_running = automation_running(username)
    rt_running = bool(rt.get("running", False))

    last_time = str(rt.get("last_apply_time", "") or sheet_stats.get("last_apply_time", "") or "")
    if last_time and len(last_time) > 12:
        last_time = last_time[-8:].strip()

    from app.config import OPENAI_API_KEY

    user = sheets.get_user(username) or {}
    has_resume = bool(str(user.get("resume_text", "")).strip())
    ai_enabled = bool(OPENAI_API_KEY)

    return {
        "running": proc_running or rt_running,
        "current_job": str(rt.get("current_job", "") or ""),
        "current_company": str(rt.get("current_company", "") or ""),
        "applied_today": int(rt.get("applied_today", sheet_stats.get("applied_today", 0)) or 0),
        "last_log": str(rt.get("last_log", "") or ""),
        "last_apply_time": last_time,
        "last_error": str(rt.get("last_error", "") or ""),
        "auto_apply_enabled": bool(sheet_stats.get("auto_apply_enabled", False)),
        "resume_uploaded": has_resume,
        "ai_enabled": ai_enabled,
    }
