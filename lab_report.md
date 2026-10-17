# 🧪 Strateji Laboratuvarı v7 — Kaldıraçlı Vadeli (Perp) Sonuç Raporu

_Üretim: 2026-10-17T07:58 UTC · fiyat: yahoo · sistem sinyalleri: signal_panel.csv.gz · denenen konfigürasyon: **1,132,076**_

**Maliyetler:** işlem başına (giriş ve çıkışta ayrı ayrı) komisyon+kayma %0.08; fonlama: long pozisyon 8 saatte %0.010 öder, short pozisyona fonlama geliri yazılmaz (tutucu). Tüm getiriler 1x pozisyon büyüklüğünde ve maliyetler düşülmüş (net); kaldıraç tablosu ayrı.

**v6:** her sinyal 5 tutma ufkunda (1 saat · 4 saat · 1 gün · 1 hafta · 1 ay), son değer ya da ufuk ortalaması, işaret / güçlü (∣z∣>0.5, ∣z∣>1), sistem yönünde ve TERS, long+short / sadece long / sadece short, 3-8 çıkış kuralıyla TEK TEK; sonra hazır kombinasyonlar ve veriden keşfedilen kombinasyonlar test edildi.

**Kanıt** (biri yeterli; **C:** kombinasyon keşfinde hiç görülmemiş son dönemde t ≥ 2) — **A:** sistem sinyalli pencerede seçim prosedürünün walk-forward OOS t ≥ 2, 5 dilimin ≥ 3'ü pozitif, Deflated Sharpe ≥ 0.90, ≥ 30 işlem · **B:** 10 yıllık günlük veride aynı testler (7 dilimin ≥ 5'i). Kanıtlı kural ayrıca 'sürekli long perp'e karşı **alfa t ≥ 2** veriyorsa **✅ KANITLI ALFA** (bot işlem yapabilir); vermiyorsa **⚠️ β AĞIRLIKLI** (kazancı çoğunlukla piyasa yönünden; işlem sinyali sayılmaz).

## 1) Varlık bazında sonuç

| Varlık | Seçilen kural (pencerenin en iyisi) | Sharpe | 1. yarı / 2. yarı | Getiri | Maks. DD | İşlem | Kazanma | DSR | WF-OOS Sharpe (t) · + dilim | Alfa t | Uzun dönem 1g: en iyi kural · WF Sharpe (t) · + dilim · alfa t | Sürekli long Sharpe / getiri | Durum | Sinyal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPX | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR / TP 6.0×ATR | 2.16 | 3.92 / 0.25 | %+52.4 | %-6.2 | 31 | %71 | 0.86 | -0.38 (-0.5) · 1/5 | -1.0 | Momentum (60) · 1d · long+short · SL 2.0×ATR / TP 4.0×ATR · -0.16 (-0.5) · 4/7 · -0.5 · 10.0 yıl | 0.38 / %+13.7 | ❌ kanıt yok | ⚪ YOK |
| NQ | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.98 | 3.29 / 0.75 | %+63.4 | %-6.9 | 31 | %77 | 0.78 | -0.48 (-0.6) · 2/5 | -0.7 | Momentum (60) · 1d · sadece long · SL 3.0×ATR / TP 6.0×ATR · 0.10 (+0.3) · 5/7 · +0.2 · 10.0 yıl | 0.54 / %+27.7 | ❌ kanıt yok | ⚪ YOK |
| XAU | Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | 2.21 | 2.65 / 1.80 | %+58.9 | %-6.4 | 18 | %67 | 0.85 | 0.09 (+0.1) · 3/5 | -0.3 | Keltner kırılımı (20/2.0) · 1d · sadece long · SL 1.5×ATR / TP 3.0×ATR · -0.13 (-0.4) · 2/7 · -0.4 · 10.0 yıl | 0.64 / %+36.4 | ❌ kanıt yok | ⚪ YOK |
| XAG | TERS Faktör: silver_vol_premium_lead (güçlü, ∣z∣>1) · 1 günlük · sadece long · SL 3.0×ATR / TP 6.0×ATR | 2.34 | 1.76 / 2.83 | %+117.1 | %-5.4 | 24 | %54 | 0.96 | -0.70 (-0.9) · 1/5 | -1.3 | TERS DMI/ADX yönü (14) · 1d · sadece long · sinyalle çıkış · -0.29 (-0.9) · 4/7 · -0.9 · 10.0 yıl | 0.52 / %+69.5 | ❌ kanıt yok | ⚪ YOK |
| BTC | TERS direction_velocity · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 2.38 | 1.21 / 3.61 | %+371.0 | %-26.0 | 53 | %76 | 0.87 | -0.12 (-0.1) · 2/5 | -0.1 | TERS RSI(2) dönüş (2/10/90) · 1d · sadece long · sinyalle çıkış · 0.31 (+0.9) · 6/7 · +0.8 · 10.0 yıl | -0.16 / %-12.7 | ❌ kanıt yok | 🔴 SHORT |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Kısa Vade Yön · 1 günlük ortalama yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 2.24 | 2.58 / 1.88 | %+138.3 | %-9.7 | 45 | %69 | 0.88 | -0.18 (-0.2) · 2/5 | -0.2 | Momentum (60) · 1d · long+short · iz süren stop 3.0×ATR · 0.10 (+0.3) · 4/7 · +0.1 · 8.9 yıl | -0.28 / %-31.4 | ❌ kanıt yok | ⚪ YOK |

_'1. yarı / 2. yarı': aynı kuralın pencerenin iki yarısındaki Sharpe'ı — biri pozitif biri negatifse kural kararsızdır. WF-OOS: her dilimde YALNIZCA geçmişte en iyi olanı seçip bir sonraki dilimde ölçen prosedürün gerçek dışı-örneklem sonucu (on binlerce aday arasından seçimin bedeli dahil)._

## 2) Tutma ufku etkisi — sistem sinyalleri tek tek (sistem yönünde, işaret, ufuk boyunca ortalama, long+short)

| Ufuk | Ortalama Sharpe | Medyan Sharpe | Pozitif oran |
|---|---|---|---|
| 1 saat | -1.82 | -0.97 | %18 |
| 4 saat | -1.09 | -0.78 | %20 |
| 1 gün | -0.40 | -0.30 | %29 |
| 1 hafta | -0.18 | -0.14 | %40 |
| 1 ay | -0.09 | -0.09 | %45 |

**Sinyal × ufuk matrisi** (6 varlık ortalaması Sharpe · parantezde pozitif varlık sayısı)

| Sinyal | 1 saat | 4 saat | 1 gün | 1 hafta | 1 ay |
|---|---|---|---|---|---|
| Faktör: nq_relative_divergence | -11.76 (0) | -6.84 (0) | -0.67 (0) | -0.91 (0) | -0.06 (0) |
| Faktör: spx_relative_divergence | -10.17 (0) | -3.76 (0) | -2.12 (0) | -0.15 (0) | 0.33 (1) |
| direction_acceleration | -8.97 (0) | -4.81 (0) | -1.25 (0) | -0.28 (3) | -0.78 (0) |
| pair_stats.residual_z | -8.57 (0) | -3.68 (0) | -0.98 (1) | 0.01 (4) | -0.47 (2) |
| pair_stats.spread | -8.56 (0) | -3.70 (0) | -0.95 (1) | 0.10 (3) | -0.65 (0) |
| current_roc | -8.21 (0) | -3.73 (0) | -0.92 (0) | -0.79 (0) | 0.23 (3) |
| Faktör: gold_macro_lead | -7.75 (0) | -2.52 (0) | -2.01 (0) | -0.70 (0) | 0.57 (1) |
| Fiyat itkisi skoru | -7.55 (0) | -3.46 (0) | -1.17 (0) | -0.57 (0) | -0.38 (1) |
| short_term_parts.price_z | -7.52 (0) | -3.45 (0) | -1.15 (0) | -0.55 (0) | -0.16 (1) |
| short_term_parts.price_part | -7.52 (0) | -3.48 (0) | -0.66 (0) | -0.21 (3) | 0.06 (4) |
| Faktör: gold_divergence_residual | -6.61 (0) | -3.05 (0) | 0.30 (1) | -0.17 (0) | -0.48 (0) |
| Makro: credit_velocity | -6.43 (0) | -3.04 (0) | -1.40 (0) | -0.66 (0) | -0.39 (0) |
| RSI(2) dönüş (2/10/90) · 1h | -6.04 (0) | -3.77 (0) | -0.41 (1) | -0.31 (2) | -0.12 (2) |
| Faktör: credit_spread | -5.25 (0) | -3.04 (0) | -1.42 (0) | -0.93 (0) | 0.09 (2) |
| Faktör: usd_strength | -5.09 (0) | -2.83 (0) | -0.61 (1) | 0.22 (4) | -0.02 (2) |
| Faktör: consumer_demand | -5.07 (0) | -3.30 (0) | 0.04 (1) | -1.86 (0) | 0.67 (1) |
| Makro: dxy_velocity | — | -4.56 (0) | — | — | — |
| direction_velocity | -4.51 (0) | -2.06 (0) | -0.80 (0) | -0.73 (0) | -0.20 (2) |
| Faktör: asset_direction | -4.06 (0) | -2.34 (0) | -0.38 (1) | -0.32 (4) | 0.05 (3) |
| Faktör: usd_jpy_carry | -3.97 (0) | -2.40 (0) | -0.71 (1) | -0.26 (1) | 0.23 (3) |
| Makro: yen_carry_z | -3.91 (0) | -3.09 (0) | -0.26 (1) | -0.81 (0) | 0.25 (3) |
| Faktör: gsr_velocity | -3.82 (0) | -1.95 (0) | -0.96 (0) | -0.86 (0) | -0.28 (0) |
| adaptive_cluster_scores.E | -3.60 (0) | -2.00 (0) | -0.35 (1) | -0.37 (2) | -0.12 (2) |
| live_score_pair_adjusted | -3.47 (0) | -1.05 (1) | -0.37 (2) | -0.31 (2) | -0.01 (2) |
| Çift-uyumlu yön skoru | -3.47 (0) | -1.88 (0) | — | — | — |
| Faktör: defensive_flight | -3.46 (0) | -2.67 (0) | -0.05 (1) | -0.67 (0) | -0.31 (0) |
| raw_model_score | -3.30 (0) | -1.72 (0) | -0.62 (1) | -0.57 (1) | -0.32 (1) |
| RSI trend (14) · 1h | -3.26 (0) | -1.63 (0) | -0.32 (2) | -0.35 (2) | 0.12 (3) |
| adaptive_cluster_scores.C | -3.25 (0) | -1.72 (0) | -0.52 (0) | -0.82 (0) | -0.76 (0) |
| Momentum (24) · 1h | -3.14 (0) | -1.81 (0) | -0.54 (2) | -0.25 (2) | -0.11 (3) |
| Adaptif skor | -3.06 (0) | -1.90 (0) | -0.44 (2) | -0.60 (1) | -0.02 (2) |
| Faktör: btc_sympathy | -3.04 (0) | -0.46 (0) | 1.05 (1) | 0.70 (1) | 0.48 (1) |
| adaptive_cluster_scores.A | -3.03 (0) | -1.82 (0) | -0.59 (1) | -0.43 (2) | — |
| Faktör: gold_sovereign_decoupling | -2.50 (0) | -1.55 (0) | -1.50 (0) | 0.12 (1) | 0.39 (1) |
| pair_common_factor.gap_before | -2.44 (0) | -1.78 (0) | -0.10 (1) | 0.69 (2) | 0.84 (2) |
| composite_usd_risk | -2.44 (0) | -0.78 (0) | 0.03 (3) | 0.25 (4) | 0.28 (4) |
| adaptive_cluster_scores.D | -2.38 (0) | -0.76 (1) | -1.42 (0) | 0.03 (1) | -0.20 (2) |
| Faktör: market_breadth | -2.28 (0) | -2.38 (0) | -1.63 (0) | -0.00 (0) | -0.98 (0) |
| pair_common_factor.common_score | -2.31 (0) | -1.68 (0) | 0.13 (1) | 0.13 (1) | — |
| score_raw_cycle | -2.29 (0) | -1.41 (0) | -0.40 (1) | -0.66 (0) | — |
| Faktör: vix_strain | -2.23 (0) | -1.78 (0) | -0.93 (0) | -1.18 (0) | -1.03 (0) |
| Faktör: semi_lead | -2.21 (0) | -0.90 (0) | -0.05 (1) | -0.09 (0) | -0.42 (0) |
| Faktör: banking_stress | -2.21 (0) | -1.13 (0) | -0.55 (1) | -0.46 (2) | -0.64 (0) |
| EMA trend (50) · 1h | -2.18 (0) | -1.22 (1) | -0.16 (2) | -0.17 (3) | 0.08 (3) |
| MACD (12/26/9) · 1h | -2.17 (0) | -1.80 (0) | -0.94 (2) | -0.07 (3) | -0.38 (2) |

