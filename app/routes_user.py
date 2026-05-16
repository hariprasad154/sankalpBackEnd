"""Resume upload — text stored in Google Sheets only (no PDF on disk)."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.config import MAX_RESUME_BYTES
from app.deps import get_current_username
from app.services.resume_service import extract_pdf_bytes
from app.services import sheets_service as sheets

router = APIRouter(prefix="/api/user", tags=["user"])


class ConfigBody(BaseModel):
    naukri_email: str = ""
    naukri_password: str = ""
    skills: str = ""
    expected_salary: str = ""
    notice_period: str = ""


@router.get("/config")
def get_config(username: str = Depends(get_current_username)):
    user = sheets.get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return sheets.user_public(user)


@router.post("/config")
def save_config(body: ConfigBody, username: str = Depends(get_current_username)):
    if not sheets.get_user_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")
    sheets.save_user_fields(username, body.model_dump())
    sheets.save_log(username, "Config updated")
    return {"status": "saved", "username": username}


@router.post("/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    username: str = Depends(get_current_username),
):
    if not sheets.get_user_by_username(username):
        raise HTTPException(status_code=404, detail="User not found")

    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    data = await file.read()
    if len(data) > MAX_RESUME_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {MAX_RESUME_BYTES // (1024 * 1024)} MB)",
        )

    text = extract_pdf_bytes(data)
    if not text.strip():
        raise HTTPException(status_code=400, detail="Could not extract text from PDF")

    sheets.save_resume(username, text)
    sheets.save_log(username, f"Resume uploaded ({len(text)} chars extracted)")
    return {"status": "saved", "text_length": len(text), "username": username}
