"""Write worker env file for Selenium process (per user)."""
import json
import os

from sqlalchemy.orm import Session

from app.config import UPLOADS_DIR
from app.models.profile import UserProfile
from app.models.resume import UserResume


def write_worker_payload(db: Session, user_id: int) -> str:
    """Sync DB profile + resume into uploads/{user_id}/worker_env.json for automation."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    resume = db.query(UserResume).filter(UserResume.user_id == user_id).first()

    payload = {
        "user_id": str(user_id),
        "naukri_email": profile.naukri_email if profile else "",
        "naukri_password": profile.naukri_password_enc if profile else "",
        "expected_salary": profile.expected_ctc if profile else "",
        "current_salary": profile.current_ctc if profile else "",
        "notice_period": profile.notice_period if profile else "",
        "apply_years": profile.apply_years if profile else "3",
        "lwd_reply": profile.lwd_reply if profile else "",
        "skills_reply": profile.skills_reply if profile else "",
        "generic_reply": profile.generic_reply if profile else "Yes",
        "resume_text": resume.resume_text if resume else "",
        "max_applies_per_day": 100,
    }

    folder = os.path.join(UPLOADS_DIR, str(user_id))
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "worker_env.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path
