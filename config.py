"""
Configuration: Calibrated Asset Matrices, Barra Cluster Parity & Risk Normalization (v31)
Enhanced with:
- Multicollinearity-Proof Cluster Risk Parity (Balanced Cluster Weights)
- Session-Adaptive ETF Resilience
- Restored Liquid Benchmarks (SPY, QQQ, GC=F, SI=F, BTC-USD, ETH-USD)
- Continuous Duration & Macro Event Calibration
"""

CLUSTERS = {
    "A": "Dolar Riski & Küresel Likidite (DXY, Net Dollar Liquidity, FX Carry)",
    "B": "Faiz, Getiri Eğrisi & Süre Riski (TIPS, 10Y, TLT/SHY)",
    "C": "Kredi, Bankacılık & Volatilite (HYG/LQD, KRE, VIX Term)",
    "D": "Emtia, Enflasyon & Sektörel Rotasyon (Petrol, Bakır, Altın)",
    "E": "Varlığa Özel İtici Güç & Mikro Yapı (4H Momentum, Çip, Taker, Sıkışma)"
}

# Kalibre Edilmiş Sinyal Eşikleri (±0.60 Giriş, ±0.30 Çıkış)
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

# =============================================================================
# 🎯 BARRA KÜME RİSK PARİTESİ İLE KALİBRE EDİLMİŞ MATRİSLER
# =============================================================================
ASSET_MATRICES = {
    "SPX": {
        "name": "S&P 500 Index",
        "benchmark_symbol": "SPY",
        "vol_scale": 1.0,
        "factors": [
            # Küme E: Varlığa Özel & Mikro Yapı (Dengeli: Toplam ~2.6)
            {"id": "asset_direction", "name": "SPY 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 1.80, "base_sign": 1.0},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 0.80, "base_sign": 1.0},
            {"id": "market_breadth", "name": "RSP/SPY Piyasa Katılım Genişliği", "cluster": "E", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "defensive_flight", "name": "XLU/SPY Kurumsal Defansif Kaçış", "cluster": "E", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "consumer_demand", "name": "XLY/XLP Tüketici Talebi & Büyüme", "cluster": "E", "base_weight": 0.55, "base_sign": 1.0},
            # Küme B: Faiz & Süre (Toplam ~1.2)
            {"id": "equity_duration_drag", "name": "10Y Reel Faiz Değerleme Baskısı", "cluster": "B", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT/SHY Uzun Vade Tahvil Süre Riski", "cluster": "B", "base_weight": 0.55, "base_sign": 1.0},
            # Küme C: Kredi & Volatilite (Multicollinearity Düzeltildi: Toplam ~2.0)
            {"id": "banking_stress", "name": "KRE/SPY Bölgesel Bankacılık Likiditesi", "cluster": "C", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "credit_spread", "name": "HYG/LQD Kredi Gücü & İştahı", "cluster": "C", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "vix_strain", "name": "VIX Opsiyon Korku Primi", "cluster": "C", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "vix_term", "name": "VIX/VIX3M Dealer Gamma & Vade Eğrisi", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0},
            # Küme D: Emtia & Enflasyon
            {"id": "stagflation_shock", "name": "Petrol / Ticaret (IYT) Şoku", "cluster": "D", "base_weight": 0.50, "base_sign": -1.0},
            # Küme A: Dolar Riski & Küresel Likidite (Toplam ~1.8)
            {"id": "usd_strength", "name": "DXY Kısa Vade Dolar Baskısı", "cluster": "A", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry & Küresel Likidite", "cluster": "A", "base_weight": 0.55, "base_sign": 1.0}
        ]
    },
    "NQ": {
        "name": "NASDAQ 100",
        "benchmark_symbol": "QQQ",
        "vol_scale": 1.2,
        "factors": [
            # Küme E: Teknoloji & İdiosinkratik
            {"id": "asset_direction", "name": "QQQ 4H Anlık Fiyat Hızı", "cluster": "E", "base_weight": 1.80, "base_sign": 1.0},
            {"id": "semi_lead", "name": "SMH Çip / AI Sektör İvmesi", "cluster": "E", "base_weight": 0.95, "base_sign": 1.0},
            {"id": "tech_breadth_dispersion", "name": "Çip & Yüksek Beta Ayrışması", "cluster": "E", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "speculative_beta", "name": "ARKK/QQQ Yüksek Beta Spekülasyon", "cluster": "E", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "defensive_flight", "name": "XLU/QQQ Kurumsal Defansif Kaçış", "cluster": "E", "base_weight": 0.50, "base_sign": -1.0},
            # Küme B: Faiz & Süre
            {"id": "equity_duration_drag", "name": "Teknoloji Değerleme / Reel Getiri Baskısı", "cluster": "B", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT Tahvil Süre Duyarlılığı", "cluster": "B", "base_weight": 0.55, "base_sign": 1.0},
            # Küme C: Kredi & Volatilite
            {"id": "banking_stress", "name": "Finansal Sistem Likidite Stresi (KRE)", "cluster": "C", "base_weight": 0.40, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Kredi Piyasası Gücü (HYG/LQD)", "cluster": "C", "base_weight": 0.50, "base_sign": 1.0},
            {"id": "vix_strain", "name": "Teknoloji Volatilite Baskısı", "cluster": "C", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "vix_term", "name": "VIX Vade Eğrisi & Gamma Stresi", "cluster": "C", "base_weight": 0.60, "base_sign": -1.0},
            # Küme D: Enerji
            {"id": "stagflation_shock", "name": "Petrol / Enerji Baskısı", "cluster": "D", "base_weight": 0.45, "base_sign": -1.0},
            # Küme A: Dolar & Carry
            {"id": "usd_strength", "name": "DXY Dolar Likidite Sıkışması", "cluster": "A", "base_weight": 0.60, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry Tasfiye Riski", "cluster": "A", "base_weight": 0.55, "base_sign": 1.0}
        ]
    },
    "XAU": {
        "name": "Ons Altın (Gold)",
        "benchmark_symbol": "GC=F",
        "vol_scale": 1.0,
        "factors": [
            {"id": "asset_direction", "name": "Altın 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 1.90, "base_sign": 1.0},
            {"id": "gold_sovereign_decoupling", "name": "🏛️ Merkez Bankası & Jeopolitik Rezerv Talebi", "cluster": "E", "base_weight": 1.00, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz (TIPS Ters Oran)", "cluster": "B", "base_weight": 0.85, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Uzun Vade Tahvil Gücü", "cluster": "B", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Bankacılık Güven Krizi Primi (KRE)", "cluster": "C", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "safe_haven", "name": "Jeopolitik & Güvenli Liman", "cluster": "C", "base_weight": 0.80, "base_sign": 1.0},
            {"id": "gold_oil_ratio", "name": "Altın / Petrol Şoku (Stagflasyon)", "cluster": "D", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Döngüsü", "cluster": "D", "base_weight": 0.55, "base_sign": -1.0},
            {"id": "gsr_velocity", "name": "Altın/Gümüş Rasyosu (GSR)", "cluster": "D", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "usd_strength", "name": "DXY Spot Dolar Baskısı", "cluster": "A", "base_weight": 0.75, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Dolar Rezerv / Net Likidite İvmesi", "cluster": "A", "base_weight": 0.65, "base_sign": 1.0}
        ]
    },
    "XAG": {
        "name": "Ons Gümüş (Silver)",
        "benchmark_symbol": "SI=F",
        "vol_scale": 1.25,
        "factors": [
            {"id": "asset_direction", "name": "Gümüş 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 1.70, "base_sign": 1.0},
            {"id": "gold_sympathy", "name": "🥇 Altın Güç İvmesi (Gold Beta)", "cluster": "E", "base_weight": 1.50, "base_sign": 1.0},
            {"id": "silver_monetary_catchup", "name": "🥈 Gümüş Parasal Yakalama & Değerleme İvmesi", "cluster": "E", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "copper_gold", "name": "Bakır/Altın Sanayi Talebi", "cluster": "D", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "silver_copper", "name": "Gümüş / Bakır Sanayi Rotasyonu", "cluster": "D", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Tahvil Getiri Baskısı", "cluster": "B", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "real_yield", "name": "10Y Reel Faiz Baskısı (TIP)", "cluster": "B", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "breakeven_infl", "name": "Enflasyon Beklenti Kalkanı", "cluster": "B", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Küresel Kredi & Sanayi İştahı", "cluster": "C", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "usd_strength", "name": "USD Gücü & Dolar Baskısı", "cluster": "A", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.60, "base_sign": 1.0}
        ]
    },
    "BTC": {
        "name": "Bitcoin / USD",
        "benchmark_symbol": "BTC-USD",
        "crypto_ccy": "BTC",
        "vol_scale": 2.0,
        "factors": [
            {"id": "asset_direction", "name": "BTC 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.00, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit Spot & Vadeli Taker Akışı", "cluster": "E", "base_weight": 1.10, "base_sign": 1.0},
            {"id": "stablecoin_usd_impulse", "name": "💵 Kripto-Yerel USD Likiditesi & Taker İştahı", "cluster": "E", "base_weight": 0.95, "base_sign": 1.0},
            {"id": "funding_stress", "name": "Türev Fonlama Oranı (Kaldıraç Riski)", "cluster": "E", "base_weight": 0.75, "base_sign": -1.0},
            {"id": "liquidation_squeeze_risk", "name": "⚠️ Likidasyon & Kaldıraç Sıkışması Riski", "cluster": "E", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "btc_dominance", "name": "BTC Dominansı / Altcoin Rotasyonu", "cluster": "E", "base_weight": 0.45, "base_sign": 1.0},
            {"id": "banking_stress", "name": "Geleneksel Bankacılık Kaçışı (KRE Ters)", "cluster": "C", "base_weight": 0.25, "base_sign": -1.0},
            {"id": "duration_risk", "name": "TLT Küresel Tahvil Likidite Baskısı", "cluster": "B", "base_weight": 0.45, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Küresel Likidite İştahı (HYG/LQD)", "cluster": "C", "base_weight": 0.65, "base_sign": 1.0},
            {"id": "real_yield", "name": "Reel Getiri Baskısı (TIP)", "cluster": "B", "base_weight": 0.50, "base_sign": -1.0},
            {"id": "vix_strain", "name": "Sistemik Volatilite Baskısı", "cluster": "C", "base_weight": 0.50, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.80, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry & Risk-On Likiditesi", "cluster": "A", "base_weight": 0.55, "base_sign": 1.0}
        ]
    },
    "ETH": {
        "name": "Ethereum / USD",
        "benchmark_symbol": "ETH-USD",
        "crypto_ccy": "ETH",
        "vol_scale": 2.2,
        "factors": [
            {"id": "asset_direction", "name": "ETH 4H Anlık Fiyat İvmesi", "cluster": "E", "base_weight": 2.00, "base_sign": 1.0},
            {"id": "crypto_taker", "name": "OKX/Bybit ETH Taker Alış Akışı", "cluster": "E", "base_weight": 1.00, "base_sign": 1.0},
            {"id": "stablecoin_usd_impulse", "name": "💵 Kripto-Yerel USD Likiditesi & Stabilcoin Akışı", "cluster": "E", "base_weight": 0.85, "base_sign": 1.0},
            {"id": "funding_stress", "name": "Canlı ETH Fonlama Oranı (Funding Riski)", "cluster": "E", "base_weight": 0.70, "base_sign": -1.0},
            {"id": "liquidation_squeeze_risk", "name": "⚠️ ETH Türev Kaldıraç & Sıkışma Riski", "cluster": "E", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "btc_sympathy", "name": "⚡ Bitcoin İtici Gücü (BTC Beta)", "cluster": "E", "base_weight": 0.55, "base_sign": 1.0},
            {"id": "eth_btc_beta", "name": "ETH/BTC Göreceli Güç (Risk İştahı)", "cluster": "E", "base_weight": 0.45, "base_sign": 1.0},
            {"id": "eth_staking_utility_drift", "name": "⛓️ L1 Ağ Aktivitesi & DeFi Likidite İvmesi", "cluster": "E", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "duration_risk", "name": "TLT Likidite Baskısı", "cluster": "B", "base_weight": 0.45, "base_sign": 1.0},
            {"id": "credit_spread", "name": "Kurumsal Kredi & Likidite", "cluster": "C", "base_weight": 0.60, "base_sign": 1.0},
            {"id": "vix_strain", "name": "Sistemik Volatilite Baskısı", "cluster": "C", "base_weight": 0.50, "base_sign": -1.0},
            {"id": "usd_strength", "name": "DXY Dolar Likidite Baskısı", "cluster": "A", "base_weight": 0.65, "base_sign": -1.0},
            {"id": "net_dollar_liquidity", "name": "Fed Net Dolar Likiditesi (NDL)", "cluster": "A", "base_weight": 0.75, "base_sign": 1.0},
            {"id": "usd_jpy_carry", "name": "USD/JPY Carry Likiditesi", "cluster": "A", "base_weight": 0.50, "base_sign": 1.0}
        ]
    }
}

ASSET_CLOCKS = {
    "SPX": {"open_utc": 13.5, "close_utc": 20.0, "type": "TRADITIONAL"},
    "NQ":  {"open_utc": 13.5, "close_utc": 20.0, "type": "TRADITIONAL"},
    "XAU": {"open_utc": 0.0,  "close_utc": 24.0, "type": "FUTURES_23H"},
    "XAG": {"open_utc": 0.0,  "close_utc": 24.0, "type": "FUTURES_23H"},
    "BTC": {"open_utc": 0.0,  "close_utc": 24.0, "type": "CRYPTO_24_7"},
    "ETH": {"open_utc": 0.0,  "close_utc": 24.0, "type": "CRYPTO_24_7"}
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
          {
            "indicator": "Petrol Şoku",
            "ticker": "Brent or WTI Spot",
            "formula": "20_day_return_52w_zscore",
            "threshold": "Z > 1.5"
          },
          {
            "indicator": "Navlun/Ticaret Çöküşü",
            "ticker": "Baltic Dry Index (BDI)",
            "formula": "52w_zscore_level",
            "threshold": "Z < -1.0"
          }
        ]
      },
      "confirmations": {
        "logic": "AND",
        "conditions": [
          {
            "indicator": "Kredi Stresi",
            "ticker": "FRED:BAMLH0A0HYM2 (HY OAS)",
            "formula": "52w_zscore",
            "threshold": "Z > 0.5"
          },
          {
            "indicator": "Hisse/Tahvil Korelasyonu",
            "ticker": "SPX & UST10Y Returns",
            "formula": "60_day_rolling_correlation",
            "threshold": "correlation > 0"
          }
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
          {
            "indicator": "Geniş Dolar Gücü",
            "ticker": "FRED:DTWEXBGS",
            "formula": "5_day_change_52w_zscore",
            "threshold": "Z > 1.0"
          },
          {
            "indicator": "JPY Carry Unwind",
            "ticker": "USD/JPY Spot",
            "formula": "1_day_change_52w_zscore",
            "threshold": "Z < -2.0"
          },
          {
            "indicator": "Volatilite Şoku",
            "ticker": "FRED:VIXCLS (VIX)",
            "formula": "level_52w_zscore",
            "threshold": "Z > 1.5"
          }
        ]
      },
      "confirmations": {
        "logic": "AND",
        "conditions": [
          {
            "indicator": "Risk Varlığı Satışı",
            "ticker": "BTC + SPX Equal-Weighted Basket",
            "formula": "5_day_return_52w_zscore",
            "threshold": "Z < -1.5"
          }
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
          {
            "indicator": "Ana Tetikleyici (Reel Faiz)",
            "ticker": "FRED:DFII10 (10Y TIPS)",
            "formula": "1_day_change_52w_zscore",
            "threshold": "Z > 1.5"
          },
          {
            "indicator": "Ayrıştırıcı (Breakeven Enflasyon)",
            "ticker": "FRED:T10YIE",
            "formula": "52w_zscore",
            "threshold": "Z < 0.5"
          }
        ]
      },
      "sub_types": [
        {
          "label": "Bear Steepener (Enflasyon/Term Premium)",
          "condition": "ΔDGS2 < 0 AND ΔDGS10 > 0"
        },
        {
          "label": "Bear Steepener (Fed Varyantı)",
          "condition": "ΔDGS2 > 0 AND ΔDGS10 > 0 AND ΔDGS10 > ΔDGS2"
        },
        {
          "label": "Bear Flattener (Fed Sıkılaştırma Baskın)",
          "condition": "ΔDGS2 > 0 AND ΔDGS10 > 0 AND ΔDGS2 > ΔDGS10"
        },
        {
          "label": "Bull Flattener/Steepener (Gevşeme - Tetiklemez)",
          "condition": "ΔDGS2 < 0 AND ΔDGS10 < 0"
        }
      ]
    },
    {
      "id": 4,
      "name": "Kredi Temerrüt Baskısı",
      "type": "SHOCK",
      "triggers": {
        "logic": "AND",
        "conditions": [
          {
            "indicator": "Yüksek Getirili Spread",
            "ticker": "FRED:BAMLH0A0HYM2 (HY OAS)",
            "formula": "52w_zscore_level",
            "threshold": "Z > 2.0"
          },
          {
            "indicator": "Trend Teyidi",
            "ticker": "FRED:BAMLH0A0HYM2 (HY OAS)",
            "formula": "10_day_rolling_slope",
            "threshold": "gradual_expansion (slope > 0)"
          }
        ]
      },
      "confirmations": {
        "logic": "AND",
        "conditions": [
          {
            "indicator": "Yatırım Yapılabilir Spread",
            "ticker": "FRED:BAMLC0A0CM (IG OAS)",
            "formula": "52w_zscore_level",
            "threshold": "Z > 1.0"
          }
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
          {
            "indicator": "Kredi Gücü",
            "ticker": "FRED:BAMLH0A0HYM2 (HY OAS)",
            "formula": "52w_zscore",
            "threshold": "Z < -0.5"
          },
          {
            "indicator": "Dolar Rejimi",
            "ticker": "FRED:DTWEXBGS",
            "formula": "52w_zscore",
            "threshold": "-1.0 <= Z <= 0.5"
          },
          {
            "indicator": "Volatilite",
            "ticker": "VIX or MOVE",
            "formula": "252_day_percentile",
            "threshold": "percentile < 30"
          },
          {
            "indicator": "Net Dolar Likiditesi",
            "ticker": "CMS_NDL_SERIES",
            "formula": "52w_zscore",
            "threshold": "Z > 0"
          }
        ]
      },
      "sub_types_post_hoc": [
        {
          "label": "Reflasyonist Risk-On",
          "condition": "DTWEXBGS_Z < -0.5 AND Gold_Price == RISING"
        },
        {
          "label": "Klasik Goldilocks Risk-On",
          "condition": "-1.0 <= DTWEXBGS_Z <= 0.5 AND Gold_Price == FLAT_OR_FALLING"
        }
      ]
    }
  ]
}

REGIME_DYNAMIC_THRESHOLDS = {
    1: {
        "name": "Küresel Enflasyon & Stagflasyon Şoku",
        "buy_enter": 0.85,
        "buy_exit": 0.40,
        "sell_enter": -0.45,
        "sell_exit": -0.20,
        "strong_buy_enter": 1.90,
        "strong_sell_enter": -1.30,
        "min_clusters": 3,
        "risk_scale": 0.70,
        "description": "Enflasyon baskısı: Alış eşiği sıkılaştırıldı (0.85), satış eşiği duyarlılaştırıldı (-0.45)."
    },
    2: {
        "name": "Sistemik Likidite Şoku & Carry Çöküşü",
        "buy_enter": 1.20,
        "buy_exit": 0.60,
        "sell_enter": -0.35,
        "sell_exit": -0.15,
        "strong_buy_enter": 2.20,
        "strong_sell_enter": -1.10,
        "min_clusters": 3,
        "risk_scale": 0.40,
        "description": "Likidite çöküşü: Alışlar aşırı yüksek teyide bağlandı (1.20), satışlar hızlandırıldı (-0.35)."
    },
    3: {
        "name": "Reel Faiz Şoku",
        "buy_enter": 0.80,
        "buy_exit": 0.35,
        "sell_enter": -0.50,
        "sell_exit": -0.25,
        "strong_buy_enter": 1.80,
        "strong_sell_enter": -1.40,
        "min_clusters": 2,
        "risk_scale": 0.75,
        "description": "Reel getiri baskısı: Değerleme şoku, süre riski yüksek varlıklarda alış filtresi (0.80)."
    },
    4: {
        "name": "Kredi Temerrüt Baskısı",
        "buy_enter": 0.95,
        "buy_exit": 0.45,
        "sell_enter": -0.40,
        "sell_exit": -0.20,
        "strong_buy_enter": 2.00,
        "strong_sell_enter": -1.20,
        "min_clusters": 3,
        "risk_scale": 0.50,
        "description": "Kredi temerrüt riski: Spread patlaması, yüksek beta varlıklarda savunma (0.95)."
    },
    5: {
        "name": "Küresel Likidite Rallisi (Risk-On)",
        "buy_enter": 0.45,
        "buy_exit": 0.20,
        "sell_enter": -0.85,
        "sell_exit": -0.40,
        "strong_buy_enter": 1.40,
        "strong_sell_enter": -1.80,
        "min_clusters": 2,
        "risk_scale": 1.25,
        "description": "Likidite rallisi: Alışlar erken tetiklenir (0.45), boğa piyasasında erken satışlar engellenir (-0.85)."
    },
    "REJIMSIZ_GECIS": {
        "name": "Rejimsiz Geçiş / Makro Denge",
        "buy_enter": 0.75,
        "buy_exit": 0.35,
        "sell_enter": -0.75,
        "sell_exit": -0.35,
        "strong_buy_enter": 1.70,
        "strong_sell_enter": -1.70,
        "min_clusters": 2,
        "risk_scale": 0.85,
        "description": "Rejimsiz Geçiş / Denge: Testere filtresi devrede, dengeli simetrik eşikler (±0.75)."
    }
}
