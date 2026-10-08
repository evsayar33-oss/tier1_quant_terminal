# 🌐 Kesitsel Kripto Perp Laboratuvarı v9 — portföy stratejileri, son 2 yıl mühürlü

_Üretim: 2026-10-08T12:10 UTC · 895 USDT perp (kapanmışlar dahil) · 1,248 portföy kuralı (etkin bağımsız 4) · eğitim 2020-03-20 → 2024-09-30 · **sınav 2024-09-30 → 2026-09-30**_

**Kanıt şartı (önceden sabit):** eğitimde yıllık walk-forward t ≥ 2 ve yılların ≥%60'ı pozitif · DSR ≥ 0.90 · sınavda t ≥ 1.5 ve BTC'ye karşı alfa t ≥ 1.0. Gerçek fonlama ödemeleri, komisyon+kayma (ilk 20: %0.06, ilk 50: %0.10, ilk 100: %0.15 / taraf) düşülmüştür; işlem bir sonraki gün uygulanır.

## 1) Seçilen strateji (eğitimin en iyisi) ve mühürlü sınav

| Kural | Eğitim Sharpe | **Sınav Sharpe** | Sınav getiri / DD | Sınav t · alfa t (β) | WF Sharpe (t) | DSR | Günlük devir | Durum |
|---|---|---|---|---|---|---|---|---|
| Fonlama carry (3 gün) · ilk 20 coin · en iyi %33 long / en kötü %33 short · ters-volatilite ağırlık · günlük yenileme | 1.62 | **0.17** | %+10.0 / %-40.9 | +0.2 · +0.3 (-0.08) | -0.93 (-1.6) | 0.99 | 0.50 | ❌ kanıt yok |

BTC'yi tutmak: eğitim Sharpe 0.61 · sınav 0.15

**Yıllık walk-forward seçimleri:** 2022: -0.75 (Fonlama carry (3 gün) · ilk 100 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · günlük yenileme) · 2023: -0.21 (Fonlama carry (7 gün) · ilk 100 coin · en iyi %33 long / en kötü %33 short · eşit ağırlık · günlük yenileme) · 2024: -1.67 (Fonlama carry (3 gün) · ilk 50 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · günlük yenileme)

## 1b) Prosedür B — aile topluluğu (tek 'en iyi' seçmeden)

_Önceden sabit kural: o güne kadarki veride varyantlarının ≥%80'i kârlı olan piyasa-nötr (long/short) aileler seçilir; her aileye eşit sermaye, aile içinde her varyanta eşit sermaye. Aynı yıllık walk-forward ve aynı mühürlü sınav._

| Seçilen aileler (eğitimin tamamıyla) | WF Sharpe (t) | **Sınav Sharpe** | Sınav getiri / DD | Sınav t · alfa t (β) | Durum |
|---|---|---|---|---|---|
| Fonlama carry (30g), Fonlama carry (3g), Fonlama carry (7g), Riske göre momentum (28g) | -0.12 (-0.2) | **1.36** | %+88.5 / %-13.9 | +1.9 · +2.0 (-0.12) | ❌ kanıt yok |

**Yıllık seçim (walk-forward):** 2022: -1.88 [Fonlama carry (30g), Fonlama carry (3g), Fonlama carry (7g), TERS Düşük volatilite (28g), Momentum (14g), Momentum (28g), Momentum (56g), Momentum (7g), Momentum (84g), Riske göre momentum (28g)] · 2023: +1.44 [Fonlama carry (30g), Fonlama carry (3g), Fonlama carry (7g), Momentum (28g), Riske göre momentum (28g)] · 2024: -0.04 [Fonlama carry (30g), Fonlama carry (3g), Fonlama carry (7g), TERS Düşük volatilite (28g), Momentum (84g), Riske göre momentum (28g)]

**Sınav yılları:** 2024: +4.24 · 2025: +1.36 · 2026: +0.47

## 2) Strateji aileleri — eğitimde VE sınavda (aile ortalaması, seçim yanlılığı neredeyse yok)

_Bir aile = aynı sinyalin tüm evren/eşik/ağırlık/yenileme varyantları. Güvenilir aile: eğitimde de sınavda da pozitif, varyantlarının çoğu pozitif._

