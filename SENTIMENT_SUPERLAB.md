# Tier-1 -> quant_superlab | 6-asset sentiment evidence bridge

## Scope and what is NEW

The system already uses VIX/VXN/GVZ/VXSLV volatility and regime factors.
This PR does **not** claim that the same signals became profitable or
that an external Fear & Greed index applies to gold, silver or equities.
It adds a *research-only* layer that logs future-observable evidence.

| Asset | New read-only observation | Meaning and caveat |
|---|---|---|
| BTC | Alternative.me daily 0–100 crypto Fear & Greed | Bitcoin-weighted crypto mood; observed with first-seen UTC |
| ETH | Same daily crypto Fear & Greed | Market context **not** an ETH-specific Fear & Greed score |
| SPX | VIX option implied-volatility percentile | Stress proxy; **not** CNN Fear & Greed |
| NQ | VXN implied-volatility percentile | Nasdaq risk stress proxy, not a direction signal |
| XAU | GVZ implied-volatility percentile | Gold ETF volatility context; not the gold spot sentiment |
| XAG | VXSLV implied-volatility percentile | Silver ETF volatility context; not spot silver sentiment |

For every asset it captures a confirmed 1-hour bar close, its actual first
observation timestamp, explicit source freshness, available volatility proxy,
the current macro-regime label, reported model direction, entry allowance,
and whether shock risk is present. Missing/future/stale/bar-still-open data
are **missing**, never converted to a fabricated zero. Volatility series
require >=20 real historical observations for a percentile. Failure to
fetch the free external API is visible; there is no paid service or token.

**Research only:** the new inputs do NOT affect `asset_verdicts`, the
production `LOGIC_VERSION`, live model thresholds, stops or executions.
Existing 30-day experiments and their frozen dates remain intact. The
current terminal has no production order broker, and this PR does not add one.

## Collection lifecycle

- Once this PR is merged into `main`, the existing hourly
  `Tier-1 Engine Loop` restores the `state` branch, then on its **first
  successful observation** creates `sentiment_30d/manifest.json` with a fresh
  UTC experiment ID, `start_utc` and fixed `end_utc = start + 30 days`.
  PR merge timestamp does not count as a start.
- State files `sentiment_30d/manifest.json`,
  `sentiment_30d/observations.csv` and `crypto_fng_cache.json` persist on
  the existing `state` branch and its bundle, via `state_sync.STATE_DIRS`.
  The main branch remains code-only.
- The collector records **exact first-seen time** (does not backdate to the
  start of the hour), one row per asset and hour. Price bars are allowed
  only after their hourly closing boundary; stale/reopened bar values are
  not accepted. It does not synthesize missing earlier hours.
- After 30 days, the locked sample window closes. For an additional
  **48-hour label grace**, only subsequent observed prices are recorded
  with `data_status=LABEL_ONLY`; no post-window features may enter
  the original study. Then collection stops. The study never resets.
- Hourly GitHub cron is best-effort and may miss runs. Run
  `Tier-1 Motoru Şimdi Yeniden Başlat (manuel)` only if the existing
  hourly engine stopped. Re-running does not reset the 30-day manifest.

## Automatic handoff after expiry

`.github/workflows/sentiment_superlab.yml` runs several times daily,
checking *the actual manifest* (not a guessed date). It runs a separate
CI suite on pull requests. On `main`, after `end_utc + 48h`:

1. Read original persisted prospective observations from `state`.
   **Ignore old `historical_replay`, `RESEARCH_LOG` performance figures
   and all previously acknowledged faulty strategy results.**
2. Download the public `evsayar33-oss/quant_superlab` repository
   at the then-current exact commit; record its SHA and source CSV hashes.
   Do not write or merge anything into `quant_superlab` automatically.
3. Run a pre-registered finite discovery grid: four sentiment
   extreme-based regimes per asset, for 0/20/40 bps *assumed* round-trip
   friction scenarios (72 total scenario cells). Results include
   hypothetical mean daily net bps, compounded daily hold return,
   exploratory Sharpe and max drawdown using **quant_superlab's own**
   `lab.metrics`. This is intentionally **not** production
   `lab.validation.GATE`.
4. Select the first available feature observation per UTC day. Assess the
   next 24h return only from a price **first observed at least 24h later**
   (up to +27h tolerance). No overlapping hourly duplicates of a daily
   Crypto Fear & Greed print are counted as independent evidence.
5. Gate is conservative: 30 days cannot provide the >=90 day
   train/holdout and ~3 years OOS required by a full Tier-1-style
   strategy approval. A 30-day result therefore reports
   `NEED_MORE_INDEPENDENT_PROSPECTIVE_DATA`, *not* a profitable strategy.
   With sufficiently long data a later separately reviewed research
   extension may use DSR/PBO/Reality Check/bootstrap/walk-forward.
6. Freeze the first results (trial-level CSV and JSON with source hashes
   and quant_superlab revision) on independent
   `audit/sentiment-superlab` branch via **ordinary Git commits**,
   not the force-pushed production state branch.
7. Reuse the existing Telegram outbox notifier, delivering a concise
   result with per-asset sample sizes and preserving delivery acknowledgements
   for retries. No live order, model update, registry approval or automatic PR
   merge is performed.

The work is intentionally **not** a general AI that invents a profitable
strategy from 30 days. It prepares trusted new inputs, runs auditable
pre-registered exploration and exposes the gate that future research must
pass. If you want model promotion after genuine new unseen OOS, that requires
an additional experiment and reviewed release policy.

## Tests and operation

The PR CI:
- compile-checks collector, research runner and existing tracker;
- tests first-seen timestamps, stale/unfinished bars, idempotence,
  frozen manifest, post-window-only labels, no future leakage and
  cross-experiment contamination;
- clones the actual public `quant_superlab` repository and runs a
  synthetic regression using its statistics (never live market data).

After merge, check:

- Actions > `Tier-1 Engine Loop` (one successful observation);
- `state/sentiment_30d/manifest.json` with an actual new UTC start/end;
- `state/sentiment_30d/observations.csv` for all six assets, source/error
  flags and valid prices. Empty or stale sources are **not success**.
- Actions > `Tier-1 30D Sentiment -> Quant Superlab (research only)`;
  it should be idle until the deadline (plus grace period), then publish
  `audit/sentiment-superlab/sentiment_study_decisions/` and Telegram.

For local testing:
```bash
pip install -r requirements.txt
python -m unittest discover -s tests -p 'test_sentiment30*.py' -v
```

## Limitations / safety

- CNN equity Fear & Greed is not silently scraped or guessed. Equity
  indices here are independently sourced IV risk proxies, not CNN scores.
- The Bitcoin-weighted F&G reading is **daily**; ETH market context
  does not represent ETH-specific positioning.
- VIX/VXN/GVZ/VXSLV can be absent, stale or unavailable. The collector
  flags this and still preserves missing data in the ledger.
- The future label depends on real later observed reference prices;
  historical and intraday fills, spread, leverage, financing, dividends
  and funding are NOT proven.
- Trial output is **hypothetical**, with fixed assumed costs.
  Tradeability/executable quotes must be separately evidenced.
- With one 30-day period, none of the six assets can be promoted as
  a validated *profitable* trading system. Better-looking ranking within
  a small data set is not a live trading edge.
- The bridge does not automatically open a second experiment or turn
  descriptive trials into a `quant_superlab` `ACCEPT` entry.
- GitHub Actions is best-effort; the actual job may run hours after
  expiry. No promise of exact-time execution.
