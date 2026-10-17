"""
Configuration: Calibrated Asset Matrices, Barra Cluster Parity & Risk Normalization (v34)
Enhanced with:
- ENTRY_GATES_CONFIG & ENTRY_FILTER_CONFIG (Dual alias for 100% crash-proof imports)
- Live 24/7 Futures Benchmarks (ES=F for S&P 500, NQ=F for Nasdaq 100)
- Globex 23/5 Continuous Asset Clocks (Eliminates 16:30 TSI Freeze)
"""

CLUSTERS = {
    "A": "Dolar Riski & Küresel Likidite (DXY, Net Dollar Liquidity, FX Carry)",
    "B": "Faiz, Getiri Eğrisi & Süre Riski (TIPS, 10Y, TLT/SHY)",
    "C": "Kredi, Bankacılık & Volatilite (HYG/LQD, KRE, VIX Term)",
    "D": "Emtia, Enflasyon & Sektörel Rotasyon (Petrol, Bakır, Altın)",
    "E": "Varlığa Özel İtici Güç & Mikro Yapı (4H Momentum, Çip, Taker, Sıkışma)"
}

SIGNAL_THRESHOLDS = {
    "strong_buy_enter": 1.60,
    "strong_buy_exit": 1.00,
    "buy_enter": 0.75,
    "buy_exit": 0.30,
    "strong_sell_enter": -1.60,
    "strong_sell_exit": -1.00,
    "sell_enter": -0.75,
    "sell_exit": -0.30
}

# 🚀 2019-2026 Kurumsal Giriş Analizi ve Şok Koruma Eşikleri
ENTRY_GATES_CONFIG = {
    "vol_shock_high": 2.20,       # ATR_14 / SMA(ATR_14, 20) > 2.20 -> Volatilite Şoku
    "vol_shock_low": 0.65,        # ATR_14 / SMA(ATR_14, 20) < 0.65 -> Sıkışma / Ölü Piyasa
    "rvol_strong_min": 1.25,      # Güçlü Al / Güçlü Sat için zorunlu taban kurumsal hacim çarpanı
    "rvol_climax_shock": 3.20,    # Climax / Tükeniş hacmi şoku
    "rvol_illiquid": 0.50,        # Düşük likidite
    "mad_z_threshold": 1.96       # Robust MAD Z-Score ayrışma eşiği
}

