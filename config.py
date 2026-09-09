"""
Tier-1 Adaptive Quant Terminal - Harmonized Twin Core Matrix (v16)
"""

CLUSTERS = {
    "A": "Dolar & Küresel Likidite (DXY)",
    "B": "Faiz & Reel Getiri (TIPS, 10Y)",
    "C": "Kredi & Volatilite (HYG/LQD, VIX)",
    "D": "Emtia & Enflasyon (Petrol/IYT, Bakır/Altın)",
    "E": "Varlığa Özel İtici Güç (Taker, Çip, Altın Beta, Genişlik)"
}

ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "SPY",
        "factors": [
            {"id": "asset_direction",  "name": "SPY 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "semi_lead",        "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 1.5, "base_sign": 1},
            {"id": "market_breadth",   "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 1.4, "base_sign": 1},
            {"id": "credit_spread",    "name": "HYG/LQD Kredi Gücü & İştahı", "cluster": "C", "base_weight": 1.6, "base_sign": 1},
            {"id": "vix_strain",       "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 1.6, "base_sign": -1},
            {"id": "stagflation_shock","name": "Petrol / Ticaret (IYT) Şoku", "cluster": "D", "base_weight": 1.4, "base_sign": -1},
            {"id": "usd_strength",     "name": "Dolar Likidite Baskısı (DXY)", "cluster": "A", "base_weight": 1.4, "base_sign": -1},
            {"id": "real_yield",       "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 1.4, "base_sign": -1}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "factors": [
            {"id": "asset_direction",  "name": "QQQ 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "semi_lead",        "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "market_breadth",   "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 1.2, "base_sign": 1},
            {"id": "credit_spread",    "name": "Kredi Piyasası Gücü", "cluster": "C", "base_weight": 1.5, "base_sign": 1},
            {"id": "vix_strain",       "name": "Teknoloji Volatilite Baskısı", "cluster": "C", "base_weight": 1.6, "base_sign": -1},
            {"id": "stagflation_shock","name": "Petrol / Enerji Baskısı", "cluster": "D", "base_weight": 1.2, "base_sign": -1},
            {"id": "usd_strength",     "name": "DXY Dolar Likidite Sıkışması", "cluster": "A", "base_weight": 1.4, "base_sign": -1},
            {"id": "real_yield",       "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 1.8, "base_sign": -1}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "factors": [
            {"id": "asset_direction",  "name": "Altın 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "real_yield",       "name": "10Y Reel Faiz (TIPS Ters Oran)", "cluster": "B", "base_weight": 2.2, "base_sign": -1},
            {"id": "breakeven_infl",   "name": "Enflasyon Beklenti Kalkanı", "cluster": "D", "base_weight": 1.8, "base_sign": 1},
            {"id": "usd_strength",     "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1},
            {"id": "safe_haven",       "name": "Jeopolitik & Güvenli Liman Talebi", "cluster": "C", "base_weight": 1.8, "base_sign": 1},
            {"id": "stagflation_shock","name": "Emtia / Petrol Enflasyon Desteği", "cluster": "D", "base_weight": 1.5, "base_sign": 1}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "factors": [
            {"id": "asset_direction",  "name": "Gümüş 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "gold_sympathy",    "name": "🥇 Altın Güç İvmesi (Gold Beta)", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "real_yield",       "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 1.8, "base_sign": -1},
            {"id": "breakeven_infl",   "name": "Enflasyon Beklenti Kalkanı", "cluster": "D", "base_weight": 1.6, "base_sign": 1},
            {"id": "usd_strength",     "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 1.6, "base_sign": -1},
            {"id": "copper_gold",      "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 1.2, "base_sign": 1}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "crypto_ccy": "BTC",
        "factors": [
            {"id": "crypto_taker",     "name": "⚡ OKX/Bybit Taker Alım Baskısı", "cluster": "E", "base_weight": 2.8, "base_sign": 1},
            {"id": "asset_direction",  "name": "BTC 4H Fiyat Hızı", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "eth_btc_beta",     "name": "ETH/BTC Risk İştahı Rasyosu", "cluster": "E", "base_weight": 1.6, "base_sign": 1},
            {"id": "usd_strength",     "name": "DXY Küresel Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.6, "base_sign": -1},
            {"id": "credit_spread",    "name": "Küresel Risk İştahı (HYG/LQD)", "cluster": "C", "base_weight": 1.4, "base_sign": 1}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "crypto_ccy": "ETH",
        "factors": [
            {"id": "crypto_taker",     "name": "⚡ OKX/Bybit Taker Alım Baskısı", "cluster": "E", "base_weight": 2.8, "base_sign": 1},
            {"id": "asset_direction",  "name": "ETH 4H Fiyat Hızı", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "eth_btc_beta",     "name": "ETH/BTC Liderlik Gücü", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "btc_sympathy",     "name": "BTC Ana Trend Teyidi", "cluster": "E", "base_weight": 1.8, "base_sign": 1},
            {"id": "usd_strength",     "name": "DXY Küresel Dolar Baskısı", "cluster": "A", "base_weight": 1.6, "base_sign": -1}
        ]
    }
}
