"""Worker internal APIs."""
from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import WORKER_API_KEY
from app.models.schemas import ApplicationBody, LogBody, RuntimeFailedBody, RuntimePatchBody
from app.services import runtime_state
from app.services import sheets_service as sheets

router = APIRouter(prefix="/api/internal", tags=["internal"])


def verify_worker_key(x_worker_key: str | None = Header(None)) -> None:
    if not x_worker_key or x_worker_key != WORKER_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid worker key")


@router.get("/active-users", dependencies=[Depends(verify_worker_key)])
def active_users():
    users = sheets.get_active_users()
    out = []
    for u in users:
        username = u.get("username", "")
        if not username:
            continue
        sheets.write_worker_env(username)
        out.append({"username": username, "naukri_email": u.get("naukri_email", ""), "auto_apply_enabled": True})
    return out


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
        failed_today=body.failed_today,
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


@router.post("/runtime-increment-failed", dependencies=[Depends(verify_worker_key)])
def worker_increment_failed(body: RuntimeFailedBody):
    runtime_state.record_apply_failure(body.username, error=body.error)
    return {"status": "ok"}


@router.post("/application", dependencies=[Depends(verify_worker_key)])
def worker_application(body: ApplicationBody):
    sheets.save_application(
        body.username,
        body.job_title,
        body.company,
        body.status,
        body.error,
    )
    st = str(body.status or "").upper()
    if st == "SUCCESS":
        sheets.touch_last_apply(body.username)
        runtime_state.record_apply_success(body.username, body.job_title, body.company)
    else:
        runtime_state.record_apply_failure(
            body.username,
            body.job_title,
            body.company,
            body.error or f"Status: {body.status}",
        )
    return {"status": "ok"}
