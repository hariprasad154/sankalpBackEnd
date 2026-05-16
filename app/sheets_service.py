"""
Google Sheets persistence via Apps Script Web App.

Set GOOGLE_SCRIPT_URL in backend/.env after deploying google-apps-script/Code.gs
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import httpx

from app.config import GOOGLE_SCRIPT_URL
from app.utils.security import decode_value, encode_value

# Re-export for mark2 API surface (live state lives in runtime_state.py)
from app.services import runtime_state as _runtime_state

SHEET_USERS = "Users"
SHEET_APPLICATIONS = "Applications"
SHEET_LOGS = "Logs"
SHEET_CACHE = "Cache"

USER_HEADERS = [
    "username",
    "password_encoded",
    "naukri_email",
    "naukri_password_encoded",
    "resume_text",
    "skills",
    "expected_salary",
    "notice_period",
    "auto_apply_enabled",
    "last_apply_time",
    "created_at",
]

APP_HEADERS = ["username", "job_title", "company", "status", "applied_at"]
LOG_HEADERS = ["username", "timestamp", "message"]
CACHE_HEADERS = ["question", "answer"]

_local_users: list[dict] = []
_local_apps: list[dict] = []
_local_logs: list[dict] = []
_local_cache: list[dict] = []


def _use_local() -> bool:
    return not GOOGLE_SCRIPT_URL


def _fetch_sheet(sheet_name: str) -> list[list]:
    if _use_local():
        store = {
            SHEET_USERS: _local_users,
            SHEET_APPLICATIONS: _local_apps,
            SHEET_LOGS: _local_logs,
            SHEET_CACHE: _local_cache,
        }
        rows = store.get(sheet_name, [])
        if not rows:
            headers = {
                SHEET_USERS: USER_HEADERS,
                SHEET_APPLICATIONS: APP_HEADERS,
                SHEET_LOGS: LOG_HEADERS,
                SHEET_CACHE: CACHE_HEADERS,
            }.get(sheet_name, [])
            return [headers] if headers else []
        hdr = {
            SHEET_USERS: USER_HEADERS,
            SHEET_APPLICATIONS: APP_HEADERS,
            SHEET_LOGS: LOG_HEADERS,
            SHEET_CACHE: CACHE_HEADERS,
        }[sheet_name]
        out = [hdr]
        for r in rows:
            out.append([r.get(h, "") for h in hdr])
        return out

    url = f"{GOOGLE_SCRIPT_URL}?sheet={sheet_name}"
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        resp = client.get(url)
        resp.raise_for_status()
        return resp.json()


def _append_row(sheet_name: str, row: list) -> None:
    if _use_local():
        headers = {
            SHEET_USERS: USER_HEADERS,
            SHEET_APPLICATIONS: APP_HEADERS,
            SHEET_LOGS: LOG_HEADERS,
            SHEET_CACHE: CACHE_HEADERS,
        }[sheet_name]
        record = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
        {
            SHEET_USERS: _local_users,
            SHEET_APPLICATIONS: _local_apps,
            SHEET_LOGS: _local_logs,
            SHEET_CACHE: _local_cache,
        }[sheet_name].append(record)
        return

    body = {"sheet": sheet_name, "row": row}
    with httpx.Client(timeout=45, follow_redirects=True) as client:
        resp = client.post(GOOGLE_SCRIPT_URL, json=body)
        resp.raise_for_status()


def _update_row(sheet_name: str, key_value: str, updates: dict[str, Any], key_column: str = "username") -> bool:
    if _use_local():
        store = {
            SHEET_USERS: _local_users,
            SHEET_APPLICATIONS: _local_apps,
            SHEET_LOGS: _local_logs,
            SHEET_CACHE: _local_cache,
        }[sheet_name]
        for rec in store:
            if str(rec.get(key_column, "")) == str(key_value):
                rec.update(updates)
                return True
        return False

    body = {
        "action": "update",
        "sheet": sheet_name,
        "key_column": 0,
        "key_value": key_value,
        "updates": updates,
    }
    if sheet_name != SHEET_USERS:
        headers = _fetch_sheet(sheet_name)
        if headers:
            try:
                body["key_column"] = headers[0].index(key_column)
            except ValueError:
                body["key_column"] = 0

    with httpx.Client(timeout=45, follow_redirects=True) as client:
        resp = client.post(GOOGLE_SCRIPT_URL, json=body)
        resp.raise_for_status()
        data = resp.json()
        return data.get("status") == "updated"


def _rows_to_dicts(data: list[list]) -> list[dict]:
    if not data or len(data) < 2:
        return []
    headers = [str(h).strip() for h in data[0]]
    out = []
    for row in data[1:]:
        if not any(str(c).strip() for c in row):
            continue
        rec = {}
        for i, h in enumerate(headers):
            rec[h] = row[i] if i < len(row) else ""
        out.append(rec)
    return out


def get_users() -> list[dict]:
    return _rows_to_dicts(_fetch_sheet(SHEET_USERS))


def get_user(username: str) -> dict | None:
    for u in get_users():
        if str(u.get("username", "")).lower() == username.lower():
            return u
    return None


get_user_by_username = get_user


def register_user(
    username: str,
    password: str,
    naukri_email: str,
    naukri_password: str,
) -> dict:
    uname = (username or "").strip()
    if not uname:
        raise ValueError("Username is required")
    if len(uname) < 2:
        raise ValueError("Username must be at least 2 characters")
    if not password or len(password) < 6:
        raise ValueError("Password must be at least 6 characters")
    if not (naukri_email or "").strip():
        raise ValueError("Naukri email is required")
    if not (naukri_password or "").strip():
        raise ValueError("Naukri password is required")
    if get_user(uname):
        raise ValueError("Username already exists")
    now = datetime.utcnow().isoformat(timespec="seconds")
    row = [
        uname,
        encode_value(password),
        naukri_email.strip(),
        encode_value(naukri_password),
        "",
        "",
        "",
        "15 days",
        "false",
        "",
        now,
    ]
    _append_row(SHEET_USERS, row)
    return get_user(uname) or {}


def login_user(username: str, password: str) -> dict | None:
    user = get_user(username)
    if not user:
        return None
    stored = str(user.get("password_encoded", ""))
    if decode_value(stored) != password:
        return None
    return user


def user_public(user: dict) -> dict:
    return {
        "username": user.get("username", ""),
        "naukri_email": user.get("naukri_email", ""),
        "skills": user.get("skills", ""),
        "expected_salary": user.get("expected_salary", ""),
        "notice_period": user.get("notice_period", ""),
        "auto_apply_enabled": str(user.get("auto_apply_enabled", "")).lower() in ("true", "1", "yes"),
        "last_apply_time": user.get("last_apply_time", ""),
        "has_resume": bool(str(user.get("resume_text", "")).strip()),
    }


def save_resume(username: str, resume_text: str) -> None:
    _update_row(SHEET_USERS, username, {"resume_text": resume_text[:50000]})


def save_user_fields(username: str, fields: dict[str, Any]) -> None:
    allowed = {
        "naukri_email",
        "skills",
        "expected_salary",
        "notice_period",
        "skills",
    }
    updates = {k: v for k, v in fields.items() if k in allowed}
    if "naukri_password" in fields and fields["naukri_password"]:
        updates["naukri_password_encoded"] = encode_value(fields["naukri_password"])
    _update_row(SHEET_USERS, username, updates)


def set_auto_apply(username: str, enabled: bool) -> None:
    _update_row(SHEET_USERS, username, {"auto_apply_enabled": "true" if enabled else "false"})


update_auto_apply = set_auto_apply


def touch_last_apply(username: str) -> None:
    _update_row(
        SHEET_USERS,
        username,
        {"last_apply_time": datetime.utcnow().isoformat(timespec="seconds")},
    )


def save_log(username: str, message: str) -> None:
    _append_row(
        SHEET_LOGS,
        [username, datetime.utcnow().isoformat(timespec="seconds"), message[:2000]],
    )


def save_application(username: str, job_title: str, company: str, status: str) -> None:
    _append_row(
        SHEET_APPLICATIONS,
        [
            username,
            job_title[:500],
            company[:255],
            status,
            datetime.utcnow().isoformat(timespec="seconds"),
        ],
    )


def get_logs(username: str, limit: int = 100) -> list[dict]:
    rows = [r for r in _rows_to_dicts(_fetch_sheet(SHEET_LOGS)) if r.get("username") == username]
    rows.reverse()
    return rows[:limit]


def get_applications(username: str, limit: int = 100) -> list[dict]:
    rows = [r for r in _rows_to_dicts(_fetch_sheet(SHEET_APPLICATIONS)) if r.get("username") == username]
    rows.reverse()
    return rows[:limit]


def get_cached_answer(question: str) -> str:
    q = (question or "").strip().lower()
    for row in _rows_to_dicts(_fetch_sheet(SHEET_CACHE)):
        if str(row.get("question", "")).strip().lower() == q:
            return str(row.get("answer", "")).strip()
    return ""


def set_cached_answer(question: str, answer: str) -> None:
    if get_cached_answer(question):
        return
    _append_row(SHEET_CACHE, [question[:2000], answer[:2000]])


def get_active_users() -> list[dict]:
    out = []
    for u in get_users():
        if str(u.get("auto_apply_enabled", "")).lower() in ("true", "1", "yes"):
            out.append(u)
    return out


def dashboard_stats(username: str) -> dict:
    from datetime import timedelta

    apps = get_applications(username, limit=500)
    today = datetime.utcnow().date()
    week_cutoff = (today - timedelta(days=7)).isoformat()
    month_cutoff = (today - timedelta(days=30)).isoformat()
    today_s = today.isoformat()

    applied_today = 0
    applied_week = 0
    applied_month = 0
    success = 0
    failed = 0
    for a in apps:
        d = str(a.get("applied_at", ""))[:10]
        if a.get("status") == "Applied":
            success += 1
        elif a.get("status") in ("ApplyUncertain", "Failed"):
            failed += 1
        if d == today_s:
            applied_today += 1
        if d >= week_cutoff:
            applied_week += 1
        if d >= month_cutoff:
            applied_month += 1

    user = get_user(username) or {}
    return {
        "applied_today": applied_today,
        "applied_week": applied_week,
        "applied_month": applied_month,
        "success_count": success,
        "failed_count": failed,
        "total": len(apps),
        "last_apply_time": user.get("last_apply_time", ""),
        "auto_apply_enabled": str(user.get("auto_apply_enabled", "")).lower() in ("true", "1", "yes"),
    }


def write_worker_env(username: str) -> str:
    """Write automation/worker_env for Selenium from sheet user row."""
    import os

    user = get_user(username)
    if not user:
        raise ValueError(f"User not found: {username}")

    payload = {
        "username": username,
        "naukri_email": user.get("naukri_email", ""),
        "naukri_password": decode_value(str(user.get("naukri_password_encoded", ""))),
        "expected_salary": user.get("expected_salary", ""),
        "current_salary": user.get("expected_salary", ""),
        "notice_period": user.get("notice_period", "15 days"),
        "apply_years": "3",
        "lwd_reply": user.get("notice_period", "15 days"),
        "skills_reply": user.get("skills", ""),
        "generic_reply": "Yes",
        "resume_text": user.get("resume_text", ""),
    }

    uploads = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "automation", "uploads")
    )
    folder = os.path.join(uploads, username)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "worker_env.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return path


def update_runtime_state(username: str, **fields) -> dict:
    """Patch live dashboard state (runtime_state.json, not Google Sheets)."""
    return _runtime_state.patch_user(username, **fields)
