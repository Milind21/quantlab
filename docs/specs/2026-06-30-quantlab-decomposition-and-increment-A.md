# QuantLab — Decomposition + Increment A spec

Capstone for the Google/Kaggle *5-Day GenAI: AI Agents Intensive* course. Full design (locked
decisions, strategy specs, phase ACs) lives in the owner's master plan — this doc is the
**build decomposition** and the **Increment A** spec. Decisions in the master plan §1 are
locked; do not relitigate.

## Context
A research-grade algorithmic-trading harness with a multi-agent market-intelligence layer.
Deterministic strategies (trend-following + mean-reversion) compared in one honest backtest;
a separate layer of LLM agents **proposes** strategy-parameter changes for human approval
only — **sentiment never places or sizes a trade; LLMs appear nowhere in the order path.**
Graded on *agent craft* (multi-agent orchestration, tools/API, memory, evaluation,
guardrails) → the intelligence layer is the centerpiece. Honest negative results
("doesn't beat SPY") are a success; this is a measurement harness, not a money printer.

Lives at `5dgai_capstone/` inside the kaggle_projects repo (sibling to F1PitStop/StellarS6E6).
Branch `milind_5dgai_capstone`; **never commit to main** (repo protocol). `uv`-managed, Python 3.11+.

## Build sequence (capstone-first, interface-anchored)
Each increment = its own spec → writing-plans → build → green-tests → commit cycle.

- **A — Scaffold + frozen config interface** (this spec). Master-plan Phase 0 + the config contract.
- **B — Honest thin core**: data → indicators → both strategies → minimal backtest + report.
  Master-plan Phases 1, 2, 3(min), 4(min). Gives the intel layer real strategies/params to target.
- **C ★ — Multi-agent intelligence layer** (capstone centerpiece): master-plan Phase 8 in full.
- **D — Backfill**: validation harness, live fundamental screen, Alpaca paper. Phases 5,6,7. Time-permitting.

The **frozen config interface** (built in A) is the contract `ParamProposal` (C) targets, so the
core (B) and the intelligence layer (C) develop independently against it without coupling.

## Increment A — scope

### Goal
A reproducible, `uv`-managed project skeleton with a pure ports-and-adapters layout, a pydantic
config system whose **tunable params carry hard bounds**, a run-manifest writer (run_id =
hash(config + git sha + package versions)), a CLI skeleton, and an import-purity guard. No
strategy/data/agent logic yet — just the spine everything hangs off.

### Deliverables
```
5dgai_capstone/
├── pyproject.toml            # uv; pinned: pandas numpy pydantic pyyaml matplotlib + dev: pytest ruff
├── .gitignore                # data/ runs/ .env .venv __pycache__ ...
├── .env.example              # ALPACA_* (paper), GOOGLE_API_KEY, REDDIT_* — all placeholders
├── .context                  # read-me-first orientation (mirrors F1PitStop/.context)
├── README.md                 # what/why, success definition, standing caveats
├── configs/
│   └── base.yaml             # universe, costs, risk, regime params + PARAM BOUNDS block
├── src/quantlab/
│   ├── __init__.py
│   ├── config.py             # pydantic models; load_config(); param-bounds registry; run_id hash
│   ├── manifest.py           # write_manifest(run_dir, config, extra) -> manifest.json
│   └── cli.py                # argparse/typer skeleton: backtest --dry-run, report, intel, proposals (stubs)
└── tests/
    ├── test_config.py        # bounds enforced; out-of-bounds value rejected; run_id deterministic & changes with config
    ├── test_manifest.py      # manifest has git sha, config hash, versions; reproducible
    └── test_import_purity.py  # core modules import no network/IO/clock libs
```

### The frozen config interface (the contract C depends on)
- `base.yaml` has a top-level `tunable:` block listing each adjustable knob with `{min, max,
  direction}` where `direction ∈ {any, tighten_only}` (risk knobs are tighten-only: e.g.
  position cap can only go DOWN, stops only tighter). Example knobs: `position_pct_cap`,
  `atr_stop_mult`, `max_positions`, `sector_pct_cap`, `regime_band`, per-strategy entry/exit thresholds.
- `config.py` exposes `PARAM_BOUNDS` (loaded from `tunable:`) and a `validate_proposal(param,
  current, proposed)` helper that Increment C's `ParamProposal` schema reuses — so bounds live
  in ONE place, enforced in code, not by LLM goodwill.
- Active config is versioned/reversible (a config is content-addressed by hash; applying a
  proposal writes a new version + an audit record). A's job is the bounds + hash + validate
  primitive; C builds the review-queue/apply/rollback on top.

### Acceptance criteria (Increment A)
- [ ] `uv run pytest` and `uv run ruff check` pass.
- [ ] `quantlab backtest --config configs/base.yaml --dry-run` writes
      `runs/<run_id>/manifest.json` with git sha, config hash, package versions (no strategy run yet).
- [ ] `run_id` is deterministic for a fixed (config, git sha) and changes when config changes.
- [ ] `validate_proposal` rejects out-of-bounds and wrong-direction (e.g. loosening a
      tighten_only risk knob) — unit-tested.
- [ ] Import-purity test: `quantlab.config`/`manifest` import no network/broker/clock modules.
- [ ] `.env` is gitignored; `.env.example` documents required keys; no secrets committed.

### Guardrails / hygiene (apply from the start)
- Secrets only in `.env`. No trade-capable MCP or live-order tools in the dev (Claude Code) session.
- Pure core: no `datetime.now()` / network / broker imports in `config`, `manifest`, future
  `indicators`/`strategies`/`portfolio`. Side effects live in adapters (added in B+).
- Learning-vehicle seam (owner goal): keep `LLMClient`, `DataProvider`, `Broker` as protocols
  so Gemini/Alpaca/(future Rust/Robinhood) impls swap in as ~1-file adapters.

### Out of scope for A
Any data fetch, indicator math, strategy logic, backtrader wiring, agents, or broker code —
those are Increments B/C/D. A is scaffold + config contract + manifest + CLI stubs only.
