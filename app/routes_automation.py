"""Start/stop auto apply — updates Users.auto_apply_enabled in Google Sheet."""
from fastapi import APIRouter, Depends

from app.automation_service import automation_running, start_automation, stop_automation
from app.deps import get_current_username
from app.services import sheets_service as sheets

router = APIRouter(prefix="/api/automation", tags=["automation"])


@router.post("/start/{username}")
def start_for_username(username: str):
    sheets.set_auto_apply(username, True)
    sheets.write_worker_env(username)
    result = start_automation(username)
    sheets.save_log(username, "Auto apply enabled — batch started")
    return {
        **result,
        "auto_apply_enabled": True,
        "message": "Automation running; scheduler repeats every 6 hours",
    }


@router.post("/stop/{username}")
def stop_for_username(username: str):
    sheets.set_auto_apply(username, False)
    stop_automation(username)
    sheets.save_log(username, "Auto apply disabled")
    return {"status": "disabled", "username": username}


@router.post("/start")
def start_me(username: str = Depends(get_current_username)):
    sheets.set_auto_apply(username, True)
    result = start_automation(username)
    sheets.save_log(username, "Manual apply started")
    return result


@router.post("/stop")
def stop_me(username: str = Depends(get_current_username)):
    sheets.set_auto_apply(username, False)
    result = stop_automation(username)
    sheets.save_log(username, "Manual apply stopped")
    return result


@router.get("/status")
def status_me(username: str = Depends(get_current_username)):
    user = sheets.get_user(username) or {}
    return {
        "username": username,
        "running": automation_running(username),
        "auto_apply_enabled": str(user.get("auto_apply_enabled", "")).lower() in ("true", "1", "yes"),
        "last_apply_time": user.get("last_apply_time", ""),
    }


@router.get("/status/{username}")
def status_username(username: str):
    user = sheets.get_user(username) or {}
    return {
        "username": username,
        "auto_apply_enabled": str(user.get("auto_apply_enabled", "")).lower() in ("true", "1", "yes"),
        "last_apply_time": user.get("last_apply_time", ""),
    }
