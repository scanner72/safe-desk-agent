"""Locate the repo root (examples / config) without secrets or network."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    env = os.environ.get("SAFE_DESK_ROOT")
    if env:
        return Path(env)
    here = Path(__file__).resolve()
    candidates = [Path.cwd(), *here.parents]
    for path in candidates:
        if (path / "examples" / "btc-ohlcv.csv").is_file():
            return path
    raise FileNotFoundError(
        "Cannot find examples/btc-ohlcv.csv. Set SAFE_DESK_ROOT or run from the repo."
    )


def default_csv() -> Path:
    return repo_root() / "examples" / "btc-ohlcv.csv"


def default_policy() -> Path:
    root = repo_root()
    for name in ("config/policy.yaml", "config/policy.example.yaml", "config/policy.example.json"):
        path = root / name
        if path.is_file():
            return path
    raise FileNotFoundError("No policy file under config/")


def static_dir() -> Path:
    return Path(__file__).resolve().parent / "static"
