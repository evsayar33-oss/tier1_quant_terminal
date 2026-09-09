"""
Resilient Data Engine: Live High-Speed ETFs (No FRED Timeouts, Zero Zeroes!)
"""
import requests
import pandas as pd
import numpy as np
import yfinance as yf
import concurrent.futures

class ResilientDataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    def fetch_crypto_taker_flow(self, ccy="BTC"):
        # 1. OKX Kurumsal Taker Hacmi
        okx_url = f"https://www.okx.com/api/v5/rubik/stat/taker-volume?ccy={ccy}&instType=CONTRACTS&period=1H"
        try:
            res = self.session.get(okx_url, timeout=5)
            if res.status_code == 200:
                data = res.json().get("data", [])
                if data and len(data) > 0:
                    latest = data[-1]
                    sell_vol = float(latest[1])
                    buy_vol = float(latest[2])
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

        # 🛡️ FRED YERİNE CANLI İŞLEM GÖREN RESMİ ETF'LER BAĞLANDI (SIFIR TIMEOUT!)
        symbols = {
            "SPX": "SPY",       # S&P 500 ETF
            "NQ": "QQQ",        # Nasdaq 100 ETF
            "XAU": "GC=F",      # Altın
            "XAG": "SI=F",      # Gümüş
            "BTC": "BTC-USD",   # Bitcoin
            "ETH": "ETH-USD",   # Ethereum
            "RSP": "RSP",       # Eşit Ağırlıklı S&P
            "SMH": "SMH",       # Yarı İletken Çip ETF
            "OIL": "CL=F",      # Ham Petrol
            "IYT": "IYT",       # Taşımacılık / Ticaret
            "DXY": "UUP",       # Dolar Endeksi
            "USDJPY": "JPY=X",  # Yen Çapraz Kuru
            "HYG": "HYG",       # Yüksek Getirili Şirket Tahvili
            "LQD": "LQD",       # Sağlam Şirket Tahvili
            "COPPER": "HG=F",   # Bakır
            "VIX": "^VIX",      # VIX
            "XME": "XME",       # Madencilik Hisseleri
            "TIPS": "TIP",      # 🛡️ 10Y Reel Faiz ETF'si (DFII10 Yerine)
            "SHY": "SHY",       # 🛡️ 1-3Y Kısa Hazine Tahvili (2Y Faiz Yerine)
            "IEF": "IEF"        # 🛡️ 7-10Y Hazine Tahvili
        }

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(self.fetch_yahoo_single, k, sym, "7d", "1h"): k for k, sym in symbols.items()}
            for f in concurrent.futures.as_completed(futures):
                k, df = f.result()
                grid_1h[k] = df

        return grid_1h
