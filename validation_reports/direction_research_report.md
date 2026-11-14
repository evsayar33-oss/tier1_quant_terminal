# 🧭 Yön Araştırması (günlük veri, Hep AL'a göre zamanlama alfası)

_Üretim: 2026-11-14T15:31 UTC · test penceresi: son 10 yıl · ufuklar: [1, 5] gün_

Bir kural sadece şu üç koşulu sağlarsa **KANITLI** sayılır: zamanlama alfası t ≥ gerekli t (denenen her kural için Bonferroni düzeltmesi), 3 dönemin en az 2'sinde pozitif alfa, yön isabeti ≥ %50.

## SPX
Veri 2010-11-15 → 2026-11-13 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +14.5 | +1.48 | %61.2 | +23.2 / +5.8 / +14.3 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | -0.5 | -0.34 | %54.0 | +1.7 / -3.2 / -0.0 | — |
| Momentum 60 gün | 1g | -1.6 | -0.44 | %53.9 | +4.2 / -7.3 / -1.6 | — |
| 200 gün ortalama (al/sat) | 5g | -9.9 | -0.62 | %57.3 | +11.1 / -27.8 / -13.0 | — |
| 200 gün ortalama (al/bekle) | 5g | -5.0 | -0.62 | %60.9 | +5.5 / -13.9 / -6.5 | — |
| Momentum 20 gün | 1g | -2.7 | -0.74 | %52.3 | +4.5 / -7.3 / -5.4 | — |
| 200 gün ortalama (al/sat) | 1g | -3.1 | -0.90 | %54.3 | +0.0 / -6.3 / -2.9 | — |
| 200 gün ortalama (al/bekle) | 1g | -1.5 | -0.90 | %55.2 | +0.0 / -3.1 / -1.4 | — |

## NQ
Veri 2010-11-15 → 2026-11-13 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +12.2 | +1.14 | %61.6 | +16.4 / +1.7 / +18.7 | — |
| 200 gün ortalama (al/sat) | 1g | -2.1 | -0.55 | %56.2 | -1.4 / -1.1 / -3.8 | — |
| 200 gün ortalama (al/bekle) | 1g | -1.1 | -0.55 | %57.6 | -0.7 / -0.6 / -1.9 | — |
| 200 gün ortalama (al/sat) | 5g | -13.8 | -0.85 | %57.9 | -14.1 / -11.4 / -15.7 | — |
| 200 gün ortalama (al/bekle) | 5g | -6.9 | -0.85 | %61.5 | -7.1 / -5.7 / -7.8 | — |
| Momentum 20 gün | 1g | -4.0 | -0.87 | %52.9 | +0.5 / -4.8 / -7.6 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | -1.7 | -1.03 | %55.8 | +0.2 / -4.9 / -0.3 | — |
| Momentum 120 gün | 5g | -17.1 | -1.06 | %57.5 | -12.6 / -17.4 / -21.5 | — |

## XAU
Veri 2010-11-15 → 2026-11-13 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +4.6 | +0.60 | %56.3 | +11.3 / -7.9 / +10.5 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | +0.2 | +0.12 | %53.3 | +2.6 / -1.6 / -0.5 | — |
| Momentum 120 gün | 1g | -0.6 | -0.30 | %53.2 | -1.1 / -2.5 / +1.8 | — |
| Momentum 120 gün | 5g | -5.1 | -0.45 | %51.9 | -7.4 / -17.6 / +9.8 | — |
| Momentum 60 gün | 1g | -1.2 | -0.52 | %51.8 | -1.1 / -1.4 / -1.0 | — |
| Momentum 60 gün | 5g | -7.0 | -0.61 | %51.2 | -9.9 / -4.7 / -6.5 | — |
| 200 gün ortalama (al/sat) | 1g | -2.2 | -1.06 | %52.6 | -1.8 / -6.3 / +1.5 | — |
| 200 gün ortalama (al/bekle) | 1g | -1.1 | -1.06 | %54.5 | -0.9 / -3.1 / +0.8 | — |

## XAG
Veri 2010-11-15 → 2026-11-13 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 1g | +1.9 | +0.81 | %52.4 | +3.1 / -1.9 / +4.6 | — |
| Hep AL + stres anında 5 gün geri dönüş | 5g | -0.8 | -0.06 | %52.4 | +19.3 / +5.7 / -27.5 | — |
| Momentum 120 gün | 1g | -2.2 | -0.47 | %51.0 | +7.7 / -17.0 / +2.7 | — |
| Momentum 250 gün | 1g | -2.3 | -0.60 | %52.3 | +5.8 / -13.5 / +0.8 | — |
| Momentum 120 gün | 5g | -18.5 | -0.75 | %49.4 | +17.9 / -61.4 / -12.2 | — |
| Momentum 250 gün | 5g | -16.8 | -0.81 | %51.6 | +9.0 / -54.8 / -4.6 | — |
| 200 gün ortalama (al/sat) | 1g | -4.1 | -0.90 | %50.9 | +0.2 / -11.5 / -1.1 | — |
| 200 gün ortalama (al/bekle) | 1g | -2.1 | -0.90 | %52.7 | +0.1 / -5.8 / -0.5 | — |

## BTC
Veri 2014-09-17 → 2026-11-14 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 20 gün | 1g | +7.1 | +0.84 | %51.9 | +22.3 / -3.1 / +1.9 | — |
| Momentum 60 gün | 1g | +6.4 | +0.84 | %52.2 | +19.2 / -0.9 / +0.8 | — |
| CTA momentum topluluğu | 1g | +5.1 | +0.81 | %52.4 | +16.1 / -0.3 / -0.4 | — |
| Momentum 250 gün | 1g | +3.6 | +0.58 | %52.0 | +8.7 / +2.3 / -0.2 | — |
| Momentum 120 gün | 1g | +3.4 | +0.48 | %51.5 | +14.0 / +0.3 / -4.0 | — |
| Momentum 20 gün | 5g | +16.0 | +0.42 | %52.0 | +63.6 / -24.6 / +8.7 | — |
| Momentum 250 gün | 5g | +11.0 | +0.36 | %54.9 | +27.1 / -1.0 / +6.8 | — |
| CTA momentum topluluğu | 5g | +5.8 | +0.19 | %52.7 | +43.0 / -14.9 / -10.9 | — |

## ETH
Veri 2017-11-09 → 2026-11-14 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 60 gün | 1g | +6.8 | +0.67 | %51.5 | -9.1 / +4.6 / +25.1 | — |
| Momentum 120 gün | 1g | +1.2 | +0.12 | %51.8 | -16.4 / +17.2 / +2.8 | — |
| CTA momentum topluluğu | 1g | +0.7 | +0.08 | %51.4 | -13.0 / +7.5 / +7.7 | — |
| Momentum 120 gün | 5g | +3.6 | +0.07 | %51.7 | -42.3 / +82.8 / -29.8 | — |
| Momentum 20 gün | 1g | +0.5 | +0.04 | %49.7 | -1.0 / -7.8 / +10.3 | — |
| 200 gün ortalama (al/sat) | 1g | +0.5 | +0.04 | %51.7 | -23.2 / +13.7 / +10.8 | — |
| 200 gün ortalama (al/bekle) | 1g | +0.2 | +0.04 | %53.0 | -11.6 / +6.8 / +5.4 | — |
| Momentum 60 gün | 5g | -6.3 | -0.12 | %51.4 | -89.0 / -49.1 / +119.3 | — |
