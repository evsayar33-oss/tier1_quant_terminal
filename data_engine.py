"""
Resilient Data Engine: Live ETFs & Pre-Market Fallback Protection
"""
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import io
import concurrent.futures
from datetime import datetime, timezone

class ResilientDataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    def fetch_fred_series(self, series_id):
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
        try:
            res = self.session.get(url, timeout=8)
            if res.status_code == 200:
                df = pd.read_csv(io.StringIO(res.text), index_col=0, parse_dates=True)
                df.columns = ["Close"]
                df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
                df = df.dropna()
                if not df.empty:
                    df.index = df.index.tz_localize(None) if df.index.tz is not None else df.index
                    return df
        except Exception:
            pass
        return pd.DataFrame()

    def fetch_binance_taker_ratio(self, symbol="BTCUSDT"):
        url = f"https://fapi.binance.com/futures/data/takerlongshortRatio?symbol={symbol}&period=15m&limit=30"
        try:
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    return {"value": float(data[-1]["buySellRatio"]), "confidence": 1.0}
        except Exception:
            pass
        return {"value": 1.0, "confidence": 0.4}

    def fetch_yahoo_single(self, key, symbol, period="7d", interval="1h"):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                df.index = df.index.tz_localize(None) if df.index.tz is not None else df.index
                return key, df
        except Exception:
            pass
        return key, pd.DataFrame()

    def fetch_global_market_grid(self):
        grid_1h = {}
        grid_daily = {}

        # 🛡️ SPX için gecikmeli ^GSPC yerine canlı SPY ETF'si bağlandı
        symbols = {
            "SPX": "SPY",       # Canlı S&P 500 ETF'si
            "NQ": "QQQ",        # Canlı Nasdaq 100 ETF'si
            "XAU": "GC=F",      # Altın
            "XAG": "SI=F",      # Gümüş
            "BTC": "BTC-USD",
            "ETH": "ETH-USD",
            "OIL": "CL=F",      # Ham Petrol
            "IYT": "IYT",       # Küresel Ticaret/Taşımacılık
            "DXY": "UUP",       # Dolar
            "USDJPY": "JPY=X",  # Yen
            "HYG": "HYG",
            "LQD": "LQD",
            "COPPER": "HG=F",
            "VIX": "^VIX"
        }

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.fetch_yahoo_single, k, sym, "7d", "1h"): k for k, sym in symbols.items()}
            for f in concurrent.futures.as_completed(futures):
                k, df = f.result()
                grid_1h[k] = df

        fred_keys = {
            "DFII10": "DFII10",
            "DGS10": "DGS10",
            "DGS2": "DGS2",
            "T10YIE": "T10YIE"
        }
        for key, s_id in fred_keys.items():
            f_df = self.fetch_fred_series(s_id)
            grid_daily[key] = f_df if not f_df.empty else pd.DataFrame()

        return grid_1h, grid_daily
