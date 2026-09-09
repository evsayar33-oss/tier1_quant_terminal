"""
Tier-1 Adaptive Quant Terminal - Standardized 3-Pillar Asset DNA & Hysteresis (v10)
"""

CLUSTERS = {
    "A": "Dolar & USD Gücü (DXY Strain)",
    "B": "Faiz & Reel Getiri (TIPS, 10Y)",
    "C": "Kredi & Sistemik Risk (HYG/LQD, VIX)",
    "D": "Emtia & Enflasyon (Petrol/IYT)",
    "E": "Varlığa Özel Yön & Likidite Akışı (Momentum, Hacim/Taker)"
}

# 🛡️ SİNYAL TİTREŞİMİNİ ÖNLEYEN HİSTEREZİS (ÖLÜ BANT) EŞİKLERİ
SIGNAL_THRESHOLDS = {
    "strong_buy_enter": 2.6,
    "strong_buy_exit": 1.8,
    "buy_enter": 1.2,
    "buy_exit": 0.5,        # 0.5'in altına inmedikçe AL sinyali NÖTR'e düşmez!
    "strong_sell_enter": -2.6,
    "strong_sell_exit": -1.8,
    "sell_enter": -1.2,
    "sell_exit": -0.5       # -0.5'in üstüne çıkmadıkça SAT sinyali NÖTR'e dönmez!
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
    {"start": 18.0, "end": 19.5, "desc": "Fed / FOMC Karar & Konuşma Saati"}
]

# 🎯 HER VARLIKTA 3 STANDART SÜTUN: YÖN + LİKİDİTE AKIŞI + USD GÜCÜ + MAKRO ÇAPA
ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "SPY",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction", "name": "SPX Anlık Yön İvmesi (4H/24H)", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "asset_liquidity", "name": "SPY Kurumsal Likidite & Hacim Akışı", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "usd_strength",    "name": "USD Gücü & DXY Likidite Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1},
            {"id": "credit_spread",   "name": "HYG/LQD Kredi Temerrüt Riski", "cluster": "C", "base_weight": 1.8, "base_sign": 1},
            {"id": "vix_strain",      "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 1.6, "base_sign": -1},
            {"id": "stagflation_shock","name": "Petrol / Ticaret Şoku", "cluster": "D", "base_weight": 1.4, "base_sign": -1}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "vol_scale": 1.2,
        "factors": [
            {"id": "asset_direction", "name": "NQ Anlık Yön İvmesi (4H/24H)", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "asset_liquidity", "name": "QQQ Kurumsal Likidite & Hacim Akışı", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "usd_strength",    "name": "USD Gücü & DXY Likidite Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1},
            {"id": "semi_lead",       "name": "SMH Çip Sektörü Öncülüğü", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "real_yield",      "name": "10Y Reel Getiri (İskonto Baskısı)", "cluster": "B", "base_weight": 1.8, "base_sign": -1},
            {"id": "vix_strain",      "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 1.6, "base_sign": -1}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "vol_scale": 0.9,
        "factors": [
            {"id": "asset_direction", "name": "Altın Anlık Yön İvmesi (4H/24H)", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "asset_liquidity", "name": "Altın Vadeli Hacim & Para Akışı", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "usd_strength",    "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 2.2, "base_sign": -1},
            {"id": "real_yield",      "name": "10Y Reel Getiri (TIPS Ters Oran)", "cluster": "B", "base_weight": 2.4, "base_sign": -1},
            {"id": "safe_haven",      "name": "Jeopolitik & Sistemik Sığınak", "cluster": "C", "base_weight": 1.8, "base_sign": 1},
            {"id": "stagflation_shock","name": "Enflasyon / Emtia Kalkanı", "cluster": "D", "base_weight": 1.6, "base_sign": 1}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "vol_scale": 1.5,
        "factors": [
            {"id": "asset_direction", "name": "Gümüş Anlık Yön İvmesi (4H/24H)", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "asset_liquidity", "name": "Gümüş Hacim & Para Akışı", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "usd_strength",    "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1},
            {"id": "gold_sympathy",   "name": "Altın İvmesi (Gold Beta Çarpanı)", "cluster": "E", "base_weight": 2.6, "base_sign": 1},
            {"id": "real_yield",      "name": "Reel Faiz Baskısı", "cluster": "B", "base_weight": 1.8, "base_sign": -1},
            {"id": "copper_gold",     "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 1.2, "base_sign": 1}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "binance_symbol": "BTCUSDT",
        "vol_scale": 2.0,
        "factors": [
            {"id": "asset_direction", "name": "BTC Anlık Fiyat İvmesi (4H/24H)", "cluster": "E", "base_weight": 2.5, "base_sign": 1},
            {"id": "asset_liquidity", "name": "Binance Futures Taker Alım Hacmi", "cluster": "E", "base_weight": 3.2, "base_sign": 1},
            {"id": "usd_strength",    "name": "USD Gücü & Küresel Dolar Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1},
            {"id": "eth_btc_beta",    "name": "ETH/BTC Risk İştahı Rasyosu", "cluster": "E", "base_weight": 1.6, "base_sign": 1},
            {"id": "credit_spread",   "name": "Küresel Kredi İştahı (HYG/LQD)", "cluster": "C", "base_weight": 1.4, "base_sign": 1}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "binance_symbol": "ETHUSDT",
        "vol_scale": 2.2,
        "factors": [
            {"id": "asset_direction", "name": "ETH Anlık Fiyat İvmesi (4H/24H)", "cluster": "E", "base_weight": 2.5, "base_sign": 1},
            {"id": "asset_liquidity", "name": "Binance Futures Taker Alım Hacmi", "cluster": "E", "base_weight": 3.2, "base_sign": 1},
            {"id": "usd_strength",    "name": "USD Gücü & Küresel Dolar Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1},
            {"id": "eth_btc_beta",    "name": "ETH/BTC Göreceli Güç Oranı", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "credit_spread",   "name": "Küresel Kredi İştahı", "cluster": "C", "base_weight": 1.4, "base_sign": 1}
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
