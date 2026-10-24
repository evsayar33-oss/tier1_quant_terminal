# 🧭 Yön Araştırması (günlük veri, Hep AL'a göre zamanlama alfası)

_Üretim: 2026-10-24T11:55 UTC · test penceresi: son 10 yıl · ufuklar: [1, 5] gün_

Bir kural sadece şu üç koşulu sağlarsa **KANITLI** sayılır: zamanlama alfası t ≥ gerekli t (denenen her kural için Bonferroni düzeltmesi), 3 dönemin en az 2'sinde pozitif alfa, yön isabeti ≥ %50.

## SPX
Veri 2010-10-25 → 2026-10-23 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 1g | -0.5 | -0.34 | %53.9 | -1.3 / -0.2 / -0.0 | — |
| Momentum 60 gün | 1g | -1.6 | -0.46 | %54.0 | -0.8 / -2.5 / -1.7 | — |
| Momentum 20 gün | 1g | -2.6 | -0.71 | %52.5 | -0.2 / -2.5 / -5.2 | — |
| Hep AL + stres anında 5 gün geri dönüş | 5g | -4.7 | -0.77 | %61.6 | -3.9 / -3.6 / -6.5 | — |
| Momentum 250 gün | 5g | -9.3 | -0.83 | %60.6 | -4.1 / -16.1 / -7.8 | — |
| 200 gün ortalama (al/sat) | 5g | -12.2 | -0.84 | %58.2 | -8.5 / -7.8 / -20.2 | — |
| 200 gün ortalama (al/bekle) | 5g | -6.1 | -0.84 | %62.4 | -4.3 / -3.9 / -10.1 | — |
| 200 gün ortalama (al/sat) | 1g | -3.1 | -0.90 | %54.2 | -3.5 / -2.8 / -2.9 | — |

## NQ
Veri 2010-10-25 → 2026-10-23 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| 200 gün ortalama (al/sat) | 5g | -4.0 | -0.24 | %58.9 | -4.0 / +8.2 / -16.2 | — |
| 200 gün ortalama (al/bekle) | 5g | -2.0 | -0.24 | %62.1 | -2.0 / +4.1 / -8.1 | — |
| 200 gün ortalama (al/sat) | 1g | -1.6 | -0.42 | %56.1 | -2.7 / +0.2 / -2.3 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.8 | -0.42 | %57.4 | -1.3 / +0.1 / -1.2 | — |
| Momentum 120 gün | 5g | -11.2 | -0.69 | %58.5 | -10.0 / -0.0 / -23.8 | — |
| Momentum 250 gün | 5g | -10.9 | -0.81 | %58.7 | -7.4 / -16.2 / -9.0 | — |
| Momentum 20 gün | 1g | -4.1 | -0.92 | %53.0 | -2.7 / -1.2 / -8.5 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | -1.7 | -1.03 | %55.7 | -2.4 / -2.2 / -0.3 | — |

## XAU
Veri 2010-10-25 → 2026-10-23 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 1g | +0.3 | +0.22 | %53.3 | +1.1 / +0.3 / -0.5 | — |
| Hep AL + stres anında 5 gün geri dönüş | 5g | +0.1 | +0.01 | %55.2 | +10.0 / +7.7 / -17.6 | — |
| Momentum 60 gün | 5g | -4.5 | -0.39 | %56.2 | -0.1 / +6.8 / -20.2 | — |
| Momentum 120 gün | 1g | -1.0 | -0.47 | %53.1 | -1.5 / -2.4 / +1.0 | — |
| Momentum 60 gün | 1g | -1.2 | -0.52 | %51.8 | -0.3 / -0.8 / -2.4 | — |
| Momentum 120 gün | 5g | -7.8 | -0.75 | %56.4 | -6.7 / -9.4 / -7.5 | — |
| 200 gün ortalama (al/sat) | 1g | -2.2 | -1.08 | %52.6 | -0.4 / -6.9 / +0.8 | — |
| 200 gün ortalama (al/bekle) | 1g | -1.1 | -1.08 | %54.4 | -0.2 / -3.5 / +0.4 | — |

## XAG
Veri 2010-10-25 → 2026-10-23 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +22.3 | +1.33 | %54.0 | +18.5 / +22.6 / +25.8 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | +2.1 | +0.88 | %52.6 | +3.0 / -1.5 / +4.8 | — |
| Momentum 120 gün | 1g | -2.9 | -0.63 | %51.0 | -2.0 / -6.0 / -0.7 | — |
| Momentum 250 gün | 1g | -2.8 | -0.72 | %52.2 | +0.8 / -8.5 / -0.6 | — |
| Momentum 120 gün | 5g | -24.8 | -1.01 | %50.9 | -34.5 / -12.6 / -27.1 | — |
| 200 gün ortalama (al/sat) | 1g | -4.9 | -1.08 | %50.9 | -7.5 / -3.9 / -3.2 | — |
| 200 gün ortalama (al/bekle) | 1g | -2.4 | -1.08 | %52.8 | -3.7 / -1.9 / -1.6 | — |
| Momentum 250 gün | 5g | -20.4 | -1.14 | %53.2 | -14.4 / -54.4 / +7.6 | — |

## BTC
Veri 2014-09-17 → 2026-10-24 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 60 gün | 1g | +5.9 | +0.77 | %52.3 | +11.7 / +6.6 / -0.8 | — |
| CTA momentum topluluğu | 1g | +4.7 | +0.74 | %52.5 | +7.2 / +8.6 / -1.6 | — |
| Momentum 20 gün | 1g | +5.9 | +0.70 | %52.0 | +12.1 / +7.1 / -1.5 | — |
| Momentum 250 gün | 1g | +3.6 | +0.58 | %52.1 | -1.5 / +12.5 / -0.2 | — |
| Momentum 120 gün | 1g | +3.4 | +0.48 | %51.6 | +6.3 / +8.0 / -4.0 | — |
| Momentum 250 gün | 5g | +14.3 | +0.46 | %53.8 | -7.5 / +47.8 / +2.8 | — |
| Momentum 60 gün | 5g | +6.2 | +0.18 | %52.0 | +51.3 / -15.8 / -17.1 | — |
| CTA momentum topluluğu | 5g | +2.9 | +0.10 | %51.9 | +5.4 / +10.0 / -6.8 | — |

## ETH
Veri 2017-11-09 → 2026-10-24 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 60 gün | 1g | +5.1 | +0.50 | %51.5 | -8.0 / +3.4 / +19.9 | — |
| Momentum 120 gün | 1g | +1.2 | +0.12 | %51.9 | -16.5 / +17.3 / +2.8 | — |
| Momentum 120 gün | 5g | +3.6 | +0.07 | %52.1 | -42.5 / +83.2 / -30.1 | — |
| CTA momentum topluluğu | 1g | -0.3 | -0.03 | %51.4 | -12.5 / +6.9 / +4.8 | — |
| 200 gün ortalama (al/sat) | 1g | -0.6 | -0.06 | %51.7 | -22.1 / +12.6 / +7.8 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.3 | -0.06 | %53.0 | -11.1 / +6.3 / +3.9 | — |
| Momentum 20 gün | 1g | -1.3 | -0.12 | %49.7 | +0.3 / -9.2 / +5.0 | — |
| Momentum 60 gün | 5g | -12.1 | -0.24 | %51.0 | -83.5 / -55.3 / +103.1 | — |
