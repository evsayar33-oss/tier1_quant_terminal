# 🧭 Yön Araştırması (günlük veri, Hep AL'a göre zamanlama alfası)

_Üretim: 2026-11-21T15:57 UTC · test penceresi: son 10 yıl · ufuklar: [1, 5] gün_

Bir kural sadece şu üç koşulu sağlarsa **KANITLI** sayılır: zamanlama alfası t ≥ gerekli t (denenen her kural için Bonferroni düzeltmesi), 3 dönemin en az 2'sinde pozitif alfa, yön isabeti ≥ %50.

## SPX
Veri 2010-11-22 → 2026-11-20 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +14.5 | +1.48 | %61.0 | +23.2 / +5.8 / +14.3 | — |
| Momentum 60 gün | 1g | -0.7 | -0.20 | %54.1 | +4.1 / -6.8 / +0.5 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | -0.5 | -0.34 | %53.9 | +1.7 / -3.2 / -0.0 | — |
| Momentum 20 gün | 1g | -2.0 | -0.54 | %52.4 | +4.0 / -6.8 / -3.2 | — |
| 200 gün ortalama (al/sat) | 5g | -9.9 | -0.62 | %57.1 | +1.3 / -18.1 / -13.0 | — |
| 200 gün ortalama (al/bekle) | 5g | -5.0 | -0.62 | %60.7 | +0.7 / -9.1 / -6.5 | — |
| 200 gün ortalama (al/sat) | 1g | -2.6 | -0.75 | %54.3 | -0.5 / -5.8 / -1.5 | — |
| 200 gün ortalama (al/bekle) | 1g | -1.3 | -0.75 | %55.1 | -0.2 / -2.9 / -0.7 | — |

## NQ
Veri 2010-11-22 → 2026-11-20 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +12.2 | +1.14 | %61.4 | +7.7 / +10.3 / +18.7 | — |
| 200 gün ortalama (al/sat) | 1g | -1.2 | -0.32 | %56.2 | -2.1 / -0.3 / -1.2 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.6 | -0.32 | %57.5 | -1.1 / -0.2 / -0.6 | — |
| Momentum 20 gün | 1g | -2.8 | -0.62 | %53.0 | +0.5 / -4.0 / -5.0 | — |
| 200 gün ortalama (al/sat) | 5g | -13.8 | -0.85 | %57.6 | -22.8 / -2.8 / -15.7 | — |
| 200 gün ortalama (al/bekle) | 5g | -6.9 | -0.85 | %61.2 | -11.4 / -1.4 / -7.8 | — |
| Momentum 120 gün | 5g | -14.6 | -0.89 | %57.5 | -21.2 / -8.7 / -13.7 | — |
| Momentum 20 gün | 5g | -20.2 | -0.97 | %55.1 | -37.0 / -1.3 / -22.2 | — |

## XAU
Veri 2010-11-22 → 2026-11-20 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 5g | +4.6 | +0.60 | %56.3 | +11.3 / -7.9 / +10.5 | — |
| Hep AL + stres anında 5 gün geri dönüş | 1g | +0.2 | +0.12 | %53.2 | +1.4 / -0.3 / -0.5 | — |
| Momentum 120 gün | 1g | +0.1 | +0.04 | %53.2 | -2.8 / -1.1 / +4.2 | — |
| Momentum 120 gün | 5g | -1.5 | -0.12 | %51.9 | -19.2 / -6.9 / +21.8 | — |
| Momentum 60 gün | 1g | -0.5 | -0.20 | %51.9 | -1.3 / -1.3 / +1.3 | — |
| Momentum 60 gün | 5g | -3.4 | -0.28 | %51.2 | -11.0 / -5.2 / +6.0 | — |
| 200 gün ortalama (al/sat) | 1g | -1.5 | -0.69 | %52.7 | -3.4 / -4.9 / +3.9 | — |
| 200 gün ortalama (al/bekle) | 1g | -0.7 | -0.69 | %54.5 | -1.7 / -2.5 / +2.0 | — |

