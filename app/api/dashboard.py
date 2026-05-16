"""Dashboard APIs — state, logs, applications, analytics."""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query

from app.deps import get_current_username
from app.services import runtime_service
from app.services import sheets_service as sheets

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


def _parse_app_date(app: dict) -> str:
    ts = str(app.get("timestamp") or app.get("applied_at") or "")
    return ts[:10] if ts else ""


def _is_success(status: str) -> bool:
    return str(status or "").upper() == "SUCCESS"


def build_analytics(username: str) -> dict:
    applications = sheets.get_applications(username, limit=500)
    daily: dict[str, int] = {}
    weekly: dict[str, int] = {}
    success = 0
    failed = 0

    for app in applications:
        day = _parse_app_date(app)
        if day:
            daily[day] = daily.get(day, 0) + 1
            try:
                dt = datetime.strptime(day, "%Y-%m-%d").date()
                week_key = dt.strftime("%Y-W%W")
                weekly[week_key] = weekly.get(week_key, 0) + 1
            except ValueError:
                pass
        if _is_success(app.get("status")):
            success += 1
        else:
            failed += 1

    today = datetime.utcnow().date()
    today_s = today.isoformat()
    week_cutoff = (today - timedelta(days=7)).isoformat()
    applied_week = sum(1 for a in applications if _parse_app_date(a) >= week_cutoff)
    applied_today = sum(
        1 for a in applications if _parse_app_date(a) == today_s and _is_success(a.get("status"))
    )
    failed_today = sum(
        1 for a in applications if _parse_app_date(a) == today_s and not _is_success(a.get("status"))
    )

    failed_apps = [a for a in applications if not _is_success(a.get("status"))][:20]

    return {
        "daily": daily,
        "weekly": weekly,
        "success": success,
        "failed": failed,
        "total": len(applications),
        "applied_today": applied_today,
        "failed_today": failed_today,
        "applied_week": applied_week,
        "applications": applications[-50:],
        "failed_applications": failed_apps,
    }


@router.get("/state/{username}")
def state_by_username(username: str):
    return runtime_service.build_dashboard_state(username)


@router.get("/state")
def state_me(username: str = Depends(get_current_username)):
    return runtime_service.build_dashboard_state(username)


@router.get("/analytics/{username}")
def analytics_by_username(username: str):
    return build_analytics(username)


@router.get("/analytics")
def analytics_me(username: str = Depends(get_current_username)):
    return build_analytics(username)


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
