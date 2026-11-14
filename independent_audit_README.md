# Independent 30-day prospective audit (non-production)

This is a separate observer for the **existing** experiment
`evidence-20261114T062426Z`, 2026-11-14 06:24:26 UTC to
2026-12-14 06:24:26 UTC. It **does not restart or alter** the original
30-day research, production signals, thresholds, positions or `state` branch.

## Start after merge

The `Tier-1 Independent 30D Audit — Read-only` workflow runs hourly
at UTC minute 22 (GitHub cron may be delayed). To start immediately, use
Actions → that workflow → Run workflow on **main**. Do this **once**.
Later hourly runs append new evidence automatically.

Evidence is persisted on `audit/30d-evidence` with ordinary commits
(no force push); `independent_audit/ledger.json`, `summary.json`, and
`report.md`. The workflow also publishes a run summary and 90-day artifact.
GitHub write permission must be enabled for Actions; failures are visible.

## Interpretation

* The auditor records the **first time it sees** a production publication.
  It does not claim to know the original signal availability if the
  production run or audit run was delayed. It does not backfill historical
  predictions. The initial audit can begin **after** the existing 30-day
  experiment began; the lost interval is explicitly not reconstructed.
* No direct executable quote is exposed by current `asset_verdicts`.
  The auditor therefore uses the most recently published 1-hour bar close
  from `performance_ledger.json` when its recording age is <=2 hours,
  labels this `lagged_1h_bar_proxy_NOT_EXECUTABLE`, and does **not**
  claim a live executable entry. If none exists, it records
  `UNPRICEABLE_ENTRY`. This is directional forecast validation only.
* A 4h/24h outcome is graded only from a price **first seen later by
  this audit** at the target time through +1h. Missing future prices
  remain missing, not silently counted as wins.
* Observations are de-overlapped per asset (not across correlated assets).
  Model vs always-long uses paired discordances; reported one-sided p
  values are unadjusted for asset dependence and multiple testing.
* 0/10/20/40 bps scenarios are **hypothetical holding-return sensitivity**,
  not executable transaction cost measurement. No realized fill, net NAV,
  risk-adjusted portfolio return, funding or leverage P&L is claimed.
* `entry_allowed` is tracked separately from raw BUY/SELL direction.
  A direction-only score is **not** an allowed-trade win rate.
* Minimum 30 independent observations is a **descriptive reporting
  threshold**, not a statistical proof. Manual review remains required.

## Integrity and operational boundaries

The separate audit branch retains ordinary Git commit history. It is
tamper-evident only to the extent that GitHub branch permissions protect
that branch; it is not cryptographically immutable. Do not delete or
force-push the audit branch. The `state` branch still uses its own
force-pushed state publishing, so this audit captures only snapshots
actually seen by the scheduled job.

Regression: `python -m unittest discover -s tests -p 'test_independent_audit.py' -v`.
This observer uses only the Python standard library. The PR CI runs
regressions; live prospective evidence starts **after merge and first
successful workflow run**, not when the PR is opened.

**Current limitations**: the original `performance_ledger.py` uses
bar timestamps and a potentially misleading proof label. This observer
does not rewrite historical statistics or alter those production reports.
Its independent results must be preferred for the 30-day prospective
claim. A genuine trade P&L / NAV system needs approved entry signals,
realistic venue-specific bid/ask and position/fill tracking; those data
are not present in the existing ledger.

## P0/P1 prospective price and outcome patch

The auditor now fetches six **independent hourly Yahoo reference series**
on every scheduled run, regardless of whether the production publication
changes. The mapping is SPX=^GSPC, NQ=^NDX, XAU=GC=F,
XAG=SI=F, BTC=BTC-USD, ETH=ETH-USD. Gold/silver are **futures proxies**,
not XAU/XAG executable spot quotes. Equity indices cannot be traded
directly. Weekend/closed-market/stale/failed prices are recorded as
missing; they are **not** forward-filled or silently synthesized.

The independent price snapshot is stored with the first-seen UTC
timestamp, source symbol and source bar UTC. Original evidence records
are retained on the same audit branch; no 30-day clock reset.
When a production signal is unchanged, hourly reference observations
continue. The 4h/24h horizon outcome remains PENDING until either a
valid snapshot in the predeclared [target,target+1h] window arrives,
or a 48h data grace period expires. Missing observations never become
fabricated fills. An ungradeable older outcome remains explicitly missing.

Reporting now includes per-asset source availability and a conservative
Bonferroni factor-12 p-value diagnostic. The paired p-values are
**not** proof of independence across related assets. Neither the
independent audit nor these proxy prices constitute an executable
profit-and-loss ledger, stop-loss/TP fill verification, or live approval.
