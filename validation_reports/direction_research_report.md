# 🧭 Yön Araştırması (günlük veri, Hep AL'a göre zamanlama alfası)

_Üretim: 2026-10-31T13:23 UTC · test penceresi: son 10 yıl · ufuklar: [1, 5] gün_

Bir kural sadece şu üç koşulu sağlarsa **KANITLI** sayılır: zamanlama alfası t ≥ gerekli t (denenen her kural için Bonferroni düzeltmesi), 3 dönemin en az 2'sinde pozitif alfa, yön isabeti ≥ %50.

## SPX
Veri 2010-11-01 → 2026-10-30 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 1g | -0.5 | -0.34 | %54.0 | -0.5 / -1.0 / -0.0 | — |
| Momentum 60 gün | 1g | -1.7 | -0.49 | %53.9 | -1.5 / -2.0 / -1.7 | — |
| Momentum 20 gün | 1g | -2.8 | -0.77 | %52.3 | -1.0 / -2.0 / -5.5 | — |
| Hep AL + stres anında 5 gün geri dönüş | 5g | -4.7 | -0.77 | %61.6 | -3.9 / -3.6 / -6.5 | — |
| Momentum 250 gün | 5g | -9.3 | -0.83 | %60.6 | -4.1 / -16.1 / -7.8 | — |
| 200 gün ortalama (al/sat) | 5g | -12.2 | -0.84 | %58.2 | -9.0 / -7.2 / -20.2 | — |
| 200 gün ortalama (al/bekle) | 5g | -6.1 | -0.84 | %62.4 | -4.5 / -3.6 / -10.1 | — |
| 200 gün ortalama (al/sat) | 1g | -3.1 | -0.90 | %54.3 | -5.3 / -1.0 / -2.9 | — |

## NQ
Veri 2010-11-01 → 2026-10-30 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| 200 gün ortalama (al/sat) | 5g | -4.0 | -0.24 | %58.9 | -4.0 / +8.2 / -16.2 | — |
| 200 gün ortalama (al/bekle) | 5g | -2.0 | -0.24 | %62.1 | -2.0 / +4.1 / -8.1 | — |
| 200 gün ortalama (al/sat) | 1g | -1.6 | -0.42 | %56.2 | -2.7 / +0.2 / -2.3 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.8 | -0.42 | %57.5 | -1.3 / +0.1 / -1.2 | — |
| Momentum 120 gün | 5g | -11.2 | -0.69 | %58.5 | -10.0 / -0.0 / -23.8 | — |
| Momentum 250 gün | 5g | -10.9 | -0.81 | %58.7 | -7.4 / -16.2 / -9.0 | — |
| Momentum 20 gün | 1g | -4.1 | -0.90 | %52.9 | -3.7 / -0.5 / -8.0 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | -1.7 | -1.03 | %55.8 | -1.8 / -2.9 / -0.3 | — |

## XAU
Veri 2010-11-01 → 2026-10-30 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 1g | +0.3 | +0.22 | %53.2 | +1.9 / -0.4 / -0.5 | — |
| Hep AL + stres anında 5 gün geri dönüş | 5g | +0.1 | +0.01 | %55.0 | +10.0 / +7.7 / -17.6 | — |
| Momentum 120 gün | 1g | -0.7 | -0.32 | %53.1 | -1.2 / -2.4 / +1.7 | — |
| Momentum 60 gün | 5g | -4.2 | -0.36 | %56.2 | +0.8 / +7.0 / -20.5 | — |
| Momentum 60 gün | 1g | -0.9 | -0.39 | %51.9 | -0.1 / -0.8 / -1.7 | — |
| Momentum 120 gün | 5g | -6.4 | -0.60 | %56.6 | -5.8 / -9.4 / -3.9 | — |
| 200 gün ortalama (al/sat) | 1g | -1.9 | -0.92 | %52.7 | -0.1 / -6.9 / +1.4 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.9 | -0.92 | %54.5 | -0.1 / -3.5 / +0.7 | — |

## XAG
Veri 2010-11-01 → 2026-10-30 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +22.3 | +1.33 | %53.8 | +18.5 / +22.6 / +25.8 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | +2.1 | +0.88 | %52.5 | +3.0 / -1.5 / +4.8 | — |
| Momentum 120 gün | 1g | -2.2 | -0.47 | %51.0 | -1.6 / -6.8 / +1.7 | — |
| Momentum 250 gün | 1g | -2.8 | -0.72 | %52.2 | +0.8 / -8.5 / -0.6 | — |
| Momentum 120 gün | 5g | -22.3 | -0.90 | %50.9 | -36.8 / -10.8 / -19.3 | — |
| 200 gün ortalama (al/sat) | 1g | -4.1 | -0.91 | %50.9 | -8.5 / -2.8 / -1.1 | — |
| 200 gün ortalama (al/bekle) | 1g | -2.1 | -0.91 | %52.8 | -4.3 / -1.4 / -0.6 | — |
| Momentum 20 gün | 1g | -5.3 | -1.01 | %48.8 | -8.0 / +0.1 / -8.0 | — |

## BTC
Veri 2014-09-17 → 2026-10-31 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 60 gün | 1g | +5.8 | +0.76 | %52.2 | +11.7 / +6.6 / -1.0 | — |
| CTA momentum topluluğu | 1g | +4.7 | +0.75 | %52.4 | +7.5 / +8.2 / -1.5 | — |
| Momentum 20 gün | 1g | +6.1 | +0.73 | %52.0 | +12.9 / +6.2 / -0.9 | — |
| Momentum 250 gün | 1g | +3.6 | +0.58 | %52.0 | -0.7 / +11.7 / -0.2 | — |
| Momentum 120 gün | 5g | +19.3 | +0.54 | %53.4 | +24.3 / +51.0 / -17.4 | — |
| Momentum 120 gün | 1g | +3.4 | +0.48 | %51.6 | +6.2 / +8.1 / -4.0 | — |
| Momentum 250 gün | 5g | +12.8 | +0.41 | %52.5 | -20.7 / +54.0 / +5.1 | — |
| 200 gün ortalama (al/sat) | 5g | +5.3 | +0.15 | %53.1 | +34.5 / +9.8 / -28.3 | — |

## ETH
Veri 2017-11-09 → 2026-10-31 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 60 gün | 1g | +5.5 | +0.53 | %51.5 | -7.8 / +3.3 / +20.9 | — |
| Momentum 120 gün | 1g | +1.2 | +0.12 | %51.9 | -16.4 / +17.3 / +2.8 | — |
| Momentum 120 gün | 5g | +3.6 | +0.07 | %52.0 | -42.5 / +83.2 / -30.0 | — |
| CTA momentum topluluğu | 1g | -0.1 | -0.01 | %51.4 | -12.4 / +6.8 / +5.3 | — |
| 200 gün ortalama (al/sat) | 1g | -0.6 | -0.06 | %51.7 | -21.9 / +12.4 / +7.8 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.3 | -0.06 | %53.0 | -11.0 / +6.2 / +3.9 | — |
| Momentum 20 gün | 1g | -0.9 | -0.09 | %49.7 | +0.3 / -9.2 / +6.1 | — |
| Momentum 60 gün | 5g | -11.7 | -0.23 | %51.1 | -83.5 / -55.3 / +103.7 | — |
