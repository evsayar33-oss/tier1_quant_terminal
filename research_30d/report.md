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
| BTC | spot | 181 | 181 | okx | OK_SAMPLE |
| BTC | linear | 181 | 181 | okx | OK_SAMPLE |
| ETH | spot | 181 | 181 | okx | OK_SAMPLE |
| ETH | linear | 181 | 181 | okx | OK_SAMPLE |

## Six-asset production ledger coverage (same 30-day UTC window)

Counts are pipeline coverage only; forecasts overlap and counts are NOT independent samples.
Previously locked v2 experiment history remains unchanged and is not mixed with this window.

| Asset | Forecasts | Graded 4h/24h | Champion trades graded/total | Clone trades graded/total | Stop | Gamma | Shadow |
|---|---:|---:|---:|---:|---:|---:|---:|
| SPX | 180 | 155/135 | 1/1 | 1/1 | 245 | 180 | 180 |
| NQ | 180 | 155/135 | 0/0 | 0/0 | 246 | 180 | 180 |
| XAU | 180 | 155/135 | 6/6 | 6/6 | 237 | 0 | 180 |
| XAG | 180 | 155/135 | 0/0 | 0/0 | 64 | 0 | 180 |
| BTC | 180 | 175/155 | 0/0 | 0/0 | 269 | 179 | 180 |
| ETH | 180 | 175/155 | 0/0 | 0/0 | 100 | 179 | 180 |

## 4-hour prospective diagnostic (NOT trading edge)

Signals use sampled spot aggressor flow, non-overlapping 4h windows, and later observed reference prices.
The interval is unadjusted and cannot establish causal alpha.

| Asset | Non-overlap N | Hit | Always-long | Wilson 95% | Verdict |
|---|---:|---:|---:|---|---|
| BTC | 45 | 51.1% | 46.7% | 37.0% to 65.0% | INSUFFICIENT |
| ETH | 45 | 57.8% | 53.3% | 43.3% to 71.0% | INSUFFICIENT |

## Promotion criteria (not automatically executed)
1. Continuous trade capture with proven gap coverage, or discard a CVD hypothesis.
2. Point-in-time independent labels, non-overlapping windows and no lookahead.
3. Walk-forward split plus baseline, costs, slippage, and multiple-test adjustment.
4. At least 30 calendar days AND sufficient independent observations; extend otherwise.
5. Manual review before any direction, risk, or stop rule changes.
