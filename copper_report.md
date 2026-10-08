# 🟠 Bakır Laboratuvarı v14 — COMEX bakır (HG=F) üzerinde tüm strateji aileleri

_Üretim 2026-10-08T18:51 UTC · veri 2000-08-30 → 2026-10-08 · seçim yalnızca 2000–2016 · **2017+ mühürlü sınav** · 1,321 deneme · maliyet %0.08/işlem birimi + long'a yıllık %3 fonlama farkı._

**Karşılaştırma — bakırı sadece tutmak:** eğitim yıllık %+3.4 · Sharpe 0.26 · DD %72  |  sınav yıllık %+7.2 · Sharpe 0.41 · DD %40

## 1) Seçim (yalnızca eğitim verisiyle) ve mühürlü sınav sonucu

**Eğitimin en iyisi (tüm denemeler):** Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 · çift yön

| | Sharpe | Yıllık | DD | Alfa t (bakıra göre) | İşlem | Piyasada |
|---|---|---|---|---|---|---|
| eğitim | 0.89 | %+8.6 | %16 | 3.6 | 1626 | %36 |
| **sınav** | **0.61** | **%+6.4** | %19 | **1.5** | 1120 | %42 |
| Deflated Sharpe (eğitim, 1321 deneme için) | 0.63 | | | | | |

**Eğitimin en iyi TEK kuralı:** madenciler bakırı öncülüyor (FCX−bakır 1 ay) · yalnız long

| | Sharpe | Yıllık | DD | Alfa t (bakıra göre) | İşlem | Piyasada |
|---|---|---|---|---|---|---|
| eğitim | 0.68 | %+11.6 | %40 | 2.7 | 426 | %53 |
| **sınav** | **0.66** | **%+10.2** | %28 | **1.6** | 210 | %52 |
| Deflated Sharpe (eğitim, 1321 deneme için) | 0.29 | | | | | |

### Fonlama senaryoları (long öder, short alır)

| | fonlama %0.0 | fonlama %3.0 | fonlama %8.0 | fonlama %15.8 |
|---|---|---|---|---|
| Bakırı tutmak (sınav yıllık) | %+10.5 | %+7.2 | %+2.0 | %-5.7 |
| Eğitimin en iyisi: sınav Sharpe / yıllık | 0.66 / %+7.2 | 0.62 / %+6.7 | 0.56 / %+5.8 | 0.45 / %+4.6 |
| En iyi tek kural: sınav Sharpe / yıllık | 0.75 / %+11.9 | 0.66 / %+10.2 | 0.50 / %+7.4 | 0.27 / %+3.1 |
| **Fonlamaya dayanıklı seçim** (Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15, çift yön; eğitimde 4 senaryonun en kötüsüne göre) | 0.66 / %+7.2 | 0.62 / %+6.7 | 0.56 / %+5.8 | 0.45 / %+4.6 |

_Seçim yine yalnız eğitim verisiyle; sınav sütunları seçimi etkilemez._

