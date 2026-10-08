"""
Alternative data (v7.0) — information the terminal did not have before
=======================================================================
1) Crypto derivatives (BTC, ETH) — Binance public data archive (free, no key):
   https://data.binance.vision/data/futures/um/daily/metrics/{SYM}/{SYM}-metrics-{YYYY-MM-DD}.zip
       5-minute open interest, top-trader long/short ratio, global long/short
       account ratio, taker buy/sell volume ratio
   https://data.binance.vision/data/futures/um/daily/premiumIndexKlines/{SYM}/1h/{SYM}-1h-{YYYY-MM-DD}.zip
       hourly perp premium over the index (basis; what drives funding)
   POINT-IN-TIME: a daily file is treated as known only 30h after its day
   starts (the archive publishes next day) -> a backtest can never use
   information earlier than the live bot could.

2) Positioning in futures (all 6 assets) — CFTC Commitments of Traders (free):
   https://www.cftc.gov/files/dea/history/fut_fin_txt_{YEAR}.zip     (S&P 500, Nasdaq, Bitcoin, Ether)
   https://www.cftc.gov/files/dea/history/fut_disagg_txt_{YEAR}.zip  (gold, silver)
   net position of leveraged funds / asset managers (financial) or managed
   money / producers (metals) as % of open interest, and its weekly change.
   POINT-IN-TIME: Tuesday positions are published Friday 15:30 ET -> known
   from Saturday 00:00 UTC.

Output: alt_panel.csv.gz  (asset, t = time the value became KNOWN, alt::* columns)
CLI:  python alt_data.py --out alt_panel.csv.gz [--days 760] [--years 4]
"""
from __future__ import annotations

import argparse
import io
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

VISION = "https://data.binance.vision/data/futures/um/daily"
CRYPTO = {"BTC": "BTCUSDT", "ETH": "ETHUSDT"}
DAILY_LAG = pd.Timedelta(hours=30)
COT_LAG = pd.Timedelta(days=4)                 # Tuesday 00:00 -> Saturday 00:00 UTC
COT_MARKETS = {                                 # (report, name must contain, name must NOT contain)
    "SPX": ("fin", "E-MINI S&P 500", ("MICRO", "ESG", "CONSUMER", "ENERGY", "FINANCIAL", "HEALTH", "TECHNOLOGY", "UTILITIES", "INDUSTRIAL", "MATERIALS", "REAL ESTATE", "STAPLES", "COMMUNICATION")),
    "NQ": ("fin", "NASDAQ", ("MICRO", "BIOTECH", "COMPOSITE")),
    "BTC": ("fin", "BITCOIN", ("MICRO", "NANO", "BITCOIN CASH")),
    "ETH": ("fin", "ETHER", ("MICRO", "NANO")),
    "XAU": ("disagg", "GOLD - COMMODITY EXCHANGE", ("MICRO", "E-MINI", "MINI")),
    "XAG": ("disagg", "SILVER - COMMODITY EXCHANGE", ("MICRO", "E-MINI", "MINI")),
}


def _get(url: str, timeout: int = 30) -> Optional[bytes]:
    import requests
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "tier1-quant-research"})
        return r.content if r.status_code == 200 and r.content else None
    except Exception:
        return None


def _read_zip_csv(blob: bytes, header="infer", names=None) -> Optional[pd.DataFrame]:
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            name = [n for n in z.namelist() if n.endswith((".csv", ".txt"))][0]
            return pd.read_csv(z.open(name), header=header, names=names, low_memory=False)
    except Exception:
        return None


