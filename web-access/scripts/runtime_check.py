#!/usr/bin/env python3
"""Runtime helpers for the web-reader/web-access readable fallback."""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

sys.dont_write_bytecode = True

SKILL_DIR = Path(__file__).resolve().parents[1]
VENDOR_PYLIB = SKILL_DIR / "vendor" / "pylib"


def bootstrap_vendor_path() -> None:
    if VENDOR_PYLIB.exists() and str(VENDOR_PYLIB) not in sys.path:
        sys.path.insert(0, str(VENDOR_PYLIB))


def module_exists(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def ensure_fallback_environment() -> None:
    bootstrap_vendor_path()

    missing = [
        module_name
        for module_name in ("scrapling", "html2text")
        if not module_exists(module_name)
    ]
    if missing:
        formatted = ", ".join(f"`{name}`" for name in missing)
        raise RuntimeError(
            "Missing fallback dependencies "
            f"{formatted}. Run `bash scripts/init_env.sh`."
        )
    if not shutil.which("curl"):
        raise RuntimeError("Missing `curl`, which is required for the fallback route.")


def ensure_jina_environment() -> None:
    if not shutil.which("curl"):
        raise RuntimeError("Missing `curl`, which is required for the Jina route.")
