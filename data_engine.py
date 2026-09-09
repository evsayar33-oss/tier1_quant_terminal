"""
Resilient Data Engine: Official FRED API + OKX/Bybit Live Crypto + 100% Live ETF Grid
"""
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import concurrent.futures
import os

class ResilientDataEngine:
    def __init__(self, fred_api_key=None):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        self.fred_api_key = fred_api_key or os.environ.get("FRED_API_KEY", "")

    def fetch_crypto_taker_flow(self, ccy="BTC"):
        # 1. OKX Canlı Taker Hacmi
        okx_url = f"https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy={ccy}&instType=CONTRACTS&period=1H"
        try:
            res = self.session.get(okx_url, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data and len(data) > 0:
                    sell_vol = float(data[-1][1])
                    buy_vol = float(data[-1][2])
                    return {"value": buy_vol / (sell_vol + 1e-9), "confidence": 1.0}
        except Exception:
            pass

        # 2. Bybit Fallback
        bybit_url = f"https://api.bybit.com/v5/market/account-ratio?category=linear&symbol={ccy}USDT&period=15min&limit=2"
        try:
            res = self.session.get(bybit_url, timeout=5)
            if res.status_code == 200:
                data = res.json().get("result", {}).get("list", [])
                if data and len(data) > 0:
                    buy_r = float(data[0].get("buyRatio", 0.5))
                    sell_r = float(data[0].get("sellRatio", 0.5))
                    return {"value": buy_r / (sell_r + 1e-9), "confidence": 0.9}
        except Exception:
            pass

        return {"value": 1.0, "confidence": 0.5}

    def fetch_official_fred_data(self, series_id):
        """Resmi FRED API üzerinden kesin veri çeker (API Key ile sıfır hata)."""
        if not self.fred_api_key:
            return pd.DataFrame()
        url = f"https://api.stlouisfed.org/fred/series/observations?series_id={series_id}&api_key={self.fred_api_key}&file_type=json&sort_order=desc&limit=40"
        try:
            res = self.session.get(url, timeout=6)
            if res.status_code == 200:
                obs = res.json().get("observations", [])
                records = []
                for item in obs:
                    val_str = item.get("value", "")
                    if val_str not in [".", "", None]:
                        records.append({"Date": pd.to_datetime(item["date"]), "Close": float(val_str)})
                if records:
                    df = pd.DataFrame(records).sort_values("Date").set_index("Date")
                    return df
        except Exception as e:
            print(f"⚠️ FRED API Hatası ({series_id}): {e}")
        return pd.DataFrame()

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

        symbols = {
            "SPX": "SPY",       # S&P 500 ETF
            "NQ": "QQQ",        # Nasdaq 100 ETF
            "XAU": "GC=F",      # Altın Vadeli
            "XAG": "SI=F",      # Gümüş Vadeli
            "BTC": "BTC-USD",   # Bitcoin
            "ETH": "ETH-USD",   # Ethereum
            "RSP": "RSP",       # S&P Eşit Ağırlıklı
            "SMH": "SMH",       # Yarı İletken Çip ETF
            "OIL": "CL=F",      # Ham Petrol
            "IYT": "IYT",       # Taşımacılık / Küresel Ticaret
            "DXY": "UUP",       # Dolar Endeksi ETF
            "USDJPY": "JPY=X",  # Yen Çapraz Kuru
            "HYG": "HYG",       # Yüksek Getirili Şirket Tahvili
            "LQD": "LQD",       # Sağlam Şirket Tahvili
            "COPPER": "HG=F",   # Bakır
            "VIX": "^VIX",      # VIX
            "XME": "XME",       # Madencilik Hisseleri
            "TIPS": "TIP",      # 10Y Reel Faiz ETF
            "IEF": "IEF",       # 7-10Y Hazine Tahvili ETF
            "SHY": "SHY"        # 1-3Y Kısa Hazine Tahvili ETF
        }

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.fetch_yahoo_single, k, sym, "7d", "1h"): k for k, sym in symbols.items()}
            for f in concurrent.futures.as_completed(futures):
                k, df = f.result()
                grid_1h[k] = df

        # Resmi FRED API Çağrıları
        fred_keys = {"DFII10": "DFII10", "T10YIE": "T10YIE"}
        for k, s_id in fred_keys.items():
            f_df = self.fetch_official_fred_data(s_id)
            if not f_df.empty:
                grid_1h[k] = f_df

        return grid_1h
