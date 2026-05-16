"""Dashboard APIs — live state + Google Sheets logs/applications."""
from fastapi import APIRouter, Depends, Query

from app.deps import get_current_username
from app.services import runtime_state
from app.services import sheets_service as sheets

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/state/{username}")
def state_by_username(username: str):
    """Real-time dashboard state (poll every 5s)."""
    return runtime_state.build_dashboard_state(username)


@router.get("/state")
def state_me(username: str = Depends(get_current_username)):
    return runtime_state.build_dashboard_state(username)


@router.get("/logs/{username}")
def logs_by_username(username: str, limit: int = Query(100, ge=1, le=500)):
    return sheets.get_logs(username, limit=limit)


@router.get("/logs")
def logs_me(username: str = Depends(get_current_username), limit: int = Query(100, ge=1, le=500)):
    return sheets.get_logs(username, limit=limit)


@router.get("/applications/{username}")
def applications_by_username(username: str, limit: int = Query(50, ge=1, le=200)):
    return sheets.get_applications(username, limit=limit)


@router.get("/applications")
def applications_me(username: str = Depends(get_current_username), limit: int = Query(50, ge=1, le=200)):
    return sheets.get_applications(username, limit=limit)
