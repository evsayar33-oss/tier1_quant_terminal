# 30-Day Evidence Research — Operational Guide

## What ships and what does not

This is an **independent research add-on**, not a profitable strategy claim and
not a new trade-execution bot. The existing six-asset production decision
logic, stop parameters, GEX policy, weights, and `LOGIC_VERSION` are unchanged.
The pre-existing 2026-10-23 to 2026-11-23 evaluation is preserved.

Fix: `trade_plan._load` now casts textual CSV outcome/exit fields to object
and numeric ones to numeric, for BOTH champion and clone trade grading.

Research: BTC/ETH, spot and linear perpetuals, Bybit public bounded recent
trades (aggressor signed USDT notional for a **bounded sample**), plus book
depth/spread, OI and latest settled funding snapshots. Source, UTC time, trade
sample span, missing data and stale/error status are persisted. Order book
snapshots **cannot** prove passive absorption. Open-interest levels do **not**
reveal long/short intent. No fabricated CVD, footprint, liquidation levels,
market-maker positioning, dealer trade prints, or Tick/DOM data.

The dealer gamma, vanna, charm, 0DTE and shadow clone tests already exist.
They are intentionally not duplicated or re-weighted by this research add-on;
they have modeled dealer-position sign assumptions. Premium flow / options
transaction direction requires properly licensed transaction data. No
unverified video claim or arbitrary AI vote changes trading signals.

## Deploy and start (one-time)

1. Merge this PR into `main` after reviewing **Research 30D — Regression Tests**.
2. Open GitHub **Actions → Tier-1 30 Gün Kanıt Araştırması — Başlat / Kontrol**.
3. Press **Run workflow**, branch **main**, choose **action: start**.
4. A single launch run restores the live `state` branch, initializes a durable
   UTC 30-day manifest and invokes `engine_loop.py --once`. The existing
   hourly tracker collects subsequent observations. There is **no new
   always-running GitHub Actions job**, and no new required secret.
5. Verify `state/research_30d/manifest.json`,
   `state/research_30d/observations.csv`, and
   `state/research_30d/report.md`. Also check
   `state/health_report.md` for active errors.
6. A repeat **start** is idempotent: no resetting the clock or overwriting the
   experiment. **check** only inspects restored state, does not publish.
7. If the hourly engine is not running, repair/restart the existing
   `stateful_adaptive_tracker.yml` workflow; otherwise no samples accumulate.

The start time is the actual UTC initiation, not the PR merge timestamp. The
30-day end is fixed at UTC start plus 30 calendar days. After expiry, new
research observations stop; past rows are preserved. There is deliberately no
`reset` command. Preserve/backup the old state to start a new study.

## Experiment controls

- Preregistered question: can signed *sampled* spot aggressor notional beat a
  trivial always-up baseline on next observed 4h return?
- `research_30d_eval.py` chooses non-overlapping 4h observations; accepts
  future price from the 4–5h observation window only; refuses a stale label.
- The descriptive Wilson interval is *unadjusted*; the method is not proof of
  alpha. Gaps, selection bias, execution costs, effective sample size, crypto
  exchange differences, and many tested hypotheses require further analysis.
- Fewer than 100 forward non-overlapping observations per asset is flagged
  `INSUFFICIENT`. Even above 100, verdict is `DESCRIPTIVE_ONLY` and
  automatic promotion is forbidden.
- A continuous CVD and executable footprint/absorption model require a
  *persistent* feed with lossless deduplicated trades + book deltas and a
  separate infrastructure and data-cost decision; hourly GitHub Actions
  polling cannot legitimately reproduce that.
- For SPX/NQ futures depth and premium/option flow, exchange licensing and
  tick-level data are prerequisite; no simulated proxy or fabricated features.
- The "six AI agents" video idea is represented only by deterministic source
  validation, observational diagnostics and separate reviewer responsibilities.
  Production model arbitration is not altered.

## Failure / safety

- A failed data source writes `ERROR` or `PARTIAL`; it never inserts zero
  as if zero were an observed market value.
- Only restored `state` files are published; no automatic model promotion,
  new trades or historical state deletion.
- Publication shares the existing single-writer GitHub Actions concurrency
  group. This is necessary because `state_sync` uses an orphan force-push.
- The 30-day result is **conditional**: no source coverage, no independent
  sample, or insufficient statistical evidence → extend or reject the
  hypothesis, not optimize on noise.
- Workflow regression tests run on pull requests and can also be dispatched
  manually. Do not claim a successful live API test until an actual workflow
  run has succeeded.

## Acceptance criteria after merge

The launch workflow completes; live state includes the manifest and all
existing ledgers; the next hourly run adds 4 research records (2 assets × 2
markets, which may explicitly contain `ERROR`); trade grading no longer
throws string-to-float errors; the report exposes sample coverage and
candidate-vs-always-long diagnostic. If the exchange blocks public REST calls
from the runner, the research source remains unverified and must be repaired
before relying on its observation data.
