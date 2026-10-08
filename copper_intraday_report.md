# 🟠 Bakır gün içi laboratuvarı v15 — 1 saatlik ve 4 saatlik mumlar

_Veri: COMEX bakır (HG=F) saatlik, ~2,4 yıl. İlk 2/3 eğitim (seçim), son 1/3 mühürlü sınav (~9 ay). Maliyet %0,08/işlem; fonlama yalnızca 00/04/08/12/16/20 UTC anlarında açık olan pozisyondan kesilir (long öder, short alır). **Kısa örneklem: sınav sonuçları güçlü kanıt değildir; Deflated Sharpe (DSR) her satırda.**_

## 1h — 13,719 mum · eğitim 2025-12-18'e kadar · 583 deneme

Bakırı tutmak (sınav yıllık): fonlama %0.0: %+27.4 · fonlama %3.0: %+24.8 · fonlama %8.0: %+20.6 · fonlama %15.8: %+14.4
Sınavda pozitif Sharpe veren denemelerin oranı (fonlama %3): %9

**Eğitimin seçimi** (4 fonlama senaryosunun en kötüsüne göre): RSI(14) 30/70 dönüş + [günlük] bakır/altın oranı > SMA100 · yalnız short · DSR 0.00

| | %0.0 | %3.0 | %8.0 | %15.8 |
|---|---|---|---|---|
| eğitim Sharpe | 1.27 | 1.30 | 1.34 | 1.42 |
| **sınav Sharpe** | **-0.05** | **-0.04** | **-0.02** | **0.01** |
| sınav yıllık | %-1.0 | %-0.9 | %-0.7 | %-0.4 |

| Aile | Yön | Deneme | Eğitim Sharpe (%3) | **Sınav Sharpe (%3)** | Sınav Sharpe (%15,8) |
|---|---|---|---|---|---|
| İKİLİ | yalnız long | 108 | 0.16 | **-0.55** | -0.70 |
| İKİLİ | yalnız short | 48 | -0.03 | **-0.69** | -0.61 |
| TREND | yalnız long | 35 | -0.95 | **-0.74** | -0.95 |
| İKİLİ | çift yön | 90 | -0.01 | **-0.75** | -0.85 |
| BREAKOUT | yalnız long | 4 | -0.30 | **-0.83** | -0.98 |
| BREAKOUT | yalnız short | 4 | -0.29 | **-1.07** | -0.95 |
| BREAKOUT | çift yön | 4 | -0.39 | **-1.30** | -1.34 |
| TREND | çift yön | 35 | -1.93 | **-2.00** | -2.03 |
| TREND | yalnız short | 35 | -1.77 | **-2.24** | -2.04 |
| MEANREV | yalnız long | 12 | -2.50 | **-2.29** | -2.42 |
| SEANS | yalnız long | 6 | -3.76 | **-2.85** | -2.97 |
| MEANREV | yalnız short | 12 | -2.48 | **-2.98** | -2.85 |
| MEANREV | çift yön | 12 | -3.50 | **-3.73** | -3.72 |
| SEANS | çift yön | 6 | -4.34 | **-3.77** | -3.87 |
| BREAKOUT+FONLAMASIZ | yalnız short | 4 | -3.13 | **-4.07** | -3.94 |
| SEANS+FONLAMASIZ | yalnız short | 1 | -3.85 | **-4.31** | -4.17 |
| SAAT+FONLAMASIZ | yalnız long | 1 | -8.10 | **-4.34** | -4.49 |
| SEANS+FONLAMASIZ | yalnız long | 5 | -5.29 | **-4.92** | -5.09 |
| BREAKOUT+FONLAMASIZ | yalnız long | 4 | -4.25 | **-5.13** | -5.29 |
| SEANS+FONLAMASIZ | çift yön | 5 | -5.61 | **-5.29** | -5.43 |
| SEANS | yalnız short | 2 | -5.05 | **-5.32** | -5.26 |
| MEANREV+FONLAMASIZ | yalnız short | 12 | -5.87 | **-5.51** | -5.37 |
| MEANREV+FONLAMASIZ | yalnız long | 12 | -5.34 | **-5.77** | -5.91 |
| BREAKOUT+FONLAMASIZ | çift yön | 4 | -5.27 | **-6.53** | -6.56 |
| TREND+FONLAMASIZ | yalnız long | 35 | -7.32 | **-6.74** | -6.98 |
| SAAT+FONLAMASIZ | yalnız short | 1 | -10.47 | **-7.56** | -7.46 |
| SAAT | yalnız long | 1 | -9.62 | **-7.61** | -7.74 |
| TREND+FONLAMASIZ | yalnız short | 35 | -6.84 | **-7.88** | -7.65 |
| MEANREV+FONLAMASIZ | çift yön | 12 | -7.93 | **-7.91** | -7.90 |
| SAAT+FONLAMASIZ | çift yön | 1 | -13.10 | **-8.60** | -8.61 |
| SAAT | yalnız short | 1 | -10.73 | **-9.13** | -9.03 |
| TREND+FONLAMASIZ | çift yön | 35 | -10.05 | **-10.22** | -10.25 |
| SAAT | çift yön | 1 | -14.36 | **-11.86** | -11.87 |

