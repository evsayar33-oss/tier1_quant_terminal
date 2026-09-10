"""
Configuration: Asset Matrices, Risk Clusters & Barra Normalization Weights (v29 Institutional Risk-Parity)
Enhanced with:
- Multicollinearity-Mitigated Risk Weights (Balanced Stress Cluster)
- Frequency-Aligned Macro Liquidity Weights
- Pre-Market Liquidity Guard
"""

CLUSTERS = {
    "A": "Dolar Riski & Küresel Likidite (DXY, Net Dollar Liquidity, FX Carry)",
    "B": "Faiz, Getiri Eğrisi & Süre Riski (TIPS, 10Y, TLT/SHY)",
    "C": "Kredi, Bankacılık & Volatilite (HYG/LQD, KRE, VIX Term)",
    "D": "Emtia, Enflasyon & Sektörel Rotasyon (Petrol, Bakır, Altın)",
    "E": "Varlığa Özel İtici Güç & İdiosinkratik Riskler (Taker, Sıkışma, Çip, Ayrışma)"
}

SIGNAL_THRESHOLDS = {
    "strong_buy_enter": 1.60,
    "strong_buy_exit": 1.00,
    "buy_enter": 0.60,
    "buy_exit": 0.30,
    "strong_sell_enter": -1.60,
    "strong_sell_exit": -1.00,
    "sell_enter": -0.60,
    "sell_exit": -0.30
}

ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "SPY",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction", "name": "SPY 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.10, "base_sign": 1.0},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 1.15, "base_sign": 1.0},
            {"id": "market_breadth", "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "defensive_flight", "name": "XLU/SPY Kurumsal Defansif Kaçış", "cluster": "E", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "consumer_demand", "name": "XLY/XLP Tüketici Talebi & Büyüme", "cluster": "E", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "equity_duration_drag", "name": "10Y Reel Faiz Değerleme Baskısı", "cluster": "B", "base_weight": 0.75, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT/SHY Uzun Vade Tahvil Süre Riski", "cluster": "B", "base_weight": 0.65, "base_sign": 1.0},
            # Çift saymayı engellemek için dengelenmiş stres faktörleri:
            {"id": "banking_stress", "name": "KRE/SPY Bölgesel Bankacılık Likiditesi", "cluster": "C", "base_weight": 0.45, "base_sign": 1.0},
            {"id": "credit_spread", "name": "HYG/LQD Kredi Gücü & İştahı", "cluster": "C", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "vix_strain", "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "vix_term", "name": "Dealer Gamma (GEX) & Vade Eğrisi", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "stagflation_shock", "name": "Petrol / Ticaret (IYT) Şoku", "cluster": "D", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Kısa Vade Dolar Baskısı", "cluster": "A", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry & Küresel Likidite", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "vol_scale": 1.2,
        "factors": [
            {"id": "asset_direction", "name": "QQQ 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 2.10, "base_sign": 1.0},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 1.25, "base_sign": 1.0},
            {"id": "tech_breadth_dispersion", "name": "Çip & Yüksek Beta Ayrışması", "cluster": "E", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "speculative_beta", "name": "ARKK/QQQ Yüksek Beta Spekülasyon", "cluster": "E", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "defensive_flight", "name": "XLU/QQQ Kurumsal Defansif Kaçış", "cluster": "E", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "equity_duration_drag", "name": "Teknoloji Değerleme / Reel Getiri Baskısı", "cluster": "B", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT Tahvil Süre Duyarlılığı", "cluster": "B", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Finansal Sistem Likidite Stresi (KRE)", "cluster": "C", "base_weight": 0.40, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Kredi Piyasası Gücü (HYG/LQD)", "cluster": "C", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "vix_strain", "name": "Teknoloji Volatilite Baskısı", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "vix_term", "name": "Dealer Gamma (GEX) & Vade Stresi", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "stagflation_shock", "name": "Petrol / Enerji Baskısı", "cluster": "D", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Sıkışması", "cluster": "A", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry Tasfiye Riski", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction", "name": "Altın 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.20, "base_sign": 1.0},
            {"id": "gold_sovereign_decoupling", "name": "🏛️ Merkez Bankası & Jeopolitik Rezerv Talebi", "cluster": "E", "base_weight": 1.20, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz (TIPS Ters Oran)", "cluster": "B", "base_weight": 0.95, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Uzun Vade Tahvil Gücü", "cluster": "B", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Bankacılık Güven Krizi Primi (KRE)", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "safe_haven", "name": "Jeopolitik & Güvenli Liman", "cluster": "C", "base_weight": 0.95, "base_sign": 1.0},
            {"id": "gold_oil_ratio", "name": "Altın / Petrol Şoku (Stagflasyon)", "cluster": "D", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Döngüsü", "cluster": "D", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "gsr_velocity", "name": "Altın/Gümüş Rasyosu (GSR)", "cluster": "D", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "usd_strength", "name": "DXY Spot Dolar Baskısı", "cluster": "A", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Dolar Rezerv / Net Likidite İvmesi", "cluster": "A", "base_weight": 0.70, "base_sign": 1.0}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "vol_scale": 1.25,
        "factors": [
            {"id": "asset_direction", "name": "Gümüş 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 1.90, "base_sign": 1.0},
            {"id": "gold_sympathy", "name": "🥇 Altın Güç İvmesi (Gold Beta)", "cluster": "E", "base_weight": 1.70, "base_sign": 1.0},
            {"id": "silver_monetary_catchup", "name": "🥈 Gümüş Parasal Yakalama & Değerleme İvmesi", "cluster": "E", "base_weight": 1.00, "base_sign": 1.0},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "silver_copper", "name": "Gümüş / Bakır Sanayi Rotasyonu", "cluster": "D", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Tahvil Getiri Baskısı", "cluster": "B", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Küresel Kredi & Sanayi İştahı", "cluster": "C", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "usd_strength", "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "crypto_ccy": "BTC",
        "vol_scale": 2.0,
        "factors": [
            {"id": "asset_direction", "name": "BTC 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.20, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit Spot & Vadeli Taker Akışı", "cluster": "E", "base_weight": 1.30, "base_sign": 1.0},
            {"id": "stablecoin_usd_impulse", "name": "💵 Kripto-Yerel USD Likiditesi & Taker İştahı", "cluster": "E", "base_weight": 1.10, "base_sign": 1.0},
            {"id": "funding_stress", "name": "Türev Fonlama Oranı (Kaldıraç Riski)", "cluster": "E", "base_weight": 0.85, "base_sign": -1.0},
            {"id": "liquidation_squeeze_risk", "name": "⚠️ Likidasyon & Kaldıraç Sıkışması Riski", "cluster": "E", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "btc_dominance", "name": "BTC Dominansı / Altcoin Rotasyonu", "cluster": "E", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Geleneksel Bankacılık Kaçışı (KRE Ters)", "cluster": "C", "base_weight": 0.30, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT Küresel Tahvil Likidite Baskısı", "cluster": "B", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Küresel Likidite İştahı (HYG/LQD)", "cluster": "C", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "real_yield", "name": "Reel Getiri Baskısı (TIP)", "cluster": "B", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "vix_strain", "name": "Sistemik Volatilite Baskısı", "cluster": "C", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry & Risk-On Likiditesi", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "crypto_ccy": "ETH",
        "vol_scale": 2.2,
        "factors": [
            {"id": "asset_direction", "name": "ETH 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.20, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit ETH Taker Alış Akışı", "cluster": "E", "base_weight": 1.20, "base_sign": 1.0},
            {"id": "stablecoin_usd_impulse", "name": "💵 Kripto-Yerel USD Likiditesi & Stabilcoin Akışı", "cluster": "E", "base_weight": 1.00, "base_sign": 1.0},
            {"id": "funding_stress", "name": "Canlı ETH Fonlama Oranı (Funding Riski)", "cluster": "E", "base_weight": 0.80, "base_sign": -1.0},
            {"id": "liquidation_squeeze_risk", "name": "⚠️ ETH Türev Kaldıraç & Sıkışma Riski", "cluster": "E", "base_weight": 0.75, "base_sign": -1.0},
            {"id": "btc_sympathy", "name": "⚡ Bitcoin İtici Gücü (BTC Beta)", "cluster": "E", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "eth_btc_beta", "name": "ETH/BTC Göreceli Güç (Risk İştahı)", "cluster": "E", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "eth_staking_utility_drift", "name": "⛓️ L1 Ağ Aktivitesi & DeFi Likidite İvmesi", "cluster": "E", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Likidite Baskısı", "cluster": "B", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Kurumsal Kredi & Likidite", "cluster": "C", "base_
