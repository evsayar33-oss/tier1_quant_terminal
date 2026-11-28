# V2.2: preregistered challenger research and math integrity

2026-11-28 — Research/PAPER only. No LIVE, order, ACCEPT, promotion, or performance guarantee.

## Correctness repairs
- Exact UTC inner joins replace outer joins with forward/backward price fill.
- Missing ratios are excluded rather than voted neutral; VIX term requires both series.
- Prior-only MAD with std fallback; zero-scale surprise is missing, not a clipped extreme.
- Clock-defined momentum/credit velocity uses exact endpoint; no shortened lookback.
- Short calibration is signed by forecast direction. Unsupported candidate thresholds leave baseline untouched. Early direction adjustment requires sufficient evidence and a confidence bound on the appropriate side.
- Exact next-hour open-to-open calibration; 1h and 4h non-overlap independently, expired missing windows excluded. Legacy evidence and score-derived state archived in memory, not used for new math. All earlier research ledgers retained.
- Duplicated SMH/QQQ and crypto funding/taker/NDL proxies are state-only. BTC/ETH price ratio is not market-cap dominance.
- Missing matrix/factor values fail closed; no fabricated normal observation.
- Closed-bar-only persistence; bounded 2,000 hourly rows retained, 200 production input rows unchanged.

## Fixed registry
Registry SHA256: `9989838e49aaaaeef0ffed36636d990b426fdcfa9867e21bd38f5bd04787a732`. 23 fixed candidates, six assets, 4/24/72h, independent forward ledger. Flow candidates apply to BTC/ETH only; native 30d samples when fresh. No result-driven tuning, no automatic promotion. All exact labels, missing, neutral and active candidates recorded. Each horizon uses chronological non-overlapping windows reserved before signal/outcome; report same-window long/short, momentum comparison, hypothetical 2/5/10 bps costs, chronological thirds. Descriptive only (not independent significance / verified fills). <100 active observations = INSUFFICIENT.

### Sources reviewed (ideas adapted, not copied verbatim)
- quant_superlab `247d2b0fc63fde6a95316ad24ae1d1e0fccbea41`: lab/rules.py (Donchian, Bollinger, volume, compression); lab/strategies/price_factors.py (residual momentum).
- eaverse `14d567c81ea9316c6fc728ea9208725ee7552039`: eaverse/early_flow.py (flow pressure/divergence; observed-volume proxy separately labeled).
- federal-incentive-radar `7da0f9627de28ed5824921207b534d394c1d2b36`: src/radar/sector_confluence.py (matched emsal/baseline comparison). Cross-market breadth/credit proxies are independent research hypotheses, not proof of flow.

### Rules

- `mom4_z05`: 4 elapsed hours, prior 48 hourly volatility, |z| >= .5
- `mom4_z10`: 4 elapsed hours, prior 48 hourly volatility, |z| >= 1
- `mom24_z05`: 24 elapsed hours, prior 48 hourly volatility, |z| >= .5
- `fade4_z10`: opposite of mom4_z10
- `trend_confirm`: 4h and 24h momentum agree
- `donchian20`: close outside prior 20 observed bars high/low
- `donchian48`: close outside prior 48 observed bars high/low
- `failed_break20`: high/low breaches prior 20 range but close returns inside
- `bollinger20`: close beyond prior 20-bar mean +/- 2 std
- `compression_break`: prior 20-bar volatility in bottom 25% of preceding 48; Donchian20
- `volume_break`: Donchian20 with volume >= 1.5x prior 20 median (positive volume only)
- `absorption_proxy`: volume >= 1.5x prior median, small body, close in outer quartile of range; not taker flow
- `rsi_revert`: prior 14 observed bar gains/losses; RSI <= 30 / >= 70
- `residual_trend`: 4h sum of hourly peer residuals, beta estimated from preceding 48 exact paired changes, |z| >= .5
- `residual_fade`: opposite of residual_trend
- `macro_proxy`: 3+ exact 4h pair votes, latest completed <=59min before asset bar time, >= 2/3 consensus; asset-specific signs
- `macro_contrarian`: opposite of macro_proxy
- `score_z035`: current aggregate score magnitude >= .35
- `score_z065`: current aggregate score magnitude >= .65
- `score_z100`: current aggregate score magnitude >= 1
- `equal_cluster`: equal weight of >=2 observed directional clusters, mean signed raw >= .35
- `flow_pressure`: BTC/ETH spot+linear fresh native sample imbalance agree at magnitude >= .08
- `flow_divergence`: same flow pressure opposed to last completed hourly price body

## Immediate exploratory test on pinned published state
Snapshot: state commit `5479d7b51ac3e5861522e908b7deec762b760fd5`, cutoff 2026-11-28 08:03 UTC. Existing 200-bar archive, not new prospective records. Legacy source volume may be missing; no volume imputation. No model-score or native flow reconstruction. Results diagnose pipelines only, not out-of-sample alpha.