| # | Strateji | Yön | Eğitim (en kötü) | DSR | Sınav Sharpe %0 / %3 / %8 / %15,8 | Sınav yıllık (%3) |
|---|---|---|---|---|---|---|
| 1 | RSI(14) 30/70 dönüş + [günlük] bakır/altın oranı > SMA100 | yalnız short | 1.27 | 0.00 | -0.05 / -0.04 / -0.02 / 0.01 | %-0.9 |
| 2 | sıkışma kırılımı (20g tut) + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız short | 1.21 | 0.00 | 0.26 / 0.28 / 0.31 / 0.37 | %+2.2 |
| 3 | RSI(14) 30/70 dönüş + [günlük] dolar (DXY) 3 ay düşüyor | yalnız short | 1.19 | 0.00 | -2.03 / -2.00 / -1.96 / -1.89 | %-18.4 |
| 4 | RSI(14) 30/70 dönüş + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 1.15 | 0.00 | -1.20 / -1.21 / -1.21 / -1.21 | %-11.5 |
| 5 | SMA 100/200 kesişimi + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız long | 1.13 | 0.00 | 0.33 / 0.29 / 0.23 / 0.14 | %+3.2 |
| 6 | RSI(14) 30/70 dönüş | yalnız short | 1.08 | 0.00 | -1.24 / -1.21 / -1.16 / -1.08 | %-16.6 |
| 7 | Donchian 100 kırılımı + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız long | 1.06 | 0.00 | 1.14 / 1.10 / 1.05 / 0.97 | %+14.1 |
| 8 | RSI(14) 30/70 dönüş + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız short | 1.00 | 0.00 | 0.22 / 0.24 / 0.27 / 0.31 | %+1.9 |
| 9 | SMA 50/200 kesişimi + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız long | 0.95 | 0.00 | 0.55 / 0.51 / 0.45 / 0.35 | %+6.6 |
| 10 | SMA 100/200 kesişimi + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.94 | 0.00 | -0.02 / -0.03 / -0.04 / -0.06 | %-2.3 |
| 11 | RSI(14) 30/70 dönüş + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız short | 0.89 | 0.00 | -1.40 / -1.37 / -1.33 / -1.26 | %-7.9 |
| 12 | SMA 50/200 kesişimi + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.85 | 0.00 | 0.26 / 0.26 / 0.25 / 0.23 | %+3.2 |
| 13 | SMA 50/100 kesişimi + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız long | 0.81 | 0.00 | 0.49 / 0.45 / 0.39 / 0.29 | %+5.6 |
| 14 | sıkışma kırılımı (20g tut) + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız short | 0.78 | 0.00 | -0.14 / -0.13 / -0.10 / -0.05 | %-1.2 |
| 15 | sıkışma kırılımı (20g tut) + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.74 | 0.00 | 0.29 / 0.29 / 0.29 / 0.29 | %+2.8 |
| 16 | momentum 252g + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız long | 0.70 | 0.00 | 0.17 / 0.13 / 0.05 / -0.07 | %+0.8 |
| 17 | SMA 50/100 kesişimi + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.70 | 0.00 | 0.31 / 0.30 / 0.30 / 0.29 | %+4.1 |
| 18 | ATR genişleme 2.0x (10g tut) + [günlük] dolar (DXY) 3 ay düşüyor | yalnız short | 0.68 | 0.00 | -1.10 / -1.08 / -1.05 / -1.01 | %-6.6 |
| 19 | SMA 100/200 kesişimi + [günlük] S&P 500 > SMA200 | çift yön | 0.68 | 0.00 | -0.56 / -0.60 / -0.68 / -0.79 | %-15.7 |
| 20 | ATR genişleme 2.0x (10g tut) + [günlük] dolar (DXY) 3 ay düşüyor | çift yön | 0.68 | 0.00 | -0.47 / -0.46 / -0.45 / -0.44 | %-4.3 |

## 4h — 3,718 mum · eğitim 2025-12-17'e kadar · 414 deneme

Bakırı tutmak (sınav yıllık): fonlama %0.0: %+27.0 · fonlama %3.0: %+24.3 · fonlama %8.0: %+20.0 · fonlama %15.8: %+13.5
Sınavda pozitif Sharpe veren denemelerin oranı (fonlama %3): %32

**Eğitimin seçimi** (4 fonlama senaryosunun en kötüsüne göre): 5g z-skoru ±1.5 dönüş (5g tut) + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) · yalnız long · DSR 0.11

| | %0.0 | %3.0 | %8.0 | %15.8 |
|---|---|---|---|---|
| eğitim Sharpe | 1.43 | 1.41 | 1.37 | 1.32 |
| **sınav Sharpe** | **0.85** | **0.83** | **0.79** | **0.73** |
| sınav yıllık | %+7.4 | %+7.2 | %+6.8 | %+6.3 |

