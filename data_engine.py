"""
Resilient Data Engine: FRED Direct Macro + Yahoo Finance + Binance Futures
"""
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import io
from datetime import datetime, timezone

class ResilientDataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    def fetch_fred_series(self, series_id):
        """FRED üzerinden resmi faiz, reel getiri ve breakeven verilerini çeker (Ücretsiz/Resmi)."""
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

    def fetch_yahoo_series(self, symbol, period="90d", interval="1d"):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                df.index = df.index.tz_localize(None) if df.index.tz is not None else df.index
                return df, {"confidence": 1.0}
        except Exception as e:
            print(f"⚠️ Yahoo Hatası ({symbol}): {e}")
        return pd.DataFrame(), {"confidence": 0.0}

    def fetch_global_market_grid(self):
        """Piyasa varlıklarını ve FRED öncü makro serilerini toplar."""
        grid = {}
        meta = {}

        # 1. Yahoo Varlıkları
        yahoo_symbols = {
            "SPX": "^GSPC",
            "NQ": "QQQ",
            "XAU": "GC=F",
            "XAG": "SI=F",
            "BTC": "BTC-USD",
            "ETH": "ETH-USD",
            "OIL": "CL=F",      # Ham Petrol
            "IYT": "IYT",       # Taşımacılık & Küresel Ticaret
            "DXY": "UUP",       # Dolar Endeksi
            "USDJPY": "JPY=X",  # Yen Çapraz Kuru
            "HYG": "HYG",
            "LQD": "LQD",
            "COPPER": "HG=F",
            "VIX": "^VIX",
            "XME": "XME"
        }
        for key, sym in yahoo_symbols.items():
            df, m = self.fetch_yahoo_series(sym, period="90d", interval="1d")
            grid[key] = df
            meta[key] = m

        # 2. Resmi FRED Makro Serileri
        fred_keys = {
            "DFII10": "DFII10",         # 10Y TIPS Reel Getiri (Nasdaq Katili)
            "DGS10": "DGS10",           # 10Y Hazine Getirisi
            "DGS2": "DGS2",             # 2Y Hazine Getirisi (Fed Beklentisi)
            "T10YIE": "T10YIE",         # 10Y Breakeven Enflasyon Beklentisi
            "HY_OAS": "BAMLH0A0HYM2"    # Yüksek Getirili Kredi Spreadi
        }
        for key, s_id in fred_keys.items():
            f_df = self.fetch_fred_series(s_id)
            if not f_df.empty:
                grid[key] = f_df
                meta[key] = {"confidence": 1.0}
            else:
                # FRED gecikirse Yahoo proxy fallback
                if key == "DFII10": grid[key] = grid.get("HYG", pd.DataFrame())
                elif key == "DGS10": grid[key], _ = self.fetch_yahoo_series("^TNX")
                elif key == "DGS2": grid[key], _ = self.fetch_yahoo_series("SHY")
                meta[key] = {"confidence": 0.6}

        return grid, meta
