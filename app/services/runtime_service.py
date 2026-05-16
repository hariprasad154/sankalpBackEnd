"""Runtime state service — re-exports live dashboard state helpers."""
from app.services.runtime_state import (  # noqa: F401
    build_dashboard_state,
    get_user_state,
    patch_user,
    record_apply_success,
    record_error,
    record_log,
    recover_stale_runtime,
    set_current_job,
    set_running,
)
