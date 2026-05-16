"""Register / login — Google Sheets Users tab."""
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field

from app.auth import create_access_token
from app.services import sheets_service as sheets

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6)
    naukri_email: EmailStr
    naukri_password: str = Field(min_length=1)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest):
    username = body.username.strip()
    try:
        user = sheets.register_user(
            username,
            body.password,
            str(body.naukri_email),
            body.naukri_password,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    sheets.save_log(username, "User registered")
    try:
        sheets.write_worker_env(username)
    except ValueError:
        pass
    token = create_access_token(user["username"])
    return TokenResponse(access_token=token, username=user["username"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    username = body.username.strip()
    if not username or not body.password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username and password required")

    user = sheets.login_user(username, body.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    sheets.save_log(username, "Login success")
    token = create_access_token(user["username"])
    return TokenResponse(access_token=token, username=user["username"])
