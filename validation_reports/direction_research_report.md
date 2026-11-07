# 🧭 Yön Araştırması (günlük veri, Hep AL'a göre zamanlama alfası)

_Üretim: 2026-11-07T14:00 UTC · test penceresi: son 10 yıl · ufuklar: [1, 5] gün_

Bir kural sadece şu üç koşulu sağlarsa **KANITLI** sayılır: zamanlama alfası t ≥ gerekli t (denenen her kural için Bonferroni düzeltmesi), 3 dönemin en az 2'sinde pozitif alfa, yön isabeti ≥ %50.

## SPX
Veri 2010-11-08 → 2026-11-06 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 1g | -0.5 | -0.34 | %54.0 | +1.7 / -3.2 / -0.0 | — |
| Momentum 60 gün | 1g | -1.5 | -0.42 | %53.9 | +3.3 / -6.8 / -1.0 | — |
| Momentum 20 gün | 1g | -2.6 | -0.69 | %52.3 | +3.9 / -6.8 / -4.8 | — |
| Hep AL + stres anında 5 gün geri dönüş | 5g | -4.7 | -0.77 | %61.4 | +7.3 / -14.8 / -6.5 | — |
| Momentum 250 gün | 5g | -9.3 | -0.83 | %60.4 | -4.1 / -16.1 / -7.8 | — |
| 200 gün ortalama (al/sat) | 5g | -12.2 | -0.84 | %58.1 | +2.2 / -18.5 / -20.2 | — |
| 200 gün ortalama (al/bekle) | 5g | -6.1 | -0.84 | %62.1 | +1.1 / -9.3 / -10.1 | — |
| 200 gün ortalama (al/sat) | 1g | -3.1 | -0.90 | %54.4 | -0.5 / -5.8 / -2.9 | — |

## NQ
Veri 2010-11-08 → 2026-11-06 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| 200 gün ortalama (al/sat) | 5g | -4.0 | -0.24 | %58.9 | -4.0 / +8.2 / -16.2 | — |
| 200 gün ortalama (al/bekle) | 5g | -2.0 | -0.24 | %62.1 | -2.0 / +4.1 / -8.1 | — |
| 200 gün ortalama (al/sat) | 1g | -1.7 | -0.45 | %56.2 | -1.3 / -1.2 / -2.6 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.8 | -0.45 | %57.6 | -0.7 / -0.6 / -1.3 | — |
| Momentum 120 gün | 5g | -9.2 | -0.56 | %58.7 | -10.0 / -0.0 / -17.5 | — |
| Momentum 20 gün | 1g | -3.7 | -0.81 | %52.8 | +0.5 / -4.8 / -6.8 | — |
| Momentum 250 gün | 5g | -10.9 | -0.81 | %58.7 | -7.4 / -16.2 / -9.0 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | -1.7 | -1.03 | %55.9 | +0.2 / -4.9 / -0.3 | — |

## XAU
Veri 2010-11-08 → 2026-11-06 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 1g | +0.2 | +0.17 | %53.3 | +2.6 / -1.6 / -0.3 | — |
| Hep AL + stres anında 5 gün geri dönüş | 5g | +0.1 | +0.01 | %54.8 | +24.2 / -6.6 / -17.6 | — |
| Momentum 60 gün | 5g | -3.3 | -0.29 | %56.4 | +1.4 / +6.5 / -17.9 | — |
| Momentum 120 gün | 1g | -1.0 | -0.48 | %53.1 | -1.2 / -2.4 / +0.6 | — |
| Momentum 60 gün | 1g | -1.2 | -0.53 | %51.9 | +0.0 / -1.2 / -2.3 | — |
| Momentum 120 gün | 5g | -5.7 | -0.54 | %56.6 | -5.8 / -9.4 / -1.9 | — |
| 200 gün ortalama (al/sat) | 1g | -2.2 | -1.08 | %52.7 | -0.1 / -6.9 / +0.4 | — |
| 200 gün ortalama (al/bekle) | 1g | -1.1 | -1.08 | %54.5 | -0.1 / -3.5 / +0.2 | — |

## XAG
Veri 2010-11-08 → 2026-11-06 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +22.3 | +1.33 | %53.6 | +52.5 / -11.7 / +25.8 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | +2.0 | +0.86 | %52.5 | +3.1 / -1.9 / +4.9 | — |
| Momentum 120 gün | 1g | -2.6 | -0.56 | %51.0 | +0.4 / -9.7 / +1.4 | — |
| Momentum 250 gün | 1g | -2.8 | -0.72 | %52.2 | +0.8 / -8.5 / -0.6 | — |
| Momentum 120 gün | 5g | -18.7 | -0.75 | %50.9 | -2.8 / -46.0 / -7.4 | — |
| 200 gün ortalama (al/sat) | 1g | -4.6 | -1.00 | %50.9 | -7.2 / -4.2 / -2.4 | — |
| 200 gün ortalama (al/bekle) | 1g | -2.3 | -1.00 | %52.8 | -3.6 / -2.1 / -1.2 | — |
| Momentum 20 gün | 1g | -5.3 | -1.01 | %48.9 | -4.9 / -2.8 / -8.4 | — |

## BTC
Veri 2014-09-17 → 2026-11-07 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 20 gün | 1g | +6.2 | +0.74 | %51.9 | +14.8 / +4.4 / -0.5 | — |
| CTA momentum topluluğu | 1g | +4.7 | +0.74 | %52.4 | +8.6 / +7.2 / -1.6 | — |
| Momentum 60 gün | 1g | +5.5 | +0.73 | %52.1 | +11.7 / +6.6 / -1.8 | — |
| Momentum 60 gün | 5g | +26.2 | +0.69 | %52.9 | +71.2 / +22.4 / -15.3 | — |
| Momentum 250 gün | 1g | +3.6 | +0.58 | %52.0 | +1.2 / +9.8 / -0.2 | — |
| CTA momentum topluluğu | 5g | +16.4 | +0.54 | %52.4 | +37.7 / +18.7 / -7.3 | — |
| Momentum 250 gün | 5g | +15.2 | +0.49 | %52.0 | +4.3 / +38.6 / +2.7 | — |
| Momentum 120 gün | 1g | +3.4 | +0.48 | %51.5 | +6.5 / +7.8 / -4.0 | — |

## ETH
Veri 2017-11-09 → 2026-11-07 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 60 gün | 1g | +5.5 | +0.53 | %51.5 | -6.5 / +2.0 / +20.9 | — |
| Momentum 120 gün | 1g | +1.2 | +0.12 | %51.9 | -16.4 / +17.2 / +2.8 | — |
| Momentum 120 gün | 5g | +3.6 | +0.07 | %51.8 | -42.3 / +82.8 / -30.0 | — |
| CTA momentum topluluğu | 1g | -0.1 | -0.01 | %51.4 | -11.7 / +6.2 / +5.3 | — |
| 200 gün ortalama (al/sat) | 1g | -0.6 | -0.06 | %51.7 | -20.6 / +11.1 / +7.8 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.3 | -0.06 | %53.1 | -10.3 / +5.6 / +3.9 | — |
| Momentum 20 gün | 1g | -0.9 | -0.08 | %49.7 | +1.6 / -10.4 / +6.1 | — |
| Momentum 60 gün | 5g | -9.9 | -0.19 | %51.3 | -89.0 / -49.1 / +108.9 | — |
