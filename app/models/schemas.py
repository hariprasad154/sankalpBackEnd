"""Pydantic request/response schemas."""
from pydantic import BaseModel, EmailStr, Field


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


class ConfigBody(BaseModel):
    naukri_email: str = ""
    naukri_password: str = ""
    skills: str = ""
    expected_salary: str = ""
    notice_period: str = ""


class LogBody(BaseModel):
    username: str
    message: str


class ApplicationBody(BaseModel):
    username: str
    job_title: str
    company: str = "Naukri"
    status: str = "SUCCESS"
    error: str = ""


class RuntimeFailedBody(BaseModel):
    username: str
    error: str = ""


class RuntimePatchBody(BaseModel):
    username: str
    running: bool | None = None
    current_job: str | None = None
    current_company: str | None = None
    applied_today: int | None = None
    failed_today: int | None = None
    last_log: str | None = None
    last_apply_time: str | None = None
    last_error: str | None = None
