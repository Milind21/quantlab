"""QuantLab — algo-trading harness + multi-agent market-intelligence layer (5DGAI capstone).

Pure ports-and-adapters: the core (config, manifest, future indicators/strategies/portfolio)
is side-effect-free; all I/O lives in adapters. The intelligence layer only PROPOSES
parameter changes within the bounds declared in configs/base.yaml `tunable:` — it never
touches the order path.
"""
__version__ = "0.1.0"