_Makro sinyallerin değeri uzun ufukta (hafta/ay) görünmeli; kısa ufukta sık yön değişimi maliyetle eriyor. Ay ufku 700 günde ~23 karar demek: istatistiksel gücü düşüktür._

## 3) Kombinasyon keşfi (keşif → doğrulama → hiç görülmemiş dönem)

_Keşif döneminde her sinyal tek tek sıralandı; en iyi 40'ın tüm ikili kombinasyonları (ikisi aynı yönü gösterdiğinde işlem) ve 2-7 sinyallik açgözlü çoğunluk oyları kuruldu. Seçim doğrulama döneminde yapıldı; son dönem hiçbir seçimde kullanılmadı. Kanıt: son dönemde t ≥ 2 ve sürekli long'a karşı alfa t ≥ 2._

**SPX** · keşif 2024-11-08→2025-10-24 · doğrulama →2026-04-17 · son dönem →2026-10-09 · 1,563 aday (1,517 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [TERS Faktör: tail_risk_skew_lead] & [TERS Faktör: vix_strain · 1 haftalık ortalama] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 1.71 | 3.34 | **-1.13** | %-3.9 | -0.8 | -0.5 | 44 |
| 2 | Hepsi aynı yönde: [TERS Faktör: tail_risk_skew_lead · 4 saatlik ortalama] & [TERS Momentum (24) · 1h · 1 aylık] · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 2.76 | 2.74 | **-3.15** | %-7.2 | -2.2 | -2.1 | 36 |
| 3 | Hepsi aynı yönde: [TERS Faktör: tail_risk_skew_lead] & [TERS Momentum (24) · 1h · 1 aylık] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 2.77 | 2.63 | **-2.56** | %-6.3 | -1.8 | -1.7 | 38 |
| 4 | Hepsi aynı yönde: [TERS Faktör: tail_risk_skew_lead] & [TERS MACD (12/26/9) · 1h · 1 aylık] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 1.02 | 2.24 | **-1.91** | %-5.1 | -1.3 | -1.3 | 37 |
| 5 | Hepsi aynı yönde: [TERS Faktör: tail_risk_skew_lead · 4 saatlik] & [TERS Faktör: vix_strain · 1 haftalık ortalama] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 1.70 | 2.12 | **-0.96** | %-3.4 | -0.7 | -0.4 | 44 |
| 6 | Hepsi aynı yönde: [pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Donchian kırılımı (168) · 1h · 4 saatlik ortalama] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 2.67 | 2.05 | **1.48** | %+1.6 | +1.0 | +1.2 | 21 |
| 7 | Hepsi aynı yönde: [pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Donchian kırılımı (168) · 1h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 2.67 | 2.05 | **1.48** | %+1.6 | +1.0 | +1.2 | 21 |
| 8 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (haftalık değişim) · 1 aylık] & [TERS Faktör: tail_risk_skew_lead (güçlü, ∣z∣>1) · 4 saatlik ortalama] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 1.56 | 2.01 | **-2.97** | %-7.1 | -2.1 | -2.0 | 21 |
| 9 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (haftalık değişim) · 1 aylık] & [TERS Faktör: tail_risk_skew_lead (güçlü, ∣z∣>1) · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 1.27 | 2.01 | **-3.16** | %-8.5 | -2.2 | -2.1 | 21 |
| 10 | Hepsi aynı yönde: [TERS Faktör: tail_risk_skew_lead · 4 saatlik ortalama] & [TERS Faktör: vix_strain · 1 haftalık ortalama] · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 1.51 | 2.01 | **-1.37** | %-4.9 | -0.9 | -0.7 | 44 |

**NQ** · keşif 2024-11-08→2025-10-24 · doğrulama →2026-04-17 · son dönem →2026-10-09 · 1,550 aday (1,504 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>0.5)] · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 2.06 | 3.67 | **0.99** | %+3.3 | +0.7 | +0.8 | 20 |
| 2 | Hepsi aynı yönde: [Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>0.5)] · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 2.11 | 3.67 | **0.99** | %+3.3 | +0.7 | +0.8 | 21 |
| 3 | Hepsi aynı yönde: [Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>0.5) · 4 saatlik] · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 2.11 | 3.63 | **0.99** | %+3.3 | +0.7 | +0.8 | 21 |
| 4 | Hepsi aynı yönde: [pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>0.5) · 4 saatlik] · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 2.06 | 3.63 | **0.99** | %+3.3 | +0.7 | +0.8 | 20 |
| 5 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 2.47 | 3.54 | **0.53** | %+2.8 | +0.4 | +0.6 | 37 |
| 6 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · 4 saatlik] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 2.23 | 3.48 | **0.28** | %+1.5 | +0.2 | +0.4 | 37 |
| 7 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1)] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 2.27 | 3.46 | **0.27** | %+1.4 | +0.2 | +0.4 | 37 |
| 8 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 2.35 | 3.44 | **-1.77** | %-4.3 | -1.2 | -1.3 | 37 |
| 9 | Hepsi aynı yönde: [Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>0.5) · 4 saatlik ortalama] · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 2.23 | 3.42 | **1.21** | %+4.0 | +0.8 | +1.0 | 17 |
| 10 | Hepsi aynı yönde: [pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>0.5) · 4 saatlik ortalama] · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 2.23 | 3.42 | **1.21** | %+4.0 | +0.8 | +1.0 | 17 |

**XAU** · keşif 2024-11-08→2025-10-24 · doğrulama →2026-04-17 · son dönem →2026-10-09 · 1,594 aday (1,548 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Bollinger dönüş (20/2.0) · 4h] · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | kombi·ikili | 1.28 | 3.64 | **0.39** | %+1.4 | +0.3 | +0.6 | 25 |
| 2 | Hepsi aynı yönde: [TERS adaptive_cluster_scores.B · 1 haftalık] & [Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık] · sadece long · sinyalle çıkış | kombi·ikili | 1.21 | 3.26 | **0.29** | %+1.6 | +0.2 | +0.7 | 15 |
| 3 | Hepsi aynı yönde: [TERS adaptive_cluster_scores.B · 1 haftalık] & [Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık] · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | kombi·ikili | 1.45 | 3.26 | **0.29** | %+1.6 | +0.2 | +0.7 | 15 |
| 4 | Hepsi aynı yönde: [TERS Bollinger dönüş (20/2.0) · 4h · 4 saatlik ortalama] & [Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık] · sadece long · sinyalle çıkış | kombi·ikili | 1.35 | 2.67 | **0.75** | %+2.4 | +0.5 | +0.9 | 25 |
| 5 | Hepsi aynı yönde: [TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5)] & [TERS Bollinger dönüş (20/2.0) · 4h · 4 saatlik ortalama] · sadece long · SL 2.0×ATR / TP 4.0×ATR | kombi·ikili | 3.26 | 2.65 | **0.40** | %+1.1 | +0.3 | +0.6 | 33 |
| 6 | Hepsi aynı yönde: [TERS Model sinyali (24s-1h) · 1 haftalık ortalama] & [Zaman dilimi uyumu (güçlü, ∣z∣>0.5) · 1 haftalık ortalama] · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 0.87 | 2.59 | **0.28** | %+1.7 | +0.2 | +0.9 | 12 |
| 7 | Hepsi aynı yönde: [TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5)] & [TERS Bollinger dönüş (20/2.0) · 4h] · sadece long · SL 2.0×ATR / TP 4.0×ATR | kombi·ikili | 3.16 | 2.55 | **0.17** | %+0.5 | +0.1 | +0.4 | 33 |
| 8 | Hepsi aynı yönde: [TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük] & [TERS Bollinger dönüş (20/2.0) · 4h] · sadece long · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 2.54 | 2.48 | **0.64** | %+2.2 | +0.5 | +0.8 | 31 |
| 9 | Hepsi aynı yönde: [TERS Bollinger dönüş (20/2.0) · 4h · 4 saatlik ortalama] & [TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 4 saatlik ortalama] · sadece long · SL 1.5×ATR / TP 3.0×ATR | kombi·ikili | 2.72 | 2.47 | **1.49** | %+3.2 | +1.0 | +1.3 | 33 |
| 10 | Hepsi aynı yönde: [TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 4 saatlik] & [TERS Bollinger dönüş (20/2.0) · 4h · 4 saatlik ortalama] · sadece long · SL 2.0 / TP 4.0×ATR × volatilite oranı | kombi·ikili | 2.83 | 2.41 | **1.52** | %+3.5 | +1.1 | +1.3 | 33 |

