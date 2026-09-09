"""
Configuration: Asset Matrices, Risk Clusters & Barra Normalization Weights (v23 Institutional Precision)
"""

CLUSTERS = {
    "A": "Dolar & Küresel Likidite (DXY)",
    "B": "Faiz, Getiri Eğrisi & Süre Riski (TIPS, 10Y, TLT/SHY)",
    "C": "Kredi, Bankacılık & Volatilite (HYG/LQD, KRE, VIX Term)",
    "D": "Emtia, Enflasyon & Sektörel Rotasyon (Petrol, Bakır, Altın)",
    "E": "Varlığa Özel İtici Güç & Riskler (Taker, Fonlama, Çip, Defansif Kaçış)"
}

# Kalibre Edilmiş Sinyal Eşikleri (±0.60 Kesin Eşikler)
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
            {"id": "asset_direction", "name": "SPY 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.50, "base_sign": 1.0},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 1.35, "base_sign": 1.0},
            {"id": "market_breadth", "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "defensive_flight", "name": "XLU/SPY Kurumsal Defansif Kaçış", "cluster": "E", "base_weight": 0.85, "base_sign": -1.0},
            {"id": "consumer_demand", "name": "XLY/XLP Tüketici Talebi & Büyüme", "cluster": "E", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT/SHY Uzun Vade Tahvil Süre Riski", "cluster": "B", "base_weight": 0.80, "base_sign": 1.0},
            {"id": "banking_stress", "name": "KRE/SPY Bölgesel Bankacılık Likiditesi", "cluster": "C", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "credit_spread", "name": "HYG/LQD Kredi Gücü & İştahı", "cluster": "C", "base_weight": 1.00, "base_sign": 1.0},
            {"id": "vix_strain", "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 1.10, "base_sign": -1.0},
            {"id": "vix_term", "name": "VIX/VIX3M Vade Eğrisi (Kuyruk Riski)", "cluster": "C", "base_weight": 1.00, "base_sign": -1.0},
            {"id": "stagflation_shock", "name": "Petrol / Ticaret (IYT) Şoku", "cluster": "D", "base_weight": 0.75, "base_sign": -1.0},
            {"id": "usd_strength", "name": "Dolar Likidite Baskısı (DXY)", "cluster": "A", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 0.75, "base_sign": -1.0}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "vol_scale": 1.2,
        "factors": [
            {"id": "asset_direction", "name": "QQQ 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.60, "base_sign": 1.0},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 1.60, "base_sign": 1.0},
            {"id": "market_breadth", "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "defensive_flight", "name": "XLU/QQQ Kurumsal Defansif Kaçış", "cluster": "E", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "speculative_beta", "name": "ARKK/QQQ Yüksek Beta Spekülasyon", "cluster": "E", "base_weight": 1.00, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Tahvil Süre (Duration) Duyarlılığı", "cluster": "B", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Finansal Sistem Likidite Stresi (KRE)", "cluster": "C", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Kredi Piyasası Gücü (HYG/LQD)", "cluster": "C", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "vix_strain", "name": "Teknoloji Volatilite Baskısı", "cluster": "C", "base_weight": 1.00, "base_sign": -1.0},
            {"id": "vix_term", "name": "VIX Vade Eğrisi Stresi (VIX/VIX3M)", "cluster": "C", "base_weight": 0.90, "base_sign": -1.0},
            {"id": "stagflation_shock", "name": "Petrol / Enerji Baskısı", "cluster": "D", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Sıkışması", "cluster": "A", "base_weight": 0.75, "base_sign": -1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 0.85, "base_sign": -1.0}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction", "name": "Altın 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.60, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz (TIPS Ters Oran)", "cluster": "B", "base_weight": 1.10, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 0.95, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Uzun Vade Tahvil Gücü", "cluster": "B", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Bankacılık Güven Krizi Primi (KRE)", "cluster": "C", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "usd_strength", "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 0.95, "base_sign": -1.0},
            {"id": "safe_haven", "name": "Jeopolitik & Güvenli Liman", "cluster": "C", "base_weight": 1.10, "base_sign": 1.0},
            {"id": "gold_oil_ratio", "name": "Altın / Petrol Şoku (Stagflasyon)", "cluster": "D", "base_weight": 0.80, "base_sign": 1.0},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Döngüsü", "cluster": "D", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "gsr_velocity", "name": "Altın/Gümüş Rasyosu (GSR)", "cluster": "D", "base_weight": 0.80, "base_sign": 1.0}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "vol_scale": 1.5,
        "factors": [
            {"id": "asset_direction", "name": "Gümüş 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.60, "base_sign": 1.0},
            {"id": "gold_sympathy", "name": "🥇 Altın Güç İvmesi (Gold Beta)", "cluster": "E", "base_weight": 1.50, "base_sign": 1.0},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 0.95, "base_sign": 1.0},
            {"id": "silver_copper", "name": "Gümüş / Bakır Sanayi Rotasyonu", "cluster": "D", "base_weight": 0.90, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Tahvil Getiri Baskısı", "cluster": "B", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 0.85, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "usd_strength", "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "credit_spread", "name": "Küresel Kredi & Sanayi İştahı", "cluster": "C", "base_weight": 0.85, "base_sign": 1.0}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "crypto_ccy": "BTC",
        "vol_scale": 2.0,
        "factors": [
            {"id": "asset_direction", "name": "BTC 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.60, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit Spot & Vadeli Taker Akışı", "cluster": "E", "base_weight": 1.60, "base_sign": 1.0},
            {"id": "funding_stress", "name": "Türev Fonlama Oranı (Kaldıraç Riski)", "cluster": "E", "base_weight": 1.00, "base_sign": -1.0},
            {"id": "btc_dominance", "name": "BTC Dominansı / Altcoin Rotasyonu", "cluster": "E", "base_weight": 0.95, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Geleneksel Bankacılık Kaçışı (KRE Ters)", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT Küresel Tahvil Likidite Baskısı", "cluster": "B", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Küresel Likidite İştahı (HYG/LQD)", "cluster": "C", "base_weight": 0.90, "base_sign": 1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 0.85, "base_sign": -1.0},
            {"id": "real_yield", "name": "Reel Getiri Baskısı (TIP)", "cluster": "B", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "vix_strain", "name": "Sistemik Volatilite Baskısı", "cluster": "C", "base_weight": 0.70, "base_sign": -1.0}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "crypto_ccy": "ETH",
        "vol_scale": 2.2,
        "factors": [
            {"id": "asset_direction", "name": "ETH 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.50, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit ETH Taker Alış Akışı", "cluster": "E", "base_weight": 1.50, "base_sign": 1.0},
            {"id": "funding_stress", "name": "Canlı ETH Fonlama Oranı (Funding Riski)", "cluster": "E", "base_weight": 0.95, "base_sign": -1.0},
            {"id": "btc_sympathy", "name": "⚡ Bitcoin İtici Gücü (BTC Beta)", "cluster": "E", "base_weight": 1.50, "base_sign": 1.0},
            {"id": "eth_btc_beta", "name": "ETH/BTC Göreceli Güç (Risk İştahı)", "cluster": "E", "base_weight": 1.10, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Likidite Baskısı", "cluster": "B", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Kurumsal Kredi & Likidite", "cluster": "C", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "vix_strain", "name": "Sistemik Volatilite Baskısı", "cluster": "C", "base_weight": 0.70, "base_sign": -1.0}
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
    "upper_threshold": 2.2,
    "lower_threshold": 1.5,
    "enter_consecutive_bars": 3,
    "vix_spike_threshold": 2.5,
    "vix_threshold": 30.0,
    "vix_absolute_floor": 20.0,
    "credit_spread_z_threshold": 2.5,
    "anomaly_threshold": 2.2,
    "hysteresis_window": 3
}
