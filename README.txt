TIER-1 Quant Terminal — Dynamic Entry Gate Update

ONLY FILE TO REPLACE:
- quant_processor.py

No other production file is changed.

Change scope:
- Replaces raw fixed ATR/RVOL entry veto thresholds with distribution-relative thresholds.
- Uses each asset's own recent 150-bar realized distribution.
- Current bar is excluded from both the RVOL baseline and the threshold distributions.
- Minimum adaptive history: 60 valid observations.
- Dynamic bands:
  - ATR low/high = P05/P95
  - RVOL illiquid = P05
  - RVOL strong-support = P70
  - RVOL climax = P99
- Gatekeeper compatibility thresholds are updated at runtime from the same dynamic profile, so its volume_supports/volatility_supports checks follow the current asset's distribution too.
- No change to data engine, model direction, pair coherence, macro engine, UI, background tracker, or asset matrices.
- No production synthetic data is introduced.

Validation performed:
- Python compile: PASS
- Existing V2.2 focused tests: PASS
- Existing comprehensive test suite: 9/9 PASS
- Dynamic entry behavior test: PASS
