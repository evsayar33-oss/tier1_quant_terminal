# Tier-1 Independent Prospective Audit

Read-only audit. No orders. No observed fills. No realized NAV or proven trading edge.
Signals are timestamped at FIRST audit observation, not the original bar timestamp.
Prices are observed prospectively by the audit; when no quote exists, the latest published 1h bar close is used as a LAGGED NON-EXECUTABLE PROXY, never a live fill.
Cost scenarios are hypothetical directional holding returns, NOT executable trade P&L.
The test compares with always-long on paired windows; p-values are unadjusted, correlated assets remain.
Neither a 30-day calendar window nor a significant directional result automatically authorizes trading.

Window: 2026-11-14T06:24:26+00:00 — 2026-12-14T06:24:26+00:00
As of: 2026-11-22T07:00:11.011657Z
Directional calls: 127; entry permitted: 0; without quote: 43
Independent price polls: 26; last: 2026-11-22T07:00:11.011657Z

| Horizon | Nonoverlap N | Model hit | Always long | Paired p (unadjusted) | Missing labels | Verdict |
|---|---:|---:|---:|---:|---:|---|
| 4h | 4 | 100.0% | 0.0% | 0.0625 | 64 | INSUFFICIENT |
| 24h | 12 | 83.3% | 16.7% | 0.0193 | 47 | INSUFFICIENT |

## Independent hourly reference price coverage

| Asset | Polls | Valid | Last source |
|---|---:|---:|---|
| SPX | 26 | 5 | UNAVAILABLE |
| NQ | 26 | 5 | UNAVAILABLE |
| XAU | 26 | 15 | UNAVAILABLE |
| XAG | 26 | 15 | UNAVAILABLE |
| BTC | 26 | 26 | YAHOO_HOURLY_DELAYED_NON_EXECUTABLE |
| ETH | 26 | 26 | YAHOO_HOURLY_DELAYED_NON_EXECUTABLE |

## Hypothetical all-in cost sensitivity (not net NAV)

These calculations use first-seen published prices, often lagged 1h bar proxies, and fixed round-trip costs. No fill, funding, borrow, or slippage verification.

| Horizon | 0 bps | 10 bps | 20 bps | 40 bps |
|---|---:|---:|---:|---:|
| 4h | +86.1 | +76.1 | +66.1 | +46.1 |
| 24h | +97.2 | +87.2 | +77.2 | +57.2 |

## Decision gate

BLOCKED: No realized trade P&L is produced by this audit. Independent samples and paired evidence are descriptive only.
Existing production entry gates, model weights, 30-day manifest, and research ledgers are untouched.
