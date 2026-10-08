"""
Copper lab data (v14) — free sources only, every value with the date it became PUBLIC
=====================================================================================
Yahoo (daily, max history):
  HG=F COMEX copper (USD/lb, front month)       GC=F gold, SI=F silver, CL=F oil
  DX-Y.NYB dollar index, AUDUSD=X, CNY=X        ^GSPC, ^VIX, ^TNX
  FXI China large caps (2004+), 000001.SS Shanghai composite, FCX Freeport, COPX copper miners (2010+)
  + HG=F hourly for the last ~730 days (intraday exploration only)
FRED (FRED_API_KEY): DFII10 real yield, T10YIE breakeven, DGS10, T10Y2Y, DTWEXBGS broad dollar, DEXCHUS USD/CNY,
  DEXUSAL USD/AUD, DGS3MO T-bill, BAMLH0A0HYM2 HY spread, NFCI (weekly, 5d lag), INDPRO (45d), CPIAUCSL (45d),
  PCOPPUSDM IMF copper price (monthly, 45d), CHNLOLITONOSTSAM / USALOLITONOSTSAM OECD leading indicators (60d)
CFTC Commitments of Traders, COMEX copper (code 085692): legacy (1986+) and disaggregated (2006+, managed money).
  Positions are as of Tuesday and published Friday after the close -> usable from the next Monday (avail = +6 days).
Bitget COPPERUSDT: contract spec, ticker, all available daily candles, funding-rate history (cost + basis check).

Output (--out): daily.csv.gz, hourly.csv.gz, fred.csv.gz, cot.csv.gz, bitget_copper.json, bitget_candles.csv
"""
from __future__ import annotations

import argparse
import json
import os
import time

import pandas as pd

DAILY = ["HG=F", "GC=F", "SI=F", "CL=F", "DX-Y.NYB", "AUDUSD=X", "CNY=X", "^GSPC", "^NDX", "^VIX", "^TNX",
         "FXI", "000001.SS", "FCX", "COPX"]
FRED = {"DFII10": 1, "T10YIE": 1, "DGS10": 1, "T10Y2Y": 1, "DTWEXBGS": 1, "DEXCHUS": 1, "DEXUSAL": 1, "DGS3MO": 1,
        "BAMLH0A0HYM2": 1, "NFCI": 5, "INDPRO": 45, "CPIAUCSL": 45, "PCOPPUSDM": 45,
        "CHNLOLITONOSTSAM": 60, "USALOLITONOSTSAM": 60}
COT_CODE = "085692"
BG = "https://api.bitget.com"


def _clean(df):
    if df is None or len(df) == 0:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    return df[[c for c in ("Open", "High", "Low", "Close") if c in df.columns]].dropna(how="all")


def yahoo(out):
    import yfinance as yf
    rep, parts = {}, []
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
    pd.concat(parts).to_csv(os.path.join(out, "daily.csv.gz"), index=False, compression="gzip", float_format="%.6g")
    try:
        h = _clean(yf.download("HG=F", period="730d", interval="1h", progress=False, auto_adjust=False, timeout=60))
        idx = pd.to_datetime(h.index)
        h.index = idx.tz_convert("UTC").tz_localize(None) if idx.tz is not None else idx
        h.reset_index(names="time").to_csv(os.path.join(out, "hourly.csv.gz"), index=False, compression="gzip")
        rep["HG=F 1h"] = len(h)
    except Exception as e:
        rep["HG=F 1h"] = f"hata: {e}"
    return rep


def fred(out, key):
    import requests
    rows, rep = [], {}
    for sid, lag in FRED.items():
        url = ("https://api.stlouisfed.org/fred/series/observations"
               f"?series_id={sid}&api_key={key}&file_type=json&observation_start=1990-01-01")
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
            rows.append((sid, d, float(v), d + pd.Timedelta(days=lag)))
            n += 1
        rep[sid] = n
        time.sleep(0.3)
    if rows:
        pd.DataFrame(rows, columns=["series", "date", "value", "avail"]).to_csv(
            os.path.join(out, "fred.csv.gz"), index=False, compression="gzip", float_format="%.6g")
    return rep


