"""
Resilient Data Engine with Institutional Macro Shock Grid
"""
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone

class ResilientDataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

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

    def fetch_yahoo_series(self, symbol, period="60d", interval="1d"):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                return df, {"confidence": 1.0}
        except Exception as e:
            print(f"⚠️ Yahoo Hatası ({symbol}): {e}")
        return pd.DataFrame(), {"confidence": 0.0}

    def fetch_global_market_grid(self):
        """Tüm öncü makro şok göstergelerini tek seferde toplar."""
        symbols = {
            # Ana Varlıklar
            "SPX": "^GSPC",
            "NQ": "QQQ",
            "XAU": "GC=F",
            "XAG": "SI=F",
            "BTC": "BTC-USD",
            "ETH": "ETH-USD",
            # Öncü 1: Enflasyon & Stagflasyon Şoku
            "OIL": "CL=F",      # WTI Ham Petrol (Maliyet Enflasyonu)
            "IYT": "IYT",       # Dow Jones Ulaşım & Küresel Ticaret Navlun ETF'si
            # Öncü 2: Döviz & Carry Trade Çözülmesi
            "DXY": "UUP",       # Dolar Endeksi
            "USDJPY": "JPY=X",  # Japon Yeni Carry Trade Barometresi
            # Öncü 3: Kredi Temerrüt Riski
            "HYG": "HYG",       # Yüksek Getirili Çöp Şirket Tahvili
            "LQD": "LQD",       # Yatırım Yapılabilir Sağlam Şirket Tahvili
            # Öncü 4: Faiz & Getiri Eğrisi
            "TNX": "^TNX",      # 10 Yıllık Tahvil Faizi (İskonto Oranı)
            "SHY": "SHY",       # 1-3 Yıllık Kısa Tahvil (Fed Faiz Beklentisi / 2Y Proxy)
            "TIPS": "TIP",      # 10Y Reel Faiz Korumalı Tahvil
            # Öncü 5: Büyüme & Korku
            "COPPER": "HG=F",   # Bakır (Küresel Sanayi)
            "VIX": "^VIX",      # CBOE 30 Günlük Opsiyon Korku Primi
            "XME": "XME"        # Madencilik Hisseleri
        }
        grid = {}
        meta = {}
        for key, sym in symbols.items():
            df, m = self.fetch_yahoo_series(sym, period="90d", interval="1d")
            grid[key] = df
            meta[key] = m
        return grid, meta
