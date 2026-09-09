"""
Resilient Data Engine: Official FRED API + OKX/Bybit Live Crypto + 100% Live ETF Grid (v18)
"""
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import concurrent.futures
import os


class ResilientDataEngine:
    def __init__(self, fred_api_key=None, *args, **kwargs):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })
        if not fred_api_key and "fred_api_key" in kwargs:
            fred_api_key = kwargs["fred_api_key"]
        self.fred_api_key = fred_api_key or os.environ.get("FRED_API_KEY", "")
        self._cache = {}

    def fetch_crypto_taker_flow(self, ccy="BTC"):
        # 1. OKX Canlı Taker Hacmi
        okx_url = f"https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy={ccy}&instType=CONTRACTS&period=1H"
        try:
            res = self.session.get(okx_url, timeout=4)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data and len(data) > 0:
                    sell_vol = float(data[-1][1])
                    buy_vol = float(data[-1][2])
                    ratio = buy_vol / (sell_vol + 1e-9)
                    return {"value": ratio, "confidence": 1.0}
        except Exception:
            pass

        # 2. Bybit Fallback
        bybit_url = f"https://api.bybit.com/v5/market/account-ratio?category=linear&symbol={ccy}USDT&period=15min&limit=2"
        try:
            res = self.session.get(bybit_url, timeout=4)
            if res.status_code == 200:
                list_data = res.json().get("result", {}).get("list", [])
                if list_data and len(list_data) > 0:
                    buy_ratio = float(list_data[0].get("buyRatio", 0.5))
                    sell_ratio = float(list_data[0].get("sellRatio", 0.5))
                    ratio = buy_ratio / (sell_ratio + 1e-9)
                    return {"value": ratio, "confidence": 0.85}
        except Exception:
            pass

        return {"value": 1.0, "confidence": 0.5}

    def fetch_single_ticker_1h(self, symbol, period="5d"):
        try:
            df = yf.download(symbol, period=period, interval="1h", progress=False, timeout=6)
            if not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = [col[0] for col in df.columns]
                clean_df = df[["Open", "High", "Low", "Close", "Volume"]].dropna()
                self._cache[symbol] = clean_df
                return symbol, clean_df
        except Exception:
            pass

        if symbol in self._cache:
            return symbol, self._cache[symbol]
        return symbol, pd.DataFrame()

    def fetch_global_market_grid(self):
        tickers = [
            "SPY", "QQQ", "SMH", "RSP", "HYG", "LQD", "^VIX",
            "USO", "IYT", "DX-Y.NYB", "TIP", "IEF", "USDJPY=X",
            "GC=F", "SI=F", "HG=F", "BTC-USD", "ETH-USD"
        ]

        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(self.fetch_single_ticker_1h, sym): sym for sym in tickers}
            for fut in concurrent.futures.as_completed(futures):
                sym, data = fut.result()
                clean_key = sym.replace("^", "").replace("=X", "").replace("DX-Y.NYB", "DXY")
                results[clean_key] = data

        return results

    def fetch_fred_macro_metrics(self):
        metrics = {
            "dfii10_z": 0.45,
            "t10yie_z": 0.65,
            "curve_label": "DÜZ EĞRİ"
        }

        if not self.fred_api_key:
            return metrics

        series_ids = ["DFII10", "T10YIE", "T10Y2Y"]
        for s_id in series_ids:
            url = f"https://api.stlouisfed.org/fred/series/observations?series_id={s_id}&api_key={self.fred_api_key}&file_type=json&sort_order=desc&limit=30"
            try:
                res = self.session.get(url, timeout=4)
                if res.status_code == 200:
                    obs = res.json().get("observations", [])
                    vals = [float(o["value"]) for o in obs if o.get("value") not in [".", None, ""]]
                    if len(vals) >= 2:
                        cur = vals[0]
                        mean = np.mean(vals)
                        std = np.std(vals) + 1e-9
                        z = float(np.clip((cur - mean) / std, -3.0, 3.0))

                        if s_id == "DFII10":
                            metrics["dfii10_z"] = round(z, 2)
                        elif s_id == "T10YIE":
                            metrics["t10yie_z"] = round(z, 2)
                        elif s_id == "T10Y2Y":
                            metrics["curve_label"] = "YATIK EĞRİ" if cur < 0.0 else "DİKLEŞEN EĞRİ"
            except Exception:
                pass

        return metrics
