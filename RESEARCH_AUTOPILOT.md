# Tier-1 expiration autopilot (research-only)

## What it does

GitHub Actions workflow **Tier-1 Study Expiry Autopilot (research only)** runs
every six hours and can be dispatched on main manually. When a pre-registered
study ends it writes `WINDOW_CLOSED_AWAITING_LABELS` and sends Telegram.
It does **not** invent final outcomes from incomplete lookahead windows.

After a fixed grade/publication grace interval it freezes a final JSON
decision, persists it to the separate `audit/study-decisions` branch using
ordinary (non-force) commits, and sends a second Telegram decision notice.
Notifications have explicit delivery acknowledgements; failures remain
pending for retries on later runs. Earlier decisions are **never reoptimized**
when new history or different reports appear.

## Currently supported and exact scope

| Study | Record boundary | Window close (UTC) | Final after grade grace |
|---|---|---|---|
| V2 champion forward evaluation | 2026-10-23 calendar day to 2026-11-23 inclusive; only logic `2026.10.23-v2` | 2026-11-24 00:00 | 2026-11-28 00:00 |
| BTC/ETH sampled-imbalance study | Exact existing `state/research_30d/manifest.json` | 2026-12-14 06:24:26 | 2026-12-16 06:24:26 |

The first study does not have a precise time-of-day inception recorded in
`PROJECT_STATUS.md`; the calendar-day bound is explicit, *not* a claim of exact
start time. Final decision uses rows matching the locked logic version.
The second manifest is never reset or modified. **Existing data collection,
state and production logic remain unchanged.**

Only valid outcomes from prospective raw `forecast_ledger.csv` are considered
for V2. The historical replay reports and old RESEARCH_LOG result tables are
deliberately ignored, because they are not trusted for this assessment.
Sampling is nonoverlapping per asset at a 4-hour horizon. Its descriptive
reference is always-long, one-sided paired discordance is Bonferroni-adjusted
for six assets, and at least 100 eligible 4h outcomes per asset are required
before a replication flag is possible. These are NOT independent executable
trade returns; no live conclusion follows.

The BTC/ETH study reads the original sample `observations.csv` bounded by
its actual manifest, requires >=100 nonoverlapping valid forward observations,
>=100 hourly spot source rows and >=80% fresh sample coverage per asset.
Its outcome remains descriptive: even with a positive observed difference it
becomes **INDEPENDENT_REPLICATION_NEEDED**, not ACCEPT or a live strategy.
Recorded order book / funding / spot samples are not continuous CVD.
The separate 30-day independent auditor is used as metadata only; delayed
market price proxies, missing fills and hypothetical cost sensitivity cannot
be interpreted as realized profit.

## Decision outputs / what 'apply' means

* `WINDOW_CLOSED_AWAITING_LABELS` -> close notification; existing study collector
  retains its own locked deadline, nothing is reset.
* `DATA_INSUFFICIENT` / `DATA_UNAVAILABLE` -> record missing evidence;
  no automatic candidate promotion. Missing required files block the final,
  rather than silently constructing a positive decision.
* `NO_DEMONSTRATED_ADVANTAGE` -> automatically mark this *research candidate*
  as unsupported in the audit decision record; no production changes.
* `REPLICATE_PROSPECTIVELY` /
  `INDEPENDENT_REPLICATION_NEEDED` -> automatically register it as
  a candidate for a **new, untouched** independent test; no live promotion.

The safety fields are always
`auto_applied=RESEARCH_STATUS_ONLY`,
`live_orders=false`, `production_logic_modified=false`.
The controller never writes to `state`, `main`, `reports`, or production
forecast/stop/entry/model files, and never authorizes live orders.

**Adding a new study is NOT automatic.** The study must have a
pre-registered immutable identity, start/end, source ledgers, proper
post-window labeling delay, and a matching evidence evaluator added in a
separate reviewed PR. This prevents guessing expiry or applying inappropriate
thresholds to unrelated experiments. No future test automatically becomes
a live trading rule.

## Operational requirements

1. Merge PR to `main`; check `Tier-1 Study Expiry Autopilot` Actions run.
2. Workflow runs PR offline tests without secrets; on main schedule/manual it
   fetches the existing `state` branch and `audit/30d-evidence`.
3. Write access to GitHub branches via `GITHUB_TOKEN` must be enabled.
   The workflow creates `audit/study-decisions` on first eligible decision.
4. Existing Actions secrets `TELEGRAM_TOKEN` and `CHAT_ID` must be available.
   On a missing/failed Telegram request the job fails and the notification
   remains pending (no fabricated success).
5. Read stable decisions in `audit/study-decisions/research_decisions/`.
   Before the first deadline, it is normal to have no decision branch.
6. GitHub cron is **best effort**, not exact time: GitHub may delay or omit
   scheduled runs. A manual `workflow_dispatch` on main is available.
   If frequent monitoring is crucial, set an external cron caller too,
   without creating a second writer to the audit branch.

Run tests offline:
`python -m unittest discover -s tests -p 'test_research_autopilot*.py' -v`

### Failure modes

