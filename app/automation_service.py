"""Start Selenium subprocess on worker machine (local/VPS)."""
import os
import signal
import subprocess
import sys
from pathlib import Path

from app.services import runtime_state
from app.services import sheets_service as sheets

_AUTOMATION_DIR = Path(__file__).resolve().parents[2] / "automation"
_processes: dict[str, subprocess.Popen] = {}


def automation_running(username: str | None = None) -> bool:
    if username is not None:
        proc = _processes.get(username)
        if proc is None:
            return False
        if proc.poll() is not None:
            _processes.pop(username, None)
            runtime_state.set_running(username, False)
            return False
        return True
    return any(automation_running(u) for u in list(_processes.keys()))


def start_automation(username: str, mode: str = "batch") -> dict:
    if automation_running(username):
        return {"status": "already_running", "username": username}

    sheets.write_worker_env(username)
    sheets.set_auto_apply(username, True)

    env = os.environ.copy()
    env["SANKALPA_USERNAME"] = username
    env["SANKALPA_USER_ID"] = username
    env["AUTOMATION_MODE"] = mode
    env["BACKEND_URL_SANKALPA"] = os.getenv("BACKEND_URL_SANKALPA", "http://localhost:8000")

    venv_python = _AUTOMATION_DIR / "venv" / "bin" / "python"
    python = str(venv_python) if venv_python.is_file() else sys.executable
    main_py = str(_AUTOMATION_DIR / "main.py")
    proc = subprocess.Popen([python, main_py, mode], cwd=str(_AUTOMATION_DIR), env=env)
    _processes[username] = proc
    runtime_state.set_running(username, True)
    runtime_state.record_log(username, "Browser started — batch apply")
    sheets.save_log(username, "Browser started — batch apply")
    return {"status": "started", "pid": proc.pid, "mode": mode, "username": username}


def stop_automation(username: str) -> dict:
    proc = _processes.get(username)
    if proc is None or proc.poll() is not None:
        _processes.pop(username, None)
        sheets.set_auto_apply(username, False)
        runtime_state.set_running(username, False)
        return {"status": "not_running", "username": username}

    proc.send_signal(signal.SIGTERM)
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    _processes.pop(username, None)
    sheets.set_auto_apply(username, False)
    runtime_state.set_running(username, False)
    runtime_state.patch_user(username, current_job="", last_error="")
    runtime_state.record_log(username, "Automation stopped")
    sheets.save_log(username, "Automation stopped")
    return {"status": "stopped", "username": username}
