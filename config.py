"""
Configuration: Asset Matrices, Risk Clusters & Barra Normalization Weights (v20)
"""

CLUSTERS = {
    "A": "Dolar & Küresel Likidite (DXY)",
    "B": "Faiz & Getiri Eğrisi (TIPS, 10Y, 2Y)",
    "C": "Kredi & Volatilite (HYG/LQD, VIX)",
    "D": "Emtia & Enflasyon (Petrol/IYT, Bakır/Altın)",
    "E": "Varlığa Özel İtici Güç (Taker, Çip, Altın Beta, Genişlik)"
}

# Kalibre Edilmiş Sinyal Eşikleri (İkiz Varlık Uyumu & Aşırı Geniş Ölü Bant Düzeltmesi)
SIGNAL_THRESHOLDS = {
    "strong_buy_enter": 1.60,
    "strong_buy_exit": 1.00,
    "buy_enter": 0.60,
    "buy_exit": 0.20,
    "strong_sell_enter": -1.60,
    "strong_sell_exit": -1.00,
    "sell_enter": -0.60,
    "sell_exit": -0.20
}

ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "SPY",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction", "name": "SPY 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 1.35, "base_sign": 1.0},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 1.05, "base_sign": 1.0},
            {"id": "market_breadth", "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 1.20, "base_sign": 1.0},
            {"id": "credit_spread", "name": "HYG/LQD Kredi Gücü & İştahı", "cluster": "C", "base_weight": 1.10, "base_sign": 1.0},
            {"id": "vix_strain", "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 1.05, "base_sign": -1.0},
            {"id": "stagflation_shock", "name": "Petrol / Ticaret (IYT) Şoku", "cluster": "D", "base_weight": 0.95, "base_sign": -1.0},
            {"id": "usd_strength", "name": "Dolar Likidite Baskısı (DXY)", "cluster": "A", "base_weight": 0.95, "base_sign": -1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 0.90, "base_sign": -1.0}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "vol_scale": 1.2,
        "factors": [
            {"id": "asset_direction", "name": "QQQ 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 1.35, "base_sign": 1.0},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 1.35, "base_sign": 1.0},
            {"id": "market_breadth", "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 1.00, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Kredi Piyasası Gücü", "cluster": "C", "base_weight": 1.00, "base_sign": 1.0},
            {"id": "vix_strain", "name": "Teknoloji Volatilite Baskısı", "cluster": "C", "base_weight": 1.05, "base_sign": -1.0},
            {"id": "stagflation_shock", "name": "Petrol / Enerji Baskısı", "cluster": "D", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Sıkışması", "cluster": "A", "base_weight": 0.95, "base_sign": -1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 1.15, "base_sign": -1.0}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction", "name": "Altın 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 1.45, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz (TIPS Ters Oran)", "cluster": "B", "base_weight": 1.45, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 1.20, "base_sign": 1.0},
            {"id": "usd_strength", "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 1.20, "base_sign": -1.0},
            {"id": "safe_haven", "name": "Jeopolitik & Güvenli Liman", "cluster": "C", "base_weight": 1.20, "base_sign": 1.0},
            {"id": "stagflation_shock", "name": "Emtia / Petrol Desteği", "cluster": "D", "base_weight": 1.00, "base_sign": 1.0}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "vol_scale": 1.5,
        "factors": [
            {"id": "asset_direction", "name": "Gümüş 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 1.45, "base_sign": 1.0},
            {"id": "gold_sympathy", "name": "🥇 Altın Güç İvmesi (Gold Beta)", "cluster": "E", "base_weight": 1.45, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 1.15, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 1.05, "base_sign": 1.0},
            {"id": "usd_strength", "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 1.05, "base_sign": -1.0},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 1.05, "base_sign": 1.0}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "crypto_ccy": "BTC",
        "vol_scale": 2.0,
        "factors": [
            {"id": "asset_direction", "name": "BTC 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 1.35, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit Spot & Vadeli Taker Akışı", "cluster": "E", "base_weight": 1.45, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Küresel Likidite İştahı (HYG/LQD)", "cluster": "C", "base_weight": 1.15, "base_sign": 1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.15, "base_sign": -1.0},
            {"id": "real_yield", "name": "Reel Getiri Baskısı (TIP)", "cluster": "B", "base_weight": 0.95, "base_sign": -1.0},
            {"id": "vix_strain", "name": "Sistemik Volatilite Baskısı", "cluster": "C", "base_weight": 0.90, "base_sign": -1.0}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "crypto_ccy": "ETH",
        "vol_scale": 2.2,
        "factors": [
            {"id": "asset_direction", "name": "ETH 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 1.30, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit ETH Taker Alış Akışı", "cluster": "E", "base_weight": 1.35, "base_sign": 1.0},
            {"id": "btc_sympathy", "name": "⚡ Bitcoin İtici Gücü (BTC Beta)", "cluster": "E", "base_weight": 1.40, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Kurumsal Kredi & Likidite", "cluster": "C", "base_weight": 1.10, "base_sign": 1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.10, "base_sign": -1.0},
            {"id": "eth_btc_beta", "name": "ETH/BTC Göreceli Güç", "cluster": "E", "base_weight": 1.05, "base_sign": 1.0}
        ]
    }
}

ASSET_CLOCKS = {
    "SPX": {"open_utc": 13.5, "close_utc": 20.0, "type": "TRADITIONAL"},
    "NQ": {"open_utc": 13.5, "close_utc": 20.0, "type": "TRADITIONAL"},
    "XAU": {"open_utc": 0.0, "close_utc": 24.0, "type": "FUTURES_23H"},
    "XAG": {"open_utc": 0.0, "close_utc": 24.0, "type": "FUTURES_23H"},
    "BTC": {"open_utc": 0.0, "close_utc": 24.0, "type": "CRYPTO_24_7"},
    "ETH": {"open_utc": 0.0, "close_utc": 24.0, "type": "CRYPTO_24_7"}
}

CRISIS_CONFIG = {
    "vix_threshold": 30.0,
    "vix_absolute_floor": 20.0,
    "credit_spread_z_threshold": 2.5,
    "anomaly_threshold": 2.2,
    "lower_threshold": 1.4,
    "hysteresis_window": 3
}
