# 🧪 Strateji Laboratuvarı v7 — Kaldıraçlı Vadeli (Perp) Sonuç Raporu

_Üretim: 2026-10-10T10:02 UTC · fiyat: yahoo · sistem sinyalleri: signal_panel.csv.gz · denenen konfigürasyon: **1,129,920**_

**Maliyetler:** işlem başına (giriş ve çıkışta ayrı ayrı) komisyon+kayma %0.08; fonlama: long pozisyon 8 saatte %0.010 öder, short pozisyona fonlama geliri yazılmaz (tutucu). Tüm getiriler 1x pozisyon büyüklüğünde ve maliyetler düşülmüş (net); kaldıraç tablosu ayrı.

**v6:** her sinyal 5 tutma ufkunda (1 saat · 4 saat · 1 gün · 1 hafta · 1 ay), son değer ya da ufuk ortalaması, işaret / güçlü (∣z∣>0.5, ∣z∣>1), sistem yönünde ve TERS, long+short / sadece long / sadece short, 3-8 çıkış kuralıyla TEK TEK; sonra hazır kombinasyonlar ve veriden keşfedilen kombinasyonlar test edildi.

**Kanıt** (biri yeterli; **C:** kombinasyon keşfinde hiç görülmemiş son dönemde t ≥ 2) — **A:** sistem sinyalli pencerede seçim prosedürünün walk-forward OOS t ≥ 2, 5 dilimin ≥ 3'ü pozitif, Deflated Sharpe ≥ 0.90, ≥ 30 işlem · **B:** 10 yıllık günlük veride aynı testler (7 dilimin ≥ 5'i). Kanıtlı kural ayrıca 'sürekli long perp'e karşı **alfa t ≥ 2** veriyorsa **✅ KANITLI ALFA** (bot işlem yapabilir); vermiyorsa **⚠️ β AĞIRLIKLI** (kazancı çoğunlukla piyasa yönünden; işlem sinyali sayılmaz).

## 1) Varlık bazında sonuç

| Varlık | Seçilen kural (pencerenin en iyisi) | Sharpe | 1. yarı / 2. yarı | Getiri | Maks. DD | İşlem | Kazanma | DSR | WF-OOS Sharpe (t) · + dilim | Alfa t | Uzun dönem 1g: en iyi kural · WF Sharpe (t) · + dilim · alfa t | Sürekli long Sharpe / getiri | Durum | Sinyal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| SPX | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış | 2.53 | 3.08 / 1.89 | %+26.3 | %-2.4 | 15 | %87 | 0.96 | -0.11 (-0.1) · 3/5 | -0.7 | Momentum (60) · 1d · long+short · SL 2.0×ATR / TP 4.0×ATR · 0.23 (+0.7) · 6/7 · +0.7 · 10.0 yıl | 0.42 / %+15.3 | ❌ kanıt yok | ⚪ YOK |
| NQ | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış | 2.70 | 3.20 / 2.13 | %+39.0 | %-3.0 | 15 | %93 | 0.98 | 0.30 (+0.4) · 4/5 | +0.4 | Momentum (60) · 1d · sadece long · SL 3.0×ATR / TP 6.0×ATR · 0.20 (+0.6) · 4/7 · +0.5 · 10.0 yıl | 0.61 / %+31.4 | ❌ kanıt yok | ⚪ YOK |
| XAU | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük ortalama · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | 1.94 | 2.18 / 1.83 | %+86.0 | %-14.0 | 28 | %64 | 0.73 | 0.32 (+0.4) · 4/5 | +0.1 | Keltner kırılımı (20/2.0) · 1d · sadece long · SL 1.5×ATR / TP 3.0×ATR · -0.21 (-0.6) · 2/7 · -0.7 · 10.0 yıl | 0.62 / %+34.8 | ❌ kanıt yok | 🟢 LONG |
| XAG | TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama · sadece long · iz süren stop 3.0×ATR | 2.35 | 2.16 / 2.57 | %+274.7 | %-16.4 | 24 | %75 | 0.90 | -0.32 (-0.4) · 2/5 | -0.8 | TERS DMI/ADX yönü (14) · 1d · sadece long · sinyalle çıkış · -0.14 (-0.4) · 4/7 · -0.4 · 10.0 yıl | 0.46 / %+67.0 | ❌ kanıt yok | 🟢 LONG |
| BTC | TERS direction_velocity · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 2.02 | 0.72 / 3.38 | %+272.9 | %-29.5 | 51 | %72 | 0.74 | -0.57 (-0.7) · 1/5 | -0.7 | TERS RSI(2) dönüş (2/10/90) · 1d · sadece long · sinyalle çıkış · 0.22 (+0.7) · 5/7 · +0.6 · 10.0 yıl | -0.11 / %-9.1 | ❌ kanıt yok | 🔴 SHORT |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Kısa Vade Yön · 1 günlük ortalama yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 2.14 | 2.62 / 1.63 | %+129.9 | %-12.2 | 46 | %63 | 0.84 | -0.69 (-0.9) · 2/5 | -0.9 | Momentum (60) · 1d · long+short · iz süren stop 3.0×ATR · 0.07 (+0.2) · 4/7 · +0.1 · 8.9 yıl | -0.18 / %-21.8 | ❌ kanıt yok | 🔴 SHORT |

_'1. yarı / 2. yarı': aynı kuralın pencerenin iki yarısındaki Sharpe'ı — biri pozitif biri negatifse kural kararsızdır. WF-OOS: her dilimde YALNIZCA geçmişte en iyi olanı seçip bir sonraki dilimde ölçen prosedürün gerçek dışı-örneklem sonucu (on binlerce aday arasından seçimin bedeli dahil)._

## 2) Tutma ufku etkisi — sistem sinyalleri tek tek (sistem yönünde, işaret, ufuk boyunca ortalama, long+short)

| Ufuk | Ortalama Sharpe | Medyan Sharpe | Pozitif oran |
|---|---|---|---|
| 1 saat | -1.79 | -0.94 | %20 |
| 4 saat | -1.08 | -0.75 | %19 |
| 1 gün | -0.41 | -0.32 | %30 |
| 1 hafta | -0.16 | -0.11 | %40 |
| 1 ay | -0.06 | -0.04 | %46 |

**Sinyal × ufuk matrisi** (6 varlık ortalaması Sharpe · parantezde pozitif varlık sayısı)

| Sinyal | 1 saat | 4 saat | 1 gün | 1 hafta | 1 ay |
|---|---|---|---|---|---|
| Faktör: nq_relative_divergence | -11.49 (0) | -6.62 (0) | -0.36 (0) | -0.86 (0) | -0.04 (0) |
| Faktör: spx_relative_divergence | -10.50 (0) | -3.92 (0) | -2.10 (0) | -0.24 (0) | 0.35 (1) |
| direction_acceleration | -8.98 (0) | -4.85 (0) | -1.13 (2) | -0.29 (2) | -0.60 (0) |
| pair_stats.spread | -8.81 (0) | -3.91 (0) | -1.09 (1) | 0.16 (4) | -0.73 (0) |
| pair_stats.residual_z | -8.77 (0) | -3.59 (0) | -1.20 (0) | -0.02 (3) | -0.27 (2) |
| current_roc | -8.14 (0) | -3.67 (0) | -0.92 (0) | -0.72 (0) | 0.36 (3) |
| Faktör: gold_macro_lead | -7.92 (0) | -2.55 (0) | -2.14 (0) | -0.41 (0) | 0.31 (1) |
| Fiyat itkisi skoru | -7.51 (0) | -3.36 (0) | -1.08 (0) | -0.56 (0) | -0.18 (3) |
| short_term_parts.price_part | -7.50 (0) | -3.41 (0) | -0.67 (0) | -0.16 (3) | -0.08 (3) |
| short_term_parts.price_z | -7.38 (0) | -3.34 (0) | -0.85 (0) | -0.59 (0) | -0.62 (0) |
| Makro: credit_velocity | -6.58 (0) | -3.17 (0) | -1.31 (0) | -0.36 (0) | 0.32 (1) |
| Faktör: gold_divergence_residual | -6.33 (0) | -2.73 (0) | -0.04 (0) | -0.18 (0) | -0.48 (0) |
| RSI(2) dönüş (2/10/90) · 1h | -5.89 (0) | -3.75 (0) | -0.41 (1) | -0.37 (2) | -0.02 (2) |
| Faktör: credit_spread | -5.23 (0) | -3.17 (0) | -1.32 (0) | -0.63 (0) | 0.34 (4) |
| Faktör: consumer_demand | -5.05 (0) | -3.23 (0) | 0.07 (1) | -1.69 (0) | 0.67 (1) |
| Faktör: usd_strength | -5.01 (0) | -2.70 (0) | -0.63 (1) | 0.12 (3) | -0.03 (2) |
| Makro: dxy_velocity | — | -4.60 (0) | — | — | — |
| direction_velocity | -4.47 (0) | -2.22 (0) | -0.77 (0) | -0.66 (0) | -0.12 (2) |
| Faktör: asset_direction | -4.06 (0) | -2.39 (0) | -0.37 (2) | -0.25 (3) | 0.26 (3) |
| Faktör: usd_jpy_carry | -3.93 (0) | -2.47 (0) | -0.70 (1) | -0.25 (1) | 0.25 (3) |
| Faktör: gsr_velocity | -3.88 (0) | -1.96 (0) | -0.96 (0) | -0.84 (0) | -0.17 (0) |
| Makro: yen_carry_z | -3.68 (0) | -2.22 (0) | -0.27 (2) | -0.40 (1) | 0.18 (2) |
| adaptive_cluster_scores.E | -3.57 (0) | -1.92 (0) | -0.26 (2) | -0.41 (2) | -0.06 (3) |
| Faktör: defensive_flight | -3.51 (0) | -2.77 (0) | 0.02 (1) | -0.83 (0) | -0.15 (0) |
| live_score_pair_adjusted | -3.38 (0) | -1.04 (1) | -0.45 (1) | -0.31 (2) | -0.06 (1) |
| Çift-uyumlu yön skoru | -3.38 (0) | -0.95 (0) | — | — | — |
| RSI trend (14) · 1h | -3.23 (0) | -1.61 (0) | -0.32 (2) | -0.34 (2) | 0.24 (4) |
| raw_model_score | -3.23 (0) | -1.71 (0) | -0.64 (1) | -0.54 (1) | -0.53 (0) |
| Faktör: btc_sympathy | -3.16 (0) | -0.66 (0) | 1.08 (1) | 0.80 (1) | 0.50 (1) |
| adaptive_cluster_scores.C | -3.11 (0) | -1.80 (0) | -0.56 (0) | -0.72 (0) | -0.78 (0) |
| Adaptif skor | -3.10 (0) | -1.84 (0) | -0.51 (1) | -0.45 (1) | 0.06 (2) |
| Momentum (24) · 1h | -3.06 (0) | -1.75 (0) | -0.47 (3) | -0.19 (2) | -0.17 (2) |
| adaptive_cluster_scores.A | -2.84 (0) | -1.77 (0) | -0.54 (1) | -0.42 (2) | 0.12 (2) |
| pair_common_factor.gap_before | -2.61 (0) | -1.88 (0) | -0.28 (0) | 0.73 (2) | 0.82 (2) |
| Faktör: market_breadth | -2.49 (0) | -2.28 (0) | -1.55 (0) | -0.16 (0) | -1.12 (0) |
| composite_usd_risk | -2.40 (0) | -0.83 (0) | 0.01 (3) | 0.30 (4) | 0.07 (4) |
| adaptive_cluster_scores.D | -2.38 (0) | -0.63 (1) | -1.28 (1) | -0.15 (1) | -0.44 (1) |
| Faktör: gold_sovereign_decoupling | -2.33 (0) | -1.65 (0) | -1.43 (0) | 0.14 (1) | 0.36 (1) |
| pair_common_factor.common_score | -2.29 (0) | -1.93 (0) | 0.10 (1) | 0.11 (1) | 0.26 (1) |
| score_raw_cycle | -2.27 (0) | -1.33 (0) | -0.55 (1) | -0.61 (0) | — |
| Faktör: semi_lead | -2.27 (0) | -0.98 (0) | -0.27 (0) | -0.17 (0) | -0.40 (0) |
| Faktör: duration_risk | -2.22 (0) | -1.69 (0) | -1.44 (0) | -0.38 (0) | -0.35 (2) |
| EMA trend (50) · 1h | -2.22 (0) | -1.23 (0) | -0.22 (2) | -0.11 (3) | 0.39 (3) |
| intraday_vol | -1.79 (1) | -1.67 (1) | -2.20 (0) | -0.47 (2) | 0.01 (2) |
| Faktör: banking_stress | -2.18 (0) | -1.10 (0) | -0.54 (1) | -0.42 (2) | -0.66 (0) |