| Asset | Input slots | Exact 4h | Exact 24h | Exact 72h |
|---|---:|---:|---:|---:|
| BTC | 198 | 48 | 8 | 2 |
| ETH | 198 | 48 | 8 | 2 |
| SPX | 195 | 40 | 7 | 3 |
| NQ | 195 | 40 | 7 | 3 |
| XAU | 195 | 41 | 7 | 3 |
| XAG | 194 | 40 | 7 | 3 |

All 17 price candidates below: active 4h windows summed across six assets (not independent across assets). Weighted descriptive gross mean, no comparison-based selection. Each asset is independently insufficient for proof.

| Candidate | Active asset-windows | Gross signed mean bps |
|---|---:|---:|
| mom4_z05 | 108 | -0.478 |
| mom4_z10 | 49 | -28.749 |
| mom24_z05 | 119 | -2.505 |
| fade4_z10 | 49 | 28.749 |
| trend_confirm | 60 | 3.698 |
| donchian20 | 27 | 49.612 |
| donchian48 | 12 | 90.850 |
| failed_break20 | 39 | 23.217 |
| bollinger20 | 46 | 2.972 |
| compression_break | 9 | 43.354 |
| volume_break | 16 | 25.007 |
| absorption_proxy | 6 | 51.008 |
| rsi_revert | 82 | -6.762 |
| residual_trend | 81 | 9.117 |
| residual_fade | 81 | -9.117 |
| macro_proxy | 0 | unavailable |
| macro_contrarian | 0 | unavailable |

Source file SHA256 (reproducibility):

- `BTC-USD.csv`: `787189cc4fbc24b3f049bd7aa1f01b90dae468025587e4b41703ccf85c328c6b`
- `DX-Y.NYB.csv`: `c3464a540b5656a0162ab6742b4bcfec47f449c23739792c7c4deec8420a7e5b`
- `ES_F.csv`: `7defd9c07cf06dfa88043ee57f8d92c48ab212df34a2b46ee1a080f78a435856`
- `ETH-USD.csv`: `e897756a80fd5f7be636035e9fe1af69a052a048cff1fe7160561a3609035903`
- `GC_F.csv`: `53cb237c18501fe9b02efc0b63aea7f8e1cbecbd5ab9693d5203c60a39753d1b`
- `HG_F.csv`: `e9f15188b48fb4aed766997398c4150112374a805d88d19269f3b6e55aab96d0`
- `HYG.csv`: `fde6bac856448644f780cc2d9df17e3bdb20c40aa4d7bb72b8dbfa421790849d`
- `LQD.csv`: `b26afa2440246c93d6df28662f6e5c8cf11d7ba0a92634bb7840d5e38563662f`
- `NQ_F.csv`: `978677220375ae7994b799242056fd41be32ddc7d7c10af34e6c8498061fa345`
- `QQQ.csv`: `f5bbda006f784a7afa95fd70d5dc78959fa59f3fd8e06f09d9e93d96d416d92d`
- `RSP.csv`: `e3a1047f74a1247af8b50f8b981138234063c507b7b881fc20fe5cbad2cf2432`
- `SHY.csv`: `d0bcd68a03802df4b40bad8f9a8fab9384c930ec2dba9f77df1c17d2fc77cf94`
- `SI_F.csv`: `bec879028c575ee39e7f43209041133a640e180fa71ff37314562a1b454475f8`
- `SMH.csv`: `15fb6e0eb1281da5e38257293924066613ff042696f152cca9de4dc451a45796`
- `SPY.csv`: `30b8fee9b9034a288e6e9b57b5e7112c926c9fa3e990fb4914196a96a81ff9ac`
- `TLT.csv`: `c4d0358f4d3347f2cee3b1c4267c44adc5e9eb2ec61aba2c88314381c539dea4`
- `XLF.csv`: `18f0eab840c1ae55c2838a5dbe20bd2193c82d2f441f696bd9dcceb7f50cbdcc`
- `XLP.csv`: `1a09194dd35ffc71f0da7d379b69961b47b451fe91dc0e3d94bab16381ad6dcb`
- `XLU.csv`: `7836760c1ade2824cee8e4799aa792eb638aedcedff650f5b7d00a24c550c076`
- `XLY.csv`: `1a5d71206072317712c1a8fb31e38234b7a593006243d3d41418d2fa2d6d203b`

## Operation and monitoring
Hourly tracker writes challenger_evidence.json, challenger_report.json and separate initial challenger_archive_report.json to state; module failure and coverage are monitored. Market closed distinct from missing. Latest per-rule availability and exact/pending/expired label counts remain visible. No new paid API or job; existing sample and OHLCV reused. The original 30-day and V2 frozen experiments are not overwritten.