# ------------------------------------------------------------------ crypto derivatives
def _one_day(sym: str, day: str) -> Optional[pd.DataFrame]:
    out = []
    m = _get(f"{VISION}/metrics/{sym}/{sym}-metrics-{day}.zip")
    if m:
        d = _read_zip_csv(m)
        if d is not None and "create_time" in d.columns:
            d["ts"] = pd.to_datetime(d["create_time"], utc=True)
            d = d.set_index("ts").sort_index()
            h = pd.DataFrame({
                "oi": d["sum_open_interest_value"].astype(float).resample("1h").last(),
                "top_ls": d["sum_toptrader_long_short_ratio"].astype(float).resample("1h").mean(),
                "acct_ls": d["count_long_short_ratio"].astype(float).resample("1h").mean(),
                "taker_ls": d["sum_taker_long_short_vol_ratio"].astype(float).resample("1h").mean(),
            })
            out.append(h)
    p = _get(f"{VISION}/premiumIndexKlines/{sym}/1h/{sym}-1h-{day}.zip")
    if p:
        d = _read_zip_csv(p)
        if d is not None and d.shape[1] >= 5:
            if "open_time" not in d.columns:           # older archive files have no header row
                d = _read_zip_csv(p, header=None)
            ot = d["open_time"] if "open_time" in d.columns else d.iloc[:, 0]
            cl = d["close"] if "close" in d.columns else d.iloc[:, 4]
            ts = pd.to_datetime(pd.to_numeric(ot, errors="coerce"), unit="ms", utc=True)
            out.append(pd.DataFrame({"premium": pd.to_numeric(cl, errors="coerce").values}, index=ts))
    if not out:
        return None
    df = pd.concat(out, axis=1)
    df["file_day"] = pd.Timestamp(day, tz="UTC")
    return df


def crypto_panel(days: int = 760, end: Optional[datetime] = None, workers: int = 8) -> pd.DataFrame:
    end = (end or datetime.now(timezone.utc)).date()
    day_list = [str(end - timedelta(days=k)) for k in range(1, days + 1)]
    rows = []
    for a, sym in CRYPTO.items():
        with ThreadPoolExecutor(workers) as ex:
            parts = [p for p in ex.map(lambda d: _one_day(sym, d), day_list) if p is not None]
        if not parts:
            print(f"[alt] {a}: Binance arşivine ulaşılamadı", flush=True)
            continue
        df = pd.concat(parts).sort_index()
        df = df[~df.index.duplicated(keep="last")]
        known = df["file_day"] + DAILY_LAG                         # when this row became public
        f = pd.DataFrame(index=df.index)
        f["alt::oi_chg_24h"] = np.log(df["oi"] / df["oi"].shift(24))
        f["alt::oi_chg_7d"] = np.log(df["oi"] / df["oi"].shift(168))
        f["alt::top_trader_ls"] = np.log(df["top_ls"])
        f["alt::account_ls"] = np.log(df["acct_ls"])
        f["alt::taker_buy_sell"] = np.log(df["taker_ls"]).rolling(24, min_periods=6).mean()
        f["alt::premium"] = df.get("premium")
        f["alt::premium_8h"] = df.get("premium", pd.Series(index=df.index, dtype=float)).rolling(8, min_periods=4).mean()
        f["t"] = known.values
        f["asset"] = a
        # one row per availability time (the whole day becomes known at once -> keep the day's last row)
        f = f.groupby("t").last().reset_index()
        f["asset"] = a
        rows.append(f)
        print(f"[alt] {a}: {len(parts)} gün türev verisi", flush=True)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


# ------------------------------------------------------------------ CFTC COT
def _col(df: pd.DataFrame, *keys) -> Optional[str]:
    for c in df.columns:
        cl = str(c).lower()
        if all(k.lower() in cl for k in keys):
            return c
    return None


