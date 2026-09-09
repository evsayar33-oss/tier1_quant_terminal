"""
Resilient Data Engine: OKX/Bybit Live Crypto Taker Flow + FRED Macro + Full Asset Grid
"""
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import io
import concurrent.futures

class ResilientDataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    def fetch_crypto_taker_flow(self, ccy="BTC"):
        """
        ⚡ OKX & BYBIT CANLI TAKER ALIM/SATIM MOTORU
        Binance'in bulut engellerine takılmaz; doğrudan açık REST uç noktalarından canlı çeker.
        """
        # 1. Öncelik: OKX Kurumsal Taker Hacmi
        okx_url = f"https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy={ccy}&instType=CONTRACTS&period=1H"
        try:
            res = self.session.get(okx_url, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data and len(data) > 0:
                    latest = data[-1]
                    # Format: [timestamp, sellVol, buyVol]
                    sell_vol = float(latest[1])
                    buy_vol = float(latest[2])
                    ratio = buy_vol / (sell_vol + 1e-9)
                    return {"value": ratio, "confidence": 1.0, "source": "OKX_FUTURES"}
        except Exception:
            pass

        # 2. Öncelik: Bybit Hesap Long/Short Rasyosu
        symbol = f"{ccy}USDT"
        bybit_url = f"https://api.bybit.com/v5/market/account-ratio?category=linear&symbol={symbol}&period=15min&limit=3"
        try:
            res = self.session.get(bybit_url, timeout=5)
            if res.status_code == 200:
                data = res.json().get("result", {}).get("list", [])
                if data and len(data) > 0:
                    latest = data[0]
                    buy_ratio = float(latest.get("buyRatio", 0.5))
                    sell_ratio = float(latest.get("sellRatio", 0.5))
                    ratio = buy_ratio / (sell_ratio + 1e-9)
                    return {"value": ratio, "confidence": 0.9, "source": "BYBIT_FUTURES"}
        except Exception:
            pass

        # 3. Fallback: Nötr
        return {"value": 1.0, "confidence": 0.5, "source": "NEUTRAL_FALLBACK"}

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

        symbols = {
            "SPX": "SPY",       # S&P 500 ETF
            "NQ": "QQQ",        # Nasdaq 100 ETF
            "XAU": "GC=F",      # Altın Vadeli
            "XAG": "SI=F",      # Gümüş Vadeli
            "BTC": "BTC-USD",   # Bitcoin
            "ETH": "ETH-USD",   # Ethereum
            "RSP": "RSP",       # S&P Eşit Ağırlıklı (Piyasa Genişliği)
            "SMH": "SMH",       # Yarı İletken Çip ETF (Tech Motoru)
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
