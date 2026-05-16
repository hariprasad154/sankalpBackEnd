"""Application settings — loads sankalpBackEnd root .env then backend/.env."""
import os
from pathlib import Path

from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_REPO_ROOT / "backend" / ".env")

JWT_SECRET = os.getenv("JWT_SECRET", "sankalpa-secret")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

WORKER_API_KEY = os.getenv("WORKER_API_KEY", "worker-dev-key")
GOOGLE_SCRIPT_URL = os.getenv("GOOGLE_SCRIPT_URL", "").strip()
AUTO_APPLY_INTERVAL_HOURS = int(os.getenv("AUTO_APPLY_INTERVAL_HOURS", "6"))

UPLOADS_DIR = os.path.abspath(os.path.join(_REPO_ROOT, "automation", "uploads"))

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://localhost:8000")

_cors = os.getenv("CORS_ORIGINS", "").strip()
CORS_ORIGINS = _cors.split(",") if _cors else [FRONTEND_URL, "http://localhost:5173"]

MAX_RESUME_BYTES = int(os.getenv("MAX_RESUME_BYTES", str(5 * 1024 * 1024)))
MAX_APPLY_PER_RUN = int(os.getenv("MAX_APPLY_PER_RUN", "50"))
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()

RUNTIME_STATE_FILE = os.getenv(
    "RUNTIME_STATE_FILE",
    os.path.join(_REPO_ROOT, "automation", "data", "runtime_state.json"),
)
