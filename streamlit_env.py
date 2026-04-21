from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def _flatten_secrets(data: Any) -> dict[str, str]:
    flattened: dict[str, str] = {}
    if isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, dict):
                flattened.update(_flatten_secrets(value))
            elif isinstance(value, (str, int, float, bool)):
                flattened[str(key)] = str(value)
    return flattened


def load_runtime_secrets(repo_root: str | Path, *, override: bool = True) -> None:
    """Load local .env values first, then overlay Streamlit secrets when available."""
    repo_root = Path(repo_root)
    load_dotenv(repo_root / ".env", override=False)

    try:
        import streamlit as st
    except Exception:
        return

    try:
        secrets = _flatten_secrets(dict(st.secrets))
    except Exception:
        return

    for key, value in secrets.items():
        if override or key not in os.environ:
            os.environ[key] = value
