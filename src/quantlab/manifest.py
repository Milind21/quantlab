"""manifest — write a reproducibility manifest for a run.

A run is fully described by (git sha, config hash, package versions, timestamp). This is the
adapter boundary for run metadata; the pure core never calls it directly.
"""
from __future__ import annotations

import json
import subprocess
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from .config import Config, run_id

_TRACKED = ["pandas", "numpy", "pydantic", "pyyaml"]


def git_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True
        )
        return out.stdout.strip()
    except Exception:
        return "nogit"


def _versions() -> dict[str, str]:
    v = {}
    for p in _TRACKED:
        try:
            v[p] = version(p)
        except PackageNotFoundError:
            v[p] = "unknown"
    return v


def write_manifest(runs_root: str | Path, cfg: Config, ts: str, extra: dict[str, Any] | None = None) -> Path:
    """Create runs/<run_id>/manifest.json. `ts` passed in (no clock in core). Returns run dir."""
    sha = git_sha()
    rid = run_id(cfg, sha)
    run_dir = Path(runs_root) / rid
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": rid,
        "git_sha": sha,
        "timestamp": ts,
        "config": cfg.model_dump(exclude={"tunable"}),
        "config_hash": rid,  # run_id already content-addresses config+sha
        "package_versions": _versions(),
        **(extra or {}),
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    return run_dir