## XAG
Veri 2010-11-22 → 2026-11-20 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Hep AL + stres anında 5 gün geri dönüş | 1g | +1.9 | +0.81 | %52.4 | +0.3 / +0.8 / +4.6 | — |
| Hep AL + stres anında 5 gün geri dönüş | 5g | -0.8 | -0.06 | %52.4 | +19.3 / +5.7 / -27.5 | — |
| Momentum 120 gün | 1g | -0.8 | -0.16 | %51.1 | +2.1 / -11.4 / +6.9 | — |
| Momentum 250 gün | 1g | -0.9 | -0.22 | %52.4 | +0.2 / -7.9 / +5.0 | — |
| Momentum 120 gün | 5g | -13.9 | -0.55 | %49.6 | -1.2 / -42.2 / +1.7 | — |
| 200 gün ortalama (al/sat) | 1g | -2.9 | -0.62 | %50.9 | -5.9 / -5.9 / +3.2 | — |
| 200 gün ortalama (al/bekle) | 1g | -1.4 | -0.62 | %52.7 | -3.0 / -3.0 / +1.6 | — |
| Momentum 20 gün | 1g | -3.7 | -0.68 | %48.9 | -3.6 / -4.5 / -2.8 | — |

## BTC
Veri 2014-09-17 → 2026-11-21 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 60 gün | 1g | +6.8 | +0.90 | %52.1 | +15.2 / +3.2 / +2.1 | — |
| Momentum 20 gün | 1g | +7.5 | +0.89 | %51.9 | +18.3 / +1.1 / +3.2 | — |
| CTA momentum topluluğu | 1g | +5.5 | +0.87 | %52.3 | +12.0 / +3.7 / +0.9 | — |
| Momentum 250 gün | 1g | +4.0 | +0.65 | %51.9 | +4.7 / +6.3 / +1.0 | — |
| Momentum 120 gün | 1g | +3.9 | +0.54 | %51.5 | +10.0 / +4.3 / -2.7 | — |
| Momentum 250 gün | 5g | +14.0 | +0.45 | %53.4 | +4.2 / +30.9 / +7.0 | — |
| Momentum 120 gün | 5g | +11.4 | +0.32 | %53.0 | +24.9 / +10.5 / -1.1 | — |
| CTA momentum topluluğu | 5g | +9.6 | +0.31 | %52.5 | +39.2 / -14.3 / +3.9 | — |

## ETH
Veri 2017-11-09 → 2026-11-21 · test sayısı 16 · gerekli t 2.96

| Kural | Ufuk | Alfa (bps) | t | İsabet | 3 dönem alfa | Durum |
|---|---|---|---|---|---|---|
| Momentum 60 gün | 1g | +7.4 | +0.72 | %51.6 | -10.7 / +6.2 / +26.7 | — |
| Momentum 120 gün | 1g | +1.6 | +0.16 | %51.9 | -16.3 / +17.1 / +3.9 | — |
| CTA momentum topluluğu | 1g | +1.2 | +0.14 | %51.5 | -13.8 / +7.7 / +9.8 | — |
| 200 gün ortalama (al/sat) | 1g | +1.0 | +0.10 | %51.7 | -24.1 / +14.6 / +12.5 | — |
| 200 gün ortalama (al/bekle) | 1g | +0.5 | +0.10 | %53.0 | -12.1 / +7.3 / +6.3 | — |
| Momentum 20 gün | 1g | +1.1 | +0.09 | %49.7 | -2.6 / -8.4 / +14.2 | — |
| Momentum 120 gün | 5g | +3.6 | +0.07 | %51.6 | -42.1 / +82.8 / -29.8 | — |
| Momentum 60 gün | 5g | -2.8 | -0.05 | %51.5 | -100.3 / -37.3 / +129.7 | — |
