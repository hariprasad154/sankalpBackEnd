"""Worker endpoints — poll active users from Google Sheet."""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.config import WORKER_API_KEY
from app.services import runtime_state
from app.services import sheets_service as sheets

router = APIRouter(prefix="/api/internal", tags=["internal"])


def verify_worker_key(x_worker_key: str | None = Header(None)) -> None:
    if not x_worker_key or x_worker_key != WORKER_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid worker key")


class LogBody(BaseModel):
    username: str
    message: str


class ApplicationBody(BaseModel):
    username: str
    job_title: str
    company: str = "Naukri"
    status: str = "Applied"


class RuntimePatchBody(BaseModel):
    username: str
    running: bool | None = None
    current_job: str | None = None
    current_company: str | None = None
    applied_today: int | None = None
    last_log: str | None = None
    last_apply_time: str | None = None
    last_error: str | None = None


@router.get("/active-users", dependencies=[Depends(verify_worker_key)])
def active_users():
    users = sheets.get_active_users()
    out = []
    for u in users:
        username = u.get("username", "")
        if not username:
            continue
        sheets.write_worker_env(username)
        out.append(
            {
                "username": username,
                "naukri_email": u.get("naukri_email", ""),
                "auto_apply_enabled": True,
            }
        )
    return out


@router.get("/user/{username}/payload", dependencies=[Depends(verify_worker_key)])
def user_payload(username: str):
    path = sheets.write_worker_env(username)
    user = sheets.get_user(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "worker_env_path": path,
        "username": username,
        "has_resume": bool(str(user.get("resume_text", "")).strip()),
    }


@router.post("/log", dependencies=[Depends(verify_worker_key)])
def worker_log(body: LogBody):
    sheets.save_log(body.username, body.message)
    runtime_state.record_log(body.username, body.message)
    low = (body.message or "").lower()
    if "fail" in low or "error" in low or "timeout" in low:
        runtime_state.record_error(body.username, body.message)
    return {"status": "ok"}


@router.post("/runtime-state", dependencies=[Depends(verify_worker_key)])
def worker_runtime_patch(body: RuntimePatchBody):
    runtime_state.patch_user(
        body.username,
        running=body.running,
        current_job=body.current_job,
        current_company=body.current_company,
        applied_today=body.applied_today,
        last_log=body.last_log,
        last_apply_time=body.last_apply_time,
        last_error=body.last_error,
    )
    return {"status": "ok"}


@router.get("/cache", dependencies=[Depends(verify_worker_key)])
def worker_cache_get(question: str):
    return {"answer": sheets.get_cached_answer(question)}


@router.post("/cache", dependencies=[Depends(verify_worker_key)])
def worker_cache_set(question: str, answer: str):
    sheets.set_cached_answer(question, answer)
    return {"status": "ok"}


@router.post("/application", dependencies=[Depends(verify_worker_key)])
def worker_application(body: ApplicationBody):
    sheets.save_application(body.username, body.job_title, body.company, body.status)
    if body.status == "Applied":
        sheets.touch_last_apply(body.username)
        runtime_state.record_apply_success(body.username, body.job_title, body.company)
    else:
        runtime_state.record_log(body.username, f"Apply status: {body.status} — {body.job_title}")
    return {"status": "ok"}