The final decision freezes after the grace interval and after required inputs
exist. Late-arriving evidence cannot silently alter it; the correct response
to invalid data discovered later is a new explicit audit/correction record,
not retroactive edits. Published branch history is not immutable against
administrators or force-push; protect it with branch rules if desired.

Future recommendations for a live strategy require untouched OOS, actual
tradeability and net P&L after execution costs, explicit risk gates and an
independently reviewed production PR. A 30-day wall clock is never enough alone.


### 2026-11-28: V2 label-integrity correction

The frozen V2 FINAL remains byte-for-byte unchanged. Its source hashes and
nominal counts were reproduced from state commit
`591f6962ccce70e0f5bc1dc4c87038f92682dccf`. The legacy grader accepted the
first Close up to 72 hours after its nominal target and recorded no actual
endpoint timestamp. The selected sample includes 43 Saturday-start futures
forecasts (SPX 17, NQ 17, XAU 7, XAG 2); repeated identical weekend returns
are not independent four-hour outcomes. The separate immutable
`LABEL_INTEGRITY_AUDIT` records this limitation against the exact previous
FINAL hash, without claiming a corrected historical performance.

New four-hour forecast card records use `NEXT_HOUR_OPEN_TO_OPEN_V1`:
the precise observation time precedes the next hourly opening; five
contiguous hourly opening prices including the exact four-hour endpoint
are necessary. The endpoint bar must have completed before grading.
Missing intervals are not filled by a later opening. Actual reference
prices/timestamps and grading time are recorded. Only non-overlapping
strict labels enter the new four-hour scorecard; existing legacy grades
are not rewritten or counted as exact. These remain non-executable proxies.
The V2 study window, active model, 24h range calibration, trade gates,
and BTC/ETH sampled-flow study remain unchanged.

### 2026-11-28: Component scope and evidence fixes (v2.1)

The immutable V2 FINAL measures only the published **short-horizon evidence
side**, compared with always-long. It does not test the whole terminal or
the performance of its executable trading decisions. A second audit,
`docs/tier1_v2_forward_scope_audit.json`, pins the original final SHA and
the exact source state. The 4,512 forecast rows, 4,518 daily-direction rows
and 12 theoretical proposals (9 settled) do not establish either total
system failure or profitability. All day selections were baseline-long
(SPX/NQ/XAU) or neutral (BTC/ETH/XAG); no candidate tournament rule actually
won selection in that window.

The closed V2 result and all old grades are preserved. The production
logic label advances to `2026.11.28-v2.1-integrity` because data/qualification
bugs can affect the published direction. The following fixes do not tune
indicators against the old result or relax evidence thresholds:

- Only an explicitly ACTIVE learned model counts as proven; NO_MODEL
  cannot grant model entry. Last-four-hour momentum requires five exact
  consecutive completed hourly closes, fresh final bar, and hourly scale
  without overnight/missing-bar returns. Pair smoothing uses the same as-of.
- New 24h forecast/day-direction labels require the next strictly future
  hourly open and the exact open 24 hours later; no later price substitutions.
  Multi-day endpoint diagnostics may span session closures, but are not
  continuous trade paths. Closed/stale observations do not produce valid
  evidence. Old unverifiable range grades do not recalibrate new forecasts.
- Daily tournament selects from per-asset, nonoverlapping clock samples.
  The established minimum of 60 days and z threshold are retained per asset;
  paired superiority to always-long is additionally adjusted for the six
  candidates and six assets. Correlated asset-days are not counted as
  separate independent days. No cross-asset proof by default.
- New stop and theoretical trade labels require an actual prospective
  opening proxy inside the original bracket and complete OHLC path through
  settlement; a missing hourly bar is not a successful trade or a stop.
  Same-bar ambiguity is stop-first, later gap-through prices use open.
  Stop calibration uses exact full-horizon evidence for the same asset,
  never historical unverifiable or correlated pooled counts. Until there are
  30 nonoverlapping labels the buffer uses its original neutral multiplier.
  Routine futures session closures (the existing regular-session calendar)
  can be crossed at observed reopening prices; no missing bars during open
  hours or unverified holiday closures are imputed. If the exact endpoint
  does not exist, the label is unavailable, not falsely loss-scored.
- `component_evidence.json` and `component_research_report.json` are
  generated by the existing tracker cycle, bounded at 20,000 rows. The
  same clock-selected windows evaluate raw model and gate-filtered model
  at 4/24/72/120h, short side, daily side and each frozen daily candidate,
  simple momentum and its inverse, range, risk pulse and proposal direction.
  Neutral, missing, closed and pending slots are accounted for separately.
  The comparison with momentum uses the same active timestamps; results
  remain descriptive/non-executable (no costs or fills). There is no automatic
  winner selection or promotion from this report.
- Legacy performance reports are explicitly descriptive; the reported
  Wilson lower bound uses actual non-overlapping winners. Legacy shadow-v1
  p-values likewise cannot certify a finding; its original grades are
  preserved, and that old path is still not exact-label research. The existing
  BTC/ETH sampled-flow experiment's manifest, sample collection and expiry
  evaluator are unchanged.

This is a correction of evidence and safety logic, not a claim that V2
would have passed. New prospective evidence must be collected before
asserting superiority. No live orders; no automatic strategy promotion.
