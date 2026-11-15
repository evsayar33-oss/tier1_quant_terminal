# Tier-1 Independent Prospective Audit

Read-only audit. No orders. No observed fills. No realized NAV or proven trading edge.
Signals are timestamped at FIRST audit observation, not the original bar timestamp.
Prices are observed prospectively by the audit; when no quote exists, the latest published 1h bar close is used as a LAGGED NON-EXECUTABLE PROXY, never a live fill.
Cost scenarios are hypothetical directional holding returns, NOT executable trade P&L.
The test compares with always-long on paired windows; p-values are unadjusted, correlated assets remain.
Neither a 30-day calendar window nor a significant directional result automatically authorizes trading.

Window: 2026-11-14T06:24:26+00:00 — 2026-12-14T06:24:26+00:00
As of: 2026-11-15T21:05:45.937541Z
Directional calls: 37; entry permitted: 0; without quote: 23
Independent price polls: 6; last: 2026-11-15T21:05:45.937541Z

| Horizon | Nonoverlap N | Model hit | Always long | Paired p (unadjusted) | Missing labels | Verdict |
|---|---:|---:|---:|---:|---:|---|
| 4h | 2 | 100.0% | 0.0% | 0.2500 | 0 | INSUFFICIENT |
| 24h | 2 | 50.0% | 50.0% | 0.7500 | 0 | INSUFFICIENT |

## Independent hourly reference price coverage

| Asset | Polls | Valid | Last source |
|---|---:|---:|---|
| SPX | 6 | 0 | UNAVAILABLE |
| NQ | 6 | 0 | UNAVAILABLE |
| XAU | 6 | 0 | UNAVAILABLE |
| XAG | 6 | 0 | UNAVAILABLE |
| BTC | 6 | 6 | YAHOO_HOURLY_DELAYED_NON_EXECUTABLE |
| ETH | 6 | 6 | YAHOO_HOURLY_DELAYED_NON_EXECUTABLE |

## Hypothetical all-in cost sensitivity (not net NAV)

These calculations use first-seen published prices, often lagged 1h bar proxies, and fixed round-trip costs. No fill, funding, borrow, or slippage verification.

| Horizon | 0 bps | 10 bps | 20 bps | 40 bps |
|---|---:|---:|---:|---:|
| 4h | +114.3 | +104.3 | +94.3 | +74.3 |
| 24h | +20.4 | +10.4 | +0.4 | -19.6 |

## Decision gate

BLOCKED: No realized trade P&L is produced by this audit. Independent samples and paired evidence are descriptive only.
Existing production entry gates, model weights, 30-day manifest, and research ledgers are untouched.