**XAG** · keşif 2024-11-08→2025-10-24 · doğrulama →2026-04-17 · son dönem →2026-10-09 · 1,386 aday (1,340 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] & [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 0.84 | 5.95 | **-0.21** | %-2.1 | -0.1 | +0.3 | 32 |
| 2 | Hepsi aynı yönde: [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] & [TERS Faktör: silver_vol_premium_lead · 4 saatlik] · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.72 | 5.37 | **0.12** | %+1.3 | +0.1 | +0.5 | 35 |
| 3 | Hepsi aynı yönde: [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] & [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 1.09 | 5.05 | **-0.28** | %-3.0 | -0.2 | +0.2 | 32 |
| 4 | Hepsi aynı yönde: [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] & [TERS Faktör: silver_vol_premium_lead · 4 saatlik] · sadece long · sinyalle çıkış | kombi·ikili | 1.05 | 5.03 | **0.12** | %+1.3 | +0.1 | +0.5 | 35 |
| 5 | Hepsi aynı yönde: [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] & [Alt: COT üretici net (haftalık değişim) · 1 haftalık] · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 1.27 | 4.13 | **-0.30** | %-3.0 | -0.2 | +0.2 | 27 |
| 6 | Hepsi aynı yönde: [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] & [TERS Momentum (12) · 4h · 1 haftalık ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 0.25 | 4.11 | **0.05** | %+0.5 | +0.0 | +0.5 | 22 |
| 7 | Hepsi aynı yönde: [TERS Faktör: silver_vol_premium_lead · 4 saatlik] & [TERS Momentum (12) · 4h · 1 haftalık ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 0.72 | 4.09 | **0.19** | %+2.1 | +0.1 | +0.6 | 26 |
| 8 | Hepsi aynı yönde: [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] & [TERS Faktör: asset_direction (güçlü, ∣z∣>0.5) · 1 haftalık ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 0.25 | 4.01 | **0.27** | %+2.3 | +0.2 | +0.5 | 17 |
| 9 | Hepsi aynı yönde: [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] & [TERS Momentum (12) · 4h · 1 haftalık ortalama] · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 0.25 | 4.00 | **0.14** | %+1.5 | +0.1 | +0.5 | 22 |
| 10 | Hepsi aynı yönde: [TERS Faktör: silver_vol_premium_lead · 4 saatlik] & [TERS Momentum (12) · 4h · 1 haftalık ortalama] · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 0.72 | 3.97 | **0.04** | %+0.4 | +0.0 | +0.4 | 26 |

**BTC** · keşif 2024-11-08→2025-10-24 · doğrulama →2026-04-17 · son dönem →2026-10-09 · 1,606 aday (1,560 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik] & [TERS Makro: stagflation_z · 1 haftalık] · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 2.92 | 2.74 | **1.31** | %+6.8 | +0.9 | +1.0 | 32 |
| 2 | Hepsi aynı yönde: [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik ortalama] & [TERS Makro: stagflation_z · 1 haftalık] · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 2.72 | 2.64 | **1.22** | %+6.5 | +0.8 | +0.9 | 32 |
| 3 | Hepsi aynı yönde: [TERS Model sinyali (24s-1h) (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS directional_confluence (güçlü, ∣z∣>1) · 1 haftalık ortalama] · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | kombi·ikili | 2.65 | 2.51 | **0.68** | %+3.5 | +0.5 | +0.5 | 12 |
| 4 | Hepsi aynı yönde: [Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1)] & [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik] · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 1.13 | 2.45 | **-0.50** | %-0.5 | -0.3 | -0.3 | 26 |
| 5 | Hepsi aynı yönde: [TERS Model sinyali (24s-1h) (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS directional_confluence (güçlü, ∣z∣>1) · 1 haftalık ortalama] · long+short · sinyalle çıkış | kombi·ikili | 1.25 | 2.44 | **0.68** | %+3.5 | +0.5 | +0.5 | 12 |
| 6 | Hepsi aynı yönde: [EMA kesişimi (50/200) · 4h] & [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik ortalama] · long+short · 24 saat tut | kombi·ikili | 1.52 | 2.42 | **-0.21** | %-1.4 | -0.1 | -0.2 | 76 |
| 7 | Hepsi aynı yönde: [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik ortalama] & [EMA trend (50) · 4h · 4 saatlik ortalama] · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 1.92 | 2.38 | **0.03** | %+0.2 | +0.0 | +0.1 | 65 |
| 8 | Hepsi aynı yönde: [EMA kesişimi (50/200) · 4h] & [EMA trend (50) · 4h · 4 saatlik ortalama] · long+short · 24 saat tut | kombi·ikili | 0.18 | 2.26 | **-0.53** | %-4.1 | -0.4 | -0.4 | 172 |
| 9 | Hepsi aynı yönde: [Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1)] & [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik ortalama] · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 1.11 | 2.25 | **0.10** | %+0.1 | +0.1 | +0.1 | 26 |
| 10 | Hepsi aynı yönde: [Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1)] & [TERS Faktör: banking_stress · 1 haftalık ortalama] · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 2.29 | 2.24 | **-2.39** | %-8.8 | -1.7 | -1.6 | 25 |

**ETH** · keşif 2024-11-08→2025-10-24 · doğrulama →2026-04-17 · son dönem →2026-10-09 · 1,570 aday (1,524 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [DMI/ADX yönü (14) · 4h] & [TERS Makro: breakeven_z (z) (güçlü, ∣z∣>1)] · sadece short · sinyalle çıkış | kombi·ikili | 0.10 | 3.26 | **-1.98** | %-9.0 | -1.4 | -1.4 | 24 |
| 2 | Hepsi aynı yönde: [DMI/ADX yönü (14) · 4h] & [TERS Makro: breakeven_z (güçlü, ∣z∣>1) · 4 saatlik] · sadece short · sinyalle çıkış | kombi·ikili | 0.10 | 3.23 | **-2.00** | %-9.1 | -1.4 | -1.4 | 24 |
| 3 | Hepsi aynı yönde: [Alt: Açık pozisyon değişimi 7g (z) · 4 saatlik ortalama] & [TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>1) · 1 haftalık] · sadece long · 4 saat tut | kombi·ikili | 1.77 | 2.78 | **-0.64** | %-1.1 | -0.5 | -0.5 | 21 |
| 4 | Hepsi aynı yönde: [Momentum (336) · 1h] & [TERS Makro: breakeven_z (z) (güçlü, ∣z∣>1)] · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 0.98 | 2.63 | **-2.38** | %-6.6 | -1.7 | -1.6 | 55 |
| 5 | Çoğunluk oyu: [Momentum (336) · 1h · 4 saatlik] & [TERS EMA kesişimi (24/96) · 1h · 4 saatlik ortalama] & [Alt: Perp primi 8s ort. (z) · 1 haftalık] & [TERS Makro: stagflation_z (güçlü, ∣z∣>1) · 1 haftalık] & [Faktör: vix_strain (güçlü, ∣z∣>1) · 1 günlük ortalama] & [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1) · 4 saatlik ortalama] & [Momentum (336) · 1h] · long+short · sinyalle çıkış | kombi·oylama | 3.97 | 2.52 | **-0.20** | %-1.3 | -0.1 | -0.1 | 118 |
| 6 | Çoğunluk oyu: [Momentum (336) · 1h · 4 saatlik] & [TERS EMA kesişimi (24/96) · 1h · 4 saatlik ortalama] & [Alt: Perp primi 8s ort. (z) · 1 haftalık] & [TERS Makro: stagflation_z (güçlü, ∣z∣>1) · 1 haftalık] & [Faktör: vix_strain (güçlü, ∣z∣>1) · 1 günlük ortalama] & [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1) · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·oylama | 4.21 | 2.45 | **-1.16** | %-8.3 | -0.8 | -0.8 | 109 |
| 7 | Hepsi aynı yönde: [Donchian kırılımı (48) · 1h · 1 haftalık ortalama] & [TERS Makro: breakeven_z (güçlü, ∣z∣>1) · 4 saatlik] · long+short · sinyalle çıkış | kombi·ikili | 0.64 | 2.26 | **-1.95** | %-23.8 | -1.4 | -1.5 | 42 |
| 8 | Hepsi aynı yönde: [Donchian kırılımı (48) · 1h · 1 haftalık ortalama] & [TERS Makro: breakeven_z (z) (güçlü, ∣z∣>1)] · long+short · sinyalle çıkış | kombi·ikili | 0.62 | 2.25 | **-1.95** | %-23.8 | -1.4 | -1.5 | 41 |
| 9 | Hepsi aynı yönde: [Alt: Büyük trader long/short (z) · 1 günlük ortalama] & [TERS Alt: Perp primi 8s ort. (z) (güçlü, ∣z∣>0.5) · 4 saatlik] · long+short · sinyalle çıkış | kombi·ikili | 1.45 | 2.22 | **-0.58** | %-6.4 | -0.4 | -0.4 | 151 |
| 10 | Hepsi aynı yönde: [Alt: Büyük trader long/short (z) · 1 günlük ortalama] & [TERS Alt: Perp primi 8s ort. (z) (güçlü, ∣z∣>0.5) · 4 saatlik] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 1.45 | 2.22 | **-0.58** | %-6.4 | -0.4 | -0.4 | 151 |

## 3b) Sistem yönü FİLTRE + teknik TETİK + ATR çıkışı

_Kural: teknik tetik (RSI(2) aşırılığı, Bollinger dönüşü, Donchian kırılımı, EMA20 kesişimi, MACD kesişimi, Keltner kırılımı) oluşunca, YALNIZCA sistemin gösterdiği yönde işleme girilir; çıkış ATR stop/hedef, başa-baş, kısmi kâr, iz süren stop veya sinyal. 'Kazanç' = aynı tetik, aynı çıkış, aynı yön modu ile filtresiz hâline göre Sharpe farkı. Bir filtreye ancak pencerenin İKİ yarısında da kazanç veriyorsa güvenilir._

**Genel:** 201,612 (tetik × filtre × çıkış × yön) eşleşmesi · filtresiz tetik ort. Sharpe **-1.17** (pozitif %20) → sistem filtreli ort. **-1.17** (pozitif %19) · ortalama kazanç **+0.04** · kazanç pozitif %54 · iki yarıda da pozitif **%33**

**Filtre olarak en faydalı sistem yönleri** (tüm tetikler ve varlıklar ortalaması)

| Filtre (sistem yönü) | Ufuk | Ort. kazanç | 1. yarı / 2. yarı kazanç | İki yarıda da + | Filtreli ort. Sharpe | Eşleşme | Varlık |
|---|---|---|---|---|---|---|---|
| Alt: Perp primi (baz) (z) | haftalık ort. | +0.82 | +0.95 / +0.67 | %71 | -0.11 | 648 | 2 |
| Model sinyali (24s-1h) | anlık | +0.82 | +0.81 / +0.77 | %48 | -0.58 | 1476 | 6 |
| Model sinyali (24s-1h) | günlük ort. | +0.78 | +0.82 / +0.79 | %49 | -0.57 | 1644 | 6 |
| Yön aşaması | haftalık ort. | +0.78 | +0.50 / +1.21 | %50 | -1.03 | 234 | 1 |
| Alt: COT varlık yöneticisi net (haftalık değişim) (z) | haftalık ort. | +0.74 | +0.64 / +0.81 | %65 | -0.71 | 1146 | 4 |
| Faktör: speculative_beta | günlük ort. | +0.68 | +0.97 / +0.34 | %52 | -0.72 | 324 | 1 |
| Alt: COT varlık yöneticisi net (haftalık değişim) | haftalık ort. | +0.68 | +0.61 / +0.74 | %64 | -0.61 | 1296 | 4 |
| Faktör: consumer_demand | günlük ort. | +0.66 | +0.90 / +0.34 | %59 | -1.25 | 324 | 1 |
| Model sinyali (24s-1h) | haftalık ort. | +0.65 | +0.63 / +0.64 | %50 | -0.60 | 1800 | 6 |
| Alt: COT kaldıraçlı fon net (haftalık değişim) (z) | anlık | +0.64 | +0.20 / +1.04 | %58 | -0.97 | 240 | 1 |
| Alt: Açık pozisyon değişimi 7g (z) | haftalık ort. | +0.64 | +0.69 / +0.54 | %64 | -0.31 | 642 | 2 |
| Alt: Perp primi 8s ort. (z) | haftalık ort. | +0.63 | +0.71 / +0.61 | %67 | -0.30 | 648 | 2 |
| Alt: Perp primi (baz) (z) | günlük ort. | +0.63 | +0.64 / +0.62 | %64 | -0.31 | 648 | 2 |
| Faktör: market_breadth | haftalık ort. | +0.60 | +0.65 / +0.55 | %50 | -1.30 | 324 | 1 |
| Faktör: defensive_flight | günlük ort. | +0.58 | +0.79 / +0.30 | %57 | -1.08 | 648 | 2 |
| Alt: Açık pozisyon değişimi 24s (z) | haftalık ort. | +0.57 | +0.53 / +0.56 | %62 | -0.37 | 648 | 2 |
| Faktör: semi_lead | günlük ort. | +0.56 | +1.03 / +0.01 | %42 | -1.09 | 648 | 2 |
| Faktör: vix_term | günlük ort. | +0.54 | +0.58 / +0.43 | %44 | -1.14 | 636 | 2 |
| Kısa Vade Yön | günlük ort. | +0.53 | +0.55 / +0.53 | %43 | -0.64 | 1932 | 6 |
| Faktör: tech_vol_premium_lead | haftalık ort. | +0.53 | +0.17 / +0.89 | %50 | -0.87 | 324 | 1 |

_En zayıf 5 filtre:_ Faktör: gold_divergence_residual (anlık) -2.45 · Fiyat itkisi skoru (anlık) -2.57 · Faktör: gold_macro_lead (anlık) -2.71 · Faktör: spx_relative_divergence (anlık) -3.97 · Faktör: nq_relative_divergence (anlık) -4.18

**Tetik bazında** (filtresiz → filtreli)

| Tetik | Filtresiz Sharpe | Filtreli ort. | Kazanç | İki yarıda + |
|---|---|---|---|---|
| EMA20 kesişimi · 1h | -4.69 | -3.68 | +1.00 | %73 |
| RSI(2) geri çekilme · 1h | -3.24 | -2.64 | +0.60 | %57 |
| Bollinger bandı dışı · 1h | -2.54 | -2.00 | +0.54 | %58 |
| MACD kesişimi · 1h | -2.79 | -2.31 | +0.49 | %54 |
| 20 mum kırılımı · 1h | -2.15 | -1.84 | +0.31 | %45 |
| Keltner kırılımı · 1h | -1.83 | -1.61 | +0.22 | %41 |
| EMA20 kesişimi · 4h | -1.17 | -1.14 | +0.02 | %33 |
| MACD kesişimi · 1d | -0.42 | -0.54 | -0.12 | %23 |
| Bollinger bandı dışı · 1d | -0.20 | -0.34 | -0.14 | %22 |
| Bollinger bandı dışı · 4h | -0.47 | -0.66 | -0.19 | %20 |
| Keltner kırılımı · 4h | -0.26 | -0.49 | -0.23 | %21 |
| MACD kesişimi · 4h | -0.27 | -0.50 | -0.23 | %19 |
| 20 mum kırılımı · 4h | -0.45 | -0.70 | -0.25 | %21 |
| RSI(2) geri çekilme · 4h | -0.63 | -0.89 | -0.26 | %25 |
| EMA20 kesişimi · 1d | -0.26 | -0.52 | -0.26 | %21 |
| 20 mum kırılımı · 1d | 0.01 | -0.25 | -0.26 | %18 |
| RSI(2) geri çekilme · 1d | -0.27 | -0.58 | -0.31 | %17 |
| Keltner kırılımı · 1d | 0.45 | 0.07 | -0.38 | %12 |

**İki yarıda da en sağlam 20 filtreli tetik kuralı** (sıralama: min(1. yarı, 2. yarı) — yine de seçim yanlılığı içerir)

| Varlık | Kural | Sharpe | 1. yarı / 2. yarı | Filtresiz | Kazanç | İşlem |
|---|---|---|---|---|---|---|
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Kısa Vade Yön · 1 günlük ortalama yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 2.24 | 2.58 / 1.88 | 1.16 | +1.08 | 45 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Faktör: real_yield yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.91 | 1.86 / 1.97 | 1.16 | +0.76 | 50 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Faktör: real_yield yönünde · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 1.78 | 1.80 / 1.78 | 0.88 | +0.91 | 50 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Kısa Vade Yön · 1 günlük ortalama yönünde · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.80 | 1.72 / 1.91 | 0.51 | +1.29 | 70 |
| BTC | Tetik: Keltner kırılımı · 1d | filtre: Alt: Perp primi (baz) (z) · 1 günlük ortalama yönünde · long+short · SL 2.0 / TP 4.0×ATR × volatilite oranı | 1.68 | 1.57 / 1.78 | 1.13 | +0.54 | 26 |
| BTC | Tetik: Keltner kırılımı · 1d | filtre: Faktör: usd_strength · 1 günlük ortalama yönünde · long+short · iz süren stop 2.0×ATR | 1.56 | 1.57 / 1.65 | 1.55 | +0.01 | 31 |
| ETH | Tetik: EMA20 kesişimi · 1d | filtre: Alt: Perp primi 8s ort. (z) · 1 haftalık ortalama yönünde · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.93 | 2.26 / 1.54 | 0.60 | +1.33 | 38 |
| ETH | Tetik: EMA20 kesişimi · 1d | filtre: Alt: Perp primi 8s ort. (z) · 1 haftalık ortalama yönünde · long+short · sinyalle çıkış | 1.70 | 1.85 / 1.54 | 0.61 | +1.09 | 38 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Faktör: real_yield yönünde · sadece short · SL 2.0 / TP 4.0×ATR × volatilite oranı | 1.79 | 1.50 / 2.09 | 0.89 | +0.90 | 50 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Faktör: real_yield yönünde · sadece short · SL 2.0×ATR / TP 4.0×ATR | 1.61 | 1.49 / 1.75 | 0.79 | +0.83 | 50 |
| XAG | Tetik: Keltner kırılımı · 4h | filtre: Alt: COT üretici net (haftalık değişim) (z) yönünde · sadece long · sinyalle çıkış | 1.48 | 1.64 / 1.49 | 0.64 | +0.84 | 24 |
| XAU | Tetik: EMA20 kesişimi · 1d | filtre: Alt: COT swap dealer net (haftalık değişim) (z) yönünde · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 1.75 | 1.49 / 2.01 | 0.40 | +1.35 | 42 |
| ETH | Tetik: MACD kesişimi · 4h | filtre: Alt: Hesap long/short oranı (z) yönünde · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 1.52 | 1.55 / 1.49 | 0.71 | +0.81 | 95 |
| XAG | Tetik: Keltner kırılımı · 4h | filtre: Alt: COT üretici net (haftalık değişim) yönünde · sadece long · sinyalle çıkış | 1.47 | 1.64 / 1.48 | 0.64 | +0.83 | 26 |
| BTC | Tetik: 20 mum kırılımı · 4h | filtre: Faktör: asset_direction · 1 günlük ortalama yönünde · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 1.47 | 1.49 / 1.48 | 0.79 | +0.69 | 73 |
| NQ | Tetik: RSI(2) geri çekilme · 1d | filtre: Alt: COT varlık yöneticisi net (haftalık değişim) (z) · 1 haftalık ortalama yönünde · long+short · SL 2.0×ATR / TP 4.0×ATR | 1.45 | 1.47 / 1.62 | 0.19 | +1.26 | 37 |
| BTC | Tetik: Keltner kırılımı · 1d | filtre: Alt: Perp primi (baz) (z) · 1 günlük ortalama yönünde · long+short · iz süren stop 2.0×ATR | 1.61 | 1.44 / 1.78 | 1.55 | +0.06 | 26 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Faktör: btc_sympathy · 1 günlük ortalama yönünde · sadece short · sinyalle çıkış | 1.45 | 1.46 / 1.44 | 0.96 | +0.49 | 49 |
| ETH | Tetik: EMA20 kesişimi · 1d | filtre: Alt: Perp primi 8s ort. (z) · 1 haftalık ortalama yönünde · long+short · iz süren stop 2.0×ATR | 1.90 | 2.27 / 1.44 | 0.76 | +1.14 | 38 |
| XAG | Tetik: Bollinger bandı dışı · 4h | filtre: Alt: COT üretici net (haftalık değişim) · 1 haftalık ortalama yönünde · sadece long · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 1.45 | 1.80 / 1.44 | -0.35 | +1.80 | 32 |

## 3c) Yeni bilgi kaynağı — türev piyasası konumlanması (Binance) ve CFTC COT

_Varlıklar: BTC, ETH, NQ, SPX, XAG, XAU. Veri, canlı botun da bilebileceği an itibarıyla kullanıldı (Binance günlük dosyası gün başlangıcından 30 saat sonra, COT salı pozisyonu cumartesi 00:00 UTC). '(z)' = sinyalin kendi 90 gözlemlik ortalamasına göre konumu. Sinyal yönünde long+short, sinyalle çıkış._

| Sinyal | Ufuk | Kural | Ort. Sharpe | 1. yarı / 2. yarı | Pozitif varlık | İki yarıda + varlık |
|---|---|---|---|---|---|---|
| Alt: Açık pozisyon değişimi 24s (z) | 1 gün | ∣z∣>1.0 · ufuk ort. | -1.79 | -2.20 / -1.34 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 4 saat | ∣z∣>0.5 · son değer | -1.77 | -1.77 / -1.78 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 1 saat | ∣z∣>0.5 · son değer | -1.75 | -1.76 / -1.76 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s | 1 gün | ∣z∣>0.5 · son değer | -1.74 | -2.41 / -1.06 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 1 gün | ∣z∣>0.5 · son değer | -1.71 | -1.69 / -1.74 | 0/2 | 0/2 |
| Alt: Perp primi (baz) (z) | 1 ay | ∣z∣>0.5 · ufuk ort. | 1.70 | 1.79 / 1.58 | 2/2 | 2/2 |
| Alt: Hesap long/short oranı | 1 ay | ∣z∣>0.5 · son değer | -1.68 | -1.91 / -1.49 | 0/1 | 0/1 |
| Alt: COT spekülatif fon net (z) | 4 saat | ∣z∣>0.5 · ufuk ort. | -1.65 | -1.57 / -1.71 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s (z) | 1 gün | ∣z∣>0.5 · ufuk ort. | -1.56 | -2.12 / -0.95 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 1 gün | ∣z∣>0.5 · ufuk ort. | -1.55 | -1.44 / -1.62 | 0/2 | 0/2 |
| Alt: Perp primi 8s ort. (z) | 1 ay | ∣z∣>0.5 · ufuk ort. | 1.53 | 1.59 / 1.44 | 2/2 | 2/2 |
| Alt: Açık pozisyon değişimi 24s | 1 gün | ∣z∣>1.0 · ufuk ort. | -1.51 | -1.80 / -1.16 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s (z) | 1 gün | ∣z∣>0.5 · son değer | -1.44 | -2.27 / -0.60 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 1 saat | ∣z∣>1.0 · son değer | -1.41 | -1.13 / -1.59 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s | 1 gün | ∣z∣>0.5 · ufuk ort. | -1.41 | -1.85 / -0.92 | 0/2 | 0/2 |
| Alt: Perp primi 8s ort. (z) | 1 ay | ∣z∣>1.0 · ufuk ort. | 1.39 | 1.65 / 1.01 | 2/2 | 2/2 |
| Alt: COT spekülatif fon net (z) | 4 saat | ∣z∣>1.0 · son değer | -1.38 | -1.13 / -1.55 | 0/2 | 0/2 |
| Alt: Perp primi (baz) (z) | 1 ay | ∣z∣>1.0 · ufuk ort. | 1.37 | 1.30 / 1.53 | 2/2 | 2/2 |
| Alt: COT spekülatif fon net (z) | 1 gün | ∣z∣>1.0 · son değer | -1.37 | -1.17 / -1.50 | 0/2 | 0/2 |
| Alt: Agresif alış/satış oranı (z) | 1 saat | ∣z∣>1.0 · son değer | -1.35 | -1.53 / -1.12 | 0/2 | 0/2 |
| Alt: Agresif alış/satış oranı (z) | 4 saat | ∣z∣>1.0 · son değer | -1.29 | -1.49 / -1.03 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 4 saat | ∣z∣>1.0 · ufuk ort. | -1.28 | -1.10 / -1.41 | 0/2 | 0/2 |
| Alt: Agresif alış/satış oranı (z) | 1 gün | ∣z∣>0.5 · son değer | -1.28 | -2.06 / -0.47 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 1 hafta | ∣z∣>0.5 · son değer | -1.27 | -1.04 / -1.38 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s (z) | 1 gün | ∣z∣>1.0 · son değer | -1.25 | -1.63 / -0.80 | 0/2 | 0/2 |
| Alt: COT swap dealer net (z) | 1 hafta | ∣z∣>1.0 · ufuk ort. | 1.25 | 0.83 / 1.51 | 2/2 | 1/2 |
| Alt: COT spekülatif fon net (z) | 1 hafta | ∣z∣>1.0 · son değer | -1.22 | -1.02 / -1.29 | 0/2 | 0/2 |
| Alt: COT varlık yöneticisi net | 1 gün | ∣z∣>0.5 · ufuk ort. | 1.20 | 1.76 / 0.50 | 1/1 | 1/1 |
| Alt: Açık pozisyon değişimi 24s | 1 gün | ∣z∣>1.0 · son değer | -1.20 | -1.60 / -0.72 | 0/2 | 0/2 |
| Alt: COT üretici net (haftalık değişim) (z) | 1 gün | ∣z∣>1.0 · ufuk ort. | -1.19 | -0.44 / -1.64 | 0/2 | 0/2 |

_Negatif ortalama + iki yarıda tutarlı = sinyal TERS yönde çalışıyor olabilir (kalabalık pozisyonun tersine işlem); bu TERS versiyonlar ayrıca test edilip tüm konfigürasyon dosyasında yer alır._

## 4) Kaldıraç ve likidasyon (seçilen kural, 730 gün, saatlik High/Low ile)

| Varlık | 1x yıllık / DD | 2x | 3x | 5x | 10x | Vol hedefli (%40, maks 5x) | Likidasyon (1/2/3/5/10x) |
|---|---|---|---|---|---|---|---|
| SPX · seçilen kural (iyimser) | %+25 / %-7 | %+53 / %-13 | %+87 / %-19 | %+170 / %-30 | %+461 / %-54 | %+74 / %-21 | 0/0/0/0/0 |
| SPX · walk-forward OOS (gerçekçi) | %-6 / %-17 | %-14 / %-32 | %-24 / %-44 | %-44 / %-64 | %-85 / %-95 | — | 0/0/0/0/0 |
| NQ · seçilen kural (iyimser) | %+29 / %-8 | %+64 / %-15 | %+105 / %-22 | %+203 / %-34 | %+501 / %-61 | %+69 / %-18 | 0/0/0/0/0 |
| NQ · walk-forward OOS (gerçekçi) | %-5 / %-17 | %-12 / %-31 | %-19 / %-44 | %-34 / %-63 | %-70 / %-90 | — | 0/0/0/0/0 |
| XAU · seçilen kural (iyimser) | %+27 / %-8 | %+60 / %-15 | %+100 / %-21 | %+199 / %-33 | %+578 / %-57 | %+69 / %-12 | 0/0/0/0/0 |
| XAU · walk-forward OOS (gerçekçi) | %+1 / %-15 | %+1 / %-28 | %-1 / %-40 | %-9 / %-61 | %-46 / %-91 | — | 0/0/0/0/0 |
| XAG · seçilen kural (iyimser) | %+50 / %-9 | %+116 / %-17 | %+199 / %-24 | %+410 / %-41 | %+692 / %-81 | %+47 / %-9 | 0/0/0/0/0 |
| XAG · walk-forward OOS (gerçekçi) | %-19 / %-42 | %-41 / %-70 | %-60 / %-86 | %-87 / %-98 | %-100 / %-100 | — | 0/0/0/0/0 |
| BTC · seçilen kural (iyimser) | %+124 / %-28 | %+345 / %-49 | %+682 / %-65 | %+1578 / %-85 | %-78 / %-100 | %+133 / %-27 | 0/0/0/0/3 |
| BTC · walk-forward OOS (gerçekçi) | %-3 / %-38 | %-11 / %-64 | %-23 / %-80 | %-53 / %-95 | %-98 / %-100 | — | 0/0/0/0/1 |
| ETH · seçilen kural (iyimser) | %+57 / %-12 | %+137 / %-22 | %+243 / %-32 | %+539 / %-50 | %+1426 / %-80 | %+38 / %-7 | 0/0/0/0/0 |
| ETH · walk-forward OOS (gerçekçi) | %-6 / %-44 | %-21 / %-72 | %-42 / %-88 | %-81 / %-99 | %-100 / %-100 | — | 0/0/0/0/1 |

_'Seçilen kural' satırı o kuralın geçmişteki en iyi hâlidir (seçim yanlılığı yüzünden iyimser). 'Walk-forward OOS' satırı, her dönemde o güne kadar en iyi olanı seçip uygulasaydınız ne olacağını gösterir (günlük kapanışla; gün içi likidasyonları kaçırabilir). Kaldıraç Sharpe'ı değiştirmez; getiriyi de düşüşü de büyütür ve likidasyonla sermayeyi sıfırlayabilir. Kanıtsız bir kurala kaldıraç eklemek beklenen kaybı büyütür._

## 5) Kombinasyon türlerine göre (6 varlık ortalaması)

| Tür | Konfigürasyon | En iyi Sharpe | Medyan Sharpe | WF-OOS Sharpe | WF pozitif varlık |
|---|---|---|---|---|---|
| tek·1 hafta | 92,640 | 2.15 | -0.18 | 0.63 | 3/6 |
| tek·1 saat | 61,894 | 1.80 | -1.96 | 0.05 | 3/6 |
| filtre+tetik | 201,612 | 1.85 | -0.88 | 0.01 | 3/6 |
| referans | 12 | 0.35 | -0.13 | 0.00 | 0/6 |
| tek·1 ay | 76,284 | 1.19 | -0.17 | -0.07 | 2/6 |
| oylama | 1,386 | 0.79 | -1.07 | -0.12 | 2/6 |
| sys×trend | 19,110 | 1.25 | -1.49 | -0.14 | 2/6 |
| sys | 51,940 | 1.61 | -2.17 | -0.20 | 2/6 |
| tetik (filtresiz) | 1,944 | 1.18 | -0.69 | -0.33 | 3/6 |
| teknik×sys | 118,916 | 1.43 | -1.50 | -0.34 | 2/6 |
| teknik | 27,048 | 1.68 | -0.73 | -0.38 | 1/6 |
| tek·1 gün | 90,384 | 1.78 | -0.45 | -0.40 | 2/6 |
| tek·4 saat | 207,368 | 1.97 | -1.33 | -0.40 | 1/6 |
| teknik×filtre | 126,714 | 1.29 | -1.57 | -1.02 | 0/6 |
| sys×filtre | 42,756 | 0.82 | -2.00 | -1.29 | 0/6 |
| sys×sys | 12,068 | 0.47 | -1.92 | -1.47 | 0/6 |

## 6) Sistemin kendi sinyalleri tek başına (long+short, sinyalle çıkış, sistemin yönünde)

| Sinyal | BTC | ETH | NQ | SPX | XAG | XAU | Ort. | 1. yarı / 2. yarı | Pozitif |
|---|---|---|---|---|---|---|---|---|---|
| Faktör: nq_relative_divergence | — | — | — | -11.76 | — | — | -11.76 | -10.74 / -13.15 | 0/1 |
| Faktör: spx_relative_divergence | — | — | -10.17 | — | — | — | -10.17 | -10.51 / -9.81 | 0/1 |
| direction_acceleration | -8.83 | -6.48 | -10.60 | -13.15 | -5.59 | -9.17 | -8.97 | -10.06 / -8.57 | 0/6 |
| pair_stats.residual_z | -7.58 | -5.00 | -10.11 | -12.44 | -6.46 | -9.84 | -8.57 | -9.07 / -8.65 | 0/6 |
| pair_stats.spread | -7.56 | -4.90 | -9.71 | -11.85 | -6.88 | -10.46 | -8.56 | -9.07 / -8.74 | 0/6 |
| current_roc | -8.17 | -4.94 | -9.43 | -12.01 | -5.97 | -8.75 | -8.21 | -8.72 / -8.33 | 0/6 |
| Faktör: gold_macro_lead | — | — | — | — | — | -7.75 | -7.75 | -7.61 / -8.06 | 0/1 |
| Fiyat itkisi skoru | -7.88 | -4.80 | -8.29 | -10.73 | -5.31 | -8.27 | -7.55 | -8.12 / -7.53 | 0/6 |
| short_term_parts.price_z | -7.88 | -4.81 | -8.26 | -10.72 | -5.28 | -8.20 | -7.52 | -8.12 / -7.49 | 0/6 |
| short_term_parts.price_part | -7.85 | -4.73 | -8.29 | -10.73 | -5.22 | -8.27 | -7.52 | -8.11 / -7.49 | 0/6 |
| Faktör: gold_divergence_residual | — | — | — | — | -6.61 | — | -6.61 | -9.73 / -5.49 | 0/1 |
| Makro: credit_velocity | — | — | — | — | — | -6.43 | -6.43 | -6.86 / -6.49 | 0/1 |
| Faktör: credit_spread | -3.66 | -2.29 | -6.46 | -8.58 | — | — | -5.25 | -4.50 / -6.09 | 0/4 |
| Faktör: usd_strength | -2.24 | -1.22 | -6.92 | -9.34 | -4.56 | -6.23 | -5.09 | -4.97 / -5.58 | 0/6 |
| Faktör: consumer_demand | — | — | — | -5.07 | — | — | -5.07 | -4.12 / -6.45 | 0/1 |
| direction_velocity | -3.73 | -3.28 | -5.28 | -6.40 | -3.71 | -4.66 | -4.51 | -5.19 / -4.24 | 0/6 |
| Faktör: asset_direction | -4.53 | -2.52 | -5.20 | -6.65 | -2.50 | -2.93 | -4.06 | -4.13 / -4.15 | 0/6 |
| Faktör: usd_jpy_carry | -2.25 | -2.04 | -5.08 | -6.50 | — | — | -3.97 | -3.56 / -4.47 | 0/4 |
| Makro: yen_carry_z | — | — | — | — | -2.89 | -4.93 | -3.91 | -4.00 / -4.06 | 0/2 |
| Faktör: gsr_velocity | — | — | — | — | — | -3.82 | -3.82 | -3.76 / -3.96 | 0/1 |
| adaptive_cluster_scores.E | -3.29 | -2.74 | -3.00 | -5.09 | -3.27 | -4.20 | -3.60 | -3.62 / -3.80 | 0/6 |
| live_score_pair_adjusted | -3.57 | -1.62 | -4.03 | -5.70 | -2.58 | -3.31 | -3.47 | -3.78 / -3.56 | 0/6 |
| Çift-uyumlu yön skoru | -3.54 | -1.61 | -4.05 | -5.70 | -2.57 | -3.33 | -3.47 | -3.78 / -3.57 | 0/6 |
| Faktör: defensive_flight | — | — | -3.02 | -3.90 | — | — | -3.46 | -3.07 / -4.01 | 0/2 |
| raw_model_score | -2.50 | -2.40 | -3.47 | -5.43 | -3.00 | -3.01 | -3.30 | -4.15 / -2.80 | 0/6 |
| adaptive_cluster_scores.C | -3.25 | -1.99 | -4.06 | -5.05 | -4.40 | -0.73 | -3.25 | -3.40 / -3.40 | 0/6 |
| Adaptif skor | -2.36 | -1.69 | -3.42 | -5.49 | -2.41 | -2.99 | -3.06 | -3.54 / -2.78 | 0/6 |
| Faktör: btc_sympathy | — | -3.04 | — | — | — | — | -3.04 | -3.48 / -2.54 | 0/1 |
| adaptive_cluster_scores.A | -1.35 | -0.95 | -4.89 | -5.61 | -2.21 | -3.15 | -3.03 | -4.80 / -1.94 | 0/6 |
| Faktör: gold_sovereign_decoupling | — | — | — | — | — | -2.50 | -2.50 | -0.94 / -3.60 | 0/1 |
| pair_common_factor.gap_before | -3.07 | -1.81 | — | — | — | — | -2.44 | -2.60 / -2.29 | 0/2 |
| composite_usd_risk | -2.35 | -1.69 | -2.65 | -3.83 | -1.70 | -2.38 | -2.44 | -3.94 / -1.08 | 0/6 |
| adaptive_cluster_scores.D | — | — | -2.45 | -2.95 | -1.03 | -3.12 | -2.38 | -2.19 / -2.81 | 0/4 |
| pair_common_factor.common_score | -2.83 | -1.78 | — | — | — | — | -2.31 | -3.32 / -1.18 | 0/2 |
| score_raw_cycle | -2.22 | -1.71 | — | — | -2.44 | -2.79 | -2.29 | -3.01 / -1.89 | 0/4 |
| Faktör: market_breadth | — | — | — | -2.28 | — | — | -2.28 | -2.83 / -1.64 | 0/1 |
| Faktör: vix_strain | -1.92 | -1.32 | -2.76 | -2.90 | — | — | -2.23 | -1.77 / -2.74 | 0/4 |
| Faktör: semi_lead | — | — | -1.84 | -2.58 | — | — | -2.21 | -2.88 / -1.36 | 0/2 |
| Faktör: banking_stress | -1.33 | — | -2.75 | -3.47 | — | -1.30 | -2.21 | -2.53 / -2.03 | 0/4 |
| Faktör: duration_risk | -0.94 | -0.47 | -2.69 | -3.37 | -1.63 | -3.68 | -2.13 | -2.98 / -1.77 | 0/6 |

_Negatif ortalama = sinyal TERS yönde kullanılırsa çalışıyor olabilir (TERS kurallar da ayrıca test edildi)._

## 7) Tüm varlıklarda aynı ayarla en tutarlı kurallar

| Kural | Ort. Sharpe | Pozitif varlık |
|---|---|---|
| Keltner kırılımı (20/2.0) · 1d · long+short · SL 2.0×ATR / TP 4.0×ATR | 0.76 | 6/6 |
| Keltner kırılımı (20/2.0) · 1d · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 0.62 | 6/6 |
| Keltner kırılımı (20/2.0) · 1d · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 0.56 | 6/6 |
| Keltner kırılımı (20/2.0) · 1d · sadece long · SL 2.0×ATR / TP 4.0×ATR | 0.55 | 6/6 |
| RSI trend (14) · 1d · sadece long · SL 2.0 / TP 4.0×ATR × volatilite oranı | 0.54 | 6/6 |
| Keltner kırılımı (20/2.0) · 1d · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | 0.51 | 6/6 |
| Momentum (60) · 1d · sadece long · sinyalle çıkış | 0.47 | 6/6 |
| EMA kesişimi (50/200) · 4h · sadece long · sinyalle çıkış | 0.46 | 6/6 |
| EMA kesişimi (10/30) · 1d · sadece long · sinyalle çıkış | 0.46 | 6/6 |
| EMA trend (50) · 1d · sadece long · sinyalle çıkış | 0.43 | 6/6 |
| EMA kesişimi (20/50) · 1d · sadece long · sinyalle çıkış | 0.43 | 6/6 |
| RSI trend (14) · 1d · sadece long · SL 2.0×ATR / TP 4.0×ATR | 0.43 | 6/6 |
| Makro: breakeven_z · sadece long · SL 1.5×ATR / TP 3.0×ATR | 0.42 | 6/6 |
| EMA trend (100) · 1d · sadece long · sinyalle çıkış | 0.42 | 6/6 |
| RSI trend (14) · 1d · sadece long · sinyalle çıkış | 0.41 | 6/6 |

## 8) Varlık bazında ilk 15 (tam pencere — seçim yanlılığı İÇERİR, tek başına kanıt değildir)

**SPX — S&P 500** · 2024-11-08 → 2026-10-09 · 188,500 konfigürasyon (etkin bağımsız: 27)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.16 | 3.92 / 0.25 | %+52.4 | %-6.2 | 31 | %71 | %38 |
| 2 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 2.14 | 3.83 / 0.25 | %+52.6 | %-6.2 | 31 | %71 | %37 |
| 3 | Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama · sadece long · SL 2.0×ATR / TP 4.0×ATR | tek·4 saat | 2.07 | 1.48 / 2.55 | %+23.6 | %-2.5 | 25 | %72 | %14 |
| 4 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.05 | 3.52 / 0.43 | %+47.0 | %-5.4 | 31 | %64 | %36 |
| 5 | Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>1) · 4 saatlik ortalama · sadece long · SL 2.0×ATR / TP 4.0×ATR | tek·4 saat | 1.90 | 1.17 / 2.48 | %+21.3 | %-2.5 | 25 | %68 | %13 |
| 6 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 1.84 | 3.44 / 0.25 | %+40.4 | %-6.2 | 31 | %71 | %38 |
| 7 | TERS Faktör: nq_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 1.82 | 4.23 / -0.72 | %+48.2 | %-11.6 | 34 | %62 | %46 |
| 8 | Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1) · sadece long · SL 2.0×ATR / TP 4.0×ATR | tek·1 saat | 1.80 | 1.03 / 2.42 | %+20.8 | %-2.7 | 25 | %72 | %15 |
| 9 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış | tek·1 hafta | 1.79 | 2.92 / 0.72 | %+20.9 | %-3.4 | 16 | %81 | %20 |
| 10 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 1.79 | 2.92 / 0.72 | %+20.9 | %-3.4 | 16 | %81 | %20 |
| 11 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 1.79 | 2.92 / 0.72 | %+20.9 | %-3.4 | 16 | %81 | %20 |
| 12 | Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1) · 4 saatlik · sadece long · SL 2.0×ATR / TP 4.0×ATR | tek·4 saat | 1.79 | 1.03 / 2.40 | %+20.9 | %-2.7 | 25 | %72 | %15 |
| 13 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 1.78 | 2.90 / 0.72 | %+20.8 | %-3.4 | 16 | %81 | %20 |
| 14 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 1.78 | 2.92 / 0.70 | %+20.7 | %-3.4 | 16 | %81 | %20 |
| 15 | Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>1) · sadece long · SL 2.0×ATR / TP 4.0×ATR | tek·1 saat | 1.72 | 1.00 / 2.31 | %+20.0 | %-2.7 | 25 | %72 | %15 |