def cot_panel(years: int = 4, end: Optional[datetime] = None) -> pd.DataFrame:
    end = end or datetime.now(timezone.utc)
    yrs = list(range(end.year - years + 1, end.year + 1))
    frames: Dict[str, List[pd.DataFrame]] = {"fin": [], "disagg": []}
    for kind, pat in (("fin", "fut_fin_txt_{y}.zip"), ("disagg", "fut_disagg_txt_{y}.zip")):
        for y in yrs:
            blob = _get("https://www.cftc.gov/files/dea/history/" + pat.format(y=y), timeout=60)
            d = _read_zip_csv(blob) if blob else None
            if d is not None:
                frames[kind].append(d)
    rows = []
    for a, (kind, must, mustnot) in COT_MARKETS.items():
        if not frames[kind]:
            continue
        d = pd.concat(frames[kind], ignore_index=True)
        name_c = _col(d, "market", "exchange") or d.columns[0]
        date_c = _col(d, "report_date_as_yyyy") or _col(d, "report_date")
        oi_c = _col(d, "open_interest_all")
        names = d[name_c].astype(str).str.upper()
        m = names.str.contains(must.upper(), regex=False)
        for bad in mustnot:
            m &= ~names.str.contains(bad.upper(), regex=False)
        x = d[m].copy()
        if x.empty or date_c is None or oi_c is None:
            print(f"[alt] {a}: COT piyasası bulunamadı", flush=True)
            continue
        x["date"] = pd.to_datetime(x[date_c], errors="coerce", utc=True)
        x["oi"] = pd.to_numeric(x[oi_c], errors="coerce")
        x = x.sort_values("oi").groupby("date").last()            # the main contract (largest OI) per week
        if kind == "fin":
            groups = {"lev": ("lev_money_positions_long", "lev_money_positions_short"),
                      "am": ("asset_mgr_positions_long", "asset_mgr_positions_short"),
                      "dealer": ("dealer_positions_long", "dealer_positions_short")}
        else:
            groups = {"mm": ("m_money_positions_long", "m_money_positions_short"),
                      "prod": ("prod_merc_positions_long", "prod_merc_positions_short"),
                      "swap": ("swap_positions_long", "swap__positions_short")}
        f = pd.DataFrame(index=x.index)
        for g, (lc, sc) in groups.items():
            lcol, scol = _col(x, lc), _col(x, sc) or _col(x, sc.replace("__", "_"))
            if lcol and scol:
                net = (pd.to_numeric(x[lcol], errors="coerce") - pd.to_numeric(x[scol], errors="coerce")) / x["oi"]
                f[f"alt::cot_{g}_net"] = net
                f[f"alt::cot_{g}_chg"] = net.diff()
        f["alt::cot_oi_chg"] = np.log(x["oi"] / x["oi"].shift(1))
        f["t"] = f.index + COT_LAG
        f["asset"] = a
        rows.append(f.reset_index(drop=True))
        print(f"[alt] {a}: {len(f)} hafta COT", flush=True)
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def build(days: int = 760, years: int = 4) -> pd.DataFrame:
    parts = [p for p in (crypto_panel(days), cot_panel(years)) if p is not None and len(p)]
    if not parts:
        return pd.DataFrame(columns=["asset", "t"])
    P = pd.concat(parts, ignore_index=True)
    P["t"] = pd.to_datetime(P["t"], utc=True)
    return P.sort_values(["asset", "t"]).reset_index(drop=True)


DEFAULT_PATHS = ("validation_reports/alt_panel.csv.gz", "alt_panel.csv.gz", "alt_recent.csv.gz")


def load(paths=DEFAULT_PATHS) -> Optional[pd.DataFrame]:
    parts = []
    for p in paths:
        if os.path.exists(p):
            try:
                d = pd.read_csv(p, low_memory=False)
                d["t"] = pd.to_datetime(d["t"], utc=True)
                parts.append(d)
            except Exception:
                pass
    if not parts:
        return None
    P = pd.concat(parts, ignore_index=True)
    return P.groupby(["asset", "t"], as_index=False).last().sort_values(["asset", "t"]).reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="alt_panel.csv.gz")
    ap.add_argument("--days", type=int, default=760)
    ap.add_argument("--years", type=int, default=4)
    a = ap.parse_args()
    P = build(a.days, a.years)
    P.to_csv(a.out, index=False, compression="gzip" if a.out.endswith(".gz") else None, float_format="%.6g")
    print(f"[alt] {len(P)} satır · {P['asset'].nunique() if len(P) else 0} varlık · "
          f"{len([c for c in P.columns if c.startswith('alt::')])} yeni sinyal → {a.out}", flush=True)


if __name__ == "__main__":
    main()
