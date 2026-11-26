# 🧭 Yön Araştırması (günlük veri, Hep AL'a göre zamanlama alfası)

_Üretim: 2026-11-26T13:50 UTC · test penceresi: son 10 yıl · ufuklar: [1, 5] gün_

Bir kural sadece şu üç koşulu sağlarsa **KANITLI** sayılır: zamanlama alfası t ≥ gerekli t (denenen her kural için Bonferroni düzeltmesi), 3 dönemin en az 2'sinde pozitif alfa, yön isabeti ≥ %50.

## SPX
Veri 2010-11-26 → 2026-11-26 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +1.6 | +0.25 | %62.4 | +12.9 / +0.4 / -8.6 | — |
| Momentum 60 gün | 1g | -1.1 | -0.30 | %54.0 | +3.1 / -5.8 / -0.5 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | -0.5 | -0.34 | %53.8 | +0.7 / -2.2 / -0.0 | — |
| Momentum 250 gün | 5g | -6.0 | -0.51 | %59.8 | +4.7 / -22.7 / +0.0 | — |
| Momentum 20 gün | 1g | -2.4 | -0.63 | %52.3 | +3.0 / -5.8 / -4.3 | — |
| Momentum 60 gün | 5g | -12.0 | -0.81 | %59.1 | +11.1 / -36.8 / -10.4 | — |
| 200 gün ortalama (al/sat) | 1g | -2.9 | -0.85 | %54.2 | -1.5 / -4.8 / -2.5 | — |
| 200 gün ortalama (al/bekle) | 1g | -1.5 | -0.85 | %55.1 | -0.7 / -2.4 / -1.3 | — |

## NQ
Veri 2010-11-26 → 2026-11-26 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +4.5 | +0.64 | %60.2 | +15.0 / +0.0 / -1.5 | — |
| 200 gün ortalama (al/sat) | 1g | -1.6 | -0.41 | %56.2 | -3.1 / +0.7 / -2.3 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.8 | -0.41 | %57.5 | -1.6 / +0.3 / -1.1 | — |
| 200 gün ortalama (al/sat) | 5g | -9.9 | -0.63 | %58.2 | -20.3 / -2.2 / -7.2 | — |
| 200 gün ortalama (al/bekle) | 5g | -5.0 | -0.63 | %61.0 | -10.1 / -1.1 / -3.6 | — |
| Momentum 20 gün | 1g | -3.2 | -0.70 | %53.0 | -0.6 / -3.0 / -6.1 | — |
| Momentum 120 gün | 5g | -10.8 | -0.74 | %58.2 | -22.8 / +5.6 / -15.2 | — |
| Momentum 250 gün | 5g | -12.3 | -0.96 | %57.6 | -30.7 / -6.2 / +0.0 | — |

## XAU
Veri 2010-11-26 → 2026-11-26 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +9.2 | +1.30 | %56.7 | +6.0 / +3.1 / +18.6 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | +0.2 | +0.12 | %53.2 | +2.3 / -1.3 / -0.5 | — |
| Momentum 120 gün | 1g | -0.2 | -0.10 | %53.2 | -3.1 / -1.1 / +3.6 | — |
| Momentum 60 gün | 1g | -0.8 | -0.33 | %51.9 | -1.7 / -1.4 / +0.8 | — |
| Momentum 120 gün | 5g | -4.1 | -0.36 | %52.3 | -21.8 / -8.4 / +18.0 | — |
| 200 gün ortalama (al/sat) | 1g | -1.8 | -0.82 | %52.7 | -3.8 / -4.9 / +3.4 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.9 | -0.82 | %54.5 | -1.9 / -2.5 / +1.7 | — |
| 200 gün ortalama (al/sat) | 5g | -10.8 | -1.00 | %51.5 | -26.0 / -17.0 / +10.9 | — |

## XAG
Veri 2010-11-26 → 2026-11-26 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +9.2 | +0.96 | %55.0 | -7.0 / +12.1 / +22.6 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | +1.9 | +0.81 | %52.4 | +1.6 / -0.4 / +4.6 | — |
| Momentum 120 gün | 1g | -0.9 | -0.19 | %51.1 | +3.3 / -12.6 / +6.5 | — |
| Momentum 120 gün | 5g | -5.6 | -0.21 | %49.8 | +0.3 / -35.2 / +18.1 | — |
| Momentum 250 gün | 1g | -1.0 | -0.25 | %52.3 | +1.4 / -9.1 / +4.7 | — |
| 200 gün ortalama (al/sat) | 5g | -15.0 | -0.58 | %48.6 | -16.3 / -21.2 / -7.6 | — |
| 200 gün ortalama (al/bekle) | 5g | -7.5 | -0.58 | %52.4 | -8.2 / -10.6 / -3.8 | — |
| 200 gün ortalama (al/sat) | 1g | -3.0 | -0.63 | %50.9 | -4.6 / -7.1 / +2.8 | — |

## BTC
Veri 2014-09-17 → 2026-11-26 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 20 gün | 1g | +7.4 | +0.88 | %51.9 | +18.7 / +1.0 / +2.5 | — |
| Momentum 60 gün | 1g | +6.7 | +0.88 | %52.1 | +15.6 / +2.7 / +1.9 | — |
| CTA momentum topluluğu | 1g | +5.5 | +0.86 | %52.3 | +12.5 / +3.4 / +0.5 | — |
| Momentum 250 gün | 1g | +3.9 | +0.63 | %51.9 | +5.1 / +5.9 / +0.7 | — |
| Momentum 120 gün | 1g | +3.8 | +0.53 | %51.4 | +10.4 / +3.9 / -3.0 | — |
| Momentum 250 gün | 5g | +15.0 | +0.48 | %53.6 | +7.4 / +27.8 / +9.9 | — |
| Momentum 120 gün | 5g | +12.4 | +0.35 | %53.1 | +28.0 / +7.3 / +1.8 | — |
| CTA momentum topluluğu | 5g | +10.6 | +0.34 | %52.7 | +42.4 / -16.9 / +6.2 | — |

## ETH
Veri 2017-11-09 → 2026-11-26 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 60 gün | 1g | +7.3 | +0.71 | %51.5 | -11.1 / +6.6 / +26.4 | — |
| Momentum 120 gün | 1g | +1.5 | +0.15 | %51.8 | -16.3 / +17.1 / +3.6 | — |
| CTA momentum topluluğu | 1g | +1.1 | +0.13 | %51.4 | -13.9 / +7.6 / +9.7 | — |
| Momentum 120 gün | 5g | +5.5 | +0.11 | %51.7 | -42.1 / +82.4 / -23.9 | — |
| Momentum 20 gün | 1g | +0.9 | +0.09 | %49.7 | -3.0 / -9.0 / +14.9 | — |
| 200 gün ortalama (al/sat) | 1g | +0.9 | +0.09 | %51.7 | -24.1 / +14.6 / +12.2 | — |
| 200 gün ortalama (al/bekle) | 1g | +0.5 | +0.09 | %53.0 | -12.0 / +7.3 / +6.1 | — |
| Momentum 60 gün | 5g | -0.8 | -0.02 | %51.5 | -100.3 / -37.1 / +135.7 | — |
