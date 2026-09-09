"""
Tier-1 Adaptive Quant Terminal - Balanced Cross-Asset Symmetry (v7)
"""

CLUSTERS = {
    "A": "Likidite & FX Carry (DXY, USD/JPY)",
    "B": "Faiz & Getiri Eğrisi (TNX, TIPS, 2Y)",
    "C": "Kredi Riski & Volatilite (HYG/LQD, VIX)",
    "D": "Enflasyon & Emtia Şoku (Petrol/IYT, Bakır/Altın)",
    "E": "Varlık Mikroyapısı & Anlık İvme (Momentum, Taker)"
}

ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "SPY", # 🛡️ Canlı ETF'ye çekildi (^GSPC gecikmesi bitti)
        "factors": [
            {"id": "spx_mom", "name": "4H Fiyat İvmesi", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "credit_spread", "name": "HYG/LQD Kredi Gücü", "cluster": "C", "base_weight": 2.0, "base_sign": 1},
            {"id": "vix_strain", "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 2.0, "base_sign": -1},
            {"id": "stagflation_shock", "name": "Petrol / Ticaret Şoku", "cluster": "D", "base_weight": 1.8, "base_sign": -1},
            {"id": "dxy_strain", "name": "Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.5, "base_sign": -1},
            {"id": "us10y_yield", "name": "Tahvil Faiz Baskısı", "cluster": "B", "base_weight": 1.5, "base_sign": -1}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "factors": [
            {"id": "nq_mom", "name": "4H Fiyat İvmesi", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "credit_spread", "name": "HYG/LQD Kredi Gücü", "cluster": "C", "base_weight": 2.0, "base_sign": 1},
            {"id": "vix_strain", "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 2.0, "base_sign": -1}, # 🛡️ S&P ile eşitlendi
            {"id": "stagflation_shock", "name": "Petrol / Ticaret Şoku", "cluster": "D", "base_weight": 1.8, "base_sign": -1},
            {"id": "dxy_strain", "name": "Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.5, "base_sign": -1},
            {"id": "us10y_yield", "name": "10Y Reel Faiz Baskısı", "cluster": "B", "base_weight": 2.0, "base_sign": -1}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "factors": [
            {"id": "xau_mom", "name": "4H Fiyat İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "real_yield", "name": "10Y Reel Getiri (TIPS)", "cluster": "B", "base_weight": 2.2, "base_sign": -1},
            {"id": "stagflation_shock", "name": "Petrol / Enflasyon Kalkanı", "cluster": "D", "base_weight": 2.0, "base_sign": 1},
            {"id": "dxy_strain", "name": "Dolar Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1},
            {"id": "safe_haven", "name": "Sistemik Sığınak Talebi", "cluster": "C", "base_weight": 1.8, "base_sign": 1}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "factors": [
            {"id": "xag_mom", "name": "4H Fiyat İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "real_yield", "name": "10Y Reel Getiri (TIPS)", "cluster": "B", "base_weight": 2.0, "base_sign": -1},
            {"id": "stagflation_shock", "name": "Emtia / Enflasyon Desteği", "cluster": "D", "base_weight": 1.8, "base_sign": 1}, # 🛡️ Altın gibi pozitife bağlandı
            {"id": "safe_haven", "name": "Değerli Metal Sığınağı", "cluster": "C", "base_weight": 1.6, "base_sign": 1},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 1.2, "base_sign": 1}, # 🛡️ Ağırlık 2.4'ten 1.2'ye indirildi
            {"id": "dxy_strain", "name": "Dolar Baskısı", "cluster": "A", "base_weight": 1.5, "base_sign": -1}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "binance_symbol": "BTCUSDT",
        "factors": [
            {"id": "taker_ratio", "name": "Binance Futures Taker Hacmi", "cluster": "E", "base_weight": 3.0, "base_sign": 1},
            {"id": "btc_mom", "name": "4H Fiyat İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "yen_carry", "name": "USD/JPY Carry Riski", "cluster": "A", "base_weight": 2.0, "base_sign": 1},
            {"id": "credit_spread", "name": "Kredi Riski (HYG/LQD)", "cluster": "C", "base_weight": 1.8, "base_sign": 1},
            {"id": "dxy_strain", "name": "Dolar Likidite Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "binance_symbol": "ETHUSDT",
        "factors": [
            {"id": "taker_ratio", "name": "Binance Futures Taker Hacmi", "cluster": "E", "base_weight": 3.0, "base_sign": 1},
            {"id": "eth_mom", "name": "4H Fiyat İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "eth_btc_beta", "name": "ETH/BTC Güç Rasyosu", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "yen_carry", "name": "USD/JPY Carry Riski", "cluster": "A", "base_weight": 1.8, "base_sign": 1},
            {"id": "credit_spread", "name": "Kredi Riski (HYG/LQD)", "cluster": "C", "base_weight": 1.6, "base_sign": 1}
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
