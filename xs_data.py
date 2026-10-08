"""
Cross-sectional crypto perp data (v9.0) — every USDT-M perpetual, free, no key
==============================================================================
Source: Binance public archive (data.binance.vision), the same files Binance
publishes for researchers. Delisted contracts stay in the archive, so the
universe is SURVIVORSHIP-FREE (coins that died are in the test, as they were
for anyone trading at the time).

  * daily klines   data/futures/um/monthly/klines/{SYM}/1d/{SYM}-1d-{YYYY-MM}.zip
  * funding rates  data/futures/um/monthly/fundingRate/{SYM}/{SYM}-fundingRate-{YYYY-MM}.zip
  * symbol list    the archive's S3 listing (includes delisted symbols)

Output: xs_panel.csv.gz  (date, symbol, open, high, low, close, quote_volume, funding)
        funding = sum of that UTC day's funding rates (what a long paid / a short received)
Only COMPLETE months are used. Incremental: an existing panel is extended
with the months it does not have yet.

CLI: python xs_data.py --out xs_data/xs_panel.csv.gz [--start 2019-09] [--workers 24]
"""
from __future__ import annotations

import argparse
import io
import os
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import List, Optional

import numpy as np
import pandas as pd

BASE = "https://data.binance.vision/"
S3 = "https://s3-ap-northeast-1.amazonaws.com/data.binance.vision"
EXCLUDE = re.compile(r"^(USDC|BUSD|TUSD|FDUSD|USDP|DAI|EUR|GBP|AEUR|USDE|BTCDOM|DEFI|FOOTBALL|BLUEBIRD)USDT$")


def _get(url: str, params: Optional[dict] = None, timeout: int = 60) -> Optional[bytes]:
    import requests
    for _ in range(3):
        try:
            r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent": "tier1-quant-research"})
            if r.status_code == 200:
                return r.content
            if r.status_code == 404:
                return None
        except Exception:
            pass
    return None


def _list(prefix: str) -> List[str]:
    """Keys or sub-prefixes under an archive prefix (handles S3 pagination)."""
    out, marker = [], None
    while True:
        p = {"delimiter": "/", "prefix": prefix}
        if marker:
            p["marker"] = marker
        blob = _get(S3, p)
        if not blob:
            break
        txt = blob.decode("utf-8", "ignore")
        items = re.findall(r"<Prefix>([^<]+)</Prefix>", txt)[1:] + re.findall(r"<Key>([^<]+)</Key>", txt)
        out += items
        if "<IsTruncated>true</IsTruncated>" not in txt or not items:
            break
        marker = items[-1]
    return out


def symbols() -> List[str]:
    syms = [p.rstrip("/").split("/")[-1] for p in _list("data/futures/um/monthly/klines/")]
    return sorted(s for s in syms if s.endswith("USDT") and not EXCLUDE.match(s))


def _read(blob: bytes) -> Optional[pd.DataFrame]:
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            raw = z.read(z.namelist()[0]).decode("utf-8", "ignore")
        first = raw.split("\n", 1)[0]
        header = 0 if any(ch.isalpha() for ch in first) else None
        return pd.read_csv(io.StringIO(raw), header=header)
    except Exception:
        return None


def _klines(sym: str, months: List[str]) -> Optional[pd.DataFrame]:
    parts = []
    for m in months:
        b = _get(f"{BASE}data/futures/um/monthly/klines/{sym}/1d/{sym}-1d-{m}.zip")
        d = _read(b) if b else None
        if d is None or d.shape[1] < 8:
            continue
        d = d.iloc[:, [0, 1, 2, 3, 4, 7]]
        d.columns = ["open_time", "open", "high", "low", "close", "quote_volume"]
        parts.append(d)
    if not parts:
        return None
    k = pd.concat(parts, ignore_index=True)
    k["open_time"] = pd.to_numeric(k["open_time"], errors="coerce")
    k = k.dropna(subset=["open_time"])
    unit = "us" if k["open_time"].max() > 1e14 else "ms"
    k["date"] = pd.to_datetime(k["open_time"].astype("int64"), unit=unit, utc=True).dt.normalize()
    for c in ("open", "high", "low", "close", "quote_volume"):
        k[c] = pd.to_numeric(k[c], errors="coerce")
    return k.drop(columns="open_time").drop_duplicates("date", keep="last")