def cot(out):
    """CFTC public reporting (Socrata). Legacy: non-commercial = speculators; disaggregated: managed money."""
    import requests
    rows = []
    for ds, fields in (("6dca-aqww", {"noncomm_positions_long_all": "spec_long", "noncomm_positions_short_all": "spec_short",
                                       "comm_positions_long_all": "comm_long", "comm_positions_short_all": "comm_short",
                                       "open_interest_all": "oi"}),
                       ("72hh-3qpy", {"m_money_positions_long_all": "mm_long", "m_money_positions_short_all": "mm_short",
                                      "prod_merc_positions_long_all": "pm_long", "prod_merc_positions_short_all": "pm_short"})):
        url = f"https://publicreporting.cftc.gov/resource/{ds}.json"
        params = {"$where": f"cftc_contract_market_code='{COT_CODE}'", "$limit": "10000",
                  "$order": "report_date_as_yyyy_mm_dd"}
        try:
            r = requests.get(url, params=params, timeout=90)
            data = r.json() if r.status_code == 200 else []
        except Exception:
            data = []
        for o in data:
            d = pd.Timestamp(str(o.get("report_date_as_yyyy_mm_dd"))[:10])
            rec = {"date": d, "avail": d + pd.Timedelta(days=6)}
            for k, v in fields.items():
                try:
                    rec[v] = float(o.get(k))
                except (TypeError, ValueError):
                    rec[v] = None
            rows.append(rec)
    if not rows:
        return 0
    df = pd.DataFrame(rows).groupby(["date", "avail"], as_index=False).first()
    df.to_csv(os.path.join(out, "cot.csv.gz"), index=False, compression="gzip")
    return len(df)


def bitget(out):
    import requests
    info = {}
    g = lambda p, q: requests.get(BG + p, params=q, timeout=30).json().get("data")  # noqa: E731
    try:
        c = g("/api/v2/mix/market/contracts", {"productType": "USDT-FUTURES", "symbol": "COPPERUSDT"})
        info["contract"] = c[0] if c else None
        t = g("/api/v2/mix/market/ticker", {"productType": "USDT-FUTURES", "symbol": "COPPERUSDT"})
        info["ticker"] = t[0] if isinstance(t, list) and t else t
    except Exception as e:
        info["error"] = str(e)
    candles, end = [], None
    for _ in range(20):
        q = {"symbol": "COPPERUSDT", "productType": "USDT-FUTURES", "granularity": "1Dutc", "limit": "200"}
        if end:
            q["endTime"] = str(end)
        try:
            d = g("/api/v2/mix/market/history-candles", q) or []
        except Exception:
            d = []
        if not d:
            break
        candles += d
        end = int(min(int(x[0]) for x in d)) - 1
        time.sleep(0.2)
    if candles:
        cdf = pd.DataFrame([x[:6] for x in candles], columns=["ts", "open", "high", "low", "close", "vol"]).drop_duplicates("ts")
        cdf["date"] = pd.to_datetime(cdf.ts.astype("int64"), unit="ms").dt.normalize()
        cdf.sort_values("date").to_csv(os.path.join(out, "bitget_candles.csv"), index=False)
        info["candles"] = len(cdf)
    fund = []
    for page in range(1, 40):
        try:
            d = g("/api/v2/mix/market/history-fund-rate", {"symbol": "COPPERUSDT", "productType": "USDT-FUTURES",
                                                            "pageSize": "100", "pageNo": str(page)}) or []
        except Exception:
            d = []
        if not d:
            break
        fund += d
        time.sleep(0.2)
    info["funding"] = fund
    json.dump(info, open(os.path.join(out, "bitget_copper.json"), "w"), default=str)
    return {"candles": info.get("candles", 0), "funding": len(fund)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="copper_data")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    print("[bakır] Yahoo:", json.dumps(yahoo(a.out)), flush=True)
    key = os.environ.get("FRED_API_KEY", "").strip()
    print("[bakır] FRED:", json.dumps(fred(a.out, key)) if key else "anahtar yok", flush=True)
    print("[bakır] COT:", cot(a.out), flush=True)
    print("[bakır] Bitget:", json.dumps(bitget(a.out)), flush=True)


if __name__ == "__main__":
    main()
