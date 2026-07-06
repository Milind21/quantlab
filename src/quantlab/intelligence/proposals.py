"""proposals — the human review gate + reversible config versioning.

A proposal is INERT until a human approves it. `approve` RE-VALIDATES against the frozen bounds
(defense in depth — never trusts the stored proposal), applies the change to the active config as
a new content-addressed version, and writes an audit record. `reject` and `rollback` fully revert.
This is the ONLY path by which the active config changes.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from ..config import parse_bounds, validate_proposal
from .schemas import ParamProposal


def _set_dotted(d: dict, dotted: str, value) -> None:
    parts = dotted.split(".")
    for p in parts[:-1]:
        d = d[p]
    d[parts[-1]] = value


def _pid(p: ParamProposal) -> str:
    return hashlib.sha256(f"{p.param}|{p.proposed}|{p.expires_at}|{p.rationale}".encode()).hexdigest()[:10]


class ProposalStore:
    """File-backed review queue. `active_config` is the live config the proposals target."""
    def __init__(self, root: str | Path, active_config: str | Path):
        self.root = Path(root)
        (self.root / "pending").mkdir(parents=True, exist_ok=True)
        (self.root / "processed").mkdir(parents=True, exist_ok=True)
        (self.root / "versions").mkdir(parents=True, exist_ok=True)
        self.active = Path(active_config)
        self.audit = self.root / "audit.jsonl"

    # --- queue ---
    def submit(self, p: ParamProposal) -> str:
        pid = _pid(p)
        (self.root / "pending" / f"{pid}.json").write_text(p.model_dump_json(indent=2))
        return pid

    def list_pending(self) -> list[tuple[str, ParamProposal]]:
        out = []
        for f in sorted((self.root / "pending").glob("*.json")):
            out.append((f.stem, ParamProposal(**json.loads(f.read_text()))))
        return out

    def _audit(self, rec: dict) -> None:
        rec["ts"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self.audit.open("a") as fh:
            fh.write(json.dumps(rec) + "\n")

    def _move_processed(self, pid: str, status: str, extra: dict) -> None:
        src = self.root / "pending" / f"{pid}.json"
        data = json.loads(src.read_text())
        data["_status"] = status
        data.update(extra)
        (self.root / "processed" / f"{pid}.json").write_text(json.dumps(data, indent=2))
        src.unlink()

    # --- human actions ---
    def approve(self, pid: str) -> dict:
        p = ParamProposal(**json.loads((self.root / "pending" / f"{pid}.json").read_text()))
        cfg = yaml.safe_load(self.active.read_text())
        bound = parse_bounds(cfg.get("tunable", {}))[p.param]
        # defense in depth: re-validate against CURRENT active value + bounds, ignore stored 'current'
        from ..config import Config, get_param
        live_current = float(get_param(Config(**cfg), p.param))
        ok, reason = validate_proposal(bound, live_current, p.proposed)
        if not ok:
            self._move_processed(pid, "rejected_invalid", {"reason": reason})
            self._audit({"action": "reject_invalid", "pid": pid, "reason": reason})
            return {"applied": False, "reason": reason}
        # snapshot current version, apply, save new version, repoint active
        prev_hash = hashlib.sha256(self.active.read_bytes()).hexdigest()[:10]
        (self.root / "versions" / f"{prev_hash}.yaml").write_text(self.active.read_text())
        _set_dotted(cfg, p.param, p.proposed)
        self.active.write_text(yaml.safe_dump(cfg, sort_keys=False))
        new_hash = hashlib.sha256(self.active.read_bytes()).hexdigest()[:10]
        self._move_processed(pid, "approved", {"prev_version": prev_hash, "new_version": new_hash})
        self._audit({"action": "approve", "pid": pid, "param": p.param,
                     "from": live_current, "to": p.proposed, "prev": prev_hash, "new": new_hash})
        return {"applied": True, "param": p.param, "from": live_current, "to": p.proposed,
                "prev_version": prev_hash, "new_version": new_hash}

    def reject(self, pid: str, reason: str = "human-rejected") -> dict:
        self._move_processed(pid, "rejected", {"reason": reason})
        self._audit({"action": "reject", "pid": pid, "reason": reason})
        return {"applied": False, "reason": reason}

    def available_versions(self) -> list[str]:
        return sorted(p.stem for p in (self.root / "versions").glob("*.yaml"))

    def rollback(self, version_hash: str) -> dict:
        vfile = self.root / "versions" / f"{version_hash}.yaml"
        if not vfile.exists():
            avail = self.available_versions()
            return {"rolled_back": False,
                    "error": f"no such version '{version_hash}' — pass a version hash (from an "
                             f"approve's prev_version), not a proposal id.",
                    "available_versions": avail}
        self.active.write_text(vfile.read_text())
        self._audit({"action": "rollback", "to_version": version_hash})
        return {"rolled_back": True, "to_version": version_hash}
