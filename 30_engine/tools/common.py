"""Shared path helpers. KBRAG_ROOT env var overrides the project root
so tests can run against a temporary directory."""

import os
import sys
from pathlib import Path


def force_utf8_stdout():
    """Git hooks / legacy consoles default to cp1252 on Windows; Chinese
    error messages must never crash a gate script."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def project_root() -> Path:
    env = os.environ.get("KBRAG_ROOT")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent


def qa_dir() -> Path:
    return project_root() / "knowledge" / "qa"


def batches_dir() -> Path:
    return project_root() / "batches"