_Walk-forward dilim getirileri: %-11.4, %+7.0, %-0.5, %-2.3, %-1.8 · seçilenler: TERS Momentum (180) · 4h · 1 günlük · long+short · sinyalle çıkış; TERS Faktör: nq_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı; TERS Faktör: nq_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı; TERS Faktör: nq_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı; pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR / TP 6.0×ATR_

**NQ — Nasdaq 100** · 2024-11-08 → 2026-10-09 · 189,886 konfigürasyon (etkin bağımsız: 26)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 1.98 | 3.29 / 0.75 | %+63.4 | %-6.9 | 31 | %77 | %38 |
| 2 | TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>1) · 4 saatlik ortalama · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·4 saat | 1.96 | 1.72 / 2.23 | %+36.7 | %-6.0 | 20 | %85 | %17 |
| 3 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 1.91 | 3.08 / 0.92 | %+31.3 | %-4.3 | 16 | %88 | %20 |
| 4 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 1.91 | 3.08 / 0.92 | %+31.3 | %-4.3 | 16 | %88 | %20 |
| 5 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 1.91 | 3.08 / 0.92 | %+31.3 | %-4.3 | 16 | %88 | %20 |
| 6 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 1.91 | 3.08 / 0.92 | %+31.3 | %-4.3 | 16 | %88 | %20 |
| 7 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış | tek·1 hafta | 1.91 | 3.08 / 0.92 | %+31.3 | %-4.3 | 16 | %88 | %20 |
| 8 | TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>1) · 4 saatlik ortalama · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·4 saat | 1.91 | 2.29 / 1.53 | %+28.8 | %-4.2 | 20 | %90 | %17 |
| 9 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 1.90 | 3.07 / 0.92 | %+31.2 | %-4.3 | 16 | %88 | %20 |
| 10 | TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·4 saat | 1.86 | 1.55 / 2.22 | %+34.3 | %-5.8 | 20 | %80 | %17 |
| 11 | Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · 4 saatlik · sadece short · SL 3.0×ATR / TP 6.0×ATR | tek·4 saat | 1.83 | 1.86 / 1.89 | %+30.4 | %-3.5 | 16 | %75 | %12 |
| 12 | TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>1) · 4 saatlik ortalama · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·4 saat | 1.82 | 1.54 / 2.14 | %+33.3 | %-6.0 | 20 | %85 | %16 |
| 13 | Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · sadece short · SL 3.0×ATR / TP 6.0×ATR | tek·1 saat | 1.81 | 1.81 / 1.89 | %+29.9 | %-3.5 | 16 | %75 | %12 |
| 14 | TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·4 saat | 1.80 | 2.09 / 1.52 | %+26.7 | %-4.2 | 20 | %85 | %17 |
| 15 | Donchian kırılımı (168) · 1h · sadece long · iz süren stop 3.0×ATR | teknik | 1.80 | 0.35 / 2.71 | %+21.8 | %-2.2 | 20 | %45 | %11 |

