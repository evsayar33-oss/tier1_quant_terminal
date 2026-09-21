# XAU-only signal correction

Scope: ONLY the XAU forecast signal is adjusted. No SPX, NQ, XAG, BTC, ETH, entry-gate, data-engine, config, macro, or UI production logic is changed.

Root cause:
- XAU has a larger/asymmetric factor stack and no one-way silver lead confirmation.
- XAG can reach an AL model state while XAU remains neutral even when GC=F and SI=F are moving closely together.
- Existing pair coherence harmonizes current-direction display but does not promote a neutral XAU forecast to AL.

Fix:
- In gatekeeper.py, after all assets are evaluated, a narrowly gated XAU-only silver-lead confirmation is applied.
- It triggers only when XAU is neutral, XAG is AL, real XAU/XAG price series are strongly correlated, the 8-bar price gap is small, the last-1H gap is small, XAU is not independently bearish, and silver is actually rising.
- XAG is never modified by this block.
- If XAU is bearish, it is never overridden.

Validation:
- Python compile: PASS
- Existing comprehensive suite: 9/9 PASS
- V2.2 tests: PASS
- Persistent OHLCV tests: PASS
- XAU-only regression tests: PASS
