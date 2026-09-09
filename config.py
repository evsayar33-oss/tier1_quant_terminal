"""
Tier-1 Adaptive Quant Terminal - Asset Clocks, Event Windows & Elasticity (v9)
"""

CLUSTERS = {
    "A": "Dolar & Küresel Likidite (DXY)",
    "B": "Faiz & Reel Getiri (TIPS, 10Y)",
    "C": "Kredi & Volatilite (HYG/LQD, VIX)",
    "D": "Emtia & Enflasyon (Petrol/IYT, Bakır/Altın)",
    "E": "Varlığa Özel İtici Güç & Mikroyapı (Taker, Altın Beta, Çip Sektörü)"
}

# 🕒 VARLIK BAZLI SEANS VE ZAMAN TANIMLARI (UTC BAZLI)
# US Cash: 13:30 - 20:00 UTC (TSİ 16:30 - 23:00)
# London Metals: 08:00 - 16:30 UTC (TSİ 11:00 - 19:30)
ASSET_CLOCKS = {
    "SPX": {"market": "US_EQUITY", "open_utc": 13.5, "close_utc": 20.0, "days": [0, 1, 2, 3, 4]},
    "NQ":  {"market": "US_EQUITY", "open_utc": 13.5, "close_utc": 20.0, "days": [0, 1, 2, 3, 4]},
    "XAU": {"market": "METALS",    "open_utc": 7.0,  "close_utc": 21.0, "days": [0, 1, 2, 3, 4]},
    "XAG": {"market": "METALS",    "open_utc": 7.0,  "close_utc": 21.0, "days": [0, 1, 2, 3, 4]},
    "BTC": {"market": "CRYPTO",    "open_utc": 0.0,  "close_utc": 24.0, "days": [0, 1, 2, 3, 4, 5, 6]},
    "ETH": {"market": "CRYPTO",    "open_utc": 0.0,  "close_utc": 24.0, "days": [0, 1, 2, 3, 4, 5, 6]}
}

# ⚠️ KRİTİK HABER VE VERİ SAATİ PENCERELERİ (UTC)
# 12:30 - 13:30 UTC (TSİ 15:30 - 16:30): ABD TÜFE, ÜFE, İstihdam Verileri
# 18:00 - 19:30 UTC (TSİ 21:00 - 22:30): Fed FOMC Faiz Kararları
CATALYST_WINDOWS_UTC = [
    {"start": 12.5, "end": 13.5, "desc": "ABD Makro Veri Saati (TÜFE/İstihdam)"},
    {"start": 18.0, "end": 19.5, "desc": "Fed / FOMC Karar & Konuşma Saati"}
]

ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "SPY",
        "vol_scale": 1.0, # Standart oynaklık tabanı
        "factors": [
            {"id": "spx_mom", "name": "SPY 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "credit_spread", "name": "HYG/LQD Kredi Gücü", "cluster": "C", "base_weight": 2.2, "base_sign": 1},
            {"id": "vix_strain", "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 2.0, "base_sign": -1},
            {"id": "stagflation_shock", "name": "Petrol / Ticaret Şoku", "cluster": "D", "base_weight": 1.8, "base_sign": -1},
            {"id": "dxy_strain", "name": "Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.5, "base_sign": -1}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "vol_scale": 1.3, # Nasdaq daha oynaktır
        "factors": [
            {"id": "nq_mom", "name": "QQQ 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "semi_lead", "name": "SMH Yarı İletken (Çip) Öncülüğü", "cluster": "E", "base_weight": 2.5, "base_sign": 1},
            {"id": "vix_strain", "name": "VIX Korku Primi", "cluster": "C", "base_weight": 2.0, "base_sign": -1},
            {"id": "real_yield", "name": "10Y Reel Getiri (İskonto Baskısı)", "cluster": "B", "base_weight": 2.2, "base_sign": -1},
            {"id": "dxy_strain", "name": "Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.5, "base_sign": -1}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "vol_scale": 0.9,
        "factors": [
            {"id": "xau_mom", "name": "Altın 4H Anlık İvmesi", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "real_yield", "name": "10Y Reel Faiz (TIPS Ters Oran)", "cluster": "B", "base_weight": 2.5, "base_sign": -1},
            {"id": "stagflation_shock", "name": "Enflasyon / Petrol Kalkanı", "cluster": "D", "base_weight": 2.2, "base_sign": 1},
            {"id": "safe_haven", "name": "Jeopolitik & Kriz Sığınağı", "cluster": "C", "base_weight": 2.0, "base_sign": 1},
            {"id": "dxy_strain", "name": "Dolar Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "vol_scale": 1.6, # Gümüş altına göre 1.6x yüksek betadır
        "factors": [
            {"id": "xag_mom", "name": "Gümüş 4H Anlık İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "gold_sympathy", "name": "Altın Güç İvmesi (Gold Beta)", "cluster": "E", "base_weight": 3.0, "base_sign": 1},
            {"id": "real_yield", "name": "Reel Faiz Baskısı", "cluster": "B", "base_weight": 2.0, "base_sign": -1},
            {"id": "stagflation_shock", "name": "Emtia / Enflasyon Desteği", "cluster": "D", "base_weight": 1.8, "base_sign": 1},
            {"id": "dxy_strain", "name": "Dolar Baskısı", "cluster": "A", "base_weight": 1.5, "base_sign": -1}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "binance_symbol": "BTCUSDT",
        "vol_scale": 2.2, # Kripto oynaklık katsayısı
        "factors": [
            {"id": "taker_ratio", "name": "Binance Futures Taker Alım Baskısı", "cluster": "E", "base_weight": 3.5, "base_sign": 1},
            {"id": "btc_mom", "name": "BTC 4H Fiyat İvmesi", "cluster": "E", "base_weight": 2.5, "base_sign": 1},
            {"id": "eth_btc_beta", "name": "ETH/BTC Risk İştahı", "cluster": "E", "base_weight": 1.8, "base_sign": 1},
            {"id": "dxy_strain", "name": "Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.5, "base_sign": -1}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "binance_symbol": "ETHUSDT",
        "vol_scale": 2.5,
        "factors": [
            {"id": "taker_ratio", "name": "Binance Futures Taker Alım Baskısı", "cluster": "E", "base_weight": 3.5, "base_sign": 1},
            {"id": "eth_mom", "name": "ETH 4H Fiyat İvmesi", "cluster": "E", "base_weight": 2.5, "base_sign": 1},
            {"id": "eth_btc_beta", "name": "ETH/BTC Güç Oranı", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "dxy_strain", "name": "Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.5, "base_sign": -1}
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
