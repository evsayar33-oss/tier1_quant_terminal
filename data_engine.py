"""
Resilient Data Engine: FRED Direct Macro + High-Speed Intraday 1H/4H Engine
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
        except Exception as e:
            print(f"⚠️ FRED çekim hatası ({series_id}): {e}")
        return pd.DataFrame()

    def fetch_binance_taker_ratio(self, symbol="BTCUSDT"):
        url = f"https://fapi.binance.com/futures/data/takerlongshortRatio?symbol={symbol}&period=15m&limit=30"
        try:
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    latest = data[-1]
                    ratio = float(latest["buySellRatio"])
                    return {"value": ratio, "confidence": 1.0}
        except Exception as e:
            print(f"⚠️ Binance API: {e}")
        return {"value": 1.0, "confidence": 0.4}

    def fetch_yahoo_single(self, key, symbol, period="7d", interval="1h"):
        """Tekil sembolü belirtilen zaman diliminde çeker."""
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
        """Piyasa varlıklarını 1 saatlik ANLIK INTRADAY hızında paralel çeker."""
        grid_1h = {}
        grid_daily = {}

        symbols = {
            "SPX": "^GSPC",
            "NQ": "QQQ",
            "XAU": "GC=F",
            "XAG": "SI=F",
            "BTC": "BTC-USD",
            "ETH": "ETH-USD",
            "OIL": "CL=F",
            "IYT": "IYT",
            "DXY": "UUP",
            "USDJPY": "JPY=X",
            "HYG": "HYG",
            "LQD": "LQD",
            "COPPER": "HG=F",
            "VIX": "^VIX",
            "XME": "XME"
        }

        # ⚡ 1 SAATLİK ANLIK VERİLERİ 10 İŞ PARÇACIĞIYLA PARALEL ÇEK (0.8 Saniye)
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.fetch_yahoo_single, k, sym, "7d", "1h"): k for k, sym in symbols.items()}
            for f in concurrent.futures.as_completed(futures):
                k, df = f.result()
                grid_1h[k] = df

        # Günlük FRED Makro Serileri
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
