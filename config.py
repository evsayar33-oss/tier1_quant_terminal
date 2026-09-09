"""
Tier-1 Adaptive Quant Terminal - Konfigürasyon ve Varlık Matrisleri (v4)
"""

# 4 Bağımsız Küme (Multicollinearity / Çoklu Bağlantı Önleme)
CLUSTERS = {
    "A": "Likidite / Para Politikası (NDL, Bakır/Altın)",
    "B": "Faiz / Reel Getiri (TNX, TIPS)",
    "C": "Dolar / Kredi Riski (DXY, HYG/LQD, VIX)",
    "D": "Varlık Mikroyapısı (Taker Oranı, CVD, Momentum, Beta)"
}

# Desteklenen Varlıklar ve Başlangıç Matrisleri
ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "^GSPC",
        "factors": [
            {"id": "spx_mom", "name": "Pure Momentum", "cluster": "D", "base_weight": 2.5, "base_sign": 1, "freq": "intraday"},
            {"id": "credit_spread", "name": "HYG/LQD Credit Risk", "cluster": "C", "base_weight": 2.0, "base_sign": -1, "freq": "daily"},
            {"id": "vix_strain", "name": "VIX Volatility Strain", "cluster": "C", "base_weight": 1.8, "base_sign": -1, "freq": "daily"},
            {"id": "copper_gold", "name": "Copper/Gold Growth", "cluster": "A", "base_weight": 1.2, "base_sign": 1, "freq": "daily"}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "factors": [
            {"id": "nq_mom", "name": "Pure Momentum", "cluster": "D", "base_weight": 2.5, "base_sign": 1, "freq": "intraday"},
            {"id": "us10y_yield", "name": "10Y Yield Pressure (TNX)", "cluster": "B", "base_weight": 2.2, "base_sign": -1, "freq": "daily"},
            {"id": "credit_spread", "name": "Credit Risk Spread", "cluster": "C", "base_weight": 1.8, "base_sign": -1, "freq": "daily"},
            {"id": "dxy_strain", "name": "DXY Currency Strain", "cluster": "C", "base_weight": 1.2, "base_sign": -1, "freq": "daily"}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "factors": [
            {"id": "xau_mom", "name": "Pure Momentum", "cluster": "D", "base_weight": 2.5, "base_sign": 1, "freq": "intraday"},
            {"id": "real_yield", "name": "10Y Real Yield (TIPS)", "cluster": "B", "base_weight": 2.2, "base_sign": -1, "freq": "daily"},
            {"id": "dxy_strain", "name": "DXY Strain", "cluster": "C", "base_weight": 2.0, "base_sign": -1, "freq": "daily"},
            {"id": "safe_haven", "name": "Safe-Haven Demand (VIX/Spread)", "cluster": "C", "base_weight": 1.5, "base_sign": 1, "freq": "daily"}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "factors": [
            {"id": "xag_mom", "name": "Pure Momentum", "cluster": "D", "base_weight": 2.5, "base_sign": 1, "freq": "intraday"},
            {"id": "copper_gold", "name": "Copper/Gold Industrial Demand", "cluster": "A", "base_weight": 2.2, "base_sign": 1, "freq": "daily"},
            {"id": "mining_beta", "name": "XME Mining Beta", "cluster": "D", "base_weight": 1.5, "base_sign": 1, "freq": "daily"},
            {"id": "rates_dxy", "name": "10Y Yield & DXY Strain", "cluster": "B", "base_weight": 1.8, "base_sign": -1, "freq": "daily"}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "binance_symbol": "BTCUSDT",
        "factors": [
            {"id": "taker_ratio", "name": "Binance Futures Taker Volume Ratio", "cluster": "D", "base_weight": 3.0, "base_sign": 1, "freq": "intraday"},
            {"id": "btc_mom", "name": "BTC Pure Momentum", "cluster": "D", "base_weight": 2.0, "base_sign": 1, "freq": "intraday"},
            {"id": "eth_btc_beta", "name": "ETH/BTC Risk Appetite Ratio", "cluster": "D", "base_weight": 1.5, "base_sign": 1, "freq": "intraday"},
            {"id": "credit_dxy", "name": "Global Liquidity & DXY Strain", "cluster": "C", "base_weight": 1.8, "base_sign": -1, "freq": "daily"}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "binance_symbol": "ETHUSDT",
        "factors": [
            {"id": "taker_ratio", "name": "Binance Futures Taker Volume Ratio", "cluster": "D", "base_weight": 3.0, "base_sign": 1, "freq": "intraday"},
            {"id": "eth_mom", "name": "ETH Pure Momentum", "cluster": "D", "base_weight": 2.0, "base_sign": 1, "freq": "intraday"},
            {"id": "eth_btc_beta", "name": "ETH/BTC Outperformance Beta", "cluster": "D", "base_weight": 1.8, "base_sign": 1, "freq": "intraday"},
            {"id": "credit_dxy", "name": "Global Liquidity Strain", "cluster": "C", "base_weight": 1.6, "base_sign": -1, "freq": "daily"}
        ]
    }
}

# 🛡️ GELİŞMİŞ KRİZ KİLİDİ VE MUTLAK VIX TABAN AYARLARI
CRISIS_CONFIG = {
    "upper_threshold": 2.2,          # Anomali normu eşiği
    "lower_threshold": 1.5,          # Hysteresis çıkış eşiği
    "enter_consecutive_bars": 3,
    "exit_consecutive_bars": 2,
    "vix_spike_threshold": 2.5,
    "credit_spike_threshold": 1.8,
    "vix_absolute_floor": 20.0       # 🛡️ VIX < 20 iken Z-Score kriz tetikleyemez (Düşük volatilite kalkanı)
}

# 🛡️ DİNAMİK EŞİK TABANI (UYUYAN PİYASA KALKANI)
THRESHOLD_CLAMPS = {
    "min_long_score": 2.0,           # Persentil ne kadar düşerse düşsün Long onayı için asgari skor
    "max_short_score": -2.0          # Persentil ne kadar yükselirse yükselsin Short onayı için azami skor
}

# Veri Tazeliği Eşikleri (Saniye Cinsinden)
STALENESS_THRESHOLDS = {
    "intraday": 900,     # 15 dakika
    "daily": 129600,     # 36 saat
    "weekly": 777600     # 9 gün
}

# Güven Çarpanları
SOURCE_TIER_CONFIDENCE = {
    "primary": 1.0,
    "secondary": 0.7,
    "proxy": 0.4
}