def _funding(sym: str, months: List[str]) -> Optional[pd.Series]:
    parts = []
    for m in months:
        b = _get(f"{BASE}data/futures/um/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip")
        d = _read(b) if b else None
        if d is None or d.shape[1] < 2:
            continue
        x = pd.DataFrame({"t": pd.to_numeric(d.iloc[:, 0], errors="coerce"),
                          "funding": pd.to_numeric(d.iloc[:, -1], errors="coerce")}).dropna()
        if x.empty:
            continue
        unit = "us" if x["t"].max() > 1e14 else "ms"
        x["date"] = pd.to_datetime(x["t"].astype("int64"), unit=unit, utc=True).dt.normalize()
        parts.append(x[["date", "funding"]])
    if not parts:
        return None
    f = pd.concat(parts, ignore_index=True)
    return f.groupby("date")["funding"].sum()


def _months_available(sym: str, kind: str) -> List[str]:
    pre = (f"data/futures/um/monthly/klines/{sym}/1d/" if kind == "k" else f"data/futures/um/monthly/fundingRate/{sym}/")
    keys = [k for k in _list(pre) if k.endswith(".zip")]
    return sorted({re.findall(r"(\d{4}-\d{2})\.zip$", k)[0] for k in keys if re.findall(r"(\d{4}-\d{2})\.zip$", k)})


def one_symbol(sym: str, after: Optional[str], last_full: str) -> Optional[pd.DataFrame]:
    mk = [m for m in _months_available(sym, "k") if (after is None or m > after) and m <= last_full]
    if not mk:
        return None
    k = _klines(sym, mk)
    if k is None or k.empty:
        return None
    mf = [m for m in _months_available(sym, "f") if m in set(mk)]
    f = _funding(sym, mf)
    k["funding"] = k["date"].map(f).fillna(0.0) if f is not None else 0.0
    k["symbol"] = sym
    return k


def build(out: str, start: str = "2019-09", workers: int = 24) -> pd.DataFrame:
    now = datetime.now(timezone.utc)
    last_full = (pd.Timestamp(now.year, now.month, 1) - pd.Timedelta(days=1)).strftime("%Y-%m")
    old, after = None, None
    if os.path.exists(out):
        try:
            old = pd.read_csv(out, parse_dates=["date"])
            # re-download the newest stored month and everything after it
            newest = pd.to_datetime(old["date"], utc=True).max().strftime("%Y-%m")
            after = (pd.Timestamp(newest + "-01") - pd.Timedelta(days=1)).strftime("%Y-%m")
            old = old[pd.to_datetime(old["date"], utc=True).dt.strftime("%Y-%m") <= after]
        except Exception:
            old, after = None, None
    syms = symbols()
    print(f"[xs] arşivde {len(syms)} USDT perp (kapanmış olanlar dahil) · son tam ay {last_full}", flush=True)
    a0 = after if after else (pd.Timestamp(start + "-01") - pd.Timedelta(days=1)).strftime("%Y-%m")
    with ThreadPoolExecutor(workers) as ex:
        parts = [p for p in ex.map(lambda s: one_symbol(s, a0, last_full), syms) if p is not None]
    new = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    P = pd.concat([old, new], ignore_index=True) if old is not None else new
    if P.empty:
        raise SystemExit("Binance arşivinden veri alınamadı")
    P["date"] = pd.to_datetime(P["date"], utc=True)
    P = P.drop_duplicates(["symbol", "date"], keep="last").sort_values(["date", "symbol"])
    P = P[["date", "symbol", "open", "high", "low", "close", "quote_volume", "funding"]]
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    P.to_csv(out, index=False, compression="gzip", float_format="%.8g")
    print(f"[xs] {len(P):,} satır · {P['symbol'].nunique()} sembol · {P['date'].min().date()} → {P['date'].max().date()}", flush=True)
    return P


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="xs_data/xs_panel.csv.gz")
    ap.add_argument("--start", default="2019-09")
    ap.add_argument("--workers", type=int, default=24)
    a = ap.parse_args()
    build(a.out, a.start, a.workers)


if __name__ == "__main__":
    main()
