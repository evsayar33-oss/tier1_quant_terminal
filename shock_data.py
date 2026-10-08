"""
Shock-lab data (v12.0) — 1990 → today, free sources only
========================================================
Yahoo Finance (daily OHLC, max history):
  ^GSPC (S&P 500), ^NDX (Nasdaq-100), ^VIX, ^VIX3M, ^VVIX, ^SKEW, DX-Y.NYB (dollar),
  ^TNX (10y yield), CL=F (oil), GC=F (gold), HYG, LQD, TLT, RSP, SPY
  + hourly ^GSPC / ^NDX / ^VIX for the last ~730 days (intraday entry timing)
FRED (needs FRED_API_KEY; every value gets an AVAILABILITY date = observation
date + publication lag, so the lab never uses a number before it was public):
  T10YIE breakeven inflation (lag 1d), DFII10 real yield (1d), DGS10, DGS2, DGS3MO,
  T10Y2Y curve (1d), BAMLH0A0HYM2 high-yield spread, BAMLC0A0CM IG spread (1d),
  FEDFUNDS (monthly, 1 month lag), NFCI financial conditions (weekly, 5d),
  STLFSI4 stress index (weekly, 7d), ICSA jobless claims (weekly, 5d),
  DTWEXBGS broad dollar (1d), VIXCLS (1d), CPIAUCSL (monthly, 45d)

Output (in --out): daily.csv.gz (date, symbol, Open, High, Low, Close),
hourly.csv.gz, fred.csv.gz (series, date, value, avail).
CLI: python shock_data.py --out shock_data
"""
from __future__ import annotations

import argparse
import json
import os
import time
from typing import Dict

import pandas as pd

DAILY = ["^GSPC", "^NDX", "^VIX", "^VIX3M", "^VVIX", "^SKEW", "DX-Y.NYB", "^TNX", "CL=F", "GC=F",
         "HYG", "LQD", "TLT", "RSP", "SPY"]
HOURLY = ["^GSPC", "^NDX", "^VIX"]
FRED = {  # series: publication lag in days
    "T10YIE": 1, "DFII10": 1, "DGS10": 1, "DGS2": 1, "DGS3MO": 1, "T10Y2Y": 1, "BAMLH0A0HYM2": 1,
    "BAMLC0A0CM": 1, "FEDFUNDS": 32, "NFCI": 5, "STLFSI4": 7, "ICSA": 5, "DTWEXBGS": 1, "VIXCLS": 1,
    "CPIAUCSL": 45,
}


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df[[c for c in ("Open", "High", "Low", "Close") if c in df.columns]].dropna(how="all")


def yahoo(out: str) -> Dict[str, int]:
    import yfinance as yf
    rep, parts, hparts = {}, [], []
    for s in DAILY:
        df = pd.DataFrame()
        for _ in range(3):
            try:
                df = _clean(yf.download(s, period="max", interval="1d", progress=False, auto_adjust=False, timeout=60))
            except Exception:
                df = pd.DataFrame()
            if len(df) > 100:
                break
            time.sleep(2)
        if len(df):
            df = df.copy()
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
            df["symbol"] = s
            parts.append(df.reset_index(names="date"))
        rep[s] = len(df)
        time.sleep(0.5)
    for s in HOURLY:
        try:
            df = _clean(yf.download(s, period="730d", interval="1h", progress=False, auto_adjust=False, timeout=60))
        except Exception:
            df = pd.DataFrame()
        if len(df):
            df = df.copy()
            idx = pd.to_datetime(df.index)
            df.index = idx.tz_convert("UTC").tz_localize(None) if idx.tz is not None else idx
            df["symbol"] = s
            hparts.append(df.reset_index(names="time"))
        rep[s + " 1h"] = len(df)
    if parts:
        pd.concat(parts).to_csv(os.path.join(out, "daily.csv.gz"), index=False, compression="gzip", float_format="%.6g")
    if hparts:
        pd.concat(hparts).to_csv(os.path.join(out, "hourly.csv.gz"), index=False, compression="gzip", float_format="%.6g")
    return rep


def fred(out: str, key: str) -> Dict[str, int]:
    import requests
    rows, rep = [], {}
    for sid, lag in FRED.items():
        url = ("https://api.stlouisfed.org/fred/series/observations"
               f"?series_id={sid}&api_key={key}&file_type=json&observation_start=1985-01-01")
        obs = []
        for _ in range(3):
            try:
                r = requests.get(url, timeout=60)
                if r.status_code == 200:
                    obs = r.json().get("observations", [])
                    break
            except Exception:
                pass
            time.sleep(2)
        n = 0
        for o in obs:
            v = o.get("value")
            if v in (None, ".", ""):
                continue
            d = pd.Timestamp(o["date"])
            # weekly series are dated at the START/END of the week depending on series -> lag counts from that date
            rows.append((sid, d, float(v), d + pd.Timedelta(days=lag)))
            n += 1
        rep[sid] = n
        time.sleep(0.3)
    if rows:
        pd.DataFrame(rows, columns=["series", "date", "value", "avail"]).to_csv(
            os.path.join(out, "fred.csv.gz"), index=False, compression="gzip", float_format="%.6g")
    return rep


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="shock_data")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    print("[shock] Yahoo:", json.dumps(yahoo(a.out)), flush=True)
    key = os.environ.get("FRED_API_KEY", "").strip()
    if key:
        print("[shock] FRED:", json.dumps(fred(a.out, key)), flush=True)
    else:
        print("[shock] FRED_API_KEY yok: temel (makro) filtreler eksik kalacak", flush=True)


if __name__ == "__main__":
    main()