# 🛡️ Dual Alias: quant_processor.py veya gatekeeper.py hangisini çağırırsa çağırsın hata vermez!
ENTRY_FILTER_CONFIG = ENTRY_GATES_CONFIG

ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "ES=F",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction", "name": "ES 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 1.10, "base_sign": 1.0, "role": "state"},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 0.35, "base_sign": 1.0},
            {"id": "market_breadth", "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 0.30, "base_sign": 1.0},
            {"id": "defensive_flight", "name": "XLU/SPY Kurumsal Defansif Kaçış", "cluster": "E", "base_weight": 0.30, "base_sign": -1.0},
            {"id": "consumer_demand", "name": "XLY/XLP Tüketici Talebi & Büyüme", "cluster": "E", "base_weight": 0.30, "base_sign": 1.0},
            {"id": "equity_duration_drag", "name": "10Y Reel Faiz Değerleme Baskısı", "cluster": "B", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT/SHY Uzun Vade Tahvil Süre Riski", "cluster": "B", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "banking_stress", "name": "KRE/SPY Bölgesel Bankacılık Likiditesi", "cluster": "C", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "credit_spread", "name": "HYG/LQD Kredi Gücü & İştahı", "cluster": "C", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "vix_strain", "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 0.55, "base_sign": -1.0, "role": "state"},
            {"id": "vix_term", "name": "VIX/VIX3M Dealer Gamma & Vade Eğrisi", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0, "role": "state"},
            {"id": "stagflation_shock", "name": "Petrol / Ticaret (IYT) Şoku", "cluster": "D", "base_weight": 0.50, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Kısa Vade Dolar Baskısı", "cluster": "A", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry & Küresel Likidite", "cluster": "A", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "nq_relative_divergence", "name": "🎯 SPX/NQ Adaptif Ayrışma (Rezidüel)", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0},
            {"id": "vix_term_lead", "name": "🔮 VIX Vade Yapısı Öncü Sinyali (Backwardation/Contango)", "cluster": "E", "base_weight": 0.70, "base_sign": 1.0, "role": "state"},
            {"id": "tail_risk_skew_lead", "name": "🔮 CBOE SKEW Kuyruk Riski Fiyatlaması (Öncü)", "cluster": "E", "base_weight": 0.95, "base_sign": 1.0},
            {"id": "cta_trend_position", "name": "🤖 CTA Trend Fonu Pozisyonu (Tahmini)", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"},
            {"id": "liquidity_sweep", "name": "🪤 Likidite Avı (Stop Süpürme) Sinyali", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"},
            {"id": "vol_control_flow", "name": "⚖️ Volatilite Hedefli Fon Akışı (Tahmini)", "cluster": "C", "base_weight": 0.40, "base_sign": 1.0, "role": "state"}
        ]
    },
    "NQ": {
        # NOTE: "spx_relative_divergence" factor added below (adaptive
        # NQ~SPX residual model) — previously NQ had no cross-asset
        # divergence detector at all versus its own benchmark pair.

        "name": "NASDAQ 100",
        "benchmark_symbol": "NQ=F",
        "vol_scale": 1.2,
        "factors": [
            {"id": "asset_direction", "name": "NQ 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 1.10, "base_sign": 1.0, "role": "state"},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0},
            {"id": "tech_breadth_dispersion", "name": "Çip & Yüksek Beta Ayrışması", "cluster": "E", "base_weight": 0.35, "base_sign": 1.0},
            {"id": "speculative_beta", "name": "ARKK/QQQ Yüksek Beta Spekülasyon", "cluster": "E", "base_weight": 0.30, "base_sign": 1.0},
            {"id": "defensive_flight", "name": "XLU/QQQ Kurumsal Defansif Kaçış", "cluster": "E", "base_weight": 0.25, "base_sign": -1.0},
            {"id": "equity_duration_drag", "name": "Teknoloji Değerleme / Reel Getiri Baskısı", "cluster": "B", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT Tahvil Süre Duyarlılığı", "cluster": "B", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Finansal Sistem Likidite Stresi (KRE)", "cluster": "C", "base_weight": 0.40, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Kredi Piyasası Gücü (HYG/LQD)", "cluster": "C", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "vix_strain", "name": "Teknoloji Volatilite Baskısı", "cluster": "C", "base_weight": 0.55, "base_sign": -1.0, "role": "state"},
            {"id": "vix_term", "name": "VIX Vade Eğrisi & Gamma Stresi", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0, "role": "state"},
            {"id": "stagflation_shock", "name": "Petrol / Enerji Baskısı", "cluster": "D", "base_weight": 0.45, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Sıkışması", "cluster": "A", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry Tasfiye Riski", "cluster": "A", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "spx_relative_divergence", "name": "🎯 NQ/SPX Adaptif Ayrışma (Rezidüel)", "cluster": "E", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "vix_term_lead", "name": "🔮 VIX Vade Yapısı Öncü Sinyali (Backwardation/Contango)", "cluster": "E", "base_weight": 0.60, "base_sign": 1.0, "role": "state"},
            {"id": "tech_vol_premium_lead", "name": "🔮 VXN/VIX Teknoloji Volatilite Primi (Öncü)", "cluster": "E", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "tail_risk_skew_lead", "name": "🔮 CBOE SKEW Kuyruk Riski Fiyatlaması (Öncü)", "cluster": "E", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "cta_trend_position", "name": "🤖 CTA Trend Fonu Pozisyonu (Tahmini)", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"},
            {"id": "liquidity_sweep", "name": "🪤 Likidite Avı (Stop Süpürme) Sinyali", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"},
            {"id": "vol_control_flow", "name": "⚖️ Volatilite Hedefli Fon Akışı (Tahmini)", "cluster": "C", "base_weight": 0.40, "base_sign": 1.0, "role": "state"}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction", "name": "Altın Hızlı 2H/16H Anlık İvme", "cluster": "E", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "gold_macro_lead", "name": "🥇 DXY/Tahvil Öncü Altın İmpulsu", "cluster": "E", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "gold_sovereign_decoupling", "name": "🏛️ Merkez Bankası & Jeopolitik Rezerv Talebi", "cluster": "E", "base_weight": 0.90, "base_sign": 1.0},
            {"id": "gold_vol_premium_lead", "name": "🔮 GVZ Opsiyon Volatilite Primi (Öncü)", "cluster": "E", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz (TIPS Ters Oran)", "cluster": "B", "base_weight": 0.85, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Uzun Vade Tahvil Gücü", "cluster": "B", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Bankacılık Güven Krizi Primi (KRE)", "cluster": "C", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "safe_haven", "name": "Jeopolitik & Güvenli Liman", "cluster": "C", "base_weight": 0.80, "base_sign": 1.0},
            {"id": "gold_oil_ratio", "name": "Altın / Petrol Şoku (Stagflasyon)", "cluster": "D", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Döngüsü", "cluster": "D", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "gsr_velocity", "name": "Altın/Gümüş Rasyosu (GSR)", "cluster": "D", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "usd_strength", "name": "DXY Spot Dolar Baskısı", "cluster": "A", "base_weight": 0.75, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Dolar Rezerv / Net Likidite İvmesi", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "cta_trend_position", "name": "🤖 CTA Trend Fonu Pozisyonu (Tahmini)", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"},
            {"id": "liquidity_sweep", "name": "🪤 Likidite Avı (Stop Süpürme) Sinyali", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "vol_scale": 1.25,
        "factors": [
            {"id": "asset_direction", "name": "Gümüş 4H/24H Trend İvmesi", "cluster": "E", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "gold_sympathy", "name": "🥇 Altın Çapa / Beta (Adaptif)", "cluster": "E", "base_weight": 0.70, "base_sign": 1.0},
            {"id": "gold_divergence_residual", "name": "🎯 XAU/XAG Adaptif Ayrışma (Rezidüel)", "cluster": "E", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "silver_monetary_catchup", "name": "🥈 Gümüş Parasal Yakalama & Değerleme İvmesi", "cluster": "E", "base_weight": 0.30, "base_sign": 1.0},
            {"id": "silver_vol_premium_lead", "name": "🔮 VXSLV Opsiyon Volatilite Primi (Öncü)", "cluster": "E", "base_weight": 1.10, "base_sign": 1.0},
            {"id": "gold_vol_premium_lead", "name": "🔮 GVZ Çapraz-Volatilite Rejimi (Öncü)", "cluster": "E", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "silver_copper", "name": "Gümüş / Bakır Sanayi Rotasyonu", "cluster": "D", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Tahvil Getiri Baskısı", "cluster": "B", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Küresel Kredi & Sanayi İştahı", "cluster": "C", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "usd_strength", "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "cta_trend_position", "name": "🤖 CTA Trend Fonu Pozisyonu (Tahmini)", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"},
            {"id": "liquidity_sweep", "name": "🪤 Likidite Avı (Stop Süpürme) Sinyali", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "crypto_ccy": "BTC",
        "vol_scale": 2.0,
        "factors": [
            {"id": "asset_direction", "name": "BTC 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit Spot & Vadeli Taker Akışı", "cluster": "E", "base_weight": 1.00, "base_sign": 1.0},
            {"id": "stablecoin_usd_impulse", "name": "💵 Kripto-Yerel USD Likiditesi & Taker İştahı", "cluster": "E", "base_weight": 0.90, "base_sign": 1.0},
            {"id": "funding_stress", "name": "Türev Fonlama Oranı (Kaldıraç Riski)", "cluster": "E", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "liquidation_squeeze_risk", "name": "⚠️ Likidasyon & Kaldıraç Sıkışması Riski", "cluster": "E", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "btc_dominance", "name": "BTC Dominansı / Altcoin Rotasyonu", "cluster": "E", "base_weight": 0.45, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Geleneksel Bankacılık Kaçışı (KRE Ters)", "cluster": "C", "base_weight": 0.25, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT Küresel Tahvil Likidite Baskısı", "cluster": "B", "base_weight": 0.45, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Küresel Likidite İştahı (HYG/LQD)", "cluster": "C", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "real_yield", "name": "Reel Getiri Baskısı (TIP)", "cluster": "B", "base_weight": 0.50, "base_sign": -1.0},
            {"id": "vix_strain", "name": "Sistemik Volatilite Baskısı", "cluster": "C", "base_weight": 0.50, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.80, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry & Risk-On Likiditesi", "cluster": "A", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "cta_trend_position", "name": "🤖 CTA Trend Fonu Pozisyonu (Tahmini)", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"},
            {"id": "liquidity_sweep", "name": "🪤 Likidite Avı (Stop Süpürme) Sinyali", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "crypto_ccy": "ETH",
        "vol_scale": 2.2,
        "factors": [
            {"id": "asset_direction", "name": "ETH 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit ETH Taker Alış Akışı", "cluster": "E", "base_weight": 1.05, "base_sign": 1.0},
            {"id": "stablecoin_usd_impulse", "name": "💵 Kripto-Yerel USD Likiditesi & Stabilcoin Akışı", "cluster": "E", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "funding_stress", "name": "Canlı ETH Fonlama Oranı (Funding Riski)", "cluster": "E", "base_weight": 0.75, "base_sign": -1.0},
            {"id": "liquidation_squeeze_risk", "name": "⚠️ ETH Türev Kaldıraç & Sıkışma Riski", "cluster": "E", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "btc_sympathy", "name": "⚡ Bitcoin İtici Gücü (BTC Beta)", "cluster": "E", "base_weight": 0.30, "base_sign": 1.0},
            {"id": "eth_btc_beta", "name": "ETH/BTC Göreceli Güç (Risk İştahı)", "cluster": "E", "base_weight": 0.25, "base_sign": 1.0},
            # v3.3.3: "eth_staking_utility_drift" REMOVED. Despite its "L1 activity /
            # DeFi" label it used no on-chain data: it was the 24h ETH/BTC price-ratio
            # MAD z-score, i.e. a cruder duplicate of eth_btc_beta (regression
            # residual), saturated at +1.8 and the single largest ETH contribution
            # (+1.21) -- the main reason ETH read NÖTR while BTC read SAT. Re-add
            # only with a real on-chain feed (gas/active addresses/staking flows).
            {"id": "duration_risk", "name": "TLT Likidite Baskısı", "cluster": "B", "base_weight": 0.45, "base_sign": 1.0},
            # v3.3.3: same macro exposure as BTC (rho ~0.9); was missing for ETH only.
            {"id": "real_yield", "name": "Reel Getiri Baskısı (TIP)", "cluster": "B", "base_weight": 0.50, "base_sign": -1.0},
            {"id": "credit_spread", "name": "Kurumsal Kredi & Likidite", "cluster": "C", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "vix_strain", "name": "Sistemik Volatilite Baskısı", "cluster": "C", "base_weight": 0.50, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry Likiditesi", "cluster": "A", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "cta_trend_position", "name": "🤖 CTA Trend Fonu Pozisyonu (Tahmini)", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"},
            {"id": "liquidity_sweep", "name": "🪤 Likidite Avı (Stop Süpürme) Sinyali", "cluster": "E", "base_weight": 0.40, "base_sign": 1.0, "role": "state"}
        ]
    }
}

# ---------------------------------------------------------------------------
# v15.0 — Factor ROLE: "direction" (default) vs "state"
# ---------------------------------------------------------------------------
# A "state" factor is still computed, shown, logged to the replay panel and
# offered to the walk-forward learned model (which may use it with ANY sign),
# but it is NOT added to the hand-weighted DIRECTION score.
# Reason (validation_reports/factor_panel.csv.gz, 2024-10 → 2026-09, 3 equal
# time periods, signed IC vs next 24h return):
#   SPX vix_term / vix_term_lead : -0.067 -0.214 -0.088  (wrong sign 3/3)
#   NQ  vix_term / vix_term_lead : -0.034 -0.210 -0.077  (wrong sign 3/3)
#   SPX vix_strain               : -0.001 -0.093 -0.048
#   vix_term and vix_term_lead have rank correlation 1.00 (same signal twice);
#   vix_strain 0.75 -> one variable (VIX level) was counted three times.
#   The same factors predict the SIZE of the next move in 3/3 periods
#   (|r24|/vol IC -0.06 … -0.30): volatility is a state, not a direction.
#   asset_direction (4H momentum, the largest weight) has ~0 IC; removing it
#   plus the VIX cluster raised the SPX/NQ score IC in 12/12 period×horizon cells
#   (SPX 24h: +0.054/-0.068/-0.052 -> +0.063/+0.010/-0.015; NQ 72h: +0.009/-0.025/+0.025 -> +0.049/+0.023/+0.110).
# Under dealer long gamma (most days) the last hours' move is absorbed by
# market-maker hedging; momentum and "fear = sell" then point the wrong way.
FACTOR_ROLE_DEFAULT = "direction"


def is_directional(factor: dict) -> bool:
    return str(factor.get("role", FACTOR_ROLE_DEFAULT)) != "state"


ASSET_CLOCKS = {
    "SPX": {"open_utc": 0.0, "close_utc": 24.0, "type": "FUTURES_23H", "continuous": True},
    "NQ":  {"open_utc": 0.0, "close_utc": 24.0, "type": "FUTURES_23H", "continuous": True},
    "XAU": {"open_utc": 0.0, "close_utc": 24.0, "type": "FUTURES_23H", "continuous": True},
    "XAG": {"open_utc": 0.0, "close_utc": 24.0, "type": "FUTURES_23H", "continuous": True},
    "BTC": {"open_utc": 0.0, "close_utc": 24.0, "type": "CRYPTO_24_7", "continuous": True},
    "ETH": {"open_utc": 0.0, "close_utc": 24.0, "type": "CRYPTO_24_7", "continuous": True}
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

MACRO_EVENT_SYSTEM_SPEC = {
  "system_architecture": {
    "module_name": "macro-event-interpretation-system",
    "version": "1.0",
    "principles": {
      "mutual_exclusivity": True,
      "active_regime_count": 1,
      "normalization": "52_week_rolling_z_score",
      "hysteresis_confirmation_period_weeks": 2,
      "scoring_type": "deterministic"
    }
  },
  "priority_rules": {
    "category_priority": [
      "SHOCK_REGIMES (1, 2, 3, 4)",
      "RISK_ON_REGIME (5)"
    ],
    "conflict_resolution": "IF multiple shock regimes trigger, select the regime with the highest absolute Z-score of its main trigger indicator.",
    "special_conflict_cases": [
      {
        "conflict": "Regime_1 vs Regime_3",
        "resolution": "IF T10YIE 52w_Z > +0.5 THEN Regime_1 ELSE Regime_3"
      }
    ],
    "fallback_rule": "IF no threshold is met THEN state = 'REJIMSIZ_GECIS' AND retain previous confirmed regime (hysteresis)."
  },
  "regimes": [
    {
      "id": 1,
      "name": "Küresel Enflasyon & Stagflasyon Şoku",
      "type": "SHOCK",
      "triggers": {
        "logic": "AND",
        "conditions": [
          {"indicator": "Petrol Şoku", "threshold": "Z > 1.5"},
          {"indicator": "Navlun/Ticaret Çöküşü", "threshold": "Z < -1.0"}
        ]
      }
    },
    {
      "id": 2,
      "name": "Sistemik Likidite Şoku & Carry Çöküşü",
      "type": "SHOCK",
      "triggers": {
        "logic": "OR_OR_OR",
        "conditions": [
          {"indicator": "Geniş Dolar Gücü", "threshold": "Z > 1.0"},
          {"indicator": "JPY Carry Unwind", "threshold": "Z < -2.0"},
          {"indicator": "Volatilite Şoku", "threshold": "Z > 1.5"}
        ]
      }
    },
    {
      "id": 3,
      "name": "Reel Faiz Şoku",
      "type": "SHOCK",
      "triggers": {
        "logic": "AND",
        "conditions": [
          {"indicator": "Ana Tetikleyici (Reel Faiz)", "threshold": "Z > 1.5"},
          {"indicator": "Ayrıştırıcı (Breakeven Enflasyon)", "threshold": "Z < 0.5"}
        ]
      }
    },
    {
      "id": 4,
      "name": "Kredi Temerrüt Baskısı",
      "type": "SHOCK",
      "triggers": {
        "logic": "AND",
        "conditions": [
          {"indicator": "Yüksek Getirili Spread", "threshold": "Z > 2.0"},
          {"indicator": "Trend Teyidi", "threshold": "gradual_expansion (slope > 0)"}
        ]
      }
    },
    {
      "id": 5,
      "name": "Küresel Likidite Rallisi (Risk-On)",
      "type": "RISK_ON",
      "triggers": {
        "logic": "AND",
        "conditions": [
          {"indicator": "Kredi Gücü", "threshold": "Z < -0.5"},
          {"indicator": "Dolar Rejimi", "threshold": "-1.0 <= Z <= 0.5"},
          {"indicator": "Volatilite", "threshold": "percentile < 30"},
          {"indicator": "Net Dolar Likiditesi", "threshold": "Z > 0"}
        ]
      }
    }
  ]
}

REGIME_DYNAMIC_THRESHOLDS = {
    1: {
        "name": "Küresel Enflasyon & Stagflasyon Şoku",
        "buy_enter": 0.85, "buy_exit": 0.35, "sell_enter": -0.50, "sell_exit": -0.20,
        "strong_buy_enter": 1.90, "strong_sell_enter": -1.30, "min_clusters": 3, "risk_scale": 0.70,
        "description": "Enflasyon baskısı: Alış eşiği sıkılaştırıldı (0.85), satış eşiği duyarlılaştırıldı (-0.50)."
    },
    2: {
        "name": "Sistemik Likidite Şoku & Carry Çöküşü",
        "buy_enter": 1.20, "buy_exit": 0.50, "sell_enter": -0.40, "sell_exit": -0.15,
        "strong_buy_enter": 2.20, "strong_sell_enter": -1.10, "min_clusters": 3, "risk_scale": 0.40,
        "description": "Likidite çöküşü: Alışlar aşırı yüksek teyide bağlandı (1.20), satışlar hızlandırıldı (-0.40)."
    },
    3: {
        "name": "Reel Faiz Şoku",
        "buy_enter": 0.80, "buy_exit": 0.30, "sell_enter": -0.55, "sell_exit": -0.25,
        "strong_buy_enter": 1.80, "strong_sell_enter": -1.40, "min_clusters": 2, "risk_scale": 0.75,
        "description": "Reel getiri baskısı: Değerleme şoku, süre riski yüksek varlıklarda alış filtresi (0.80)."
    },
    4: {
        "name": "Kredi Temerrüt Baskısı",
        "buy_enter": 0.95, "buy_exit": 0.40, "sell_enter": -0.45, "sell_exit": -0.20,
        "strong_buy_enter": 2.00, "strong_sell_enter": -1.20, "min_clusters": 3, "risk_scale": 0.50,
        "description": "Kredi temerrüt riski: Spread patlaması, yüksek beta varlıklarda savunma (0.95)."
    },
    5: {
        "name": "Küresel Likidite Rallisi (Risk-On)",
        "buy_enter": 0.50, "buy_exit": 0.25, "sell_enter": -0.80, "sell_exit": -0.35,
        "strong_buy_enter": 1.40, "strong_sell_enter": -1.80, "min_clusters": 2, "risk_scale": 1.25,
        "description": "Likidite rallisi: Alışlar erken tetiklenir (0.50), boğa piyasasında erken satışlar engellenir (-0.80)."
    },
    "REJIMSIZ_GECIS": {
        "name": "Rejimsiz Geçiş / Makro Denge",
        "buy_enter": 0.75, "buy_exit": 0.30, "sell_enter": -0.75, "sell_exit": -0.30,
        "strong_buy_enter": 1.70, "strong_sell_enter": -1.70, "min_clusters": 2, "risk_scale": 0.85,
        "description": "Rejimsiz Geçiş / Denge: Testere filtresi devrede, simetrik eşikler (±0.75 Giriş / ±0.30 Çıkış)."
    }
}


# ---------------------------------------------------------------------------
# Final entry-TIMING gate (gatekeeper.apply_final_entry_gate)
# ---------------------------------------------------------------------------
# These do NOT change forecast direction -- only whether an entry is timed.
# They are deliberately few and explainable; the performance ledger
# (performance_ledger.py) reports hit-rates per entry grade (A/B/C), so any
# future change to these numbers can be justified with measured evidence
# instead of opinion.
ENTRY_TIMING_CONFIG = {
    "ltf_trigger_min": 0.05,          # LTF directional score (x signal sign) needed to count as "trigger turned"
    "max_opposing_confluence": 0.35,  # aggregate multi-TF score against the signal beyond this blocks timing
    "grade_a_min_confluence": 0.35,   # aggregate multi-TF score with the signal needed for grade A
}


# ---------------------------------------------------------------------------
# v3.4 — Self-optimising walk-forward model (walkforward_optimizer.py)
# ---------------------------------------------------------------------------
# The weekly historical replay learns factor weights + drift + regime
# deviations per asset out-of-sample and writes validation_reports/learned_model.json.
#   "advisory": deployed asset -> learned score; not-proven asset -> old score is
#               still computed and SHOWN (direction/velocity/persistence stay
#               live) but tagged "KANITSIZ" and entry permission is closed.  (default)
#   "abstain" : not-proven asset -> no signal at all (NÖTR).
#   "legacy"  : not-proven asset -> old score, entry rules unchanged.
LEARNED_MODEL_POLICY = "advisory"
LEARNED_MODEL_PATH = "validation_reports/learned_model.json"


# ---------------------------------------------------------------------------
# v3.6 — "Kısa Vade Yön (1-4 Saat)": a FORECAST of the next 1h/4h candles,
# not a description of the last bar. Both parts are normalised to z-units;
# price action is capped at the project's 10-30% principle.
# The weekly walk-forward learns these weights from real 4h outcomes and
# overrides them only when its out-of-sample evidence passes (t >= 2).
# ---------------------------------------------------------------------------
SHORT_TERM_WEIGHTS = {"model": 0.70, "price": 0.30}
SHORT_TERM_SCALES = {"model": 0.60, "price": 1.20}   # typical |score| of each part


# v3.7: where the app downloads the published state bundle (branch `state`).
STATE_REPO = "evsayar33-oss/tier1_quant_terminal"


# ---------------------------------------------------------------------------
# v15.0 — Dealer gamma map (dealer_gamma.py)
# ---------------------------------------------------------------------------
# "advisory": the map only adds notes; it never changes entry permission.
# "active"  : when the map's own ledger has PROVEN the wall effect for an asset
#             (n >= 30 independent days, t >= 2), a long into a near call wall /
#             short into a near put wall in +gamma loses entry permission.
# The map never grants entry and never changes direction.
DEALER_GAMMA_POLICY = "advisory"