**Eğitimde en kötü senaryoda en iyi 15 (sınav Sharpe'ları senaryo sırasıyla):**

| Strateji | Yön | Eğitim (en kötü) | Sınav: %0.0 / %3.0 / %8.0 / %15.8 |
|---|---|---|---|
| Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | çift yön | 0.93 | 0.67 / 0.62 / 0.56 / 0.45 |
| Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.84 | 0.59 / 0.55 / 0.48 / 0.37 |
| momentum 252g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | çift yön | 0.80 | 0.59 / 0.57 / 0.52 / 0.45 |
| Donchian 100 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | çift yön | 0.80 | 0.19 / 0.16 / 0.10 / 0.01 |
| momentum topluluğu 1-3-6-12 ay + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.76 | 0.38 / 0.35 / 0.30 / 0.22 |
| momentum 63g + Çin öncü göstergesi yükseliyor · oynaklık hedefi %15 | çift yön | 0.76 | 0.49 / 0.48 / 0.47 / 0.45 |
| Donchian 100 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.75 | 0.20 / 0.17 / 0.12 / 0.03 |
| momentum 252g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.74 | 0.54 / 0.51 / 0.46 / 0.38 |
| momentum 63g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.74 | 0.15 / 0.13 / 0.10 / 0.04 |
| momentum 63g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | çift yön | 0.72 | 0.26 / 0.24 / 0.21 / 0.16 |
| yavaş MACD 28/36/20 (ATVS yönü) + COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.71 | 0.06 / 0.06 / 0.04 / 0.03 |
| momentum topluluğu 1-3-6-12 ay + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | çift yön | 0.71 | 0.48 / 0.46 / 0.41 / 0.34 |
| yavaş MACD 28/36/20 (ATVS yönü) + Çin öncü göstergesi yükseliyor | çift yön | 0.70 | 0.16 / 0.17 / 0.19 / 0.21 |
| SMA 20/50 kesişimi + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.69 | 0.37 / 0.35 / 0.33 / 0.28 |
| momentum 63g + Çin öncü göstergesi yükseliyor | çift yön | 0.69 | 0.34 / 0.34 / 0.33 / 0.32 |

_Seçilen tek kuralın ailesindeki 21 komşu: eğitimde pozitif %100, sınavda pozitif %76, sınav Sharpe ortalaması 0.26._

## 2) Aileler (tek kurallar, ortalama)

| Aile | Yön | Kural | Eğitim Sharpe | **Sınav Sharpe** | Sınav alfa t | Sınavda + |
|---|---|---|---|---|---|---|
| ML | yalnız long | 1 | 0.43 | **0.52** | 1.04 | %100 |
| MACRO | yalnız long | 21 | 0.37 | **0.26** | -0.16 | %76 |
| MEANREV | yalnız long | 12 | 0.05 | **0.22** | 0.20 | %75 |
| ML | çift yön | 1 | 0.43 | **0.19** | 0.83 | %100 |
| COT | yalnız long | 4 | 0.25 | **0.17** | -0.02 | %75 |
| TREND | yalnız long | 35 | 0.30 | **0.06** | -1.30 | %63 |
| MEANREV | çift yön | 12 | -0.16 | **0.04** | 0.28 | %58 |
| BREAKOUT | yalnız long | 4 | 0.09 | **0.04** | -0.77 | %50 |
| ATVS | yalnız long | 2 | -0.07 | **0.02** | -0.55 | %50 |
| SEASONAL | yalnız long | 3 | -0.09 | **0.01** | -0.70 | %33 |
| MACRO | çift yön | 21 | 0.21 | **-0.08** | -0.33 | %48 |
| COT | çift yön | 4 | 0.19 | **-0.13** | -0.30 | %50 |
| MEANREV | yalnız short | 12 | -0.29 | **-0.13** | 0.23 | %33 |
| ML | yalnız short | 1 | 0.14 | **-0.19** | 0.62 | %0 |
| ATVS | çift yön | 2 | -0.14 | **-0.19** | -0.97 | %0 |
| BREAKOUT | çift yön | 4 | -0.07 | **-0.20** | -0.94 | %0 |
| TREND | çift yön | 35 | 0.12 | **-0.32** | -1.45 | %20 |
| COT | yalnız short | 4 | -0.01 | **-0.32** | -0.32 | %0 |
| SEASONAL | çift yön | 3 | -0.23 | **-0.33** | -1.33 | %33 |
| ATVS | yalnız short | 2 | -0.12 | **-0.35** | -0.93 | %0 |
| MACRO | yalnız short | 21 | -0.06 | **-0.39** | -0.53 | %5 |
| BREAKOUT | yalnız short | 4 | -0.22 | **-0.41** | -0.81 | %0 |
| SEASONAL | yalnız short | 3 | -0.23 | **-0.48** | -1.23 | %0 |
| TREND | yalnız short | 35 | -0.12 | **-0.63** | -1.53 | %0 |

## 3) Eğitimin en iyi 30 denemesi ve sınavdaki sonuçları

| # | Strateji | Yön | Eğitim Sharpe / yıllık / DD | DSR | **Sınav Sharpe / yıllık / DD** | Sınav alfa t | İşlem (sınav) |
|---|---|---|---|---|---|---|---|
| 1 | Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | çift yön | 0.90 / %+8.6 / %16 | 0.63 | **0.61 / %+6.4 / %19** | 1.5 | 1120 |
| 2 | momentum 63g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.89 / %+12.0 / %18 | 0.62 | **0.60 / %+8.1 / %19** | 1.4 | 188 |
| 3 | Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | yalnız long | 0.88 / %+6.0 / %13 | 0.60 | **0.68 / %+6.5 / %15** | 1.7 | 867 |
| 4 | momentum 63g + Çin öncü göstergesi yükseliyor | yalnız long | 0.84 / %+13.3 / %31 | 0.55 | **0.82 / %+8.7 / %13** | 2.2 | 39 |
| 5 | SMA 20/100 kesişimi + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.84 / %+11.1 / %24 | 0.54 | **0.52 / %+6.8 / %23** | 1.1 | 146 |
| 6 | Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.83 / %+14.0 / %32 | 0.52 | **0.54 / %+7.7 / %25** | 1.3 | 184 |
| 7 | momentum 63g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | yalnız long | 0.82 / %+7.1 / %19 | 0.52 | **0.74 / %+7.3 / %18** | 1.9 | 951 |
| 8 | momentum 63g + Çin öncü göstergesi yükseliyor · oynaklık hedefi %15 | yalnız long | 0.82 / %+7.6 / %26 | 0.51 | **0.95 / %+7.8 / %9** | 2.7 | 605 |
| 9 | Donchian 55 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.82 / %+9.3 / %22 | 0.50 | **0.36 / %+4.0 / %21** | 0.5 | 112 |
| 10 | Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.81 / %+9.1 / %26 | 0.50 | **0.57 / %+7.4 / %25** | 1.3 | 144 |
| 11 | momentum 63g + Çin öncü göstergesi yükseliyor · oynaklık hedefi %15 | çift yön | 0.80 / %+9.8 / %23 | 0.48 | **0.44 / %+4.4 / %28** | 1.3 | 1199 |
| 12 | Donchian 55 kırılımı + Çin öncü göstergesi yükseliyor | yalnız long | 0.80 / %+11.1 / %22 | 0.48 | **0.62 / %+5.9 / %20** | 1.6 | 15 |
| 13 | Donchian 100 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.80 / %+9.2 / %21 | 0.48 | **0.22 / %+2.0 / %25** | 0.1 | 112 |
| 14 | Donchian 100 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | yalnız long | 0.79 / %+5.5 / %11 | 0.46 | **0.26 / %+1.9 / %16** | 0.2 | 745 |
| 15 | Donchian 100 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | çift yön | 0.78 / %+7.5 / %16 | 0.45 | **0.13 / %+0.8 / %23** | 0.2 | 1050 |
| 16 | momentum 252g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | çift yön | 0.78 / %+8.3 / %22 | 0.45 | **0.54 / %+6.2 / %20** | 1.4 | 1441 |
| 17 | momentum topluluğu 1-3-6-12 ay + Çin öncü göstergesi yükseliyor · oynaklık hedefi %15 | yalnız long | 0.77 / %+6.5 / %22 | 0.43 | **0.87 / %+6.7 / %13** | 2.4 | 531 |
| 18 | Donchian 100 kırılımı + Çin öncü göstergesi yükseliyor · oynaklık hedefi %15 | yalnız long | 0.77 / %+6.2 / %16 | 0.43 | **0.60 / %+4.4 / %19** | 1.5 | 501 |
| 19 | momentum 252g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.77 / %+9.5 / %37 | 0.42 | **0.42 / %+5.3 / %32** | 0.7 | 174 |
| 20 | momentum topluluğu 1-3-6-12 ay + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.76 / %+8.8 / %22 | 0.42 | **0.51 / %+6.3 / %19** | 1.0 | 184 |
| 21 | momentum topluluğu 1-3-6-12 ay + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.76 / %+13.3 / %28 | 0.42 | **0.32 / %+4.0 / %38** | 0.7 | 311 |
| 22 | momentum 63g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.76 / %+14.7 / %30 | 0.41 | **0.09 / %-0.0 / %40** | 0.0 | 349 |
| 23 | fiyat > SMA100 + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.76 / %+10.0 / %27 | 0.41 | **0.42 / %+5.3 / %28** | 0.7 | 186 |
| 24 | momentum 63g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · iz süren stop 3 ATR | yalnız long | 0.76 / %+9.3 / %24 | 0.41 | **0.35 / %+4.0 / %20** | 0.5 | 188 |
| 25 | momentum 126g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.76 / %+9.6 / %31 | 0.41 | **0.45 / %+5.6 / %24** | 0.8 | 192 |
| 26 | EMA100 eğimi + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.76 / %+9.9 / %24 | 0.41 | **0.52 / %+6.9 / %28** | 1.1 | 164 |
| 27 | fiyat > SMA100 + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · iz süren stop 3 ATR | yalnız long | 0.76 / %+9.3 / %25 | 0.41 | **0.24 / %+2.4 / %32** | 0.0 | 186 |
| 28 | momentum 63g + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 | çift yön | 0.75 / %+8.6 / %18 | 0.41 | **0.20 / %+1.8 / %32** | 0.4 | 1591 |
| 29 | Donchian 100 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.75 / %+13.0 / %30 | 0.40 | **0.15 / %+1.1 / %25** | 0.2 | 157 |
| 30 | SMA 20/100 kesişimi + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · iz süren stop 3 ATR | yalnız long | 0.75 / %+8.6 / %18 | 0.39 | **0.18 / %+1.6 / %25** | -0.2 | 146 |

## 4) Bütün tek kurallar (eğitim sırasıyla)

| Aile | Strateji | Yön | Eğitim Sharpe | Sınav Sharpe | Sınav alfa t |
|---|---|---|---|---|---|
| MACRO | Çin öncü göstergesi yükseliyor | yalnız long | 0.72 | 0.60 | 1.4 |
| MACRO | madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.68 | 0.66 | 1.6 |
| MACRO | Çin öncü göstergesi yükseliyor | çift yön | 0.68 | 0.40 | 1.4 |
| MACRO | ABD öncü göstergesi yükseliyor | yalnız long | 0.61 | 0.35 | 0.5 |
| MACRO | enflasyon beklentisi 3 ay yükseliyor | yalnız long | 0.60 | 0.21 | -0.5 |
| MACRO | madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.59 | 0.44 | 1.4 |
| TREND | momentum 63g | yalnız long | 0.57 | 0.05 | -1.6 |
| MACRO | finansal koşullar gevşiyor (NFCI 3 ay) | yalnız long | 0.55 | 0.56 | 1.2 |
| TREND | Donchian 55 kırılımı | yalnız long | 0.54 | 0.06 | -1.1 |
| MACRO | reel faiz 3 ay düşüyor | yalnız long | 0.53 | -0.12 | -1.6 |
| TREND | Donchian 100 kırılımı | yalnız long | 0.52 | -0.17 | -2.2 |
| MACRO | petrol 3 ay yükseliyor | yalnız long | 0.52 | -0.14 | -2.1 |
| TREND | momentum 252g | yalnız long | 0.52 | 0.38 | 0.2 |
| TREND | SMA 20/100 kesişimi | yalnız long | 0.50 | 0.22 | -0.7 |
| TREND | Donchian 200 kırılımı | yalnız long | 0.50 | 0.51 | 1.0 |
| TREND | SMA 10/50 kesişimi | yalnız long | 0.49 | 0.18 | -0.8 |
| TREND | SMA 20/50 kesişimi | yalnız long | 0.49 | 0.27 | -0.3 |
| TREND | momentum 63g | çift yön | 0.49 | -0.37 | -1.7 |
| COT | COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.48 | 0.29 | 0.7 |
| TREND | momentum 42g | yalnız long | 0.47 | 0.04 | -1.6 |
| MACRO | ABD öncü göstergesi yükseliyor | çift yön | 0.46 | 0.15 | 0.4 |
| TREND | EMA100 eğimi | yalnız long | 0.46 | 0.17 | -1.0 |
| MACRO | enflasyon beklentisi 3 ay yükseliyor | çift yön | 0.45 | -0.15 | -0.7 |
| TREND | momentum 126g | yalnız long | 0.44 | 0.32 | -0.1 |
| MACRO | S&P 500 > SMA200 | yalnız long | 0.44 | 0.48 | 0.8 |
| MACRO | petrol 3 ay yükseliyor | çift yön | 0.44 | -0.66 | -2.3 |
| TREND | yavaş MACD 28/36/20 (ATVS yönü) | yalnız long | 0.43 | 0.10 | -1.0 |
| TREND | Donchian 100 kırılımı | çift yön | 0.43 | -0.23 | -1.3 |
| TREND | fiyat > SMA100 | yalnız long | 0.43 | 0.01 | -1.8 |
| ML | makine öğrenmesi (yıllık ileri yürüyen) | yalnız long | 0.43 | 0.52 | 1.0 |
| ML | makine öğrenmesi (yıllık ileri yürüyen) | çift yön | 0.43 | 0.19 | 0.8 |
| TREND | momentum topluluğu 1-3-6-12 ay | çift yön | 0.42 | -0.09 | -1.0 |
| MACRO | reel faiz 3 ay düşüyor | çift yön | 0.42 | -0.65 | -1.9 |
| MACRO | finansal koşullar gevşiyor (NFCI 3 ay) | çift yön | 0.42 | 0.39 | 1.1 |
| TREND | fiyat > SMA150 | yalnız long | 0.42 | 0.12 | -1.2 |
| TREND | fiyat > SMA200 | yalnız long | 0.39 | 0.19 | -0.9 |
| TREND | Donchian 200 kırılımı | çift yön | 0.39 | 0.33 | 0.4 |
| MACRO | altın/gümüş oranı düşüyor (risk iştahı) | yalnız long | 0.39 | 0.04 | -1.2 |
| TREND | Donchian 55 kırılımı | çift yön | 0.39 | -0.33 | -1.6 |
| TREND | SMA 20/100 kesişimi | çift yön | 0.38 | -0.10 | -0.8 |
| TREND | momentum topluluğu 1-3-6-12 ay | yalnız long | 0.38 | 0.20 | -0.6 |
| TREND | SMA 20/50 kesişimi | çift yön | 0.38 | -0.02 | -0.5 |
| COT | COT spekülatör aşırı uç → ters | yalnız long | 0.37 | -0.25 | -1.1 |
| TREND | SMA 10/50 kesişimi | çift yön | 0.36 | -0.16 | -1.0 |
| TREND | EMA50 eğimi | yalnız long | 0.36 | -0.08 | -2.3 |
| TREND | momentum 252g | çift yön | 0.36 | 0.20 | 0.1 |
| COT | COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız long | 0.35 | 0.49 | 0.9 |
| TREND | fiyat > SMA250 | yalnız long | 0.35 | 0.27 | -0.5 |
| TREND | SMA 100/200 kesişimi | yalnız long | 0.35 | 0.10 | -1.5 |
| COT | COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız short | 0.34 | -0.14 | 0.5 |
| TREND | EMA100 eğimi | çift yön | 0.33 | -0.17 | -1.2 |
| TREND | SMA 50/100 kesişimi | yalnız long | 0.33 | 0.30 | -0.2 |
| MACRO | bakır/altın oranı > SMA100 | yalnız long | 0.32 | -0.09 | -1.6 |
| TREND | momentum 42g | çift yön | 0.32 | -0.40 | -1.7 |
| MACRO | VIX < 20 | yalnız long | 0.32 | 0.23 | -0.5 |
| TREND | SMA 50/200 kesişimi | yalnız long | 0.31 | 0.27 | -0.4 |
| MACRO | sanayi üretimi ivmeleniyor | yalnız long | 0.31 | 0.28 | -0.0 |
| TREND | momentum 126g | çift yön | 0.31 | 0.09 | -0.3 |
| MACRO | dolar (DXY) 3 ay düşüyor | yalnız long | 0.31 | 0.48 | 0.9 |
| MEANREV | 4 gün seri sonrası ters (5g) | yalnız long | 0.30 | 0.35 | 0.7 |
| MACRO | S&P 500 > SMA200 | çift yön | 0.30 | 0.42 | 0.7 |
| TREND | fiyat > SMA100 | çift yön | 0.28 | -0.43 | -1.9 |
| TREND | SMA 10/30 kesişimi | yalnız long | 0.28 | 0.06 | -1.3 |
| TREND | yavaş MACD 28/36/20 (ATVS yönü) | çift yön | 0.28 | -0.31 | -1.1 |
| COT | COT spekülatör 4 hafta artıyor → aynı yön | yalnız long | 0.28 | 0.33 | 0.1 |
| MACRO | Şanghay endeksi 3 ay yükseliyor | yalnız long | 0.27 | 0.07 | -1.2 |
| TREND | momentum 63g (ADX>20 iken) | yalnız short | 0.27 | -0.19 | -0.1 |
| MACRO | AUD 3 ay yükseliyor | çift yön | 0.26 | 0.04 | -0.0 |
| TREND | momentum 63g (ADX>20 iken) | çift yön | 0.26 | -0.12 | -0.8 |
| TREND | momentum 189g | yalnız long | 0.26 | 0.32 | -0.1 |
| TREND | fiyat > SMA150 | çift yön | 0.25 | -0.26 | -1.4 |
| MACRO | Çin hisseleri (FXI) 3 ay yükseliyor | yalnız long | 0.25 | 0.18 | -0.5 |
| MACRO | Çin öncü göstergesi yükseliyor | yalnız short | 0.24 | 0.02 | 1.0 |
| MEANREV | RSI(2) 20/80 dönüş | yalnız long | 0.24 | 0.16 | -0.4 |
| MEANREV | RSI(2) 5/95 dönüş | yalnız long | 0.24 | -0.07 | -0.7 |
| COT | COT spekülatör aşırı uç → ters | çift yön | 0.23 | -0.40 | -0.9 |
| TREND | MACD 12/26/9 | yalnız long | 0.22 | 0.10 | -0.8 |
| TREND | momentum topluluğu 1-3-6-12 ay | yalnız short | 0.22 | -0.53 | -1.2 |
| BREAKOUT | sıkışma kırılımı (20g tut) | yalnız long | 0.21 | 0.16 | -0.2 |
| MACRO | altın/gümüş oranı düşüyor (risk iştahı) | çift yön | 0.21 | -0.42 | -1.4 |
| TREND | fiyat > SMA50 | yalnız long | 0.20 | -0.12 | -2.3 |
| TREND | fiyat > SMA200 | çift yön | 0.20 | -0.13 | -1.0 |
| TREND | SMA 5/20 kesişimi | yalnız long | 0.20 | -0.24 | -2.8 |
| MACRO | bakır/altın oranı > SMA200 | yalnız long | 0.20 | -0.16 | -1.7 |
| TREND | MACD sıfır çizgisi | yalnız long | 0.20 | -0.01 | -1.8 |
| MACRO | madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız short | 0.19 | -0.02 | 1.2 |
| MACRO | AUD 3 ay yükseliyor | yalnız short | 0.19 | -0.33 | -0.2 |
| MACRO | AUD 3 ay yükseliyor | yalnız long | 0.18 | 0.35 | 0.2 |
| MEANREV | 3 gün seri sonrası ters (5g) | yalnız long | 0.18 | 0.29 | 0.1 |
| TREND | EMA50 eğimi | çift yön | 0.18 | -0.59 | -2.4 |
| MACRO | yuan güçleniyor (USD/CNY 3 ay düşüş) | yalnız long | 0.17 | 0.41 | 0.5 |
| MEANREV | RSI(2) 10/90 dönüş | yalnız long | 0.17 | 0.16 | -0.0 |
| MEANREV | 5 gün seri sonrası ters (5g) | yalnız long | 0.17 | 0.21 | 0.4 |
| BREAKOUT | ATR genişleme 1.0x (10g tut) | yalnız long | 0.17 | 0.21 | -0.6 |
| MACRO | bakır/altın oranı > SMA50 | yalnız long | 0.16 | -0.03 | -1.5 |
| TREND | Donchian 20 kırılımı | yalnız long | 0.16 | -0.12 | -1.8 |
| TREND | momentum 21g | yalnız long | 0.15 | -0.12 | -2.2 |
| TREND | SMA 50/100 kesişimi | çift yön | 0.15 | 0.04 | -0.4 |
| TREND | SMA 100/200 kesişimi | çift yön | 0.14 | -0.27 | -1.6 |
| ML | makine öğrenmesi (yıllık ileri yürüyen) | yalnız short | 0.14 | -0.19 | 0.6 |
| MACRO | Çin hisseleri (FXI) 3 ay yükseliyor | çift yön | 0.14 | -0.21 | -0.7 |
| MACRO | VIX < 20 | çift yön | 0.13 | -0.08 | -0.6 |
| TREND | fiyat > SMA250 | çift yön | 0.13 | 0.01 | -0.6 |
| TREND | momentum 63g | yalnız short | 0.12 | -0.73 | -1.9 |
| MACRO | bakır/altın oranı > SMA100 | çift yön | 0.12 | -0.60 | -1.9 |
| TREND | momentum 63g (ADX>20 iken) | yalnız long | 0.11 | -0.02 | -1.1 |
| MACRO | geniş dolar endeksi 3 ay düşüyor | yalnız long | 0.10 | 0.36 | 0.3 |
| MACRO | getiri eğrisi 3 ay dikleşiyor | yalnız long | 0.10 | 0.70 | 1.8 |
| TREND | SMA 50/200 kesişimi | çift yön | 0.10 | 0.00 | -0.6 |
| TREND | Donchian 100 kırılımı | yalnız short | 0.10 | -0.16 | 0.1 |
| MACRO | dolar (DXY) 3 ay düşüyor | çift yön | 0.09 | 0.14 | 0.7 |
| MACRO | ABD öncü göstergesi yükseliyor | yalnız short | 0.09 | -0.15 | 0.3 |
| TREND | SMA 10/30 kesişimi | çift yön | 0.09 | -0.36 | -1.5 |
| MACRO | petrol 3 ay yükseliyor | yalnız short | 0.09 | -0.86 | -2.4 |
| MEANREV | 5 gün seri sonrası ters (5g) | çift yön | 0.07 | -0.28 | -0.8 |
| MACRO | geniş dolar endeksi 3 ay düşüyor | çift yön | 0.06 | 0.04 | 0.1 |
| MACRO | finansal koşullar gevşiyor (NFCI 3 ay) | yalnız short | 0.06 | -0.05 | 0.9 |
| MACRO | Şanghay endeksi 3 ay yükseliyor | çift yön | 0.05 | -0.34 | -1.3 |
| TREND | Donchian 200 kırılımı | yalnız short | 0.05 | -0.28 | -0.4 |
| MACRO | reel faiz 3 ay düşüyor | yalnız short | 0.05 | -0.75 | -2.1 |
| TREND | SMA 20/100 kesişimi | yalnız short | 0.04 | -0.49 | -1.0 |
| MACRO | enflasyon beklentisi 3 ay yükseliyor | yalnız short | 0.04 | -0.49 | -1.0 |
| MEANREV | 4 gün seri sonrası ters (5g) | çift yön | 0.04 | 0.04 | 0.2 |
| TREND | SMA 20/50 kesişimi | yalnız short | 0.04 | -0.41 | -0.7 |
| MEANREV | 5g z-skoru ±1.5 dönüş (5g tut) | yalnız long | 0.04 | 0.13 | -0.1 |
| COT | COT spekülatör 4 hafta artıyor → aynı yön | çift yön | 0.04 | 0.04 | -0.1 |
| TREND | SMA 10/50 kesişimi | yalnız short | 0.03 | -0.54 | -1.2 |
| TREND | momentum 189g | çift yön | 0.02 | 0.08 | -0.3 |
| TREND | EMA20 eğimi | yalnız long | 0.02 | -0.27 | -3.0 |
| COT | COT fon (managed money) aşırı uç → ters | yalnız long | 0.02 | 0.11 | 0.1 |
| BREAKOUT | ATR genişleme 1.0x (10g tut) | çift yön | 0.01 | -0.03 | -0.6 |
| MACRO | sanayi üretimi ivmeleniyor | çift yön | 0.01 | -0.10 | -0.2 |
| MEANREV | IBS 0.2/0.8 (1g) | yalnız long | 0.01 | 0.41 | 0.8 |
| BREAKOUT | ATR genişleme 2.0x (10g tut) | yalnız short | 0.01 | -0.24 | -0.3 |
| TREND | Donchian 55 kırılımı | yalnız short | 0.01 | -0.70 | -1.8 |
| TREND | EMA100 eğimi | yalnız short | 0.01 | -0.58 | -1.3 |
| MACRO | yuan güçleniyor (USD/CNY 3 ay düşüş) | çift yön | 0.01 | 0.19 | 0.3 |
| BREAKOUT | ATR genişleme 2.0x (10g tut) | çift yön | 0.00 | -0.30 | -1.0 |
| COT | COT fon (managed money) aşırı uç → ters | çift yön | 0.00 | -0.44 | -0.9 |
| TREND | MACD 12/26/9 | çift yön | 0.00 | -0.33 | -1.0 |
| ATVS | ATVS X kuralı | yalnız short | 0.00 | 0.00 | 0.0 |
| SEASONAL | ay dönümü (son 2 + ilk 3 gün) | yalnız short | 0.00 | 0.00 | 0.0 |
| TREND | Donchian 20 kırılımı | çift yön | -0.00 | -0.48 | -1.9 |
| BREAKOUT | ATR genişleme 2.0x (10g tut) | yalnız long | -0.00 | -0.19 | -1.2 |
| MEANREV | RSI(2) 10/90 dönüş | çift yön | -0.01 | -0.07 | -0.1 |
| MACRO | geniş dolar endeksi 3 ay düşüyor | yalnız short | -0.01 | -0.31 | -0.1 |
| TREND | momentum 126g | yalnız short | -0.01 | -0.33 | -0.4 |
| TREND | momentum 252g | yalnız short | -0.01 | -0.24 | -0.1 |
| TREND | momentum 42g | yalnız short | -0.01 | -0.73 | -1.9 |
| TREND | momentum 10g | yalnız long | -0.01 | -0.25 | -2.7 |
| COT | COT fon (managed money) aşırı uç → ters | yalnız short | -0.02 | -0.51 | -1.1 |
| TREND | Donchian 10 kırılımı | yalnız long | -0.03 | -0.30 | -2.5 |
| TREND | fiyat > SMA100 | yalnız short | -0.03 | -0.78 | -2.1 |
| ATVS | ATVS EMA kuralı | yalnız long | -0.03 | 0.07 | -0.6 |
| SEASONAL | ay mevsimselliği (ileri yürüyen) | yalnız long | -0.03 | 0.27 | -0.0 |
| BREAKOUT | ATR genişleme 1.5x (10g tut) | yalnız long | -0.03 | -0.02 | -1.1 |
| TREND | MACD sıfır çizgisi | çift yön | -0.03 | -0.47 | -2.0 |
| TREND | SMA 5/20 kesişimi | çift yön | -0.03 | -0.84 | -3.0 |
| TREND | yavaş MACD 28/36/20 (ATVS yönü) | yalnız short | -0.03 | -0.59 | -1.3 |
| MACRO | S&P 500 > SMA200 | yalnız short | -0.03 | -0.01 | 0.7 |
| TREND | fiyat > SMA50 | çift yön | -0.04 | -0.64 | -2.4 |
| SEASONAL | ay dönümü (son 2 + ilk 3 gün) | çift yön | -0.04 | -0.10 | -0.9 |
| SEASONAL | ay dönümü (son 2 + ilk 3 gün) | yalnız long | -0.04 | -0.10 | -0.9 |
| TREND | fiyat > SMA20 | yalnız long | -0.05 | -0.26 | -2.8 |
| MACRO | Çin hisseleri (FXI) 3 ay yükseliyor | yalnız short | -0.05 | -0.49 | -0.9 |
| TREND | fiyat > SMA150 | yalnız short | -0.06 | -0.64 | -1.6 |
| MEANREV | RSI(2) 20/80 dönüş | çift yön | -0.06 | -0.14 | -0.6 |
| MEANREV | 5 gün seri sonrası ters (5g) | yalnız short | -0.08 | -0.57 | -1.5 |
| TREND | momentum 21g | çift yön | -0.08 | -0.65 | -2.3 |
| MACRO | altın/gümüş oranı düşüyor (risk iştahı) | yalnız short | -0.09 | -0.66 | -1.6 |
| MEANREV | IBS 0.2/0.8 (1g) | çift yön | -0.10 | 0.27 | 1.1 |
| MACRO | bakır/altın oranı > SMA200 | çift yön | -0.10 | -0.69 | -2.0 |
| TREND | EMA50 eğimi | yalnız short | -0.10 | -0.92 | -2.6 |
| MEANREV | 3 gün seri sonrası ters (5g) | çift yön | -0.10 | 0.04 | -0.1 |
| MACRO | bakır/altın oranı > SMA50 | çift yön | -0.11 | -0.52 | -1.7 |
| TREND | fiyat > SMA200 | yalnız short | -0.11 | -0.54 | -1.2 |
| ATVS | ATVS X kuralı | yalnız long | -0.11 | -0.03 | -0.5 |
| ATVS | ATVS X kuralı | çift yön | -0.11 | -0.03 | -0.5 |
| MACRO | VIX < 20 | yalnız short | -0.12 | -0.44 | -0.7 |
| TREND | SMA 50/100 kesişimi | yalnız short | -0.12 | -0.37 | -0.5 |
| MEANREV | 5g z-skoru ±2.0 dönüş (5g tut) | yalnız long | -0.13 | -0.05 | -0.5 |
| BREAKOUT | ATR genişleme 1.5x (10g tut) | çift yön | -0.13 | -0.29 | -1.3 |
| MEANREV | IBS 0.2/0.8 (1g) | yalnız short | -0.14 | 0.03 | 1.1 |
| MACRO | bakır/altın oranı > SMA100 | yalnız short | -0.14 | -0.75 | -2.1 |
| MEANREV | Bollinger 2.0σ dönüş | yalnız long | -0.15 | 0.63 | 1.6 |
| BREAKOUT | sıkışma kırılımı (20g tut) | çift yön | -0.15 | -0.18 | -0.9 |
| TREND | SMA 10/30 kesişimi | yalnız short | -0.15 | -0.67 | -1.7 |
| TREND | SMA 100/200 kesişimi | yalnız short | -0.15 | -0.70 | -1.8 |
| MACRO | getiri eğrisi 3 ay dikleşiyor | çift yön | -0.16 | 0.47 | 1.6 |
| MEANREV | RSI(14) 30/70 dönüş | yalnız short | -0.16 | -0.02 | 0.8 |
| MACRO | dolar (DXY) 3 ay düşüyor | yalnız short | -0.16 | -0.20 | 0.6 |
| MEANREV | RSI(2) 5/95 dönüş | çift yön | -0.16 | -0.11 | -0.3 |
| TREND | Donchian 20 kırılımı | yalnız short | -0.16 | -0.66 | -1.6 |
| SEASONAL | ay mevsimselliği (ileri yürüyen) | çift yön | -0.17 | 0.07 | -0.1 |
| TREND | fiyat > SMA250 | yalnız short | -0.17 | -0.42 | -0.8 |
| BREAKOUT | ATR genişleme 1.5x (10g tut) | yalnız short | -0.17 | -0.47 | -1.0 |
| COT | COT spekülatör 4 hafta artıyor → aynı yön | yalnız short | -0.17 | -0.33 | -0.3 |
| COT | COT spekülatör aşırı uç → ters | yalnız short | -0.18 | -0.32 | -0.5 |
| ATVS | ATVS EMA kuralı | çift yön | -0.18 | -0.34 | -1.4 |
| TREND | SMA 50/200 kesişimi | yalnız short | -0.18 | -0.42 | -0.7 |
| MEANREV | Bollinger 2.5σ dönüş | yalnız long | -0.18 | 0.45 | 1.0 |
| MACRO | Şanghay endeksi 3 ay yükseliyor | yalnız short | -0.18 | -0.63 | -1.5 |
| MEANREV | RSI(2) 10/90 dönüş | yalnız short | -0.19 | -0.24 | -0.2 |
| MEANREV | 5g z-skoru ±1.5 dönüş (5g tut) | çift yön | -0.20 | 0.15 | 0.5 |
| SEASONAL | haftanın günü (ileri yürüyen) | yalnız long | -0.20 | -0.15 | -1.2 |
| SEASONAL | ay mevsimselliği (ileri yürüyen) | yalnız short | -0.21 | -0.24 | -0.1 |
| TREND | MACD 12/26/9 | yalnız short | -0.22 | -0.55 | -1.1 |
| MACRO | sanayi üretimi ivmeleniyor | yalnız short | -0.23 | -0.39 | -0.4 |
| TREND | SMA 5/20 kesişimi | yalnız short | -0.23 | -1.04 | -3.1 |
| TREND | MACD sıfır çizgisi | yalnız short | -0.23 | -0.79 | -2.1 |
| ATVS | ATVS EMA kuralı | yalnız short | -0.24 | -0.70 | -1.9 |
| TREND | momentum 189g | yalnız short | -0.24 | -0.34 | -0.4 |
| MEANREV | 4 gün seri sonrası ters (5g) | yalnız short | -0.25 | -0.26 | -0.4 |
| TREND | fiyat > SMA50 | yalnız short | -0.25 | -0.91 | -2.6 |
| MACRO | yuan güçleniyor (USD/CNY 3 ay düşüş) | yalnız short | -0.25 | -0.22 | 0.1 |
| TREND | momentum 21g | yalnız short | -0.26 | -0.89 | -2.5 |
| BREAKOUT | ATR genişleme 1.0x (10g tut) | yalnız short | -0.26 | -0.38 | -0.6 |
| TREND | EMA20 eğimi | çift yön | -0.28 | -0.88 | -3.1 |
| MACRO | bakır/altın oranı > SMA50 | yalnız short | -0.29 | -0.73 | -1.9 |
| MACRO | bakır/altın oranı > SMA200 | yalnız short | -0.31 | -0.77 | -2.2 |
| MEANREV | Bollinger 2.0σ dönüş | yalnız short | -0.31 | -0.07 | 0.8 |
| MEANREV | Bollinger 2.0σ dönüş | çift yön | -0.32 | 0.28 | 1.3 |
| MACRO | getiri eğrisi 3 ay dikleşiyor | yalnız short | -0.32 | -0.02 | 1.3 |
| MEANREV | RSI(14) 30/70 dönüş | yalnız long | -0.33 | -0.02 | -0.5 |
| MEANREV | 5g z-skoru ±1.5 dönüş (5g tut) | yalnız short | -0.34 | 0.09 | 0.9 |
| TREND | Donchian 10 kırılımı | çift yön | -0.34 | -0.78 | -2.8 |
| MEANREV | RSI(2) 20/80 dönüş | yalnız short | -0.34 | -0.38 | -0.6 |
| TREND | momentum 10g | çift yön | -0.34 | -0.84 | -2.9 |
| TREND | momentum 5g | yalnız long | -0.35 | -0.13 | -1.8 |
| MEANREV | RSI(14) 30/70 dönüş | çift yön | -0.35 | -0.03 | 0.3 |
| MEANREV | 5g z-skoru ±2.0 dönüş (5g tut) | çift yön | -0.36 | 0.08 | 0.3 |
| TREND | fiyat > SMA20 | çift yön | -0.36 | -0.86 | -3.0 |
| MEANREV | 3 gün seri sonrası ters (5g) | yalnız short | -0.36 | -0.29 | -0.3 |
| MEANREV | Bollinger 2.5σ dönüş | yalnız short | -0.37 | 0.07 | 1.1 |
| MEANREV | Bollinger 2.5σ dönüş | çift yön | -0.37 | 0.30 | 1.4 |
| TREND | EMA20 eğimi | yalnız short | -0.40 | -1.08 | -3.3 |
| MEANREV | 5g z-skoru ±2.0 dönüş (5g tut) | yalnız short | -0.43 | 0.14 | 0.8 |
| BREAKOUT | sıkışma kırılımı (20g tut) | yalnız short | -0.44 | -0.55 | -1.3 |
| TREND | fiyat > SMA20 | yalnız short | -0.45 | -1.03 | -3.1 |
| TREND | Donchian 10 kırılımı | yalnız short | -0.45 | -0.87 | -2.4 |
| TREND | momentum 10g | yalnız short | -0.46 | -1.00 | -3.0 |
| SEASONAL | haftanın günü (ileri yürüyen) | çift yön | -0.48 | -0.97 | -3.0 |
| SEASONAL | haftanın günü (ileri yürüyen) | yalnız short | -0.48 | -1.21 | -3.6 |
| MEANREV | RSI(2) 5/95 dönüş | yalnız short | -0.48 | -0.09 | 0.2 |
| TREND | momentum 5g | yalnız short | -0.74 | -0.78 | -2.2 |
| TREND | momentum 5g | çift yön | -0.78 | -0.66 | -2.0 |

_Eğitimde 6 yıldan kısa verisi olduğu için seçime girmeyenler: kredi spreadi 3 ay daralıyor_

## 5) Portföye katkı (risk paritesi, %10 oynaklık hedefi ×2)

| Portföy | Eğitim yıllık / DD / Sharpe | **Sınav yıllık / DD / Sharpe** |
|---|---|---|
| Mevcut risk paritesi (S&P, Nasdaq, altın, gümüş) | %+8.1 / %43 / 0.47 | **%+22.3 / %31 / 1.07** |
| Risk paritesi + bakır (5. varlık, zamanlamasız) | %+7.5 / %45 / 0.45 | **%+20.9 / %30 / 1.02** |
| Risk paritesi + bakır, seçilen kuralla zamanlanmış (madenciler bakırı öncülüyor (FCX−bakır 1 ay), yalnız long) | %+9.5 / %42 / 0.57 | **%+22.6 / %28 / 1.17** |
| Risk paritesi + bakır, seçilen kuralla zamanlanmış (Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15, çift yön) | %+9.6 / %37 / 0.60 | **%+21.8 / %25 / 1.18** |

_Botun bugünkü risk paritesiyle aynı yapı (VIX katmanı hariç); bakırın katkısını göreli olarak ölçer._

## 6) Yıllar

| Yıl | Bakır al-tut | Seçilen: Donchian 200 kırılımı + madenciler bakırı öncülüyor (FCX−bakır 1 ay) · oynaklık hedefi %15 (çift yön) | Seçilen tek: madenciler bakırı öncülüyor (FCX−bakır 1 ay) (yalnız long) |
|---|---|---|---|
| 2000 | %-9 | %+0 | %-3 |
| 2001 | %-23 | %+6 | %-19 |
| 2002 | %+6 | %-0 | %+6 |
| 2003 | %+47 | %+32 | %+56 |
| 2004 | %+37 | %+8 | %+11 |
| 2005 | %+38 | %+22 | %+43 |
| 2006 | %+28 | %+14 | %+14 |
| 2007 | %+4 | %-4 | %+4 |
| 2008 | %-54 | %+14 | %-8 |
| 2009 | %+128 | %+7 | %+73 |
| 2010 | %+28 | %+18 | %+40 |
| 2011 | %-23 | %+2 | %+6 |
| 2012 | %+3 | %+1 | %+9 |
| 2013 | %-11 | %+8 | %+1 |
| 2014 | %-20 | %+3 | %-5 |
| 2015 | %-29 | %+21 | %-12 |
| 2016 | %+16 | %-6 | %+11 |
| 2017 | %+27 | %+14 | %+16 |
| 2018 | %-22 | %-6 | %-15 |
| 2019 | %+5 | %-12 | %+2 |
| 2020 | %+22 | %+19 | %+50 |
| 2021 | %+21 | %+0 | %-7 |
| 2022 | %-17 | %+12 | %+6 |
| 2023 | %-0 | %-1 | %+3 |
| 2024 | %+0 | %+6 | %+4 |
| 2025 | %+37 | %+36 | %+50 |
| 2026 | %+14 | %+3 | %+7 |

## 7) Bitget COPPERUSDT kontrolü

Kontrat: symbol=COPPERUSDT, baseCoin=COPPER, minTradeNum=0.1, sizeMultiplier=0.1, minTradeUSDT=5, maxLever=100, fundInterval=4, isRwa=YES, symbolStatus=normal
Son fiyat Bitget 6.576 / HG=F 6.564 → oran 1.002
Bitget günlük mum: 211 (2026-03-09'ten beri) · oran medyanı 1.01 (sapma %0.7) · günlük getiri korelasyonu 0.84
Fonlama: 540 gözlem · yıllık ortalama %+15.8 · 90. yüzdelik %+43.1

## 8) Saatlik keşif (son ~2 yıl; seçimde KULLANILMADI)

İlk 2/3'te en iyi saat (UTC) 16 → son 1/3'te o saatin ortalaması %+0.010 · saat profillerinin iki dönem arası korelasyonu 0.29
4 saatlik EMA20/50 trendi Sharpe: ilk 2/3 0.39, son 1/3 -1.26

