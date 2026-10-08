# 🧭 Uzun Dönem Laboratuvarı v8 — ~10 yıl, son 2 yıl mühürlü sınav

_Üretim: 2026-10-08T11:00 UTC. Son 730 gün hiçbir seçimde kullanılmadı; seçim yalnızca önceki dönemde yapıldı, sınav bir kez uygulandı._

**Kanıt şartı (önceden sabit):** eğitimde yıllık walk-forward t ≥ 2 ve yılların ≥%60'ı pozitif · DSR ≥ 0.90 · sınavda t ≥ 1.5 ve sürekli long'a karşı alfa t ≥ 1.0. Kararlar günlük kapanış verisiyle, ertesi gün açılışında uygulanır; komisyon/kayma ve perp fonlaması düşülmüştür.

⚠️ Sistem burada **günlük saatle** çalıştırıldı (canlı sistem saatlik çalışır; içindeki 'N mum' hesapları burada 'N gün'). Bu, sistemin haftalık/aylık ufuktaki değerini ölçmek için doğru sorudur; saatlik sistemin birebir kopyası değildir.

## 1) Varlık bazında sonuç

| Varlık | Eğitim → sınav | Kural sayısı (etkin) | Seçilen kural (eğitimin en iyisi) | Eğitim Sharpe | **Sınav Sharpe** | Sınav getiri / DD | Sınav t · alfa t | WF Sharpe (t) · + yıl | DSR | Sürekli long eğitim / sınav | Durum |
|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC | 2016–2024-10 → 2026-10 | 6,005 (19) | live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.53 | **-0.82** | %-25.3 / %-37.2 | -1.2 · -1.3 | 0.37 (+0.9) · %50 | 1.00 | 0.65 / 0.08 | ❌ kanıt yok |
| ETH | 2017–2024-10 → 2026-10 | 5,977 (18) | TERS bear_clusters (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.49 | **0.50** | %+62.3 / %-37.8 | +0.7 · +0.7 | 0.20 (+0.4) · %60 | 0.98 | 0.22 / -0.12 | ❌ kanıt yok |
| NQ | 2016–2024-10 → 2026-10 | 6,253 (15) | Volatilite desteği (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.02 | **0.25** | %+3.1 / %-8.9 | +0.3 · +0.1 | 0.50 (+1.2) · %50 | 0.88 | 0.30 / 0.52 | ❌ kanıt yok |
| SPX | 2016–2024-10 → 2026-10 | 6,145 (14) | TERS direction_velocity (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış | 1.07 | **0.43** | %+4.5 / %-4.6 | +0.6 · +0.5 | 0.15 (+0.4) · %67 | 0.90 | 0.08 / 0.28 | ❌ kanıt yok |
| XAG | 2016–2024-10 → 2026-10 | 5,961 (17) | Momentum (60 gün) (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.85 | **0.69** | %+19.4 / %-10.8 | +1.0 · +0.9 | -0.21 (-0.5) · %17 | 0.74 | -0.12 / 0.38 | ❌ kanıt yok |
| XAU | 2016–2024-10 → 2026-10 | 6,005 (17) | Faktör: net_dollar_liquidity (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.77 | **0.00** | %+0.0 / %-0.0 | +0.0 · +0.0 | -0.58 (-1.4) · %17 | 0.64 | -0.10 / 0.45 | ❌ kanıt yok |

## 2) 'Harika geçmiş test' sınavda ne oluyor? (eğitimin ilk 20'si ve sınav sonuçları)

**BTC**

| # | Kural | Eğitim Sharpe | Sınav Sharpe | Sınav getiri | İşlem (eğitim) |
|---|---|---|---|---|---|
| 1 | live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.53 | -0.82 | %-25.3 | 128 |
| 2 | live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 1.44 | -0.94 | %-29.9 | 128 |
| 3 | adaptive_cluster_scores.B · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.41 | -0.30 | %-11.7 | 118 |
| 4 | live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.41 | -0.58 | %-21.6 | 142 |
| 5 | direction_velocity · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.34 | -0.80 | %-33.2 | 232 |
| 6 | adaptive_cluster_scores.B · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.33 | -0.27 | %-16.5 | 119 |
| 7 | short_term_parts.price_part (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 1.32 | 0.14 | %+6.2 | 136 |
| 8 | adaptive_cluster_scores.B · 1 gün · sadece long · iz süren stop 3×ATR | 1.31 | 0.42 | %+24.3 | 612 |
| 9 | Faktör: duration_risk (güçlü ∣z∣>0.5) · 1 gün · sadece long · iz süren stop 3×ATR | 1.28 | -1.13 | %-30.7 | 210 |
| 10 | EMA trend (50 gün) (güçlü ∣z∣>0.5) · 1 gün · sadece long · iz süren stop 3×ATR | 1.27 | 0.32 | %+15.0 | 150 |
| 11 | Faktör: duration_risk (güçlü ∣z∣>0.5) · 1 gün · sadece long · sinyalle çıkış | 1.25 | -1.02 | %-35.4 | 210 |
| 12 | EMA trend (50 gün) (güçlü ∣z∣>0.5) · 1 gün · sadece long · sinyalle çıkış | 1.25 | 0.37 | %+18.7 | 150 |
| 13 | short_term_parts.price_part (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.25 | 0.17 | %+7.3 | 136 |
| 14 | EMA trend (200 gün) (güçlü ∣z∣>0.5) · 1 gün · sadece long · sinyalle çıkış | 1.24 | 0.45 | %+20.4 | 88 |
| 15 | Momentum (20 gün) (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.22 | 0.50 | %+23.1 | 82 |
| 16 | Momentum (20 gün) · 1 gün · sadece long · sinyalle çıkış | 1.22 | 0.24 | %+14.9 | 257 |
| 17 | adaptive_cluster_scores.B (güçlü ∣z∣>0.5) · 1 gün · long+short · iz süren stop 3×ATR | 1.22 | -0.59 | %-32.9 | 967 |
| 18 | Zaman dilimi uyumu · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.18 | 0.12 | %+6.3 | 137 |
| 19 | Faktör: duration_risk · 1 gün · sadece long · iz süren stop 3×ATR | 1.18 | -0.16 | %-6.7 | 236 |
| 20 | live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış | 1.17 | -0.86 | %-35.7 | 142 |

**ETH**

| # | Kural | Eğitim Sharpe | Sınav Sharpe | Sınav getiri | İşlem (eğitim) |
|---|---|---|---|---|---|
| 1 | TERS bear_clusters (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.49 | 0.50 | %+62.3 | 211 |
| 2 | TERS bear_clusters (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.47 | 0.39 | %+25.3 | 132 |
| 3 | Faktör: duration_risk · 1 gün · long+short · iz süren stop 3×ATR | 1.44 | -0.55 | %-44.3 | 224 |
| 4 | TERS bear_clusters (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 1.35 | 0.41 | %+30.7 | 132 |
| 5 | TERS bear_clusters (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış | 1.34 | 0.71 | %+122.4 | 211 |
| 6 | pair_common_factor.common_score (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.34 | 0.26 | %+15.5 | 118 |
| 7 | Faktör: duration_risk · 1 gün · sadece long · iz süren stop 3×ATR | 1.34 | -0.62 | %-34.4 | 216 |
| 8 | Faktör: duration_risk · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.29 | 0.08 | %+7.2 | 98 |
| 9 | score_raw_cycle (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.28 | 0.70 | %+43.2 | 108 |
| 10 | Model skoru (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.25 | 0.76 | %+48.9 | 106 |
| 11 | score_raw_cycle (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.23 | 0.25 | %+26.8 | 195 |
| 12 | adaptive_cluster_scores.B · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.22 | -0.65 | %-49.3 | 104 |
| 13 | Kısa Vade Yön (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.22 | 0.47 | %+28.7 | 122 |
| 14 | short_term_parts.model_part (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.21 | 0.76 | %+48.9 | 104 |
| 15 | Model z (kısa vade) (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.21 | 0.76 | %+48.9 | 104 |
| 16 | Model skoru (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.21 | 0.36 | %+41.2 | 194 |
| 17 | pair_common_factor.common_score · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.18 | 0.43 | %+58.5 | 138 |
| 18 | Adaptif skor (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.17 | 0.48 | %+29.0 | 114 |
| 19 | Makro model skoru (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.17 | 0.48 | %+29.0 | 114 |
| 20 | Makro model skoru (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · iz süren stop 3×ATR | 1.16 | 0.33 | %+38.2 | 201 |

**NQ**

| # | Kural | Eğitim Sharpe | Sınav Sharpe | Sınav getiri | İşlem (eğitim) |
|---|---|---|---|---|---|
| 1 | Volatilite desteği (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 1.02 | 0.25 | %+3.1 | 19 |
| 2 | Volatilite desteği (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 0.99 | 0.30 | %+7.6 | 19 |
| 3 | TERS ADX trend rejimi (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.90 | -0.28 | %-4.5 | 56 |
| 4 | timeframe_confluence.all_aligned (güçlü ∣z∣>0.5) · 1 gün · sadece long · sinyalle çıkış | 0.90 | 0.00 | %+0.0 | 46 |
| 5 | TERS direction_velocity · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.87 | -0.08 | %-1.2 | 56 |
| 6 | timeframe_confluence.all_aligned (güçlü ∣z∣>0.5) · 1 gün · sadece long · iz süren stop 3×ATR | 0.87 | 0.00 | %+0.0 | 46 |
| 7 | Faktör: duration_risk (güçlü ∣z∣>0.5) · 1 gün · sadece long · iz süren stop 3×ATR | 0.85 | -0.08 | %-1.4 | 214 |
| 8 | Faktör: duration_risk · 1 gün · sadece long · iz süren stop 3×ATR | 0.84 | 0.32 | %+6.8 | 236 |
| 9 | Faktör: tech_vol_premium_lead · 1 hafta ort. · sadece long · sinyalle çıkış | 0.82 | 0.78 | %+25.9 | 85 |
| 10 | Faktör: tech_vol_premium_lead (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış | 0.81 | 0.77 | %+35.8 | 135 |
| 11 | TERS direction_velocity · 1 ay ort. · sadece long · sinyalle çıkış | 0.78 | 0.50 | %+8.6 | 56 |
| 12 | TERS direction_velocity (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış | 0.78 | 0.37 | %+5.4 | 42 |
| 13 | Alt: COT kaldıraçlı fon net · 1 ay ort. · sadece long · sinyalle çıkış | 0.78 | -0.20 | %-1.2 | 8 |
| 14 | adaptive_cluster_scores.B · 1 hafta ort. · sadece long · sinyalle çıkış | 0.78 | 0.29 | %+9.0 | 116 |
| 15 | TERS composite_usd_risk · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.76 | -0.02 | %-0.2 | 16 |
| 16 | TERS Makro: composite_usd_risk · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.76 | -0.02 | %-0.2 | 16 |
| 17 | TERS Giriş notu (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.76 | 0.30 | %+3.5 | 35 |
| 18 | Faktör: tech_vol_premium_lead · 1 ay ort. · sadece long · sinyalle çıkış | 0.74 | 1.11 | %+20.0 | 30 |
| 19 | Faktör: duration_risk · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.74 | 0.92 | %+26.9 | 92 |
| 20 | adaptive_cluster_scores.B · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.74 | 0.75 | %+20.7 | 116 |

**SPX**

| # | Kural | Eğitim Sharpe | Sınav Sharpe | Sınav getiri | İşlem (eğitim) |
|---|---|---|---|---|---|
| 1 | TERS direction_velocity (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış | 1.07 | 0.43 | %+4.5 | 48 |
| 2 | Giriş izni (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.97 | 0.71 | %+14.6 | 134 |
| 3 | TERS live_regime_event (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.95 | 0.60 | %+7.6 | 28 |
| 4 | Giriş izni (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 0.82 | 0.59 | %+13.0 | 134 |
| 5 | Faktör: duration_risk (güçlü ∣z∣>0.5) · 1 gün · sadece long · iz süren stop 3×ATR | 0.78 | -0.71 | %-9.3 | 214 |
| 6 | bear_clusters (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.77 | -0.34 | %-4.0 | 34 |
| 7 | TERS direction_velocity (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.68 | 0.41 | %+3.7 | 48 |
| 8 | TERS Faktör: market_breadth (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.67 | 0.73 | %+8.7 | 42 |
| 9 | TERS direction_warmup (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış | 0.65 | 0.00 | %+0.0 | 6 |
| 10 | Giriş izni (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · iz süren stop 3×ATR | 0.62 | -0.16 | %-4.0 | 220 |
| 11 | Alt: COT dealer net · 1 gün · sadece long · iz süren stop 3×ATR | 0.59 | 0.00 | %+0.0 | 12 |
| 12 | TERS Makro: composite_usd_risk · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.59 | -0.08 | %-0.7 | 16 |
| 13 | TERS composite_usd_risk · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.59 | -0.08 | %-0.7 | 16 |
| 14 | Faktör: defensive_flight (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.58 | 0.32 | %+3.5 | 46 |
| 15 | TERS direction_acceleration · 1 ay ort. · sadece long · sinyalle çıkış | 0.57 | -0.07 | %-1.7 | 48 |
| 16 | Faktör: duration_risk · 1 gün · sadece long · iz süren stop 3×ATR | 0.57 | -0.44 | %-6.4 | 236 |
| 17 | TERS ADX trend rejimi (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.56 | 0.56 | %+10.0 | 74 |
| 18 | Alt: COT kaldıraçlı fon net (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.56 | -0.60 | %-5.0 | 26 |
| 19 | adaptive_cluster_scores.B · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.56 | 0.41 | %+7.8 | 110 |
| 20 | Faktör: duration_risk · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.55 | 0.68 | %+13.5 | 92 |

**XAG**

| # | Kural | Eğitim Sharpe | Sınav Sharpe | Sınav getiri | İşlem (eğitim) |
|---|---|---|---|---|---|
| 1 | Momentum (60 gün) (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.85 | 0.69 | %+19.4 | 16 |
| 2 | Faktör: duration_risk (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.84 | 0.60 | %+27.0 | 92 |
| 3 | TERS direction_persistence (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · iz süren stop 3×ATR | 0.76 | -1.13 | %-53.8 | 244 |
| 4 | TERS Kısa vade=model (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.72 | 0.38 | %+8.4 | 40 |
| 5 | TERS direction_persistence (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.71 | -1.01 | %-46.1 | 187 |
| 6 | Faktör: duration_risk · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.70 | 0.67 | %+34.2 | 92 |
| 7 | TERS Makro: real_yield_z · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.67 | -0.18 | %-6.2 | 47 |
| 8 | TERS Makro: dfii10_z · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.67 | -0.18 | %-6.2 | 47 |
| 9 | Faktör: real_yield · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.66 | -0.18 | %-6.2 | 49 |
| 10 | Faktör: net_dollar_liquidity (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.65 | 0.00 | %+0.0 | 10 |
| 11 | Momentum (60 gün) (güçlü ∣z∣>0.5) · 1 ay ort. · long+short · iz süren stop 3×ATR | 0.65 | -0.06 | %-1.6 | 42 |
| 12 | Yön aşaması · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.63 | 0.61 | %+34.5 | 29 |
| 13 | live_regime_event (güçlü ∣z∣>0.5) · 1 ay ort. · sadece short · iz süren stop 3×ATR | 0.59 | 0.35 | %+7.9 | 35 |
| 14 | TERS timeframe_confluence.weight_total (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.58 | 0.94 | %+27.4 | 19 |
| 15 | Volatilite desteği (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 0.57 | 0.37 | %+34.5 | 19 |
| 16 | pair_stats.divergence_z_used (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 0.57 | 0.17 | %+17.0 | 38 |
| 17 | Alt: COT spekülatif fon net (haftalık değişim) · 1 ay ort. · long+short · sinyalle çıkış | 0.57 | -0.62 | %-48.3 | 48 |
| 18 | TERS Giriş notu (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.56 | -0.23 | %-5.0 | 40 |
| 19 | TERS pair_stats.spread (güçlü ∣z∣>0.5) · 1 ay ort. · sadece short · sinyalle çıkış | 0.56 | -0.72 | %-44.2 | 38 |
| 20 | Volatilite desteği (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış | 0.56 | 0.33 | %+34.0 | 91 |

**XAU**

| # | Kural | Eğitim Sharpe | Sınav Sharpe | Sınav getiri | İşlem (eğitim) |
|---|---|---|---|---|---|
| 1 | Faktör: net_dollar_liquidity (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.77 | 0.00 | %+0.0 | 10 |
| 2 | TERS intraday_regime.adx_val (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış | 0.73 | 0.39 | %+6.9 | 43 |
| 3 | TERS adx_val (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış | 0.73 | 0.39 | %+6.9 | 43 |
| 4 | TERS ADX trend rejimi (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış | 0.62 | 0.09 | %+2.2 | 34 |
| 5 | TERS timeframe_confluence.weight_total (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.60 | 1.26 | %+29.1 | 25 |
| 6 | TERS Alt: COT üretici net (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.59 | -0.06 | %-0.7 | 29 |
| 7 | pair_stats.divergence_z_used (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 0.59 | -0.11 | %-3.9 | 38 |
| 8 | TERS intraday_regime.adx_val (güçlü ∣z∣>0.5) · 1 ay ort. · long+short · sinyalle çıkış | 0.58 | -0.13 | %-3.8 | 56 |
| 9 | TERS adx_val (güçlü ∣z∣>0.5) · 1 ay ort. · long+short · sinyalle çıkış | 0.58 | -0.13 | %-3.8 | 56 |
| 10 | Faktör: net_dollar_liquidity (güçlü ∣z∣>0.5) · 1 gün · sadece long · iz süren stop 3×ATR | 0.55 | 0.00 | %+0.0 | 14 |
| 11 | TERS Makro: composite_usd_risk · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.54 | 0.59 | %+5.3 | 16 |
| 12 | TERS composite_usd_risk · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.54 | 0.59 | %+5.3 | 16 |
| 13 | TERS adaptive_cluster_scores.B · 1 ay ort. · sadece long · sinyalle çıkış | 0.54 | 0.56 | %+21.4 | 27 |
| 14 | Faktör: breakeven_infl (güçlü ∣z∣>0.5) · 1 gün · sadece long · iz süren stop 3×ATR | 0.53 | -0.51 | %-9.0 | 54 |
| 15 | Alt: COT swap dealer net (güçlü ∣z∣>0.5) · 1 gün · sadece long · iz süren stop 3×ATR | 0.52 | 0.25 | %+4.1 | 34 |
| 16 | Faktör: duration_risk (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR | 0.48 | -0.18 | %-4.2 | 92 |
| 17 | Makro: composite_usd_risk (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 0.48 | 0.60 | %+19.6 | 159 |
| 18 | composite_usd_risk (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış | 0.48 | 0.60 | %+19.6 | 159 |
| 19 | adaptive_cluster_scores.A · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.47 | -0.16 | %-1.3 | 17 |
| 20 | TERS Faktör: gold_oil_ratio (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR | 0.47 | -1.01 | %-10.8 | 28 |

## 3) Aile bazında sınav (seçim yanlılığı yok denecek kadar az)

_Bir ailedeki TÜM kuralların sınav ortalaması. 'Sıra korelasyonu': eğitimde iyi olan sınavda da iyi mi? (0 = hayır)._

| Varlık | Aile · ufuk | Kural | Eğitim ort. Sharpe | Sınav ort. Sharpe | Sınavda pozitif | Sıra korelasyonu |
|---|---|---|---|---|---|---|
| BTC | teknik · 1 hafta | 84 | 0.42 | 0.28 | %75 | -0.15 |
| BTC | teknik · 1 gün | 84 | 0.55 | 0.20 | %69 | -0.21 |
| BTC | makro · 1 ay | 120 | 0.17 | 0.05 | %47 | +0.02 |
| BTC | COT · 1 ay | 78 | 0.18 | 0.03 | %47 | -0.27 |
| BTC | sistem · 1 hafta · TERS | 598 | -0.30 | 0.02 | %50 | — |
| BTC | makro · 1 hafta | 120 | 0.04 | 0.01 | %48 | -0.14 |
| BTC | teknik · 1 ay | 84 | 0.42 | -0.05 | %50 | -0.05 |
| BTC | sistem · 1 ay | 604 | 0.13 | -0.07 | %50 | +0.13 |
| BTC | makro · 1 gün · TERS | 120 | -0.02 | -0.08 | %44 | — |
| BTC | COT · 1 hafta | 78 | 0.00 | -0.09 | %40 | -0.24 |
| BTC | faktör · 1 hafta | 120 | 0.25 | -0.10 | %38 | +0.08 |
| BTC | faktör · 1 ay | 120 | 0.15 | -0.11 | %33 | +0.11 |
| BTC | COT · 1 gün · TERS | 78 | -0.09 | -0.12 | %37 | — |
| BTC | faktör · 1 hafta · TERS | 120 | -0.18 | -0.16 | %42 | — |
| BTC | COT · 1 hafta · TERS | 78 | 0.01 | -0.16 | %28 | — |
| BTC | faktör · 1 gün · TERS | 120 | -0.27 | -0.17 | %34 | — |
| BTC | sistem · 1 hafta | 598 | 0.34 | -0.19 | %37 | +0.01 |
| BTC | COT · 1 gün | 78 | 0.07 | -0.19 | %27 | -0.05 |
| BTC | faktör · 1 gün | 120 | 0.17 | -0.21 | %40 | +0.01 |
| BTC | makro · 1 hafta · TERS | 120 | -0.00 | -0.22 | %31 | — |
| BTC | faktör · 1 ay · TERS | 120 | 0.06 | -0.26 | %42 | — |
| BTC | sistem · 1 gün | 594 | 0.11 | -0.29 | %29 | +0.49 |
| BTC | sistem · 1 gün · TERS | 594 | -0.36 | -0.30 | %23 | — |
| BTC | COT · 1 ay · TERS | 78 | -0.08 | -0.34 | %18 | — |
| BTC | makro · 1 gün | 120 | -0.14 | -0.38 | %14 | +0.29 |
| BTC | teknik · 1 hafta · TERS | 84 | -0.36 | -0.39 | %13 | — |
| BTC | makro · 1 ay · TERS | 120 | -0.03 | -0.43 | %20 | — |
| BTC | sistem · 1 ay · TERS | 604 | -0.01 | -0.47 | %25 | — |
| BTC | teknik · 1 gün · TERS | 84 | -0.57 | -0.47 | %17 | — |
| BTC | teknik · 1 ay · TERS | 84 | -0.38 | -0.48 | %14 | — |
| ETH | teknik · 1 hafta | 84 | 0.34 | 0.45 | %82 | -0.65 |
| ETH | teknik · 1 gün | 84 | 0.42 | 0.41 | %86 | -0.29 |
| ETH | sistem · 1 ay | 598 | 0.11 | 0.29 | %69 | +0.35 |
| ETH | faktör · 1 ay | 120 | 0.12 | 0.20 | %63 | +0.21 |
| ETH | makro · 1 ay | 120 | 0.18 | 0.17 | %61 | -0.25 |
| ETH | faktör · 1 hafta | 120 | 0.33 | 0.13 | %61 | -0.10 |
| ETH | makro · 1 hafta | 120 | 0.02 | 0.11 | %66 | -0.46 |
| ETH | COT · 1 gün · TERS | 78 | -0.03 | 0.07 | %53 | — |
| ETH | sistem · 1 hafta | 594 | 0.42 | 0.06 | %56 | +0.09 |
| ETH | faktör · 1 gün | 120 | 0.29 | 0.06 | %43 | -0.28 |
| ETH | COT · 1 ay | 78 | 0.12 | 0.04 | %55 | +0.05 |
| ETH | teknik · 1 ay | 84 | 0.28 | 0.00 | %50 | +0.01 |
| ETH | makro · 1 gün · TERS | 120 | -0.01 | -0.03 | %36 | — |
| ETH | COT · 1 hafta · TERS | 78 | -0.00 | -0.04 | %49 | — |
| ETH | COT · 1 hafta | 78 | 0.00 | -0.09 | %42 | +0.42 |
| ETH | sistem · 1 gün | 590 | 0.19 | -0.12 | %44 | +0.50 |
| ETH | COT · 1 ay · TERS | 78 | -0.10 | -0.14 | %40 | — |
| ETH | sistem · 1 hafta · TERS | 594 | -0.24 | -0.17 | %38 | — |
| ETH | makro · 1 hafta · TERS | 120 | 0.08 | -0.17 | %33 | — |
| ETH | COT · 1 gün | 78 | -0.01 | -0.17 | %41 | +0.44 |
| ETH | faktör · 1 hafta · TERS | 120 | -0.15 | -0.18 | %38 | — |
| ETH | teknik · 1 ay · TERS | 84 | -0.16 | -0.19 | %36 | — |
| ETH | makro · 1 gün | 120 | -0.07 | -0.20 | %23 | +0.14 |
| ETH | sistem · 1 gün · TERS | 590 | -0.34 | -0.21 | %31 | — |
| ETH | makro · 1 ay · TERS | 120 | -0.01 | -0.27 | %31 | — |
| ETH | faktör · 1 gün · TERS | 120 | -0.30 | -0.31 | %28 | — |
| ETH | faktör · 1 ay · TERS | 120 | 0.10 | -0.31 | %33 | — |
| ETH | sistem · 1 ay · TERS | 598 | 0.06 | -0.41 | %28 | — |
| ETH | teknik · 1 gün · TERS | 84 | -0.32 | -0.59 | %17 | — |
| ETH | teknik · 1 hafta · TERS | 84 | -0.21 | -0.62 | %12 | — |
| NQ | teknik · 1 hafta | 84 | -0.20 | 0.05 | %54 | +0.54 |
| NQ | makro · 1 ay | 120 | -0.25 | 0.04 | %51 | -0.10 |
| NQ | sistem · 1 hafta · TERS | 542 | -0.26 | -0.10 | %47 | — |
| NQ | makro · 1 hafta · TERS | 120 | -0.12 | -0.10 | %35 | — |
| NQ | COT · 1 ay | 78 | -0.16 | -0.10 | %41 | +0.25 |
| NQ | sistem · 1 ay | 550 | -0.19 | -0.13 | %43 | -0.13 |
| NQ | COT · 1 gün | 78 | -0.25 | -0.13 | %44 | +0.25 |
| NQ | teknik · 1 gün | 84 | -0.30 | -0.17 | %35 | +0.67 |
| NQ | faktör · 1 ay | 216 | -0.15 | -0.20 | %40 | +0.06 |
| NQ | teknik · 1 ay | 84 | -0.14 | -0.20 | %37 | +0.13 |
| NQ | teknik · 1 ay · TERS | 84 | -0.25 | -0.22 | %32 | — |
| NQ | COT · 1 hafta | 78 | -0.24 | -0.24 | %32 | -0.31 |
| NQ | faktör · 1 hafta · TERS | 216 | -0.32 | -0.26 | %37 | — |
| NQ | teknik · 1 gün · TERS | 84 | -0.27 | -0.26 | %39 | — |
| NQ | faktör · 1 hafta | 216 | -0.22 | -0.31 | %30 | +0.32 |
| NQ | faktör · 1 ay · TERS | 216 | -0.26 | -0.38 | %38 | — |
| NQ | COT · 1 ay · TERS | 78 | -0.25 | -0.38 | %33 | — |
| NQ | COT · 1 hafta · TERS | 78 | -0.25 | -0.39 | %27 | — |
| NQ | teknik · 1 hafta · TERS | 84 | -0.23 | -0.41 | %29 | — |
| NQ | faktör · 1 gün · TERS | 216 | -0.49 | -0.42 | %25 | — |
| NQ | makro · 1 hafta | 120 | -0.42 | -0.42 | %25 | +0.39 |
| NQ | sistem · 1 hafta | 542 | -0.31 | -0.43 | %25 | +0.20 |
| NQ | makro · 1 gün · TERS | 120 | -0.30 | -0.46 | %23 | — |
| NQ | COT · 1 gün · TERS | 78 | -0.31 | -0.47 | %26 | — |
| NQ | sistem · 1 ay · TERS | 550 | -0.23 | -0.49 | %29 | — |
| NQ | sistem · 1 gün · TERS | 540 | -0.50 | -0.52 | %23 | — |
| NQ | makro · 1 ay · TERS | 120 | -0.14 | -0.52 | %25 | — |
| NQ | sistem · 1 gün | 540 | -0.54 | -0.55 | %20 | +0.41 |
| NQ | faktör · 1 gün | 216 | -0.39 | -0.56 | %14 | +0.19 |
| NQ | makro · 1 gün | 120 | -0.68 | -0.65 | %12 | +0.57 |
| SPX | makro · 1 ay | 120 | -0.29 | 0.08 | %53 | -0.06 |
| SPX | sistem · 1 hafta · TERS | 542 | -0.31 | -0.04 | %53 | — |
| SPX | makro · 1 hafta · TERS | 120 | -0.16 | -0.10 | %35 | — |
| SPX | sistem · 1 ay | 550 | -0.38 | -0.13 | %45 | -0.06 |
| SPX | teknik · 1 hafta | 84 | -0.40 | -0.16 | %39 | +0.16 |
| SPX | COT · 1 ay · TERS | 72 | -0.22 | -0.17 | %38 | — |
| SPX | teknik · 1 ay · TERS | 84 | -0.20 | -0.20 | %39 | — |
| SPX | teknik · 1 ay | 84 | -0.28 | -0.24 | %36 | +0.19 |
| SPX | COT · 1 gün | 72 | -0.24 | -0.25 | %31 | -0.22 |
| SPX | faktör · 1 hafta · TERS | 204 | -0.39 | -0.28 | %33 | — |
| SPX | teknik · 1 gün | 84 | -0.38 | -0.28 | %31 | +0.19 |
| SPX | COT · 1 hafta · TERS | 72 | -0.32 | -0.30 | %36 | — |
| SPX | teknik · 1 gün · TERS | 84 | -0.43 | -0.33 | %40 | — |
| SPX | faktör · 1 ay · TERS | 204 | -0.27 | -0.34 | %39 | — |
| SPX | COT · 1 hafta | 72 | -0.33 | -0.35 | %32 | +0.01 |
| SPX | COT · 1 gün · TERS | 72 | -0.50 | -0.36 | %25 | — |
| SPX | COT · 1 ay | 72 | -0.27 | -0.38 | %29 | +0.38 |
| SPX | faktör · 1 ay | 204 | -0.30 | -0.40 | %32 | +0.15 |
| SPX | teknik · 1 hafta · TERS | 84 | -0.24 | -0.41 | %26 | — |
| SPX | faktör · 1 hafta | 204 | -0.35 | -0.43 | %23 | +0.35 |
| SPX | sistem · 1 ay · TERS | 550 | -0.16 | -0.54 | %26 | — |
| SPX | makro · 1 gün · TERS | 120 | -0.41 | -0.63 | %14 | — |
| SPX | makro · 1 hafta | 120 | -0.55 | -0.63 | %12 | +0.49 |
| SPX | faktör · 1 gün · TERS | 204 | -0.71 | -0.64 | %21 | — |
| SPX | sistem · 1 hafta | 542 | -0.45 | -0.69 | %12 | +0.26 |
| SPX | faktör · 1 gün | 204 | -0.45 | -0.70 | %15 | +0.09 |
| SPX | sistem · 1 gün | 540 | -0.61 | -0.72 | %9 | +0.43 |
| SPX | makro · 1 ay · TERS | 120 | -0.21 | -0.75 | %16 | — |
| SPX | sistem · 1 gün · TERS | 540 | -0.66 | -0.76 | %11 | — |
| SPX | makro · 1 gün | 120 | -0.82 | -0.86 | %4 | +0.71 |
| XAG | makro · 1 hafta · TERS | 120 | -0.27 | 0.28 | %70 | — |
| XAG | sistem · 1 ay | 562 | -0.08 | 0.13 | %60 | -0.18 |
| XAG | faktör · 1 ay | 156 | -0.12 | 0.07 | %52 | -0.06 |
| XAG | makro · 1 gün · TERS | 120 | -0.47 | 0.05 | %52 | — |
| XAG | COT · 1 ay | 78 | -0.13 | 0.04 | %47 | -0.77 |
| XAG | COT · 1 gün · TERS | 78 | -0.18 | 0.03 | %47 | — |
| XAG | teknik · 1 ay | 84 | -0.05 | 0.03 | %55 | +0.08 |
| XAG | sistem · 1 hafta · TERS | 554 | -0.11 | 0.00 | %50 | — |
| XAG | teknik · 1 hafta · TERS | 84 | 0.02 | -0.02 | %44 | — |
| XAG | faktör · 1 hafta · TERS | 156 | -0.16 | -0.03 | %49 | — |
| XAG | COT · 1 hafta · TERS | 78 | -0.27 | -0.04 | %40 | — |
| XAG | makro · 1 ay | 120 | -0.16 | -0.05 | %48 | -0.22 |
| XAG | teknik · 1 gün · TERS | 84 | -0.21 | -0.09 | %36 | — |
| XAG | faktör · 1 hafta | 156 | -0.26 | -0.11 | %46 | +0.14 |
| XAG | makro · 1 ay · TERS | 120 | -0.15 | -0.11 | %42 | — |
| XAG | sistem · 1 hafta | 554 | -0.37 | -0.14 | %43 | +0.23 |
| XAG | COT · 1 ay · TERS | 78 | -0.23 | -0.16 | %38 | — |
| XAG | teknik · 1 hafta | 84 | -0.40 | -0.18 | %44 | +0.23 |
| XAG | faktör · 1 gün · TERS | 156 | -0.43 | -0.23 | %33 | — |
| XAG | faktör · 1 ay · TERS | 156 | -0.25 | -0.23 | %37 | — |
| XAG | COT · 1 gün | 78 | -0.35 | -0.24 | %27 | +0.47 |
| XAG | COT · 1 hafta | 78 | -0.20 | -0.24 | %29 | -0.09 |
| XAG | sistem · 1 gün | 550 | -0.51 | -0.26 | %35 | +0.42 |
| XAG | sistem · 1 ay · TERS | 562 | -0.26 | -0.27 | %30 | — |
| XAG | faktör · 1 gün | 156 | -0.37 | -0.27 | %33 | -0.17 |
| XAG | teknik · 1 gün | 84 | -0.33 | -0.27 | %36 | +0.64 |
| XAG | teknik · 1 ay · TERS | 84 | -0.23 | -0.33 | %19 | — |
| XAG | sistem · 1 gün · TERS | 550 | -0.45 | -0.38 | %27 | — |
| XAG | makro · 1 hafta | 120 | -0.17 | -0.46 | %17 | +0.08 |
| XAG | makro · 1 gün | 120 | -0.38 | -0.57 | %20 | -0.44 |
| XAU | teknik · 1 ay | 84 | -0.11 | 0.24 | %74 | -0.15 |
| XAU | teknik · 1 hafta | 84 | -0.42 | 0.07 | %64 | -0.00 |
| XAU | teknik · 1 gün | 84 | -0.51 | 0.06 | %56 | +0.39 |
| XAU | faktör · 1 ay | 168 | -0.29 | 0.05 | %51 | -0.06 |
| XAU | makro · 1 ay · TERS | 120 | -0.24 | 0.05 | %54 | — |
| XAU | sistem · 1 ay | 562 | -0.37 | 0.02 | %52 | -0.05 |
| XAU | COT · 1 gün · TERS | 72 | -0.45 | -0.08 | %46 | — |
| XAU | COT · 1 ay · TERS | 72 | -0.28 | -0.10 | %43 | — |
| XAU | faktör · 1 gün · TERS | 168 | -0.65 | -0.14 | %43 | — |
| XAU | COT · 1 hafta · TERS | 72 | -0.39 | -0.14 | %38 | — |
| XAU | sistem · 1 hafta | 556 | -0.45 | -0.16 | %38 | -0.14 |
| XAU | sistem · 1 ay · TERS | 562 | -0.29 | -0.16 | %42 | — |
| XAU | faktör · 1 ay · TERS | 168 | -0.39 | -0.16 | %45 | — |
| XAU | COT · 1 ay | 72 | -0.40 | -0.16 | %36 | +0.41 |
| XAU | makro · 1 hafta · TERS | 120 | -0.50 | -0.18 | %42 | — |
| XAU | faktör · 1 hafta · TERS | 168 | -0.37 | -0.22 | %33 | — |
| XAU | makro · 1 ay | 120 | -0.38 | -0.23 | %41 | +0.23 |
| XAU | faktör · 1 hafta | 168 | -0.45 | -0.30 | %33 | -0.13 |
| XAU | sistem · 1 hafta · TERS | 556 | -0.40 | -0.32 | %29 | — |
| XAU | sistem · 1 gün · TERS | 552 | -0.75 | -0.38 | %27 | — |
| XAU | makro · 1 hafta | 120 | -0.30 | -0.38 | %23 | +0.45 |
| XAU | COT · 1 hafta | 72 | -0.40 | -0.42 | %26 | +0.12 |
| XAU | makro · 1 gün · TERS | 120 | -0.68 | -0.47 | %28 | — |
| XAU | teknik · 1 hafta · TERS | 84 | -0.15 | -0.47 | %20 | — |
| XAU | COT · 1 gün | 72 | -0.35 | -0.49 | %22 | +0.86 |
| XAU | teknik · 1 ay · TERS | 84 | -0.51 | -0.49 | %20 | — |
| XAU | makro · 1 gün | 120 | -0.84 | -0.56 | %17 | -0.05 |
| XAU | teknik · 1 gün · TERS | 84 | -0.31 | -0.62 | %11 | — |
| XAU | sistem · 1 gün | 552 | -0.88 | -0.68 | %14 | +0.60 |
| XAU | faktör · 1 gün | 168 | -0.69 | -0.69 | %10 | +0.09 |

## 4) Kombinasyonlar (eğitimin en iyi 12 sinyalinin ikilileri, ikisi aynı yönde → işlem)

**BTC** · 66 ikili · seçilen: [live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış] & [score_raw_cycle · 1 hafta ort. · long+short · sinyalle çıkış] · eğitim 1.47 → **sınav -0.64** (t -0.9) · tüm ikililerin sınav ortalaması 0.00, pozitif %76

**ETH** · 66 ikili · seçilen: [Faktör: duration_risk · 1 gün · long+short · sinyalle çıkış] & [TERS Makro: composite_usd_risk · 1 ay ort. · long+short · sinyalle çıkış] · eğitim 1.77 → **sınav -0.67** (t -0.9) · tüm ikililerin sınav ortalaması 0.27, pozitif %70

**NQ** · 65 ikili · seçilen: [Faktör: tech_vol_premium_lead (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış] & [adaptive_cluster_scores.B · 1 hafta ort. · long+short · sinyalle çıkış] · eğitim 1.02 → **sınav 0.70** (t +1.0) · tüm ikililerin sınav ortalaması -0.03, pozitif %55

**SPX** · 66 ikili · seçilen: [adaptive_cluster_scores.B (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış] & [Makro: ndl_z · 1 hafta ort. · long+short · sinyalle çıkış] · eğitim 0.92 → **sınav -0.48** (t -0.7) · tüm ikililerin sınav ortalaması -0.59, pozitif %14

**XAG** · 66 ikili · seçilen: [pair_stats.divergence_z_used (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış] & [TERS Momentum (60 gün) · 1 hafta ort. · long+short · sinyalle çıkış] · eğitim 1.15 → **sınav -0.71** (t -1.0) · tüm ikililerin sınav ortalaması -0.13, pozitif %45

**XAU** · 66 ikili · seçilen: [direction_z_support (güçlü ∣z∣>0.5) · 1 ay ort. · long+short · sinyalle çıkış] & [composite_usd_risk (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış] · eğitim 0.83 → **sınav -0.64** (t -0.9) · tüm ikililerin sınav ortalaması -0.12, pozitif %41

## 5) Yıllık walk-forward seçimleri (eğitim dönemi)

**BTC**: 2019: -0.09 (TERS direction_acceleration · 1 ay ort. · sadece long · iz süren stop 3×ATR) · 2020: -0.28 (live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış) · 2021: +1.38 (live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR) · 2022: -0.67 (live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR) · 2023: +0.29 (live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR) · 2024: +2.88 (live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR)

**ETH**: 2020: -1.46 (TERS Momentum (120 gün) · 1 hafta ort. · sadece short · iz süren stop 3×ATR) · 2021: -0.36 (pair_common_factor.common_score · 1 hafta ort. · long+short · iz süren stop 3×ATR) · 2022: +0.61 (TERS bear_clusters (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR) · 2023: +1.08 (TERS bear_clusters (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · iz süren stop 3×ATR) · 2024: +0.85 (TERS bear_clusters (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR)

**NQ**: 2019: +1.63 (TERS composite_usd_risk (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış) · 2020: +1.08 (TERS composite_usd_risk (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · sinyalle çıkış) · 2021: -0.57 (TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR) · 2022: -0.21 (Alt: COT dealer net (haftalık değişim) · 1 ay ort. · sadece long · iz süren stop 3×ATR) · 2023: +1.82 (TERS ADX trend rejimi (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR) · 2024: -0.37 (TERS direction_velocity · 1 ay ort. · sadece long · iz süren stop 3×ATR)

**SPX**: 2019: +0.00 (TERS direction_warmup (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış) · 2020: -0.26 (Faktör: duration_risk · 1 ay ort. · sadece long · sinyalle çıkış) · 2021: +0.30 (Giriş izni (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR) · 2022: +0.95 (TERS direction_velocity (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış) · 2023: +0.44 (TERS direction_velocity (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış) · 2024: +1.07 (TERS direction_velocity (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · sinyalle çıkış)

**XAG**: 2019: -0.63 (TERS EMA trend (100 gün) · 1 hafta ort. · sadece short · sinyalle çıkış) · 2020: -0.58 (TERS RVOL (güçlü ∣z∣>0.5) · 1 gün · long+short · sinyalle çıkış) · 2021: -0.49 (TERS Makro: dfii10_z · 1 ay ort. · sadece long · iz süren stop 3×ATR) · 2022: -1.68 (TERS Kısa vade=model (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR) · 2023: -0.97 (Momentum (60 gün) (güçlü ∣z∣>0.5) · 1 ay ort. · sadece long · iz süren stop 3×ATR) · 2024: +1.33 (Faktör: duration_risk (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR)

**XAU**: 2019: -2.00 (directional_confluence (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece short · iz süren stop 3×ATR) · 2020: +0.93 (Faktör: net_dollar_liquidity (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR) · 2021: -0.46 (live_counter_trend (güçlü ∣z∣>0.5) · 1 hafta ort. · long+short · sinyalle çıkış) · 2022: +0.00 (Faktör: net_dollar_liquidity (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR) · 2023: +0.00 (Faktör: net_dollar_liquidity (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR) · 2024: +0.00 (Faktör: net_dollar_liquidity (güçlü ∣z∣>0.5) · 1 hafta ort. · sadece long · iz süren stop 3×ATR)

## 6) Kaldıraç — seçilen kural, sınav dönemi

| Varlık | 1x | 2x | 3x | 5x | 10x |
|---|---|---|---|---|---|
| BTC | %-14 / %-37 | %-28 / %-62 | %-41 / %-79 | %-66 / %-94 | %-97 / %-100 |
| ETH | %+27 / %-38 | %+29 / %-63 | %+3 / %-80 | %-68 / %-96 | %-100 / %-100 · 2 lik. |
| NQ | %+2 / %-9 | %+3 / %-17 | %+4 / %-25 | %+4 / %-39 | %-3 / %-66 |
| SPX | %+2 / %-5 | %+4 / %-9 | %+6 / %-13 | %+9 / %-22 | %+11 / %-40 |
| XAG | %+9 / %-11 | %+17 / %-21 | %+24 / %-31 | %+31 / %-50 | %-4 / %-87 |
| XAU | %+0 / %-0 | %+0 / %-0 | %+0 / %-0 | %+0 / %-0 | %+0 / %-0 |