| Aile | Varyant | Eğitim ort. Sharpe | Eğitimde + | **Sınav ort. Sharpe** | Sınavda + | Sıra korelasyonu |
|---|---|---|---|---|---|---|
| Fonlama carry (7g) · long/short | 24 | 1.07 | %100 | **0.54** | %83 | -0.01 |
| Fonlama carry (30g) · long/short | 24 | 0.84 | %100 | **0.54** | %83 | -0.67 |
| Riske göre momentum (28g) · long/short | 24 | 0.48 | %88 | **1.51** | %100 | -0.19 |
| Fonlama carry (3g) · long/short | 24 | 0.90 | %100 | **0.44** | %75 | -0.48 |
| Momentum (14g) · sadece long | 24 | 0.42 | %100 | **0.27** | %75 | +0.26 |
| Momentum (28g) · long/short | 24 | 0.25 | %79 | **0.86** | %100 | -0.28 |
| Riske göre momentum (28g) · sadece long | 24 | 0.49 | %100 | **0.25** | %83 | +0.33 |
| Momentum (84g) · long/short | 24 | 0.21 | %71 | **0.34** | %71 | -0.33 |
| Momentum (56g) · long/short | 24 | 0.19 | %67 | **0.92** | %96 | -0.07 |
| Momentum (14g) · long/short | 24 | 0.11 | %54 | **1.23** | %100 | -0.19 |
| İlgi (hacim 7g/30g) (7g) · sadece long | 24 | 0.19 | %100 | **0.09** | %62 | +0.15 |
| Momentum (7g) · long/short | 24 | 0.03 | %62 | **0.32** | %62 | +0.49 |
| Momentum (56g) · sadece long | 24 | 0.32 | %96 | **0.02** | %46 | -0.29 |
| Momentum (28g) · sadece long | 24 | 0.43 | %100 | **0.01** | %50 | +0.14 |
| Momentum (7g) · sadece long | 24 | 0.38 | %100 | **-0.11** | %46 | +0.43 |
| Fonlama carry (3g) · sadece long | 24 | 0.60 | %100 | **-0.11** | %25 | +0.07 |
| Fonlama carry (7g) · sadece long | 24 | 0.48 | %100 | **-0.17** | %21 | +0.08 |
| Düşük volatilite (28g) · TERS · long/short | 24 | 0.12 | %71 | **-0.29** | %25 | -0.01 |
| Momentum (84g) · sadece long | 24 | 0.31 | %100 | **-0.30** | %8 | -0.34 |
| Fonlama carry (30g) · sadece long | 24 | 0.40 | %100 | **-0.31** | %8 | -0.10 |
| Momentum (3g) · sadece long | 24 | 0.20 | %83 | **-0.32** | %25 | +0.44 |
| Düşük volatilite (28g) · sadece long | 24 | 0.36 | %100 | **-0.32** | %0 | +0.41 |
| İlgi (hacim 7g/30g) (7g) · long/short | 24 | -0.46 | %17 | **1.32** | %100 | -0.64 |
| Momentum (3g) · long/short | 24 | -0.48 | %29 | **-0.31** | %42 | +0.75 |
| Düşük volatilite (28g) · TERS · sadece long | 24 | 0.20 | %100 | **-0.58** | %0 | -0.09 |
| Momentum (1g) · TERS · sadece long | 24 | -0.31 | %25 | **-0.70** | %0 | +0.62 |
| Düşük volatilite (28g) · long/short | 24 | -0.72 | %0 | **-0.43** | %8 | +0.31 |
| Momentum (3g) · TERS · sadece long | 24 | -0.18 | %21 | **-0.77** | %0 | +0.11 |
| Momentum (84g) · TERS · sadece long | 24 | 0.00 | %62 | **-0.83** | %0 | -0.55 |
| Fonlama carry (7g) · TERS · sadece long | 24 | -0.31 | %0 | **-0.87** | %0 | -0.07 |
| Momentum (1g) · sadece long | 24 | -0.15 | %50 | **-0.88** | %0 | +0.52 |
| Fonlama carry (3g) · TERS · sadece long | 24 | -0.28 | %21 | **-0.91** | %0 | +0.12 |
| Momentum (7g) · TERS · sadece long | 24 | -0.17 | %17 | **-0.99** | %0 | +0.18 |
| Fonlama carry (30g) · TERS · sadece long | 24 | -0.17 | %12 | **-0.99** | %0 | +0.43 |
| Momentum (56g) · TERS · sadece long | 24 | -0.01 | %71 | **-1.02** | %0 | -0.43 |
| Momentum (28g) · TERS · sadece long | 24 | -0.04 | %50 | **-1.08** | %0 | +0.22 |
| Momentum (84g) · TERS · long/short | 24 | -0.97 | %0 | **-1.13** | %0 | +0.12 |
| Momentum (14g) · TERS · sadece long | 24 | -0.06 | %42 | **-1.21** | %0 | +0.20 |
| İlgi (hacim 7g/30g) (7g) · TERS · sadece long | 24 | 0.14 | %92 | **-1.21** | %0 | -0.21 |
| Riske göre momentum (28g) · TERS · sadece long | 24 | -0.08 | %38 | **-1.33** | %0 | +0.25 |
| Momentum (3g) · TERS · long/short | 24 | -1.42 | %0 | **-1.39** | %0 | -0.27 |
| Fonlama carry (30g) · TERS · long/short | 24 | -1.42 | %0 | **-1.13** | %0 | +0.12 |
| Momentum (1g) · long/short | 24 | -1.24 | %12 | **-1.47** | %0 | +0.89 |
| Momentum (1g) · TERS · long/short | 24 | -1.64 | %0 | **-0.88** | %17 | +0.72 |
| Momentum (7g) · TERS · long/short | 24 | -1.49 | %0 | **-1.69** | %0 | +0.18 |
| Momentum (56g) · TERS · long/short | 24 | -0.91 | %0 | **-1.70** | %0 | +0.01 |
| Momentum (28g) · TERS · long/short | 24 | -1.19 | %0 | **-1.74** | %0 | -0.02 |
| Fonlama carry (7g) · TERS · long/short | 24 | -2.10 | %0 | **-1.46** | %0 | +0.80 |
| Momentum (14g) · TERS · long/short | 24 | -1.26 | %0 | **-2.23** | %0 | +0.02 |
| Fonlama carry (3g) · TERS · long/short | 24 | -2.24 | %0 | **-1.65** | %0 | +0.63 |
| İlgi (hacim 7g/30g) (7g) · TERS · long/short | 24 | -0.53 | %8 | **-2.26** | %0 | +0.20 |
| Riske göre momentum (28g) · TERS · long/short | 24 | -1.50 | %0 | **-2.40** | %0 | +0.19 |

