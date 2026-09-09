"""
Tier-1 Adaptive Quant Terminal - Balanced Factor Weights (v14)
"""

CLUSTERS = {
    "A": "Dolar & Küresel Likidite (DXY)",
    "B": "Faiz & Reel Getiri (TIPS, 10Y)",
    "C": "Kredi & Volatilite (HYG/LQD, VIX)",
    "D": "Emtia & Enflasyon (Petrol/IYT, Bakır/Altın)",
    "E": "Varlığa Özel İtici Güç (Taker, Çip, Altın Beta, Genişlik)"
}

SIGNAL_THRESHOLDS = {
    "strong_buy_enter": 2.5,
    "strong_buy_exit": 1.5,
    "buy_enter": 1.0,
    "buy_exit": 0.4,
    "strong_sell_enter": -2.5,
    "strong_sell_exit": -1.5,
    "sell_enter": -1.0,
    "sell_exit": -0.4
}

ASSET_CLOCKS = {
    "SPX": {"market": "US_EQUITY", "open_utc": 13.5, "close_utc": 20.0, "days": [0, 1, 2, 3, 4]},
    "NQ":  {"market": "US_EQUITY", "open_utc": 13.5, "close_utc": 20.0, "days": [0, 1, 2, 3, 4]},
    "XAU": {"market": "METALS",    "open_utc": 7.0,  "close_utc": 21.0, "days": [0, 1, 2, 3, 4]},
    "XAG": {"market": "METALS",    "open_utc": 7.0,  "close_utc": 21.0, "days": [0, 1, 2, 3, 4]},
    "BTC": {"market": "CRYPTO",    "open_utc": 0.0,  "close_utc": 24.0, "days": [0, 1, 2, 3, 4, 5, 6]},
    "ETH": {"market": "CRYPTO",    "open_utc": 0.0,  "close_utc": 24.0, "days": [0, 1, 2, 3, 4, 5, 6]}
}

CATALYST_WINDOWS_UTC = [
    {"start": 12.5, "end": 13.5, "desc": "ABD Makro Veri Saati (TÜFE/İstihdam)"},
    {"start": 18.0, "end": 19.5, "desc": "Fed / FOMC Karar Saati"}
]

# 🛡️ SİMETRİK VE DENGELENMİŞ VARLIK MATRİSİ (UÇURUM KAPATILDI)
ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "SPY",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction",  "name": "SPY 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "market_breadth",   "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 1.4, "base_sign": 1},
            {"id": "credit_spread",    "name": "HYG/LQD Kredi Gücü", "cluster": "C", "base_weight": 1.8, "base_sign": 1},
            {"id": "vix_strain",       "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 1.6, "base_sign": -1},
            {"id": "stagflation_shock","name": "Petrol / Ticaret Şoku", "cluster": "D", "base_weight": 1.4, "base_sign": -1},
            {"id": "usd_strength",     "name": "Dolar Likidite Baskısı (DXY)", "cluster": "A", "base_weight": 1.4, "base_sign": -1},
            {"id": "real_yield",       "name": "10Y Reel Faiz Baskısı", "cluster": "B", "base_weight": 1.4, "base_sign": -1}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "vol_scale": 1.2,
        "factors": [
            {"id": "asset_direction",  "name": "QQQ 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "semi_lead",        "name": "SMH Çip Sektörü Liderliği", "cluster": "E", "base_weight": 1.8, "base_sign": 1},
            {"id": "credit_spread",    "name": "HYG/LQD Kredi Gücü", "cluster": "C", "base_weight": 1.6, "base_sign": 1},
            {"id": "vix_strain",       "name": "Teknoloji Volatilite Baskısı", "cluster": "C", "base_weight": 1.6, "base_sign": -1},
            {"id": "real_yield",       "name": "10Y Reel Faiz Baskısı", "cluster": "B", "base_weight": 1.8, "base_sign": -1},
            {"id": "stagflation_shock","name": "Petrol / Enerji Baskısı", "cluster": "D", "base_weight": 1.4, "base_sign": -1},
            {"id": "usd_strength",     "name": "DXY Dolar Likidite Sıkışması", "cluster": "A", "base_weight": 1.4, "base_sign": -1}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction",  "name": "Altın 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "real_yield",       "name": "10Y Reel Faiz (TIPS Ters Oran)", "cluster": "B", "base_weight": 2.2, "base_sign": -1},
            {"id": "breakeven_infl",   "name": "Enflasyon Beklenti Kalkanı", "cluster": "D", "base_weight": 1.8, "base_sign": 1},
            {"id": "usd_strength",     "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1},
            {"id": "safe_haven",       "name": "Jeopolitik & Güvenli Liman", "cluster": "C", "base_weight": 1.8, "base_sign": 1},
            {"id": "stagflation_shock","name": "Emtia / Petrol Desteği", "cluster": "D", "base_weight": 1.6, "base_sign": 1}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "vol_scale": 1.3,
        "factors": [
            {"id": "asset_direction",  "name": "Gümüş 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "gold_sympathy",    "name": "🥇 Altın Güç İvmesi (Gold Beta)", "cluster": "E", "base_weight": 2.5, "base_sign": 1},
            {"id": "gsr_velocity",     "name": "Altın/Gümüş Rasyosu (GSR)", "cluster": "E", "base_weight": 1.4, "base_sign": -1},
            {"id": "real_yield",       "name": "10Y Reel Faiz Baskısı", "cluster": "B", "base_weight": 1.8, "base_sign": -1},
            {"id": "usd_strength",     "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 1.6, "base_sign": -1},
            {"id": "copper_gold",      "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 1.2, "base_sign": 1}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "crypto_ccy": "BTC",
        "vol_scale": 1.8,
        "factors": [
            {"id": "crypto_taker",     "name": "⚡ OKX/Bybit Taker Alım Baskısı", "cluster": "E", "base_weight": 3.0, "base_sign": 1},
            {"id": "asset_direction",  "name": "BTC 4H Fiyat Hızı", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "eth_btc_beta",     "name": "ETH/BTC Risk İştahı", "cluster": "E", "base_weight": 1.6, "base_sign": 1},
            {"id": "usd_strength",     "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.6, "base_sign": -1},
            {"id": "credit_spread",    "name": "Küresel Risk İştahı (HYG/LQD)", "cluster": "C", "base_weight": 1.4, "base_sign": 1}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "crypto_ccy": "ETH",
        "vol_scale": 2.0,
        "factors": [
            {"id": "crypto_taker",     "name": "⚡ OKX/Bybit Taker Alım Baskısı", "cluster": "E", "base_weight": 3.0, "base_sign": 1},
            {"id": "asset_direction",  "name": "ETH 4H Fiyat Hızı", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "eth_btc_beta",     "name": "ETH/BTC Liderlik Gücü", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "btc_sympathy",     "name": "BTC Ana Trend Teyidi", "cluster": "E", "base_weight": 1.8, "base_sign": 1},
            {"id": "usd_strength",     "name": "DXY Küresel Dolar Baskısı", "cluster": "A", "base_weight": 1.6, "base_sign": -1}
        ]
    }
}

CRISIS_CONFIG = {
    "upper_threshold": 2.2,
    "lower_threshold": 1.5,
    "enter_consecutive_bars": 3,
    "vix_spike_threshold": 2.5,
    "vix_absolute_floor": 20.0
}
