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
| BTC | spot | 345 | 345 | okx | OK_SAMPLE |
| BTC | linear | 345 | 345 | okx | OK_SAMPLE |
| ETH | spot | 345 | 343 | okx | OK_SAMPLE |
| ETH | linear | 345 | 344 | okx | OK_SAMPLE |

## Six-asset production ledger coverage (same 30-day UTC window)

Counts are pipeline coverage only; forecasts overlap and counts are NOT independent samples.
Previously locked v2 experiment history remains unchanged and is not mixed with this window.

| Asset | Forecasts | Graded 4h/24h | Champion trades graded/total | Clone trades graded/total | Stop | Gamma | Shadow |
|---|---:|---:|---:|---:|---:|---:|---:|
| SPX | 338 | 320/300 | 1/1 | 1/1 | 466 | 332 | 344 |
| NQ | 338 | 320/300 | 0/0 | 0/0 | 467 | 332 | 344 |
| XAU | 338 | 320/300 | 9/9 | 9/9 | 429 | 0 | 344 |
| XAG | 338 | 320/300 | 0/0 | 0/0 | 145 | 0 | 344 |
| BTC | 344 | 333/313 | 0/0 | 0/0 | 326 | 342 | 344 |
| ETH | 344 | 333/313 | 0/0 | 0/0 | 156 | 342 | 344 |

## 4-hour prospective diagnostic (NOT trading edge)

Signals use sampled spot aggressor flow, non-overlapping 4h windows, and later observed reference prices.
The interval is unadjusted and cannot establish causal alpha.

| Asset | Non-overlap N | Hit | Always-long | Wilson 95% | Verdict |
|---|---:|---:|---:|---|---|
| BTC | 86 | 55.8% | 41.9% | 45.3% to 65.8% | INSUFFICIENT |
| ETH | 86 | 62.8% | 46.5% | 52.2% to 72.2% | INSUFFICIENT |

## Promotion criteria (not automatically executed)
1. Continuous trade capture with proven gap coverage, or discard a CVD hypothesis.
2. Point-in-time independent labels, non-overlapping windows and no lookahead.
3. Walk-forward split plus baseline, costs, slippage, and multiple-test adjustment.
4. At least 30 calendar days AND sufficient independent observations; extend otherwise.
5. Manual review before any direction, risk, or stop rule changes.