_Walk-forward dilim getirileri: %-13.2, %+5.3, %+8.2, %-4.4, %-3.2 · seçilenler: Alt: COT dealer net (haftalık değişim) (z) (güçlü, ∣z∣>0.5) · 4 saatlik ortalama · long+short · SL 2.0×ATR / TP 4.0×ATR; pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama · long+short · SL 2.0×ATR / TP 4.0×ATR; TERS MACD (12/26/9) · 4h · 1 aylık · sadece long · sinyalle çıkış_

**XAU — Altın** · 2024-11-08 → 2026-10-09 · 184,050 konfigürasyon (etkin bağımsız: 31)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.21 | 2.65 / 1.80 | %+58.9 | %-6.4 | 18 | %67 | %25 |
| 2 | Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 2.18 | 2.51 / 1.86 | %+60.8 | %-6.4 | 18 | %72 | %27 |
| 3 | Zaman dilimi uyumu (güçlü, ∣z∣>0.5) · 1 haftalık ortalama · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.12 | 2.69 / 1.70 | %+60.3 | %-8.8 | 15 | %53 | %26 |
| 4 | Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.11 | 2.44 / 1.80 | %+56.8 | %-6.4 | 18 | %72 | %26 |
| 5 | Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 2.02 | 2.08 / 1.99 | %+66.2 | %-6.4 | 18 | %72 | %27 |
| 6 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>1) · 1 günlük · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 gün | 1.94 | 2.27 / 1.92 | %+87.2 | %-12.8 | 23 | %70 | %43 |
| 7 | Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 1.94 | 2.04 / 1.85 | %+51.6 | %-6.4 | 18 | %72 | %28 |
| 8 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>1) · 1 günlük · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 gün | 1.94 | 2.13 / 2.02 | %+90.7 | %-12.8 | 23 | %70 | %43 |
| 9 | EMA kesişimi (24/96) · 1h · 4 saatlik ortalama · sadece long · 24 saat tut | tek·4 saat | 1.94 | 2.18 / 1.65 | %+22.5 | %-3.1 | 54 | %56 | %11 |
| 10 | Keltner kırılımı (20/2.0) · 1d + teyit: Yön z-skoru · sadece long · SL 1.5×ATR / TP 3.0×ATR | teknik×sys | 1.92 | 1.55 / 2.27 | %+36.8 | %-5.2 | 32 | %56 | %13 |
| 11 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük ortalama · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 gün | 1.87 | 2.13 / 1.76 | %+83.4 | %-14.0 | 28 | %61 | %59 |
| 12 | MACD (12/26/9) · 1h · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 1.85 | 1.76 / 1.98 | %+67.8 | %-8.6 | 24 | %62 | %39 |
| 13 | adaptive_cluster_scores.D · 1 haftalık ortalama · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 1.83 | 2.38 / 1.42 | %+73.5 | %-12.1 | 19 | %63 | %44 |
| 14 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 gün | 1.83 | 3.18 / 0.83 | %+40.9 | %-7.0 | 15 | %67 | %25 |
| 15 | Zaman dilimi uyumu (güçlü, ∣z∣>0.5) · 1 haftalık ortalama · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 1.82 | 2.04 / 1.66 | %+52.7 | %-8.8 | 15 | %53 | %29 |

