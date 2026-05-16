"""Auth helpers."""
from app.services import sheets_service as sheets
from app.utils.jwt_utils import create_access_token


def register_user(username: str, password: str, naukri_email: str, naukri_password: str) -> dict:
    user = sheets.register_user(username, password, naukri_email, naukri_password)
    sheets.save_log(username, "User registered")
    try:
        sheets.write_worker_env(username)
    except ValueError:
        pass
    token = create_access_token(user["username"])
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}


def login_user(username: str, password: str) -> dict | None:
    user = sheets.login_user(username, password)
    if not user:
        return None
    sheets.save_log(username, "Login success")
    token = create_access_token(user["username"])
    return {"access_token": token, "token_type": "bearer", "username": user["username"]}
