"""config — pydantic config models + the FROZEN CONFIG INTERFACE (param bounds).

Pure module: no network, no clock, no I/O beyond reading a YAML file path given to it.
The `tunable:` block in base.yaml is parsed into PARAM_BOUNDS; `validate_proposal` is the
single enforcement point the intelligence layer's ParamProposal reuses, so bounds live in
ONE place and are enforced in code (not by LLM goodwill).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field


# ---- typed config sections ----
class Universe(BaseModel):
    source: str = "sp500"
    benchmark: str = "SPY"


class Costs(BaseModel):
    commission_per_share: float = 0.0
    slippage_bps: float = 5.0


class Risk(BaseModel):
    position_pct_cap: float = 0.05
    sector_pct_cap: float = 0.30
    max_positions: int = 20
    risk_per_trade: float = 0.005
    atr_stop_mult: float = 2.5
    kill_switch_dd: float = 0.20


class Regime(BaseModel):
    sma_window: int = 200
    band: float = 0.02
    exit_all: bool = False


class Backtest(BaseModel):
    start: str = "2010-01-01"
    fill: str = "next_open"


class Config(BaseModel):
    # extra='allow' captures per-strategy param blocks (e.g. `trend_following:`) so they are
    # preserved for signals() AND included in run_id (sweeping a threshold changes the run).
    model_config = ConfigDict(extra="allow")

    strategy: str = "trend_following"
    universe: Universe = Field(default_factory=Universe)
    costs: Costs = Field(default_factory=Costs)
    risk: Risk = Field(default_factory=Risk)
    regime: Regime = Field(default_factory=Regime)
    backtest: Backtest = Field(default_factory=Backtest)
    # raw bounds, kept out of the hashed payload's "values" but recorded
    tunable: dict[str, Any] = Field(default_factory=dict)


# ---- frozen config interface: bounds ----
@dataclass(frozen=True)
class Bound:
    param: str
    min: float
    max: float
    direction: Literal["any", "tighten_only"]


def parse_bounds(tunable: dict[str, Any]) -> dict[str, Bound]:
    out: dict[str, Bound] = {}
    for param, spec in (tunable or {}).items():
        out[param] = Bound(param, float(spec["min"]), float(spec["max"]), spec["direction"])
    return out


def load_config(path: str | Path) -> Config:
    raw = yaml.safe_load(Path(path).read_text())
    return Config(**raw)


def get_param(cfg: Config, dotted: str) -> Any:
    """Read a dotted param path like 'risk.atr_stop_mult' from a Config."""
    obj: Any = cfg
    for part in dotted.split("."):
        obj = getattr(obj, part)
    return obj


def validate_proposal(bound: Bound, current: float, proposed: float) -> tuple[bool, str]:
    """Single enforcement point for ParamProposal. Returns (ok, reason).

    - proposed must lie within [min, max]
    - direction 'tighten_only' (risk knobs): proposed must be MORE conservative than current,
      i.e. proposed <= current (lower cap / fewer positions / tighter ATR-stop multiple).
    - direction 'any': any value within bounds is allowed.
    """
    if not (bound.min <= proposed <= bound.max):
        return False, f"{bound.param}={proposed} outside [{bound.min}, {bound.max}]"
    if bound.direction == "tighten_only" and proposed > current:
        return False, (
            f"{bound.param} is tighten_only: proposed {proposed} loosens current {current} "
            "(risk knobs may only become more conservative)"
        )
    return True, "ok"


# ---- reproducibility: run_id ----
def _canonical(cfg: Config) -> str:
    # hash the VALUES only (exclude the static bounds block) so run_id tracks behavior
    payload = cfg.model_dump(exclude={"tunable"})
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def run_id(cfg: Config, git_sha: str) -> str:
    h = hashlib.sha256(f"{_canonical(cfg)}|{git_sha}".encode()).hexdigest()
    return h[:12]