| Aile | Yön | Deneme | Eğitim Sharpe (%3) | **Sınav Sharpe (%3)** | Sınav Sharpe (%15,8) |
|---|---|---|---|---|---|
| İKİLİ | yalnız long | 162 | 0.37 | **0.03** | -0.18 |
| MEANREV | yalnız long | 12 | -0.18 | **0.00** | -0.13 |
| İKİLİ | çift yön | 81 | 0.18 | **-0.17** | -0.31 |
| TREND | yalnız long | 35 | 0.08 | **-0.18** | -0.41 |
| İKİLİ | yalnız short | 18 | 0.14 | **-0.57** | -0.49 |
| MEANREV | çift yön | 12 | -0.54 | **-0.66** | -0.63 |
| MEANREV | yalnız short | 12 | -0.58 | **-0.84** | -0.70 |
| BREAKOUT | yalnız long | 4 | -0.72 | **-0.89** | -1.01 |
| TREND | çift yön | 35 | -0.65 | **-1.10** | -1.18 |
| BREAKOUT | yalnız short | 4 | -0.25 | **-1.39** | -1.25 |
| BREAKOUT | çift yön | 4 | -0.68 | **-1.54** | -1.55 |
| TREND | yalnız short | 35 | -1.04 | **-1.68** | -1.48 |

| # | Strateji | Yön | Eğitim (en kötü) | DSR | Sınav Sharpe %0 / %3 / %8 / %15,8 | Sınav yıllık (%3) |
|---|---|---|---|---|---|---|
| 1 | 5g z-skoru ±1.5 dönüş (5g tut) + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 1.32 | 0.11 | 0.85 / 0.83 / 0.79 / 0.73 | %+7.2 |
| 2 | momentum 189g + [günlük] S&P 500 > SMA200 | yalnız long | 1.19 | 0.08 | -0.18 / -0.24 / -0.35 / -0.51 | %-8.5 |
| 3 | Bollinger 2.0σ dönüş + [günlük] S&P 500 > SMA200 | çift yön | 1.05 | 0.06 | 0.98 / 0.94 / 0.87 / 0.77 | %+12.4 |
| 4 | Bollinger 2.0σ dönüş + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 1.05 | 0.06 | -0.27 / -0.28 / -0.29 / -0.32 | %-4.4 |
| 5 | momentum 189g + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 1.05 | 0.06 | -0.46 / -0.51 / -0.58 / -0.71 | %-12.7 |
| 6 | SMA 10/50 kesişimi + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız long | 1.05 | 0.06 | 0.72 / 0.68 / 0.61 / 0.50 | %+9.2 |
| 7 | Bollinger 2.0σ dönüş + [günlük] S&P 500 > SMA200 | yalnız long | 0.99 | 0.05 | 0.98 / 0.94 / 0.87 / 0.77 | %+12.2 |
| 8 | 5g z-skoru ±1.5 dönüş (5g tut) + [günlük] S&P 500 > SMA200 | çift yön | 0.98 | 0.05 | 1.08 / 1.05 / 1.00 / 0.93 | %+10.8 |
| 9 | 5g z-skoru ±1.5 dönüş (5g tut) + [günlük] S&P 500 > SMA200 | yalnız long | 0.95 | 0.04 | 1.04 / 1.01 / 0.96 / 0.88 | %+10.1 |
| 10 | momentum 126g + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | yalnız long | 0.94 | 0.04 | 1.58 / 1.53 / 1.44 / 1.30 | %+26.3 |
| 11 | momentum 189g + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.93 | 0.04 | 0.22 / 0.20 / 0.17 / 0.11 | %+2.0 |
| 12 | momentum 126g + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.92 | 0.04 | 0.26 / 0.22 / 0.15 / 0.04 | %+2.4 |
| 13 | yavaş MACD 28/36/20 (ATVS yönü) + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.89 | 0.04 | 1.32 / 1.32 / 1.32 / 1.32 | %+27.2 |
| 14 | momentum 189g + [günlük] S&P 500 > SMA200 | çift yön | 0.87 | 0.04 | -0.35 / -0.40 / -0.49 / -0.63 | %-12.6 |
| 15 | 5g z-skoru ±1.5 dönüş (5g tut) + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | çift yön | 0.85 | 0.04 | -0.59 / -0.60 / -0.61 / -0.62 | %-6.6 |
| 16 | SMA 20/100 kesişimi + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.85 | 0.03 | -0.21 / -0.25 / -0.32 / -0.43 | %-7.0 |
| 17 | SMA 20/50 kesişimi + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.85 | 0.03 | 0.52 / 0.51 / 0.50 / 0.48 | %+8.3 |
| 18 | momentum 63g (ADX>20 iken) + [günlük] madenciler bakırı öncülüyor (FCX−bakır 1 ay) | yalnız long | 0.84 | 0.03 | -0.53 / -0.56 / -0.62 / -0.70 | %-10.8 |
| 19 | SMA 100/200 kesişimi + [günlük] COT fon (managed money) 4 hafta artıyor → aynı yön | çift yön | 0.83 | 0.03 | 0.64 / 0.62 / 0.58 / 0.53 | %+11.8 |
| 20 | momentum 189g | yalnız long | 0.83 | 0.03 | -0.18 / -0.24 / -0.35 / -0.51 | %-8.5 |