## 3) Eğitimin en iyi 25 kuralı ve sınav sonuçları

| # | Kural | Eğitim Sharpe | Sınav Sharpe | Sınav getiri | Günlük devir |
|---|---|---|---|---|---|
| 1 | Fonlama carry (3 gün) · ilk 20 coin · en iyi %33 long / en kötü %33 short · ters-volatilite ağırlık · günlük yenileme | 1.62 | 0.17 | %+10.0 | 0.50 |
| 2 | Fonlama carry (3 gün) · ilk 20 coin · en iyi %33 long / en kötü %33 short · eşit ağırlık · günlük yenileme | 1.50 | -0.05 | %-5.9 | 0.42 |
| 3 | Fonlama carry (7 gün) · ilk 20 coin · en iyi %33 long / en kötü %33 short · ters-volatilite ağırlık · günlük yenileme | 1.40 | 0.18 | %+10.2 | 0.32 |
| 4 | Fonlama carry (7 gün) · ilk 100 coin · en iyi %33 long / en kötü %33 short · eşit ağırlık · günlük yenileme | 1.38 | 1.21 | %+76.5 | 0.22 |
| 5 | Fonlama carry (7 gün) · ilk 20 coin · en iyi %20 long / en kötü %20 short · ters-volatilite ağırlık · günlük yenileme | 1.35 | -0.00 | %-0.1 | 0.38 |
| 6 | Fonlama carry (7 gün) · ilk 20 coin · en iyi %33 long / en kötü %33 short · eşit ağırlık · günlük yenileme | 1.33 | 0.07 | %+8.8 | 0.26 |
| 7 | Fonlama carry (7 gün) · ilk 20 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · günlük yenileme | 1.32 | -0.14 | %-23.1 | 0.30 |
| 8 | Fonlama carry (3 gün) · ilk 20 coin · en iyi %20 long / en kötü %20 short · ters-volatilite ağırlık · günlük yenileme | 1.28 | 0.40 | %+48.8 | 0.57 |
| 9 | Fonlama carry (3 gün) · ilk 20 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · günlük yenileme | 1.26 | -0.04 | %-7.1 | 0.47 |
| 10 | Fonlama carry (30 gün) · ilk 50 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · haftalık yenileme | 1.23 | 0.01 | %+1.1 | 0.07 |
| 11 | Fonlama carry (30 gün) · ilk 50 coin · en iyi %20 long / en kötü %20 short · ters-volatilite ağırlık · haftalık yenileme | 1.23 | 0.08 | %+5.7 | 0.09 |
| 12 | Riske göre momentum (28 gün) · ilk 20 coin · en iyi %33 long / en kötü %33 short · eşit ağırlık · günlük yenileme | 1.22 | 1.38 | %+322.3 | 0.28 |
| 13 | Fonlama carry (3 gün) · ilk 20 coin · en iyi %33 long / en kötü %33 short · eşit ağırlık · haftalık yenileme | 1.21 | 0.32 | %+40.3 | 0.14 |
| 14 | Fonlama carry (3 gün) · ilk 50 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · günlük yenileme | 1.19 | 0.46 | %+59.5 | 0.45 |
| 15 | Fonlama carry (7 gün) · ilk 50 coin · en iyi %33 long / en kötü %33 short · eşit ağırlık · günlük yenileme | 1.19 | 0.85 | %+78.1 | 0.23 |
| 16 | Fonlama carry (7 gün) · ilk 50 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · günlük yenileme | 1.18 | 0.38 | %+48.3 | 0.28 |
| 17 | Fonlama carry (7 gün) · ilk 100 coin · en iyi %33 long / en kötü %33 short · eşit ağırlık · haftalık yenileme | 1.18 | 0.71 | %+36.9 | 0.11 |
| 18 | Fonlama carry (3 gün) · ilk 20 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · haftalık yenileme | 1.18 | 0.31 | %+69.6 | 0.16 |
| 19 | Riske göre momentum (28 gün) · ilk 20 coin · en iyi %33 long / en kötü %33 short · ters-volatilite ağırlık · günlük yenileme | 1.18 | 1.16 | %+93.0 | 0.34 |
| 20 | Riske göre momentum (28 gün) · ilk 20 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · günlük yenileme | 1.16 | 1.82 | %+1067.7 | 0.35 |
| 21 | Fonlama carry (7 gün) · ilk 100 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · günlük yenileme | 1.15 | 0.98 | %+102.8 | 0.26 |
| 22 | Fonlama carry (7 gün) · ilk 100 coin · en iyi %20 long / en kötü %20 short · eşit ağırlık · haftalık yenileme | 1.14 | 0.24 | %+17.7 | 0.13 |
| 23 | Fonlama carry (7 gün) · ilk 100 coin · en iyi %33 long / en kötü %33 short · ters-volatilite ağırlık · günlük yenileme | 1.13 | 1.64 | %+65.4 | 0.27 |
| 24 | Fonlama carry (7 gün) · ilk 50 coin · en iyi %20 long / en kötü %20 short · ters-volatilite ağırlık · günlük yenileme | 1.11 | 0.05 | %+3.2 | 0.34 |
| 25 | Fonlama carry (7 gün) · ilk 20 coin · en iyi %33 long / en kötü %33 short · eşit ağırlık · haftalık yenileme | 1.09 | 0.47 | %+66.4 | 0.12 |

## 4) Kaldıraç — seçilen kural, sınav dönemi

| 1x | 2x | 3x | 5x | 10x |
|---|---|---|---|---|
| %+5 / %-41 | %+2 / %-68 | %-8 / %-84 | %-41 / %-97 | %-98 / %-100 |

_Not: kapanan (delist) kontratlar son kapanıştan çıkılmış sayılır; gerçekte kapanıştan önce düşüş olabilir. Short tarafında borç/likidite kısıtı yok varsayıldı (perp'lerde short serbesttir)._
