"""
Resilient Data Engine with Staleness & Fallback Hierarchy
"""
import requests
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timezone
from config import STALENESS_THRESHOLDS, SOURCE_TIER_CONFIDENCE

class ResilientDataEngine:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})

    def check_staleness(self, last_timestamp, freq="daily"):
        """Veri zaman damgasına göre tazelik ve güven çarpanı belirler."""
        if last_timestamp is None:
            return "KAYIP", 0.0
        
        now = datetime.now(timezone.utc)
        if last_timestamp.tzinfo is None:
            last_timestamp = last_timestamp.replace(tzinfo=timezone.utc)
            
        elapsed = (now - last_timestamp).total_seconds()
        max_allowed = STALENESS_THRESHOLDS.get(freq, 86400)

        if elapsed > (1.5 * max_allowed):
            return "BAYAT_VERİ", 0.5
        return "TAZE", 1.0

    def fetch_binance_taker_ratio(self, symbol="BTCUSDT"):
        """Binance Futures Taker Long/Short alım hacmi oranını çeker."""
        url = f"https://fapi.binance.com/futures/data/takerlongshortRatio?symbol={symbol}&period=15m&limit=30"
        try:
            res = self.session.get(url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    latest = data[-1]
                    ratio = float(latest["buySellRatio"])
                    ts = datetime.fromtimestamp(int(latest["timestamp"]) / 1000, tz=timezone.utc)
                    staleness_status, staleness_mult = self.check_staleness(ts, "intraday")
                    return {
                        "value": ratio,
                        "timestamp": ts,
                        "source_tier": "primary",
                        "confidence": SOURCE_TIER_CONFIDENCE["primary"] * staleness_mult,
                        "staleness": staleness_status
                    }
        except Exception as e:
            print(f"⚠️ Binance API uyarısı: {e}")
            
        # Fallback: Proxy Modu
        return {
            "value": 1.0,
            "timestamp": datetime.now(timezone.utc),
            "source_tier": "proxy",
            "confidence": SOURCE_TIER_CONFIDENCE["proxy"],
            "staleness": "PROXY_MODU"
        }

    def fetch_yahoo_series(self, symbol, period="60d", interval="1d"):
        """Yahoo Finance üzerinden veri çeker; hata durumunda güven çarpanını düşürür."""
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if not df.empty:
                last_ts = df.index[-1].to_pydatetime()
                freq = "intraday" if "m" in interval or "h" in interval else "daily"
                staleness_status, staleness_mult = self.check_staleness(last_ts, freq)
                return df, {
                    "source_tier": "primary",
                    "confidence": SOURCE_TIER_CONFIDENCE["primary"] * staleness_mult,
                    "staleness": staleness_status,
                    "timestamp": last_ts
                }
        except Exception as e:
            print(f"⚠️ Yahoo çekim hatası ({symbol}): {e}")

        # Boş seri ve sıfır güven
        return pd.DataFrame(), {
            "source_tier": "proxy",
            "confidence": 0.0,
            "staleness": "VERİ_YOK",
            "timestamp": None
        }

    def fetch_global_market_grid(self):
        """Tüm makro ve kredi gridini tek seferde toplar."""
        symbols = {
            "SPX": "^GSPC",
            "NQ": "QQQ",
            "XAU": "GC=F",
            "XAG": "SI=F",
            "BTC": "BTC-USD",
            "ETH": "ETH-USD",
            "VIX": "^VIX",
            "DXY": "UUP",
            "HYG": "HYG",
            "LQD": "LQD",
            "TNX": "^TNX",
            "COPPER": "HG=F",
            "TIPS": "TIP",
            "XME": "XME"
        }
        grid = {}
        meta = {}
        for key, sym in symbols.items():
            df, m = self.fetch_yahoo_series(sym, period="120d", interval="1d")
            grid[key] = df
            meta[key] = m
        return grid, meta
