"""Sankalpa API — Google Sheets + live runtime state."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, automation, dashboard, internal, user
from app.config import CORS_ORIGINS, GOOGLE_SCRIPT_URL
from app.services import runtime_state


@asynccontextmanager
async def lifespan(_app: FastAPI):
    runtime_state.recover_stale_runtime()
    yield


app = FastAPI(title="Sankalpa API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(user.router)
app.include_router(automation.router)
app.include_router(dashboard.router)
app.include_router(internal.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "storage": "google_sheets" if GOOGLE_SCRIPT_URL else "local_memory_dev",
        "google_script_configured": bool(GOOGLE_SCRIPT_URL),
    }