_Walk-forward dilim getirileri: %+2.3, %+2.4, %+0.0, %-4.6, %+1.7 · seçilenler: Tetik: 20 mum kırılımı · 1h | filtre: Faktör: safe_haven · 1 günlük ortalama yönünde · sadece long · sinyalle çıkış; TERS Yön z-skoru (güçlü, ∣z∣>1) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; TERS Makro: breakeven_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı; TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük · sadece long · SL 3.0×ATR / TP 6.0×ATR; Faktör: gold_macro_lead (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş)_

**XAG — Gümüş** · 2024-11-08 → 2026-10-09 · 183,314 konfigürasyon (etkin bağımsız: 26)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | TERS Faktör: silver_vol_premium_lead (güçlü, ∣z∣>1) · 1 günlük · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 gün | 2.34 | 1.76 / 2.83 | %+117.1 | %-5.4 | 24 | %54 | %11 |
| 2 | Adaptif skor (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.20 | 1.97 / 2.42 | %+125.2 | %-9.2 | 17 | %71 | %20 |
| 3 | TERS Faktör: silver_vol_premium_lead (güçlü, ∣z∣>1) · 1 günlük · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 gün | 2.16 | 1.40 / 2.72 | %+96.2 | %-4.4 | 24 | %54 | %12 |
| 4 | Adaptif skor (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 2.14 | 2.15 / 2.28 | %+118.5 | %-11.1 | 17 | %76 | %20 |
| 5 | TERS Kısa Vade Yön · 1 günlük · sadece long · sinyalle çıkış | tek·1 gün | 2.04 | 0.70 / 2.84 | %+142.5 | %-11.2 | 51 | %69 | %15 |
| 6 | TERS Kısa Vade Yön (güçlü, ∣z∣>0.5) · 1 günlük · sadece long · sinyalle çıkış | tek·1 gün | 2.04 | 0.70 / 2.84 | %+142.3 | %-11.2 | 50 | %68 | %15 |
| 7 | composite_usd_risk (güçlü, ∣z∣>0.5) · 1 haftalık ortalama · sadece long · sinyalle çıkış | tek·1 hafta | 2.02 | 1.35 / 2.54 | %+173.3 | %-18.8 | 15 | %67 | %47 |
| 8 | adaptive_cluster_scores.B (güçlü, ∣z∣>1) · 1 günlük · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 gün | 1.99 | -0.20 / 3.21 | %+141.2 | %-8.8 | 76 | %59 | %18 |
| 9 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>1) · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 saat | 1.99 | 1.05 / 2.62 | %+118.9 | %-8.6 | 24 | %67 | %22 |
| 10 | score_raw_cycle (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 1.97 | 2.20 / 1.88 | %+111.2 | %-12.0 | 19 | %68 | %21 |
| 11 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>1) · 4 saatlik · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·4 saat | 1.97 | 1.10 / 2.56 | %+118.5 | %-8.6 | 24 | %67 | %22 |
| 12 | adaptive_cluster_scores.B (güçlü, ∣z∣>1) · 1 günlük · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 gün | 1.95 | -0.28 / 3.20 | %+136.7 | %-9.8 | 76 | %59 | %18 |
| 13 | adaptive_cluster_scores.B (güçlü, ∣z∣>1) · 1 günlük · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 gün | 1.95 | -0.28 / 3.20 | %+136.7 | %-9.8 | 76 | %59 | %18 |
| 14 | adaptive_cluster_scores.B (güçlü, ∣z∣>1) · 1 günlük · sadece long · iz süren stop 3.0×ATR | tek·1 gün | 1.95 | -0.28 / 3.20 | %+136.7 | %-9.8 | 76 | %59 | %18 |
| 15 | adaptive_cluster_scores.B (güçlü, ∣z∣>1) · 1 günlük · sadece long · sinyalle çıkış | tek·1 gün | 1.95 | -0.28 / 3.20 | %+136.7 | %-9.8 | 76 | %59 | %18 |

_Walk-forward dilim getirileri: %-8.9, %+4.0, %-7.5, %-13.9, %-5.8 · seçilenler: EMA kesişimi (20/50) · 4h · 4 saatlik ortalama · long+short · SL 1.5×ATR / TP 3.0×ATR; Tetik: RSI(2) geri çekilme · 1d | filtre: Alt: COT üretici net (haftalık değişim) · 1 günlük ortalama yönünde · sadece short · SL 2.0 / TP 4.0×ATR × volatilite oranı; Bollinger dönüş (20/2.0) · 4h · 1 haftalık ortalama · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; TERS Alt: COT üretici net (z) (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış; composite_usd_risk (güçlü, ∣z∣>0.5) · 1 haftalık ortalama · sadece long · sinyalle çıkış_

**BTC — Bitcoin** · 2024-11-08 → 2026-10-09 · 195,044 konfigürasyon (etkin bağımsız: 37)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | TERS direction_velocity · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 2.38 | 1.21 / 3.61 | %+371.0 | %-26.0 | 53 | %76 | %76 |
| 2 | TERS direction_velocity · 1 haftalık · long+short · sinyalle çıkış | tek·1 hafta | 2.21 | 1.60 / 2.81 | %+546.2 | %-17.3 | 53 | %76 | %100 |
| 3 | TERS direction_velocity · 1 haftalık · long+short · iz süren stop 3.0×ATR | tek·1 hafta | 2.21 | 1.02 / 3.23 | %+363.1 | %-16.7 | 53 | %70 | %68 |
| 4 | TERS direction_velocity · 1 haftalık · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.13 | 1.01 / 3.34 | %+331.6 | %-24.8 | 53 | %72 | %78 |
| 5 | TERS direction_velocity · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.10 | 0.90 / 3.24 | %+277.0 | %-23.4 | 53 | %60 | %64 |
| 6 | TERS direction_velocity · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 2.00 | 0.81 / 3.29 | %+290.7 | %-24.9 | 53 | %72 | %77 |
| 7 | Tetik: Keltner kırılımı · 1d | filtre: Alt: COT kaldıraçlı fon net (haftalık değişim) yönünde · long+short · iz süren stop 2.0×ATR | filtre+tetik | 1.90 | 0.82 / 2.67 | %+102.5 | %-7.5 | 16 | %56 | %8 |
| 8 | Alt: COT kaldıraçlı fon net (z) (güçlü, ∣z∣>1) · 4 saatlik · long+short · SL 1.5×ATR / TP 3.0×ATR | tek·4 saat | 1.86 | 1.68 / 2.05 | %+65.2 | %-9.2 | 33 | %55 | %17 |
| 9 | TERS direction_velocity · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 1.86 | 1.66 / 2.05 | %+126.2 | %-12.9 | 26 | %73 | %37 |
| 10 | Alt: COT kaldıraçlı fon net (z) (güçlü, ∣z∣>1) · long+short · SL 1.5×ATR / TP 3.0×ATR | tek·1 saat | 1.85 | 1.66 / 2.03 | %+64.4 | %-9.2 | 33 | %52 | %17 |
| 11 | TERS direction_velocity · 1 haftalık · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 1.84 | 1.99 / 1.70 | %+132.2 | %-11.5 | 26 | %69 | %36 |
| 12 | TERS Alt: Açık pozisyon değişimi 24s · 1 haftalık · long+short · sinyalle çıkış | tek·1 hafta | 1.83 | 1.77 / 1.88 | %+371.2 | %-24.5 | 53 | %72 | %100 |
| 13 | Alt: COT kaldıraçlı fon net (z) (güçlü, ∣z∣>1) · 4 saatlik · sadece long · SL 1.5×ATR / TP 3.0×ATR | tek·4 saat | 1.81 | 1.95 / 1.69 | %+40.7 | %-6.6 | 16 | %62 | %11 |
| 14 | Alt: COT kaldıraçlı fon net (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama · sadece long · SL 1.5×ATR / TP 3.0×ATR | tek·4 saat | 1.81 | 1.89 / 1.74 | %+40.4 | %-5.8 | 16 | %62 | %10 |
| 15 | Alt: COT kaldıraçlı fon net (z) (güçlü, ∣z∣>1) · sadece long · SL 1.5×ATR / TP 3.0×ATR | tek·1 saat | 1.80 | 1.95 / 1.68 | %+40.5 | %-6.7 | 16 | %62 | %11 |

_Walk-forward dilim getirileri: %+27.2, %+9.4, %-21.0, %-8.7, %-4.7 · seçilenler: TERS Yön z-skoru · 4 saatlik ortalama · long+short · 24 saat tut; TERS Yön z-skoru · 4 saatlik ortalama · long+short · 24 saat tut; TERS Yön z-skoru · 4 saatlik ortalama · long+short · 24 saat tut; TERS Makro: stagflation_z (güçlü, ∣z∣>1) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş); Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1) · 1 aylık ortalama · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR_

**ETH — Ethereum** · 2024-11-08 → 2026-10-09 · 191,282 konfigürasyon (etkin bağımsız: 35)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Tetik: Keltner kırılımı · 4h | filtre: Kısa Vade Yön · 1 günlük ortalama yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | filtre+tetik | 2.24 | 2.58 / 1.88 | %+138.3 | %-9.7 | 45 | %69 | %10 |
| 2 | RSI trend (14) · 1d · 4 saatlik ortalama · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·4 saat | 2.04 | 2.26 / 1.82 | %+338.2 | %-18.9 | 56 | %55 | %59 |
| 3 | Alt: Perp primi (baz) (z) · 1 haftalık ortalama · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.00 | 2.22 / 1.79 | %+647.9 | %-24.0 | 44 | %55 | %72 |
| 4 | RSI trend (14) · 1d · 4 saatlik ortalama · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·4 saat | 2.00 | 2.40 / 1.50 | %+673.3 | %-24.0 | 56 | %45 | %64 |
| 5 | TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>1) · 1 haftalık · long+short · iz süren stop 3.0×ATR | tek·1 hafta | 1.97 | 2.18 / 1.72 | %+397.8 | %-23.9 | 33 | %73 | %39 |
| 6 | Tetik: EMA20 kesişimi · 1d | filtre: Alt: Perp primi 8s ort. (z) · 1 haftalık ortalama yönünde · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | filtre+tetik | 1.93 | 2.26 / 1.54 | %+160.8 | %-18.4 | 38 | %53 | %18 |
| 7 | Faktör: asset_direction (güçlü, ∣z∣>0.5) · 1 haftalık ortalama · sadece short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 1.92 | 1.80 / 2.13 | %+311.8 | %-23.1 | 20 | %65 | %29 |
| 8 | RSI trend (14) · 1d · 4 saatlik ortalama · long+short · SL 2.0 / TP 4.0×ATR × volatilite oranı | tek·4 saat | 1.92 | 2.38 / 1.33 | %+434.7 | %-22.7 | 56 | %46 | %46 |
| 9 | Tetik: Keltner kırılımı · 4h | filtre: Faktör: real_yield yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | filtre+tetik | 1.91 | 1.86 / 1.97 | %+105.6 | %-9.2 | 50 | %62 | %8 |
| 10 | Tetik: EMA20 kesişimi · 1d | filtre: Alt: Perp primi 8s ort. (z) · 1 haftalık ortalama yönünde · long+short · iz süren stop 2.0×ATR | filtre+tetik | 1.90 | 2.27 / 1.44 | %+193.0 | %-18.4 | 38 | %53 | %17 |
| 11 | TERS Model z (kısa vade) + teyit: Momentum (60) · 1d · sadece long · iz süren stop 2.0×ATR | sys×trend | 1.89 | 2.84 / 0.45 | %+101.0 | %-13.1 | 89 | %64 | %14 |
| 12 | TERS Model skoru + teyit: Momentum (60) · 1d · sadece long · iz süren stop 2.0×ATR | sys×trend | 1.89 | 2.84 / 0.45 | %+101.0 | %-13.1 | 90 | %63 | %14 |
| 13 | EMA trend (200) · 1d · 4 saatlik ortalama · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·4 saat | 1.89 | 1.67 / 2.42 | %+295.5 | %-25.3 | 15 | %47 | %27 |
| 14 | Tetik: EMA20 kesişimi · 1d | filtre: Alt: Perp primi 8s ort. (z) · 1 haftalık ortalama yönünde · long+short · SL 2.0×ATR / TP 4.0×ATR | filtre+tetik | 1.89 | 2.39 / 1.20 | %+215.2 | %-19.3 | 38 | %50 | %17 |
| 15 | Momentum (60) · 1d · long+short · SL 2.0×ATR / TP 4.0×ATR | teknik | 1.88 | 1.85 / 1.91 | %+258.1 | %-16.6 | 19 | %53 | %20 |

_Walk-forward dilim getirileri: %-8.2, %+17.4, %+18.7, %-15.6, %-16.0 · seçilenler: Momentum (336) · 1h · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; Momentum (336) · 1h · 4 saatlik · long+short · SL 3.0×ATR / TP 6.0×ATR; Momentum (336) · 1h · 4 saatlik · long+short · SL 3.0×ATR / TP 6.0×ATR; Momentum (336) · 1h · 4 saatlik · long+short · SL 3.0×ATR / TP 6.0×ATR; TERS composite_usd_risk (güçlü, ∣z∣>0.5) · 1 aylık ortalama · long+short · sinyalle çıkış_

_Tüm konfigürasyonların tek tek sonuçları: **lab_all_configs.csv.gz**._
