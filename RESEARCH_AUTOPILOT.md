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
