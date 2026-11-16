# 30-day evidence observation report

- Experiment: `evidence-20261114T062426Z`
- Window (UTC): 2026-11-14T06:24:26+00:00 to 2026-12-14T06:24:26+00:00
- Status: COLLECTING
- Scope: observational only; production decisions unchanged
- Bybit is attempted first; OKX is tried on rejection, stale or insufficient samples
- Every row records its actual venue and instrument; notional conversions are contract-aware
- Important: bounded recent-trade samples are not continuous CVD, DOM, or a full footprint
- Orderbook data are isolated snapshots, not observed executions or proof of absorption
- OI and funding are historical published readings; do not assume same timestamp as trades
- No demonstrated forecast edge or profitability can be inferred from sample imbalance

| Asset | Market | Samples | Fresh valid samples | Latest source | Latest status |
|---|---|---:|---:|---|---|
| BTC | spot | 50 | 50 | okx | OK_SAMPLE |
| BTC | linear | 50 | 50 | okx | OK_SAMPLE |
| ETH | spot | 50 | 50 | okx | OK_SAMPLE |
| ETH | linear | 50 | 50 | okx | OK_SAMPLE |

## Six-asset production ledger coverage (same 30-day UTC window)

Counts are pipeline coverage only; forecasts overlap and counts are NOT independent samples.
Previously locked v2 experiment history remains unchanged and is not mixed with this window.

| Asset | Forecasts | Graded 4h/24h | Champion trades graded/total | Clone trades graded/total | Stop | Gamma | Shadow |
|---|---:|---:|---:|---:|---:|---:|---:|
| SPX | 49 | 44/24 | 0/1 | 0/1 | 54 | 49 | 49 |
| NQ | 49 | 44/24 | 0/0 | 0/0 | 54 | 49 | 49 |
| XAU | 49 | 44/24 | 1/1 | 1/1 | 47 | 0 | 49 |
| XAG | 49 | 44/24 | 0/0 | 0/0 | 7 | 0 | 49 |
| BTC | 49 | 44/24 | 0/0 | 0/0 | 71 | 49 | 49 |
| ETH | 49 | 44/24 | 0/0 | 0/0 | 30 | 49 | 49 |

## 4-hour prospective diagnostic (NOT trading edge)

Signals use sampled spot aggressor flow, non-overlapping 4h windows, and later observed reference prices.
The interval is unadjusted and cannot establish causal alpha.

| Asset | Non-overlap N | Hit | Always-long | Wilson 95% | Verdict |
|---|---:|---:|---:|---|---|
| BTC | 12 | 50.0% | 41.7% | 25.4% to 74.6% | INSUFFICIENT |
| ETH | 12 | 66.7% | 50.0% | 39.1% to 86.2% | INSUFFICIENT |

## Promotion criteria (not automatically executed)
1. Continuous trade capture with proven gap coverage, or discard a CVD hypothesis.
2. Point-in-time independent labels, non-overlapping windows and no lookahead.
3. Walk-forward split plus baseline, costs, slippage, and multiple-test adjustment.
4. At least 30 calendar days AND sufficient independent observations; extend otherwise.
5. Manual review before any direction, risk, or stop rule changes.