_Makro sinyallerin değeri uzun ufukta (hafta/ay) görünmeli; kısa ufukta sık yön değişimi maliyetle eriyor. Ay ufku 700 günde ~23 karar demek: istatistiksel gücü düşüktür._

## 3) Kombinasyon keşfi (keşif → doğrulama → hiç görülmemiş dönem)

_Keşif döneminde her sinyal tek tek sıralandı; en iyi 40'ın tüm ikili kombinasyonları (ikisi aynı yönü gösterdiğinde işlem) ve 2-7 sinyallik açgözlü çoğunluk oyları kuruldu. Seçim doğrulama döneminde yapıldı; son dönem hiçbir seçimde kullanılmadı. Kanıt: son dönemde t ≥ 2 ve sürekli long'a karşı alfa t ≥ 2._

**SPX** · keşif 2024-11-06→2025-10-22 · doğrulama →2026-04-15 · son dönem →2026-10-07 · 1,606 aday (1,560 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Donchian kırılımı (168) · 1h · 4 saatlik ortalama] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 1.76 | 4.41 | **1.49** | %+1.6 | +1.0 | +1.2 | 17 |
| 2 | Hepsi aynı yönde: [pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Donchian kırılımı (168) · 1h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 1.76 | 4.41 | **1.49** | %+1.6 | +1.0 | +1.2 | 17 |
| 3 | Hepsi aynı yönde: [pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Donchian kırılımı (168) · 1h · 4 saatlik ortalama] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 1.94 | 3.84 | **0.79** | %+0.9 | +0.6 | +0.7 | 18 |
| 4 | Hepsi aynı yönde: [pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Donchian kırılımı (168) · 1h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 1.94 | 3.84 | **0.79** | %+0.9 | +0.6 | +0.7 | 18 |
| 5 | Hepsi aynı yönde: [TERS Faktör: tail_risk_skew_lead · 4 saatlik ortalama] & [TERS Momentum (24) · 1h · 1 aylık] · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 2.46 | 2.54 | **-3.00** | %-7.0 | -2.1 | -2.0 | 35 |
| 6 | Hepsi aynı yönde: [TERS Faktör: tail_risk_skew_lead] & [TERS Momentum (24) · 1h · 1 aylık] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 2.55 | 2.46 | **-2.38** | %-5.9 | -1.6 | -1.5 | 37 |
| 7 | Hepsi aynı yönde: [TERS Faktör: nq_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Donchian kırılımı (168) · 1h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 2.37 | 2.44 | **0.60** | %+0.7 | +0.4 | +0.6 | 21 |
| 8 | Hepsi aynı yönde: [TERS Faktör: nq_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS Donchian kırılımı (168) · 1h · 4 saatlik ortalama] · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 2.34 | 2.44 | **0.60** | %+0.7 | +0.4 | +0.6 | 21 |
| 9 | Hepsi aynı yönde: [TERS Faktör: usd_strength · 1 haftalık] & [pair_stats.spread · 1 haftalık] · long+short · sinyalle çıkış | kombi·ikili | 1.03 | 2.22 | **-0.63** | %-2.9 | -0.4 | -0.4 | 46 |
| 10 | Hepsi aynı yönde: [TERS Faktör: usd_strength · 1 haftalık] & [pair_stats.spread · 1 haftalık] · long+short · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 2.85 | 2.22 | **-0.63** | %-2.9 | -0.4 | -0.4 | 46 |

**NQ** · keşif 2024-11-06→2025-10-22 · doğrulama →2026-04-15 · son dönem →2026-10-07 · 1,514 aday (1,468 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · 4 saatlik] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · SL 2.0×ATR / TP 4.0×ATR | kombi·ikili | 2.28 | 4.00 | **-2.43** | %-6.6 | -1.7 | -1.7 | 35 |
| 2 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1)] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · SL 2.0×ATR / TP 4.0×ATR | kombi·ikili | 2.34 | 3.97 | **-2.43** | %-6.6 | -1.7 | -1.7 | 35 |
| 3 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 2.45 | 3.79 | **0.52** | %+2.8 | +0.4 | +0.7 | 35 |
| 4 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · 4 saatlik] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 2.22 | 3.73 | **0.28** | %+1.5 | +0.2 | +0.5 | 35 |
| 5 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1)] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 2.26 | 3.71 | **0.27** | %+1.5 | +0.2 | +0.5 | 35 |
| 6 | Hepsi aynı yönde: [Alt: COT varlık yöneticisi net (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 2.33 | 3.46 | **-1.76** | %-4.3 | -1.2 | -1.3 | 35 |
| 7 | Hepsi aynı yönde: [pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 2.00 | 3.15 | **0.39** | %+1.1 | +0.3 | +0.6 | 25 |
| 8 | Hepsi aynı yönde: [pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS EMA kesişimi (20/50) · 4h · 4 saatlik ortalama] · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 2.00 | 3.15 | **0.39** | %+1.1 | +0.3 | +0.6 | 25 |
| 9 | Hepsi aynı yönde: [pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS EMA trend (200) · 4h · 4 saatlik ortalama] · long+short · sinyalle çıkış | kombi·ikili | 1.90 | 2.91 | **-0.84** | %-2.9 | -0.6 | -0.3 | 40 |
| 10 | Hepsi aynı yönde: [pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık] & [TERS EMA trend (200) · 4h · 4 saatlik ortalama] · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.90 | 2.91 | **-0.84** | %-2.9 | -0.6 | -0.3 | 40 |

**XAU** · keşif 2024-11-06→2025-10-22 · doğrulama →2026-04-15 · son dönem →2026-10-07 · 1,588 aday (1,542 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [adaptive_cluster_scores.D · 1 haftalık ortalama] & [TERS Faktör: duration_risk · 1 haftalık] · sadece long · sinyalle çıkış | kombi·ikili | 1.03 | 3.20 | **-0.63** | %-5.4 | -0.4 | +0.6 | 25 |
| 2 | Hepsi aynı yönde: [Alt: COT swap dealer net (haftalık değişim) · 1 haftalık] & [adaptive_cluster_scores.D · 1 haftalık ortalama] · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 3.20 | 3.16 | **-0.09** | %-0.5 | -0.1 | +0.5 | 19 |
| 3 | Hepsi aynı yönde: [adaptive_cluster_scores.D · 1 haftalık ortalama] & [TERS Faktör: duration_risk · 1 haftalık] · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.04 | 3.12 | **-0.64** | %-4.7 | -0.5 | +0.3 | 25 |
| 4 | Hepsi aynı yönde: [TERS adaptive_cluster_scores.B · 1 haftalık] & [adaptive_cluster_scores.D · 1 haftalık ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 1.24 | 2.95 | **-0.18** | %-1.6 | -0.1 | +1.1 | 20 |
| 5 | Hepsi aynı yönde: [TERS adaptive_cluster_scores.A (güçlü, ∣z∣>0.5) · 1 haftalık ortalama] & [TERS Faktör: duration_risk · 1 haftalık] · sadece long · sinyalle çıkış | kombi·ikili | 2.62 | 2.69 | **-3.12** | %-21.9 | -2.2 | -1.9 | 19 |
| 6 | Hepsi aynı yönde: [Alt: COT swap dealer net (haftalık değişim) · 1 haftalık] & [adaptive_cluster_scores.D · 1 haftalık ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 2.12 | 2.65 | **-0.08** | %-0.4 | -0.1 | +0.5 | 19 |
| 7 | Hepsi aynı yönde: [TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük] & [TERS Bollinger dönüş (20/2.0) · 4h] · sadece long · SL 3.0×ATR / TP 6.0×ATR | kombi·ikili | 2.54 | 2.48 | **1.09** | %+3.3 | +0.8 | +1.2 | 30 |
| 8 | Hepsi aynı yönde: [Alt: COT swap dealer net (haftalık değişim) · 1 haftalık] & [TERS Faktör: duration_risk · 1 haftalık] · sadece long · sinyalle çıkış | kombi·ikili | 1.86 | 2.42 | **-0.87** | %-6.0 | -0.6 | +0.1 | 26 |
| 9 | Hepsi aynı yönde: [Makro: credit_velocity (güçlü, ∣z∣>1) · 1 günlük] & [adaptive_cluster_scores.D · 1 haftalık ortalama] · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 1.74 | 2.42 | **1.37** | %+5.5 | +0.9 | +0.8 | 52 |
| 10 | Hepsi aynı yönde: [Makro: credit_velocity (güçlü, ∣z∣>1) · 1 günlük] & [adaptive_cluster_scores.D · 1 haftalık ortalama] · long+short · sinyalle çıkış | kombi·ikili | 1.74 | 2.42 | **1.37** | %+5.5 | +0.9 | +0.8 | 52 |

**XAG** · keşif 2024-11-06→2025-10-22 · doğrulama →2026-04-15 · son dönem →2026-10-07 · 1,416 aday (1,370 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] & [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.70 | 5.78 | **-0.28** | %-3.0 | -0.2 | +0.3 | 34 |
| 2 | Hepsi aynı yönde: [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] & [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 0.79 | 5.69 | **-0.28** | %-3.0 | -0.2 | +0.3 | 34 |
| 3 | Hepsi aynı yönde: [TERS Faktör: breakeven_infl (güçlü, ∣z∣>1) · 1 günlük ortalama] & [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 1.58 | 4.67 | **-1.83** | %-20.0 | -1.3 | -0.9 | 19 |
| 4 | Hepsi aynı yönde: [TERS Makro: breakeven_z (güçlü, ∣z∣>1) · 1 günlük ortalama] & [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 1.58 | 4.67 | **-1.99** | %-21.6 | -1.4 | -1.0 | 18 |
| 5 | Hepsi aynı yönde: [TERS Makro: breakeven_z (güçlü, ∣z∣>1) · 1 günlük ortalama] & [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 1.58 | 4.57 | **-2.59** | %-13.7 | -1.8 | -1.6 | 18 |
| 6 | Hepsi aynı yönde: [TERS Faktör: breakeven_infl (güçlü, ∣z∣>1) · 1 günlük ortalama] & [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 1.58 | 4.57 | **-2.34** | %-12.5 | -1.6 | -1.4 | 19 |
| 7 | Hepsi aynı yönde: [TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama] & [TERS Alt: COT açık pozisyon değişimi] · sadece long · sinyalle çıkış | kombi·ikili | 1.85 | 4.51 | **0.31** | %+3.0 | +0.2 | +0.7 | 25 |
| 8 | Hepsi aynı yönde: [TERS Faktör: asset_direction (güçlü, ∣z∣>0.5) · 1 haftalık ortalama] & [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] · sadece long · sinyalle çıkış | kombi·ikili | 0.25 | 4.49 | **0.27** | %+2.3 | +0.2 | +0.5 | 18 |
| 9 | Hepsi aynı yönde: [TERS Faktör: asset_direction (güçlü, ∣z∣>0.5) · 1 haftalık ortalama] & [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 0.25 | 4.45 | **0.27** | %+2.3 | +0.2 | +0.5 | 18 |
| 10 | Hepsi aynı yönde: [TERS Faktör: silver_vol_premium_lead · 4 saatlik ortalama] & [TERS Faktör: duration_risk · 1 haftalık] · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | kombi·ikili | 0.34 | 4.41 | **-0.09** | %-1.1 | -0.1 | +0.5 | 35 |

**BTC** · keşif 2024-11-06→2025-10-22 · doğrulama →2026-04-15 · son dönem →2026-10-07 · 1,606 aday (1,560 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>0.5) · 4 saatlik] & [TERS score_raw_cycle (güçlü, ∣z∣>1) · 1 haftalık] · long+short · sinyalle çıkış | kombi·ikili | 1.29 | 2.75 | **0.81** | %+3.1 | +0.6 | +0.6 | 21 |
| 2 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>0.5) · 4 saatlik] & [TERS Adaptif skor (güçlü, ∣z∣>1) · 1 haftalık] · long+short · sinyalle çıkış | kombi·ikili | 1.16 | 2.63 | **-0.29** | %-0.7 | -0.2 | -0.2 | 18 |
| 3 | Hepsi aynı yönde: [Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1)] & [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik] · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 1.13 | 2.45 | **-0.50** | %-0.5 | -0.3 | -0.3 | 26 |
| 4 | Hepsi aynı yönde: [EMA kesişimi (50/200) · 4h] & [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik ortalama] · long+short · 24 saat tut | kombi·ikili | 1.64 | 2.41 | **-0.31** | %-2.0 | -0.2 | -0.2 | 75 |
| 5 | Hepsi aynı yönde: [EMA kesişimi (50/200) · 4h] & [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik] · long+short · 24 saat tut | kombi·ikili | 1.62 | 2.38 | **-0.39** | %-2.5 | -0.3 | -0.3 | 76 |
| 6 | Hepsi aynı yönde: [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik ortalama] & [Model sinyali (24s-1h) (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 0.83 | 2.26 | **-0.22** | %-1.4 | -0.1 | -0.1 | 33 |
| 7 | Hepsi aynı yönde: [Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1)] & [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik ortalama] · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 1.11 | 2.25 | **0.10** | %+0.1 | +0.1 | +0.0 | 26 |
| 8 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>0.5) · 4 saatlik] & [TERS Adaptif skor (güçlü, ∣z∣>1) · 1 haftalık] · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 0.65 | 2.25 | **1.65** | %+0.9 | +1.1 | +1.1 | 18 |
| 9 | Hepsi aynı yönde: [Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1)] & [TERS Faktör: banking_stress · 1 haftalık ortalama] · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 2.29 | 2.24 | **-2.39** | %-8.8 | -1.7 | -1.6 | 25 |
| 10 | Hepsi aynı yönde: [EMA trend (50) · 4h · 4 saatlik ortalama] & [TERS Alt: Hesap long/short oranı (güçlü, ∣z∣>1) · 4 saatlik ortalama] · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | kombi·ikili | 2.01 | 2.24 | **0.05** | %+0.3 | +0.0 | +0.1 | 64 |

**ETH** · keşif 2024-11-06→2025-10-22 · doğrulama →2026-04-15 · son dönem →2026-10-07 · 1,572 aday (1,526 ikili, 6 oylama) · ❌ son dönemde geçmedi

| # | Kombinasyon | Tür | Keşif Sharpe | Doğrulama | **Son dönem** | Son dönem getiri | t | Alfa t | İşlem |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1)] & [TERS Model z (kısa vade) (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.42 | 2.80 | **0.32** | %+1.4 | +0.2 | +0.2 | 38 |
| 2 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1) · 4 saatlik] & [TERS short_term_parts.model_part (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.27 | 2.80 | **-0.53** | %-2.3 | -0.4 | -0.4 | 38 |
| 3 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1)] & [TERS short_term_parts.model_part (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.29 | 2.80 | **0.32** | %+1.4 | +0.2 | +0.2 | 38 |
| 4 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1)] & [TERS Model skoru (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.29 | 2.80 | **0.32** | %+1.4 | +0.2 | +0.2 | 38 |
| 5 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1) · 4 saatlik] & [TERS Model z (kısa vade) (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.40 | 2.80 | **-0.53** | %-2.3 | -0.4 | -0.4 | 38 |
| 6 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1) · 4 saatlik] & [TERS Model skoru (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | kombi·ikili | 1.27 | 2.80 | **-0.53** | %-2.3 | -0.4 | -0.4 | 38 |
| 7 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1) · 4 saatlik] & [TERS Model z (kısa vade) (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · sinyalle çıkış | kombi·ikili | 0.54 | 2.77 | **-0.54** | %-5.4 | -0.4 | -0.5 | 38 |
| 8 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1) · 4 saatlik] & [TERS Model skoru (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · sinyalle çıkış | kombi·ikili | 1.04 | 2.77 | **-0.54** | %-5.4 | -0.4 | -0.5 | 38 |
| 9 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1)] & [TERS Model skoru (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · sinyalle çıkış | kombi·ikili | 1.05 | 2.77 | **-0.38** | %-3.9 | -0.3 | -0.3 | 38 |
| 10 | Hepsi aynı yönde: [TERS Alt: COT açık pozisyon değişimi (güçlü, ∣z∣>1)] & [TERS short_term_parts.model_part (güçlü, ∣z∣>0.5) · 4 saatlik] · sadece long · sinyalle çıkış | kombi·ikili | 1.05 | 2.77 | **-0.38** | %-3.9 | -0.3 | -0.3 | 38 |

## 3b) Sistem yönü FİLTRE + teknik TETİK + ATR çıkışı

_Kural: teknik tetik (RSI(2) aşırılığı, Bollinger dönüşü, Donchian kırılımı, EMA20 kesişimi, MACD kesişimi, Keltner kırılımı) oluşunca, YALNIZCA sistemin gösterdiği yönde işleme girilir; çıkış ATR stop/hedef, başa-baş, kısmi kâr, iz süren stop veya sinyal. 'Kazanç' = aynı tetik, aynı çıkış, aynı yön modu ile filtresiz hâline göre Sharpe farkı. Bir filtreye ancak pencerenin İKİ yarısında da kazanç veriyorsa güvenilir._

**Genel:** 202,686 (tetik × filtre × çıkış × yön) eşleşmesi · filtresiz tetik ort. Sharpe **-1.16** (pozitif %20) → sistem filtreli ort. **-1.16** (pozitif %19) · ortalama kazanç **+0.04** · kazanç pozitif %54 · iki yarıda da pozitif **%32**

**Filtre olarak en faydalı sistem yönleri** (tüm tetikler ve varlıklar ortalaması)

| Filtre (sistem yönü) | Ufuk | Ort. kazanç | 1. yarı / 2. yarı kazanç | İki yarıda da + | Filtreli ort. Sharpe | Eşleşme | Varlık |
|---|---|---|---|---|---|---|---|
| Alt: Perp primi (baz) (z) | haftalık ort. | +0.81 | +0.97 / +0.60 | %69 | -0.10 | 648 | 2 |
| Yön aşaması | haftalık ort. | +0.74 | +0.55 / +1.08 | %60 | -0.71 | 564 | 3 |
| Model sinyali (24s-1h) | anlık | +0.73 | +0.76 / +0.64 | %44 | -0.57 | 1602 | 6 |
| Faktör: speculative_beta | günlük ort. | +0.69 | +1.03 / +0.28 | %50 | -0.69 | 324 | 1 |
| Model sinyali (24s-1h) | günlük ort. | +0.68 | +0.74 / +0.65 | %44 | -0.60 | 1722 | 6 |
| Alt: COT varlık yöneticisi net (haftalık değişim) (z) | haftalık ort. | +0.68 | +0.56 / +0.78 | %61 | -0.74 | 1164 | 4 |
| Faktör: consumer_demand | günlük ort. | +0.68 | +0.88 / +0.42 | %58 | -1.22 | 324 | 1 |
| Alt: COT varlık yöneticisi net (haftalık değişim) | haftalık ort. | +0.64 | +0.57 / +0.72 | %63 | -0.63 | 1296 | 4 |
| Alt: Perp primi (baz) (z) | günlük ort. | +0.64 | +0.68 / +0.62 | %66 | -0.27 | 648 | 2 |
| Alt: Açık pozisyon değişimi 7g (z) | haftalık ort. | +0.63 | +0.72 / +0.50 | %62 | -0.30 | 642 | 2 |
| Alt: COT kaldıraçlı fon net (haftalık değişim) (z) | anlık | +0.63 | +0.15 / +1.07 | %56 | -0.98 | 240 | 1 |
| Alt: Perp primi 8s ort. (z) | haftalık ort. | +0.63 | +0.74 / +0.56 | %67 | -0.29 | 648 | 2 |
| Faktör: defensive_flight | günlük ort. | +0.61 | +0.83 / +0.33 | %60 | -1.03 | 648 | 2 |
| Alt: Açık pozisyon değişimi 24s (z) | haftalık ort. | +0.60 | +0.56 / +0.62 | %65 | -0.31 | 648 | 2 |
| Model sinyali (24s-1h) | haftalık ort. | +0.58 | +0.48 / +0.69 | %47 | -0.64 | 1836 | 6 |
| Faktör: vix_term | günlük ort. | +0.58 | +0.63 / +0.46 | %45 | -1.12 | 630 | 2 |
| Faktör: btc_sympathy | haftalık ort. | +0.54 | +0.68 / +0.28 | %49 | -0.14 | 324 | 1 |
| Faktör: market_breadth | haftalık ort. | +0.53 | +0.56 / +0.49 | %48 | -1.37 | 324 | 1 |
| Faktör: gold_sovereign_decoupling | haftalık ort. | +0.52 | +0.62 / +0.49 | %58 | -0.58 | 324 | 1 |
| Faktör: tech_vol_premium_lead | haftalık ort. | +0.51 | +0.11 / +0.92 | %46 | -0.86 | 324 | 1 |

_En zayıf 5 filtre:_ Faktör: gold_divergence_residual (anlık) -2.28 · Fiyat itkisi skoru (anlık) -2.55 · Faktör: gold_macro_lead (anlık) -2.78 · Faktör: nq_relative_divergence (anlık) -4.08 · Faktör: spx_relative_divergence (anlık) -4.13

**Tetik bazında** (filtresiz → filtreli)

| Tetik | Filtresiz Sharpe | Filtreli ort. | Kazanç | İki yarıda + |
|---|---|---|---|---|
| EMA20 kesişimi · 1h | -4.68 | -3.67 | +1.01 | %73 |
| RSI(2) geri çekilme · 1h | -3.21 | -2.61 | +0.59 | %56 |
| Bollinger bandı dışı · 1h | -2.55 | -2.02 | +0.53 | %57 |
| MACD kesişimi · 1h | -2.78 | -2.29 | +0.49 | %53 |
| 20 mum kırılımı · 1h | -2.08 | -1.79 | +0.29 | %45 |
| Keltner kırılımı · 1h | -1.82 | -1.60 | +0.22 | %42 |
| EMA20 kesişimi · 4h | -1.15 | -1.13 | +0.02 | %32 |
| MACD kesişimi · 1d | -0.41 | -0.54 | -0.13 | %22 |
| Bollinger bandı dışı · 1d | -0.20 | -0.34 | -0.14 | %23 |
| Bollinger bandı dışı · 4h | -0.49 | -0.65 | -0.16 | %20 |
| MACD kesişimi · 4h | -0.24 | -0.48 | -0.23 | %19 |
| Keltner kırılımı · 4h | -0.27 | -0.51 | -0.23 | %21 |
| RSI(2) geri çekilme · 4h | -0.64 | -0.89 | -0.25 | %25 |
| EMA20 kesişimi · 1d | -0.26 | -0.51 | -0.25 | %20 |
| 20 mum kırılımı · 4h | -0.42 | -0.69 | -0.28 | %20 |
| 20 mum kırılımı · 1d | 0.04 | -0.24 | -0.28 | %17 |
| RSI(2) geri çekilme · 1d | -0.31 | -0.60 | -0.28 | %18 |
| Keltner kırılımı · 1d | 0.49 | 0.08 | -0.41 | %11 |

**İki yarıda da en sağlam 20 filtreli tetik kuralı** (sıralama: min(1. yarı, 2. yarı) — yine de seçim yanlılığı içerir)

| Varlık | Kural | Sharpe | 1. yarı / 2. yarı | Filtresiz | Kazanç | İşlem |
|---|---|---|---|---|---|---|
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Faktör: real_yield yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.84 | 1.88 / 1.80 | 1.14 | +0.70 | 48 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Model sinyali (24s-1h) · 1 günlük ortalama yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.70 | 1.67 / 1.73 | 1.14 | +0.55 | 40 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Kısa Vade Yön · 1 günlük ortalama yönünde · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.75 | 1.84 / 1.66 | 0.48 | +1.27 | 74 |
| BTC | Tetik: Keltner kırılımı · 1d | filtre: Alt: Perp primi (baz) (z) · 1 günlük ortalama yönünde · long+short · SL 2.0 / TP 4.0×ATR × volatilite oranı | 1.72 | 1.66 / 1.78 | 1.17 | +0.55 | 26 |
| BTC | Tetik: Keltner kırılımı · 1d | filtre: Faktör: usd_strength · 1 günlük ortalama yönünde · long+short · iz süren stop 2.0×ATR | 1.60 | 1.64 / 1.67 | 1.58 | +0.02 | 32 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Kısa Vade Yön · 1 günlük ortalama yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 2.14 | 2.62 / 1.63 | 1.14 | +0.99 | 46 |
| ETH | Tetik: Bollinger bandı dışı · 4h | filtre: Alt: Açık pozisyon değişimi 24s · 1 haftalık ortalama yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.60 | 1.58 / 1.73 | 0.03 | +1.57 | 41 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Model sinyali (24s-1h) · 1 günlük ortalama yönünde · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.73 | 1.57 / 1.89 | 0.48 | +1.25 | 44 |
| ETH | Tetik: MACD kesişimi · 4h | filtre: Alt: Hesap long/short oranı (z) yönünde · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 1.54 | 1.55 / 1.53 | 0.72 | +0.82 | 94 |
| BTC | Tetik: Keltner kırılımı · 1d | filtre: Alt: Perp primi (baz) (z) · 1 günlük ortalama yönünde · long+short · iz süren stop 2.0×ATR | 1.65 | 1.53 / 1.78 | 1.58 | +0.07 | 26 |
| XAG | Tetik: Keltner kırılımı · 4h | filtre: Alt: COT üretici net (haftalık değişim) (z) yönünde · sadece long · sinyalle çıkış | 1.45 | 1.52 / 1.53 | 0.57 | +0.88 | 25 |
| XAG | Tetik: Keltner kırılımı · 4h | filtre: Alt: COT üretici net (haftalık değişim) yönünde · sadece long · sinyalle çıkış | 1.44 | 1.52 / 1.52 | 0.57 | +0.86 | 27 |
| SPX | Tetik: RSI(2) geri çekilme · 1d | filtre: Faktör: nq_relative_divergence · 1 günlük ortalama yönünde · sadece long · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.46 | 1.51 / 1.52 | 1.19 | +0.27 | 52 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Faktör: real_yield yönünde · sadece short · SL 2.0 / TP 4.0×ATR × volatilite oranı | 1.67 | 1.50 / 1.86 | 0.85 | +0.83 | 48 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Faktör: real_yield yönünde · sadece short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 1.66 | 1.80 / 1.50 | 0.81 | +0.85 | 48 |
| XAU | Tetik: EMA20 kesişimi · 1d | filtre: Alt: COT swap dealer net (haftalık değişim) (z) yönünde · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 1.73 | 1.49 / 1.97 | 0.32 | +1.41 | 42 |
| ETH | Tetik: EMA20 kesişimi · 1d | filtre: Alt: COT dealer net (haftalık değişim) yönünde · long+short · SL 2.0 / TP 4.0×ATR × volatilite oranı | 1.52 | 1.48 / 1.74 | 0.69 | +0.84 | 38 |
| ETH | Tetik: EMA20 kesişimi · 1d | filtre: Alt: COT dealer net (haftalık değişim) yönünde · long+short · SL 2.0×ATR / TP 4.0×ATR | 1.56 | 1.48 / 1.84 | 0.76 | +0.80 | 38 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Faktör: real_yield yönünde · sadece short · SL 2.0×ATR / TP 4.0×ATR | 1.48 | 1.49 / 1.47 | 0.73 | +0.75 | 48 |
| ETH | Tetik: Keltner kırılımı · 4h | filtre: Model sinyali (24s-1h) yönünde · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 1.66 | 1.46 / 1.88 | 0.48 | +1.18 | 44 |

## 3c) Yeni bilgi kaynağı — türev piyasası konumlanması (Binance) ve CFTC COT

_Varlıklar: BTC, ETH, NQ, SPX, XAG, XAU. Veri, canlı botun da bilebileceği an itibarıyla kullanıldı (Binance günlük dosyası gün başlangıcından 30 saat sonra, COT salı pozisyonu cumartesi 00:00 UTC). '(z)' = sinyalin kendi 90 gözlemlik ortalamasına göre konumu. Sinyal yönünde long+short, sinyalle çıkış._

| Sinyal | Ufuk | Kural | Ort. Sharpe | 1. yarı / 2. yarı | Pozitif varlık | İki yarıda + varlık |
|---|---|---|---|---|---|---|
| Alt: Açık pozisyon değişimi 24s (z) | 1 gün | ∣z∣>1.0 · ufuk ort. | -1.75 | -2.15 / -1.30 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s | 1 gün | ∣z∣>0.5 · son değer | -1.70 | -2.31 / -1.08 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 4 saat | ∣z∣>0.5 · son değer | -1.70 | -1.70 / -1.71 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 1 saat | ∣z∣>0.5 · son değer | -1.68 | -1.70 / -1.68 | 0/2 | 0/2 |
| Alt: Hesap long/short oranı | 1 ay | ∣z∣>0.5 · son değer | -1.68 | -1.96 / -1.45 | 0/1 | 0/1 |
| Alt: COT spekülatif fon net (z) | 1 gün | ∣z∣>0.5 · son değer | -1.63 | -1.60 / -1.65 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 4 saat | ∣z∣>0.5 · ufuk ort. | -1.60 | -1.55 / -1.64 | 0/2 | 0/2 |
| Alt: Perp primi (baz) (z) | 1 ay | ∣z∣>0.5 · ufuk ort. | 1.56 | 1.55 / 1.52 | 2/2 | 2/2 |
| Alt: COT spekülatif fon net (z) | 1 gün | ∣z∣>0.5 · ufuk ort. | -1.54 | -1.40 / -1.62 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s (z) | 1 gün | ∣z∣>0.5 · ufuk ort. | -1.51 | -2.11 / -0.86 | 0/2 | 0/2 |
| Alt: Perp primi 8s ort. (z) | 1 ay | ∣z∣>0.5 · ufuk ort. | 1.49 | 1.54 / 1.37 | 2/2 | 2/2 |
| Alt: Agresif alış/satış oranı (z) | 1 saat | ∣z∣>1.0 · son değer | -1.48 | -1.67 / -1.25 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s | 1 gün | ∣z∣>0.5 · ufuk ort. | -1.45 | -1.98 / -0.86 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s (z) | 1 gün | ∣z∣>0.5 · son değer | -1.42 | -2.19 / -0.64 | 0/2 | 0/2 |
| Alt: Açık pozisyon değişimi 24s | 1 gün | ∣z∣>1.0 · ufuk ort. | -1.42 | -1.75 / -0.98 | 0/2 | 0/2 |
| Alt: Agresif alış/satış oranı (z) | 4 saat | ∣z∣>1.0 · son değer | -1.41 | -1.62 / -1.16 | 0/2 | 0/2 |
| Alt: Agresif alış/satış oranı (z) | 1 gün | ∣z∣>0.5 · son değer | -1.38 | -2.14 / -0.61 | 0/2 | 0/2 |
| Alt: Perp primi 8s ort. (z) | 1 ay | ∣z∣>1.0 · ufuk ort. | 1.37 | 1.64 / 0.97 | 2/2 | 2/2 |
| Alt: Açık pozisyon değişimi 24s (z) | 1 gün | ∣z∣>1.0 · son değer | -1.33 | -1.72 / -0.90 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 1 saat | ∣z∣>1.0 · son değer | -1.32 | -1.02 / -1.49 | 0/2 | 0/2 |
| Alt: COT varlık yöneticisi net | 1 gün | ∣z∣>0.5 · ufuk ort. | 1.32 | 1.75 / 0.81 | 1/1 | 1/1 |
| Alt: Perp primi (baz) (z) | 1 ay | ∣z∣>1.0 · ufuk ort. | 1.31 | 1.18 / 1.49 | 2/2 | 2/2 |
| Alt: COT spekülatif fon net (z) | 4 saat | ∣z∣>1.0 · son değer | -1.30 | -1.02 / -1.46 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 1 gün | ∣z∣>1.0 · son değer | -1.29 | -1.06 / -1.41 | 0/2 | 0/2 |
| Alt: Agresif alış/satış oranı (z) | 4 saat | ∣z∣>1.0 · ufuk ort. | -1.29 | -1.53 / -0.97 | 0/2 | 0/2 |
| Alt: COT swap dealer net (z) | 1 hafta | ∣z∣>1.0 · ufuk ort. | 1.26 | 0.74 / 1.59 | 2/2 | 2/2 |
| Alt: Açık pozisyon değişimi 24s | 1 gün | ∣z∣>1.0 · son değer | -1.24 | -1.63 / -0.82 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 4 saat | ∣z∣>1.0 · ufuk ort. | -1.20 | -0.99 / -1.32 | 0/2 | 0/2 |
| Alt: COT spekülatif fon net (z) | 1 hafta | ∣z∣>0.5 · son değer | -1.18 | -1.01 / -1.25 | 0/2 | 0/2 |
| Alt: Perp primi (baz) (z) | 4 saat | ∣z∣>1.0 · ufuk ort. | -1.15 | -1.83 / -0.34 | 0/2 | 0/2 |

_Negatif ortalama + iki yarıda tutarlı = sinyal TERS yönde çalışıyor olabilir (kalabalık pozisyonun tersine işlem); bu TERS versiyonlar ayrıca test edilip tüm konfigürasyon dosyasında yer alır._

## 4) Kaldıraç ve likidasyon (seçilen kural, 730 gün, saatlik High/Low ile)

| Varlık | 1x yıllık / DD | 2x | 3x | 5x | 10x | Vol hedefli (%40, maks 5x) | Likidasyon (1/2/3/5/10x) |
|---|---|---|---|---|---|---|---|
| SPX · seçilen kural (iyimser) | %+13 / %-3 | %+27 / %-6 | %+43 / %-9 | %+79 / %-15 | %+199 / %-28 | %+32 / %-11 | 0/0/0/0/0 |
| SPX · walk-forward OOS (gerçekçi) | %-2 / %-18 | %-5 / %-34 | %-11 / %-47 | %-27 / %-67 | %-71 / %-94 | — | 0/0/0/0/0 |
| NQ · seçilen kural (iyimser) | %+19 / %-4 | %+40 / %-7 | %+65 / %-11 | %+125 / %-18 | %+352 / %-33 | %+38 / %-9 | 0/0/0/0/0 |
| NQ · walk-forward OOS (gerçekçi) | %+4 / %-19 | %+6 / %-36 | %+7 / %-49 | %+4 / %-70 | %-27 / %-93 | — | 0/0/0/0/0 |
| XAU · seçilen kural (iyimser) | %+38 / %-15 | %+86 / %-28 | %+146 / %-39 | %+297 / %-56 | %+771 / %-82 | %+100 / %-24 | 0/0/0/0/0 |
| XAU · walk-forward OOS (gerçekçi) | %+4 / %-13 | %+6 / %-25 | %+7 / %-36 | %+5 / %-55 | %-27 / %-88 | — | 0/0/0/0/0 |
| XAG · seçilen kural (iyimser) | %+99 / %-17 | %+265 / %-34 | %+515 / %-48 | %+1257 / %-71 | %-62 / %-100 | %+92 / %-11 | 0/0/0/0/2 |
| XAG · walk-forward OOS (gerçekçi) | %-9 / %-39 | %-25 / %-66 | %-44 / %-83 | %-77 / %-97 | %-100 / %-100 | — | 0/0/0/0/1 |
| BTC · seçilen kural (iyimser) | %+99 / %-31 | %+249 / %-54 | %+446 / %-71 | %+829 / %-89 | %-93 / %-100 | %+101 / %-32 | 0/0/0/0/3 |
| BTC · walk-forward OOS (gerçekçi) | %-11 / %-28 | %-25 / %-51 | %-39 / %-69 | %-66 / %-90 | %-98 / %-100 | — | 0/0/0/0/0 |
| ETH · seçilen kural (iyimser) | %+54 / %-14 | %+128 / %-26 | %+223 / %-37 | %+472 / %-56 | %+1079 / %-85 | %+36 / %-9 | 0/0/0/0/0 |
| ETH · walk-forward OOS (gerçekçi) | %-20 / %-44 | %-42 / %-73 | %-63 / %-89 | %-91 / %-99 | %-100 / %-100 | — | 0/0/0/0/1 |

_'Seçilen kural' satırı o kuralın geçmişteki en iyi hâlidir (seçim yanlılığı yüzünden iyimser). 'Walk-forward OOS' satırı, her dönemde o güne kadar en iyi olanı seçip uygulasaydınız ne olacağını gösterir (günlük kapanışla; gün içi likidasyonları kaçırabilir). Kaldıraç Sharpe'ı değiştirmez; getiriyi de düşüşü de büyütür ve likidasyonla sermayeyi sıfırlayabilir. Kanıtsız bir kurala kaldıraç eklemek beklenen kaybı büyütür._

## 5) Kombinasyon türlerine göre (6 varlık ortalaması)

| Tür | Konfigürasyon | En iyi Sharpe | Medyan Sharpe | WF-OOS Sharpe | WF pozitif varlık |
|---|---|---|---|---|---|
| tek·1 hafta | 92,904 | 2.24 | -0.17 | 0.07 | 3/6 |
| tek·1 ay | 75,132 | 1.07 | -0.17 | 0.03 | 3/6 |
| tek·1 saat | 62,118 | 1.82 | -1.93 | 0.02 | 3/6 |
| referans | 12 | 0.34 | -0.13 | 0.00 | 0/6 |
| tek·1 gün | 90,660 | 1.85 | -0.44 | -0.21 | 2/6 |
| tetik (filtresiz) | 1,944 | 1.18 | -0.66 | -0.28 | 3/6 |
| sys×trend | 18,830 | 1.28 | -1.44 | -0.33 | 1/6 |
| filtre+tetik | 202,686 | 1.81 | -0.86 | -0.57 | 1/6 |
| oylama | 1,386 | 0.77 | -1.04 | -0.60 | 1/6 |
| tek·4 saat | 208,404 | 1.95 | -1.32 | -0.62 | 0/6 |
| teknik | 27,048 | 1.76 | -0.73 | -0.65 | 1/6 |
| sys | 51,716 | 1.62 | -2.14 | -0.68 | 1/6 |
| teknik×sys | 116,984 | 1.24 | -1.54 | -0.73 | 1/6 |
| sys×filtre | 41,832 | 0.89 | -2.01 | -0.78 | 1/6 |
| teknik×filtre | 126,364 | 1.33 | -1.53 | -1.09 | 0/6 |
| sys×sys | 11,900 | 0.59 | -1.95 | -1.29 | 0/6 |

## 6) Sistemin kendi sinyalleri tek başına (long+short, sinyalle çıkış, sistemin yönünde)

| Sinyal | BTC | ETH | NQ | SPX | XAG | XAU | Ort. | 1. yarı / 2. yarı | Pozitif |
|---|---|---|---|---|---|---|---|---|---|
| Faktör: nq_relative_divergence | — | — | — | -11.49 | — | — | -11.49 | -10.47 / -12.87 | 0/1 |
| Faktör: spx_relative_divergence | — | — | -10.50 | — | — | — | -10.50 | -10.92 / -10.07 | 0/1 |
| direction_acceleration | -8.42 | -5.90 | -10.75 | -13.36 | -5.94 | -9.51 | -8.98 | -10.20 / -8.51 | 0/6 |
| pair_stats.spread | -7.65 | -4.93 | -10.20 | -12.49 | -7.16 | -10.41 | -8.81 | -9.17 / -9.21 | 0/6 |
| pair_stats.residual_z | -7.83 | -5.15 | -10.49 | -12.92 | -6.11 | -10.11 | -8.77 | -9.36 / -8.96 | 0/6 |
| current_roc | -7.92 | -5.06 | -9.34 | -11.74 | -6.16 | -8.63 | -8.14 | -8.79 / -8.16 | 0/6 |
| Faktör: gold_macro_lead | — | — | — | — | — | -7.92 | -7.92 | -7.96 / -8.12 | 0/1 |
| Fiyat itkisi skoru | -7.72 | -4.90 | -8.04 | -10.60 | -5.64 | -8.16 | -7.51 | -8.11 / -7.47 | 0/6 |
| short_term_parts.price_part | -7.72 | -4.85 | -8.05 | -10.61 | -5.61 | -8.16 | -7.50 | -8.15 / -7.43 | 0/6 |
| short_term_parts.price_z | -7.70 | -4.91 | — | -10.61 | -5.61 | -8.08 | -7.38 | -8.18 / -7.26 | 0/5 |
| Makro: credit_velocity | — | — | — | — | — | -6.58 | -6.58 | -7.08 / -6.60 | 0/1 |
| Faktör: gold_divergence_residual | — | — | — | — | -6.33 | — | -6.33 | -10.24 / -5.26 | 0/1 |
| Faktör: credit_spread | -3.62 | -1.90 | -6.65 | -8.73 | — | — | -5.23 | -4.55 / -5.98 | 0/4 |
| Faktör: consumer_demand | — | — | — | -5.05 | — | — | -5.05 | -3.90 / -6.69 | 0/1 |
| Faktör: usd_strength | -2.15 | -0.87 | -6.95 | -9.36 | -4.63 | -6.13 | -5.01 | -4.94 / -5.45 | 0/6 |
| direction_velocity | -3.66 | -3.11 | -5.19 | -6.91 | -3.41 | -4.56 | -4.47 | -5.13 / -4.26 | 0/6 |
| Faktör: asset_direction | -4.71 | -2.53 | -5.09 | -6.60 | -2.64 | -2.80 | -4.06 | -4.05 / -4.26 | 0/6 |
| Faktör: usd_jpy_carry | -2.30 | -1.94 | -5.01 | -6.46 | — | — | -3.93 | -3.58 / -4.36 | 0/4 |
| Faktör: gsr_velocity | — | — | — | — | — | -3.88 | -3.88 | -3.66 / -4.15 | 0/1 |
| Makro: yen_carry_z | — | — | — | — | -2.52 | -4.83 | -3.68 | -3.92 / -3.76 | 0/2 |
| adaptive_cluster_scores.E | -3.18 | -2.76 | -3.27 | -5.09 | -3.00 | -4.11 | -3.57 | -3.55 / -3.87 | 0/6 |
| Faktör: defensive_flight | — | — | -2.96 | -4.07 | — | — | -3.51 | -3.11 / -4.06 | 0/2 |
| live_score_pair_adjusted | -3.29 | -1.47 | -3.91 | -5.66 | -2.47 | -3.49 | -3.38 | -3.63 / -3.66 | 0/6 |
| Çift-uyumlu yön skoru | -3.31 | -1.46 | -3.91 | -5.64 | -2.45 | -3.49 | -3.38 | -3.62 / -3.66 | 0/6 |
| raw_model_score | -2.57 | -2.15 | -3.44 | -5.35 | -3.00 | -2.87 | -3.23 | -4.08 / -2.79 | 0/6 |
| Faktör: btc_sympathy | — | -3.16 | — | — | — | — | -3.16 | -3.32 / -2.98 | 0/1 |
| adaptive_cluster_scores.C | -3.04 | -1.77 | -4.04 | -5.02 | -3.84 | -0.94 | -3.11 | -3.35 / -3.23 | 0/6 |
| Adaptif skor | -2.35 | -1.26 | -3.75 | -5.70 | -2.64 | -2.92 | -3.10 | -3.59 / -2.90 | 0/6 |
| adaptive_cluster_scores.A | -1.27 | -0.86 | -4.48 | -5.41 | -1.89 | -3.12 | -2.84 | -4.77 / -1.59 | 0/6 |
| pair_common_factor.gap_before | -3.28 | -1.94 | — | — | — | — | -2.61 | -2.58 / -2.65 | 0/2 |
| Faktör: market_breadth | — | — | — | -2.49 | — | — | -2.49 | -3.19 / -1.69 | 0/1 |
| composite_usd_risk | -2.40 | -1.69 | -2.72 | -3.88 | -1.31 | -2.42 | -2.40 | -4.01 / -1.04 | 0/6 |
| adaptive_cluster_scores.D | — | — | -2.41 | -2.91 | -1.13 | -3.08 | -2.38 | -2.17 / -2.81 | 0/4 |
| Faktör: gold_sovereign_decoupling | — | — | — | — | — | -2.33 | -2.33 | -1.04 / -3.25 | 0/1 |
| pair_common_factor.common_score | -2.87 | -1.71 | — | — | — | — | -2.29 | -2.93 / -1.57 | 0/2 |
| score_raw_cycle | -2.43 | -1.43 | — | — | -2.50 | -2.71 | -2.27 | -2.90 / -2.00 | 0/4 |
| Faktör: semi_lead | — | — | -1.92 | -2.61 | — | — | -2.27 | -2.84 / -1.56 | 0/2 |
| Faktör: duration_risk | -1.26 | -0.37 | -2.75 | -3.41 | -1.78 | -3.77 | -2.22 | -2.96 / -1.95 | 0/6 |
| Faktör: banking_stress | -1.30 | — | -2.76 | -3.50 | — | -1.15 | -2.18 | -2.45 / -2.07 | 0/4 |
| Faktör: gold_oil_ratio | — | — | — | — | — | -2.04 | -2.04 | -0.88 / -2.83 | 0/1 |

_Negatif ortalama = sinyal TERS yönde kullanılırsa çalışıyor olabilir (TERS kurallar da ayrıca test edildi)._

## 7) Tüm varlıklarda aynı ayarla en tutarlı kurallar

| Kural | Ort. Sharpe | Pozitif varlık |
|---|---|---|
| Keltner kırılımı (20/2.0) · 1d · long+short · SL 2.0×ATR / TP 4.0×ATR | 0.79 | 6/6 |
| Keltner kırılımı (20/2.0) · 1d · long+short · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 0.68 | 6/6 |
| Donchian kırılımı (55) · 1d · sadece long · 24 saat tut | 0.66 | 6/6 |
| Keltner kırılımı (20/2.0) · 1d · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | 0.59 | 6/6 |
| Keltner kırılımı (20/2.0) · 1d · sadece long · SL 2.0×ATR / TP 4.0×ATR | 0.59 | 6/6 |
| RSI trend (14) · 1d · sadece long · SL 2.0 / TP 4.0×ATR × volatilite oranı | 0.54 | 6/6 |
| Keltner kırılımı (20/2.0) · 1d · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | 0.54 | 6/6 |
| Momentum (60) · 1d · sadece long · sinyalle çıkış | 0.52 | 6/6 |
| Makro: breakeven_z · sadece long · iz süren stop 3.0×ATR | 0.51 | 6/6 |
| EMA kesişimi (10/30) · 1d · sadece long · sinyalle çıkış | 0.51 | 6/6 |
| EMA kesişimi (50/200) · 4h · sadece long · sinyalle çıkış | 0.50 | 6/6 |
| EMA trend (50) · 1d · sadece long · sinyalle çıkış | 0.49 | 6/6 |
| EMA trend (100) · 1d · sadece long · sinyalle çıkış | 0.48 | 6/6 |
| Keltner kırılımı (20/2.0) · 1d · sadece long · SL 2.0 / TP 4.0×ATR, 1.0×ATR kârda stop girişe (başa baş) | 0.48 | 6/6 |
| EMA kesişimi (20/50) · 1d · sadece long · sinyalle çıkış | 0.47 | 6/6 |

## 8) Varlık bazında ilk 15 (tam pencere — seçim yanlılığı İÇERİR, tek başına kanıt değildir)

**SPX — S&P 500** · 2024-11-06 → 2026-10-07 · 187,668 konfigürasyon (etkin bağımsız: 27)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış | tek·1 hafta | 2.53 | 3.08 / 1.89 | %+26.3 | %-2.4 | 15 | %87 | %17 |
| 2 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.53 | 3.08 / 1.89 | %+26.3 | %-2.4 | 15 | %87 | %17 |
| 3 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 2.53 | 3.08 / 1.89 | %+26.3 | %-2.4 | 15 | %87 | %17 |
| 4 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 2.53 | 3.08 / 1.89 | %+26.3 | %-2.4 | 15 | %87 | %17 |
| 5 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 2.52 | 3.06 / 1.89 | %+26.2 | %-2.4 | 15 | %87 | %17 |
| 6 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.52 | 3.08 / 1.85 | %+26.2 | %-2.5 | 15 | %87 | %17 |
| 7 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 2.13 | 3.44 / 0.73 | %+50.2 | %-4.4 | 29 | %69 | %33 |
| 8 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.12 | 3.45 / 0.73 | %+48.4 | %-4.4 | 29 | %69 | %33 |
| 9 | Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1) · 4 saatlik ortalama · sadece long · SL 2.0×ATR / TP 4.0×ATR | tek·4 saat | 2.09 | 1.51 / 2.56 | %+23.4 | %-2.5 | 25 | %72 | %14 |
| 10 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.08 | 3.25 / 0.77 | %+44.8 | %-4.0 | 29 | %62 | %32 |
| 11 | pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.01 | 2.14 / 1.89 | %+20.4 | %-3.7 | 15 | %80 | %18 |
| 12 | pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 2.01 | 2.14 / 1.89 | %+20.4 | %-3.7 | 15 | %80 | %18 |
| 13 | pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış | tek·1 hafta | 2.01 | 2.14 / 1.89 | %+20.4 | %-3.7 | 15 | %80 | %18 |
| 14 | pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 2.01 | 2.14 / 1.89 | %+20.4 | %-3.7 | 15 | %80 | %18 |
| 15 | pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 2.00 | 2.12 / 1.89 | %+20.3 | %-3.7 | 15 | %80 | %18 |

_Walk-forward dilim getirileri: %-12.4, %+4.5, %+3.3, %+3.2, %-0.3 · seçilenler: TERS Momentum (180) · 4h · 1 günlük · long+short · sinyalle çıkış; TERS Faktör: nq_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı; TERS Faktör: nq_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı; pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış; pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış_

**NQ — Nasdaq 100** · 2024-11-06 → 2026-10-07 · 190,154 konfigürasyon (etkin bağımsız: 26)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış | tek·1 hafta | 2.70 | 3.20 / 2.13 | %+39.0 | %-3.0 | 15 | %93 | %17 |
| 2 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.70 | 3.20 / 2.13 | %+39.0 | %-3.0 | 15 | %93 | %17 |
| 3 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 2.70 | 3.20 / 2.13 | %+39.0 | %-3.0 | 15 | %93 | %17 |
| 4 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 2.70 | 3.20 / 2.13 | %+39.0 | %-3.0 | 15 | %93 | %17 |
| 5 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 2.69 | 3.19 / 2.13 | %+38.9 | %-3.0 | 15 | %93 | %17 |
| 6 | pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.57 | 2.96 / 2.13 | %+36.7 | %-3.0 | 15 | %87 | %17 |
| 7 | Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.41 | 3.08 / 1.68 | %+35.3 | %-3.0 | 16 | %88 | %19 |
| 8 | Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış | tek·1 hafta | 2.41 | 3.08 / 1.68 | %+35.3 | %-3.0 | 16 | %88 | %19 |
| 9 | Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 2.41 | 3.08 / 1.68 | %+35.3 | %-3.0 | 16 | %88 | %19 |
| 10 | Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 2.41 | 3.08 / 1.68 | %+35.3 | %-3.0 | 16 | %88 | %19 |
| 11 | Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.41 | 3.08 / 1.68 | %+35.3 | %-3.0 | 16 | %88 | %19 |
| 12 | Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 2.41 | 3.07 / 1.68 | %+35.1 | %-3.0 | 16 | %88 | %19 |
| 13 | pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 2.28 | 2.42 / 2.13 | %+32.3 | %-4.5 | 15 | %80 | %18 |
| 14 | pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.28 | 2.42 / 2.13 | %+32.3 | %-4.5 | 15 | %80 | %18 |
| 15 | pair_stats.spread (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış | tek·1 hafta | 2.28 | 2.42 / 2.13 | %+32.3 | %-4.5 | 15 | %80 | %18 |

_Walk-forward dilim getirileri: %-15.4, %+5.6, %+12.3, %+4.9, %+0.7 · seçilenler: TERS Donchian kırılımı (168) · 1h · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; Faktör: spx_relative_divergence (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış; pair_stats.residual_z (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle ç_

**XAU — Altın** · 2024-11-06 → 2026-10-07 · 184,292 konfigürasyon (etkin bağımsız: 31)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük ortalama · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 gün | 1.94 | 2.18 / 1.83 | %+86.0 | %-14.0 | 28 | %64 | %57 |
| 2 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>1) · 1 günlük · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 gün | 1.91 | 2.32 / 1.83 | %+85.2 | %-12.7 | 23 | %70 | %43 |
| 3 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>1) · 1 günlük · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 gün | 1.91 | 2.18 / 1.93 | %+88.7 | %-12.7 | 23 | %70 | %43 |
| 4 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük ortalama · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 gün | 1.86 | 1.99 / 1.84 | %+82.3 | %-14.0 | 28 | %64 | %57 |
| 5 | MACD (12/26/9) · 1h · 1 haftalık · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 1.79 | 1.76 / 1.88 | %+65.4 | %-9.9 | 24 | %62 | %39 |
| 6 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>1) · long+short · iz süren stop 3.0×ATR | tek·1 saat | 1.78 | 1.45 / 2.08 | %+58.5 | %-6.2 | 23 | %61 | %21 |
| 7 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 gün | 1.78 | 2.38 / 1.47 | %+76.8 | %-12.3 | 28 | %71 | %58 |
| 8 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 gün | 1.77 | 2.55 / 1.47 | %+75.9 | %-12.3 | 28 | %71 | %56 |
| 9 | TERS direction_velocity (güçlü, ∣z∣>1) · 1 haftalık ortalama · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 1.77 | 0.27 / 2.90 | %+54.5 | %-5.2 | 31 | %58 | %34 |
| 10 | Donchian kırılımı (20) · 4h · sadece long · 24 saat tut | teknik | 1.77 | 2.05 / 1.52 | %+17.4 | %-2.7 | 29 | %72 | %6 |
| 11 | TERS Faktör: banking_stress · 1 haftalık ortalama · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 1.77 | 2.34 / 1.55 | %+54.8 | %-8.6 | 18 | %78 | %38 |
| 12 | MACD (12/26/9) · 1h · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 1.76 | 0.84 / 2.43 | %+116.2 | %-16.2 | 49 | %61 | %90 |
| 13 | TERS Faktör: gold_vol_premium_lead · 4 saatlik ortalama · sadece long · iz süren stop 2.0×ATR | tek·4 saat | 1.76 | 1.69 / 1.84 | %+18.5 | %-2.2 | 23 | %61 | %7 |
| 14 | EMA kesişimi (24/96) · 1h · 4 saatlik ortalama · sadece long · 24 saat tut | tek·4 saat | 1.76 | 2.18 / 1.26 | %+20.7 | %-3.1 | 53 | %57 | %11 |
| 15 | TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>1) · 4 saatlik · long+short · iz süren stop 3.0×ATR | tek·4 saat | 1.74 | 1.43 / 2.02 | %+57.0 | %-6.2 | 23 | %61 | %21 |

_Walk-forward dilim getirileri: %+2.3, %+2.4, %+0.5, %-4.6, %+5.8 · seçilenler: Tetik: 20 mum kırılımı · 1h | filtre: Faktör: safe_haven · 1 günlük ortalama yönünde · sadece long · sinyalle çıkış; TERS Yön z-skoru (güçlü, ∣z∣>1) · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 4 saatlik · sadece long · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; TERS Alt: COT spekülatif fon net (z) (güçlü, ∣z∣>0.5) · 1 günlük · sadece long · SL 3.0×ATR / TP 6.0×ATR; Fiyat itkisi skoru · 1 aylık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kal_

**XAG — Gümüş** · 2024-11-06 → 2026-10-07 · 181,902 konfigürasyon (etkin bağımsız: 24)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama · sadece long · iz süren stop 3.0×ATR | tek·1 hafta | 2.35 | 2.16 / 2.57 | %+274.7 | %-16.4 | 24 | %75 | %48 |
| 2 | TERS Faktör: silver_vol_premium_lead (güçlü, ∣z∣>1) · 1 günlük · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 gün | 2.31 | 1.78 / 2.78 | %+115.0 | %-5.4 | 25 | %52 | %12 |
| 3 | TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 2.29 | 2.21 / 2.42 | %+248.0 | %-15.7 | 24 | %62 | %47 |
| 4 | TERS Kısa Vade Yön · 1 günlük · sadece long · sinyalle çıkış | tek·1 gün | 2.25 | 0.76 / 3.13 | %+191.8 | %-12.2 | 47 | %74 | %16 |
| 5 | TERS Kısa Vade Yön (güçlü, ∣z∣>0.5) · 1 günlük · sadece long · sinyalle çıkış | tek·1 gün | 2.20 | 0.56 / 3.13 | %+184.7 | %-12.2 | 46 | %74 | %16 |
| 6 | TERS Kısa Vade Yön · 1 günlük · sadece long · iz süren stop 3.0×ATR | tek·1 gün | 2.16 | 0.76 / 2.99 | %+171.5 | %-14.6 | 47 | %74 | %16 |
| 7 | TERS DMI/ADX yönü (14) · 1h · 1 haftalık ortalama · long+short · iz süren stop 3.0×ATR | tek·1 hafta | 2.12 | 2.34 / 2.09 | %+346.0 | %-22.0 | 46 | %65 | %70 |
| 8 | TERS Kısa Vade Yön (güçlü, ∣z∣>0.5) · 1 günlük · sadece long · iz süren stop 3.0×ATR | tek·1 gün | 2.11 | 0.56 / 2.99 | %+164.9 | %-14.6 | 46 | %74 | %16 |
| 9 | TERS Faktör: silver_vol_premium_lead (güçlü, ∣z∣>1) · 1 günlük · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 gün | 2.10 | 1.35 / 2.66 | %+93.1 | %-4.4 | 25 | %52 | %12 |
| 10 | TERS Kısa Vade Yön · 1 günlük · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 gün | 2.10 | 0.76 / 2.90 | %+166.4 | %-16.2 | 47 | %74 | %16 |
| 11 | TERS Kısa Vade Yön · 1 günlük · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 gün | 2.10 | 0.76 / 2.90 | %+166.4 | %-16.2 | 47 | %74 | %16 |
| 12 | TERS Kısa Vade Yön · 1 günlük · sadece long · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 gün | 2.10 | 0.76 / 2.90 | %+166.4 | %-16.2 | 47 | %74 | %16 |
| 13 | TERS Kısa Vade Yön · 1 günlük · sadece long · SL 3.0×ATR / TP 6.0×ATR | tek·1 gün | 2.10 | 0.76 / 2.90 | %+166.4 | %-16.2 | 47 | %74 | %16 |
| 14 | adaptive_cluster_scores.B (güçlü, ∣z∣>0.5) · 1 günlük · sadece long · iz süren stop 3.0×ATR | tek·1 gün | 2.10 | -0.16 / 3.31 | %+214.4 | %-14.6 | 102 | %61 | %32 |
| 15 | TERS short_term_parts.price_part (güçlü, ∣z∣>0.5) · 1 günlük · sadece long · sinyalle çıkış | tek·1 gün | 2.09 | 2.18 / 2.28 | %+174.6 | %-18.1 | 108 | %55 | %26 |

_Walk-forward dilim getirileri: %-4.0, %+5.2, %+15.2, %-16.8, %-11.6 · seçilenler: TERS Keltner kırılımı (20/2.0) · 4h · long+short · iz süren stop 2.0×ATR; Tetik: RSI(2) geri çekilme · 1d | filtre: Alt: COT üretici net (haftalık değişim) · 1 günlük ortalama yönünde · sadece short · SL 2.0 / TP 4.0×ATR × volatilite oranı; Makro: dfii10_z · sadece long · SL 2.0 / TP 4.0×ATR × volatilite oranı; TERS Alt: COT üretici net (z) (güçlü, ∣z∣>0.5) · 1 haftalık · sadece long · sinyalle çıkış; TERS Makro: yen_carry_z · 1 haftalık · sadece long · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR_

**BTC — Bitcoin** · 2024-11-06 → 2026-10-07 · 195,586 konfigürasyon (etkin bağımsız: 37)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | TERS direction_velocity · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 2.02 | 0.72 / 3.38 | %+272.9 | %-29.5 | 51 | %72 | %75 |
| 2 | TERS direction_velocity · 1 haftalık · long+short · sinyalle çıkış | tek·1 hafta | 1.91 | 1.16 / 2.64 | %+400.5 | %-17.3 | 51 | %72 | %99 |
| 3 | Tetik: Keltner kırılımı · 1d | filtre: Alt: COT kaldıraçlı fon net (haftalık değişim) yönünde · long+short · iz süren stop 2.0×ATR | filtre+tetik | 1.90 | 0.82 / 2.67 | %+102.5 | %-7.5 | 16 | %56 | %8 |
| 4 | Donchian kırılımı (55) · 4h · sadece long · SL 2.0 / TP 4.0×ATR × volatilite oranı | teknik | 1.87 | 3.15 / 0.41 | %+54.4 | %-9.1 | 18 | %72 | %8 |
| 5 | TERS adaptive_cluster_scores.E (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 1.87 | 1.07 / 2.69 | %+208.6 | %-20.9 | 43 | %67 | %58 |
| 6 | Alt: COT kaldıraçlı fon net (z) (güçlü, ∣z∣>1) · 4 saatlik · long+short · SL 1.5×ATR / TP 3.0×ATR | tek·4 saat | 1.86 | 1.68 / 2.05 | %+65.2 | %-9.2 | 33 | %55 | %17 |
| 7 | TERS adaptive_cluster_scores.E (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 1.85 | 1.13 / 2.60 | %+205.1 | %-20.9 | 43 | %67 | %60 |
| 8 | Alt: COT kaldıraçlı fon net (z) (güçlü, ∣z∣>1) · long+short · SL 1.5×ATR / TP 3.0×ATR | tek·1 saat | 1.85 | 1.66 / 2.03 | %+64.4 | %-9.2 | 33 | %52 | %17 |
| 9 | TERS Adaptif skor (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 1.83 | 1.91 / 1.74 | %+198.0 | %-30.3 | 44 | %64 | %59 |
| 10 | TERS score_raw_cycle (güçlü, ∣z∣>1) · 1 haftalık · long+short · sinyalle çıkış | tek·1 hafta | 1.82 | 1.93 / 1.72 | %+153.2 | %-21.6 | 33 | %58 | %35 |
| 11 | TERS Adaptif skor (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 1.81 | 1.83 / 1.79 | %+203.7 | %-31.1 | 44 | %64 | %58 |
| 12 | TERS score_raw_cycle (güçlü, ∣z∣>1) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 1.81 | 2.18 / 1.40 | %+142.7 | %-26.7 | 33 | %55 | %31 |
| 13 | TERS Adaptif skor (güçlü, ∣z∣>1) · 1 haftalık · long+short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 hafta | 1.81 | 2.11 / 1.49 | %+130.2 | %-21.3 | 31 | %55 | %29 |
| 14 | Alt: COT kaldıraçlı fon net (z) (güçlü, ∣z∣>1) · 4 saatlik · sadece long · SL 1.5×ATR / TP 3.0×ATR | tek·4 saat | 1.81 | 1.95 / 1.69 | %+40.7 | %-6.6 | 16 | %62 | %11 |
| 15 | TERS adaptive_cluster_scores.E (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·1 hafta | 1.81 | 1.00 / 2.67 | %+189.6 | %-21.6 | 43 | %70 | %61 |

_Walk-forward dilim getirileri: %-14.7, %+14.4, %-10.1, %-4.6, %-1.5 · seçilenler: Makro: dfii10_z · 4 saatlik ortalama · sadece long · SL 3.0 / TP 6.0×ATR × volatilite oranı; TERS Yön z-skoru · 4 saatlik ortalama · long+short · 24 saat tut; TERS Yön z-skoru · 4 saatlik ortalama · long+short · 24 saat tut; TERS Yön z-skoru · 4 saatlik ortalama · sadece short · 24 saat tut; Alt: COT kaldıraçlı fon net (haftalık değişim) (z) (güçlü, ∣z∣>1) · 1 aylık ortalama · long+short · SL 3.0×ATR, yarısı 3.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR_

**ETH — Ethereum** · 2024-11-06 → 2026-10-07 · 190,318 konfigürasyon (etkin bağımsız: 34)

| # | Kural | Tür | Sharpe | 1./2. yarı | Getiri | Maks. DD | İşlem | Kazanma | Pozisyonda |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Tetik: Keltner kırılımı · 4h | filtre: Kısa Vade Yön · 1 günlük ortalama yönünde · sadece short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | filtre+tetik | 2.14 | 2.62 / 1.63 | %+129.9 | %-12.2 | 46 | %63 | %11 |
| 2 | Donchian kırılımı (48) · 1h · 1 haftalık ortalama · long+short · SL 3.0×ATR / TP 6.0×ATR | tek·1 hafta | 2.03 | 2.38 / 1.62 | %+727.1 | %-30.9 | 48 | %56 | %75 |
| 3 | Donchian kırılımı (48) · 1h · 1 haftalık ortalama · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 hafta | 2.01 | 2.37 / 1.61 | %+637.1 | %-30.9 | 48 | %56 | %73 |
| 4 | Model sinyali (24s-1h) (güçlü, ∣z∣>1) · 1 günlük · sadece short · SL 3.0 / TP 6.0×ATR, 1.5×ATR kârda stop girişe (başa baş) | tek·1 gün | 1.99 | 1.12 / 2.78 | %+266.5 | %-20.9 | 51 | %51 | %22 |
| 5 | Donchian kırılımı (48) · 1h · 1 haftalık ortalama · long+short · sinyalle çıkış | tek·1 hafta | 1.98 | 2.91 / 0.88 | %+1284.6 | %-36.9 | 48 | %56 | %100 |
| 6 | Tetik: EMA20 kesişimi · 1d | filtre: Alt: Perp primi 8s ort. (z) · 1 haftalık ortalama yönünde · long+short · iz süren stop 2.0×ATR | filtre+tetik | 1.96 | 2.46 / 1.31 | %+204.9 | %-18.4 | 37 | %51 | %17 |
| 7 | Momentum (60) · 1d · 4 saatlik ortalama · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·4 saat | 1.95 | 2.18 / 1.72 | %+523.1 | %-30.2 | 19 | %47 | %42 |
| 8 | TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>1) · 1 haftalık · long+short · iz süren stop 3.0×ATR | tek·1 hafta | 1.94 | 2.18 / 1.66 | %+404.3 | %-22.3 | 33 | %73 | %38 |
| 9 | Momentum (60) · 1d · long+short · SL 2.0×ATR / TP 4.0×ATR | teknik | 1.93 | 1.95 / 1.90 | %+254.6 | %-16.6 | 19 | %53 | %19 |
| 10 | TERS Alt: COT kaldıraçlı fon net (haftalık değişim) (güçlü, ∣z∣>0.5) · 1 haftalık · long+short · sinyalle çıkış | tek·1 hafta | 1.91 | 1.95 / 1.89 | %+751.4 | %-38.3 | 53 | %64 | %72 |
| 11 | Momentum (60) · 1d · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı | teknik | 1.91 | 2.19 / 1.63 | %+504.8 | %-31.1 | 19 | %47 | %43 |
| 12 | Momentum (60) · 1d · 4 saatlik ortalama · long+short · SL 2.0 / TP 4.0×ATR × volatilite oranı | tek·4 saat | 1.91 | 2.06 / 1.75 | %+188.7 | %-23.8 | 19 | %47 | %17 |
| 13 | Model sinyali (24s-1h) (güçlü, ∣z∣>1) · 1 günlük · sadece short · SL 3.0 / TP 6.0×ATR × volatilite oranı | tek·1 gün | 1.91 | 0.89 / 2.85 | %+287.7 | %-24.1 | 51 | %51 | %22 |
| 14 | Tetik: EMA20 kesişimi · 1d | filtre: Alt: Perp primi 8s ort. (z) · 1 haftalık ortalama yönünde · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | filtre+tetik | 1.90 | 2.34 / 1.34 | %+157.2 | %-18.4 | 37 | %51 | %18 |
| 15 | RSI trend (14) · 1d · 4 saatlik ortalama · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR | tek·4 saat | 1.89 | 2.08 / 1.70 | %+295.3 | %-18.9 | 56 | %54 | %58 |

_Walk-forward dilim getirileri: %-8.1, %+5.3, %+3.7, %-10.1, %-22.4 · seçilenler: Momentum (336) · 1h · long+short · SL 2.0×ATR, yarısı 2.0×ATR'de kâr al, kalanı başa baş + iz süren 3.0×ATR; Momentum (336) · 1h · 4 saatlik · long+short · SL 3.0 / TP 6.0×ATR × volatilite oranı; Momentum (336) · 1h · 4 saatlik · long+short · iz süren stop 3.0×ATR; Momentum (336) · 1h · 4 saatlik · long+short · SL 3.0×ATR / TP 6.0×ATR; TERS composite_usd_risk (güçlü, ∣z∣>0.5) · 1 aylık ortalama · long+short · sinyalle çıkış_

_Tüm konfigürasyonların tek tek sonuçları: **lab_all_configs.csv.gz**._
