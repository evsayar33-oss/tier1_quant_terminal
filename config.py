"""
Tier-1 Adaptive Quant Terminal - Leading Macro & Multi-Asset Matrix (v5)
"""

# 5 Bağımsız Küme (Tam Kurumsal Kapsam)
CLUSTERS = {
    "A": "Likidite & FX Carry (DXY, USD/JPY)",
    "B": "Faiz & Getiri Eğrisi (TNX, 2Y Yield, TIPS)",
    "C": "Kredi Riski & Temerrüt (HYG/LQD)",
    "D": "Enflasyon & Emtia Şoku (Petrol, Taşımacılık/IYT, Bakır/Altın)",
    "E": "Varlık Mikroyapısı & Anlık Akış (Taker Ratio, Momentum, Beta)"
}

ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "^GSPC",
        "factors": [
            {"id": "spx_mom", "name": "Pure Momentum", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "credit_spread", "name": "HYG/LQD Kredi Gücü", "cluster": "C", "base_weight": 2.2, "base_sign": 1},
            {"id": "vix_strain", "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 1.8, "base_sign": -1},
            {"id": "stagflation_shock", "name": "Petrol / Ticaret (IYT) Şoku", "cluster": "D", "base_weight": 2.0, "base_sign": -1},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Büyümesi", "cluster": "D", "base_weight": 1.2, "base_sign": 1},
            {"id": "dxy_strain", "name": "Dolar Likidite Baskısı (DXY)", "cluster": "A", "base_weight": 1.5, "base_sign": -1}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "factors": [
            {"id": "nq_mom", "name": "Pure Momentum", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "us10y_yield", "name": "10Y Tahvil Faiz İvmesi", "cluster": "B", "base_weight": 2.2, "base_sign": -1},
            {"id": "yield_curve", "name": "Getiri Eğrisi Şoku (10Y - 2Y)", "cluster": "B", "base_weight": 1.8, "base_sign": -1},
            {"id": "credit_spread", "name": "Kredi Temerrüt Riski", "cluster": "C", "base_weight": 1.8, "base_sign": 1},
            {"id": "stagflation_shock", "name": "Enflasyon / Enerji Baskısı", "cluster": "D", "base_weight": 1.6, "base_sign": -1},
            {"id": "dxy_strain", "name": "DXY Likidite Sıkışması", "cluster": "A", "base_weight": 1.4, "base_sign": -1}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "factors": [
            {"id": "xau_mom", "name": "Pure Momentum", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "real_yield", "name": "10Y Reel Faiz (TIPS Ters Oran)", "cluster": "B", "base_weight": 2.5, "base_sign": -1},
            {"id": "stagflation_shock", "name": "Petrol / Enflasyon Şoku Kalkanı", "cluster": "D", "base_weight": 2.2, "base_sign": 1},
            {"id": "dxy_strain", "name": "Dolar Baskısı", "cluster": "A", "base_weight": 1.8, "base_sign": -1},
            {"id": "safe_haven", "name": "Sistemik Korunma Talebi", "cluster": "C", "base_weight": 1.5, "base_sign": 1}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "factors": [
            {"id": "xag_mom", "name": "Pure Momentum", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 2.4, "base_sign": 1},
            {"id": "mining_beta", "name": "XME Madencilik Hisseleri İvmesi", "cluster": "E", "base_weight": 1.8, "base_sign": 1},
            {"id": "real_yield", "name": "Reel Faiz Baskısı", "cluster": "B", "base_weight": 1.8, "base_sign": -1},
            {"id": "dxy_strain", "name": "Dolar Gücü", "cluster": "A", "base_weight": 1.5, "base_sign": -1}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "binance_symbol": "BTCUSDT",
        "factors": [
            {"id": "taker_ratio", "name": "Binance Futures Taker Alım Hacmi", "cluster": "E", "base_weight": 3.0, "base_sign": 1},
            {"id": "btc_mom", "name": "BTC Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "yen_carry", "name": "USD/JPY Carry Trade Çözülme Riski", "cluster": "A", "base_weight": 2.2, "base_sign": 1},
            {"id": "credit_spread", "name": "Küresel Kredi İştahı (HYG/LQD)", "cluster": "C", "base_weight": 1.8, "base_sign": 1},
            {"id": "dxy_strain", "name": "Dolar Likidite Çekilmesi (DXY)", "cluster": "A", "base_weight": 1.8, "base_sign": -1}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "binance_symbol": "ETHUSDT",
        "factors": [
            {"id": "taker_ratio", "name": "Binance Futures Taker Alım Hacmi", "cluster": "E", "base_weight": 3.0, "base_sign": 1},
            {"id": "eth_mom", "name": "ETH Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.0, "base_sign": 1},
            {"id": "eth_btc_beta", "name": "ETH/BTC Risk İştahı Rasyosu", "cluster": "E", "base_weight": 2.2, "base_sign": 1},
            {"id": "yen_carry", "name": "USD/JPY Carry Trade Riski", "cluster": "A", "base_weight": 1.8, "base_sign": 1},
            {"id": "credit_spread", "name": "Küresel Likidite İştahı", "cluster": "C", "base_weight": 1.6, "base_sign": 1}
        ]
    }
}

CRISIS_CONFIG = {
    "upper_threshold": 2.2,
    "lower_threshold": 1.5,
    "enter_consecutive_bars": 3,
    "vix_spike_threshold": 2.5,
    "credit_spike_threshold": -1.8,
    "vix_absolute_floor": 20.0
}

THRESHOLD_CLAMPS = {
    "min_long_score": 2.2,
    "max_short_score": -2.2
}
