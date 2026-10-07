# 🧪 Strateji Laboratuvarı — Sonuç Raporu

_Üretim: 2026-10-07T10:43 UTC · kaynak: panel · denenen konfigürasyon: **1,248** · tüm getiriler maliyet sonrası (net)_

> ⚠️ ÖN İZLEME: bu sonuçlar 700 günlük walk-forward panelinden yeniden kurulan GÜNLÜK kapanışlarla üretildi (yalnızca 1g zaman dilimi, stoplar kapanışla kontrol edildi). 1s/4s ve 10 yıllık günlük test, GitHub Actions'taki ilk 'Strategy Lab' çalışmasında yapılır.

**Kanıt yolları** (biri yeterli):
- **A — 730 gün, tüm zaman dilimleri:** walk-forward OOS t ≥ 2 · 5 test diliminin ≥ 3'ü pozitif · Deflated Sharpe ≥ 0.90 · ≥ 30 işlem
- **B — uzun günlük geçmiş (≥ 6 yıl), sadece 1g:** uzun walk-forward OOS t ≥ 2 · 7 dilimin ≥ 5'i pozitif · Deflated Sharpe ≥ 0.90 · ≥ 30 işlem

## 1) Varlık bazında özet

| Varlık | Aday strateji | Sharpe | Getiri | Maks. DD | İşlem | Kazanma | WF-OOS Sharpe (t) | + dilim | DSR | Uzun dönem 1g: WF Sharpe (t) · + dilim | Al-tut Sharpe / getiri | Durum | Şu anki sinyal |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BTC | RSI ortalamaya dönüş (2/10/90) · 1d · sadece alış · SL 1.5×ATR · TP 3.0×ATR | 1.37 | %+60.8 | %-14.6 | 42 | %76 | -0.79 (-1.0) | 1/5 | 0.57 | — | 0.16 / %+14.9 | ❌ kanıt yok | ⚪ POZİSYON YOK |
| ETH | Donchian kırılımı (20) · 1d · çift yönlü · sinyalle çıkış | 1.11 | %+356.2 | %-48.2 | 15 | %67 | 0.54 (+0.7) | 3/5 | 0.41 | — | 0.00 / %+0.5 | ❌ kanıt yok | 🟢 AL |
| NQ | Momentum (zaman serisi) (60) · 1d · sadece alış · sinyalle çıkış | 1.18 | %+38.0 | %-7.8 | 19 | %37 | 0.29 (+0.4) | 3/5 | 0.49 | — | 0.93 / %+49.5 | ❌ kanıt yok | 🟢 AL |
| SPX | RSI ortalamaya dönüş (2/5/95) · 1d · sadece alış · sinyalle çıkış | 1.37 | %+27.2 | %-2.6 | 27 | %70 | -1.06 (-1.4) | 1/5 | 0.64 | — | 0.87 / %+32.4 | ❌ kanıt yok | ⚪ POZİSYON YOK |
| XAG | Momentum (zaman serisi) (20) · 1d · sadece alış · SL 1.5×ATR · TP 3.0×ATR | 0.82 | %+20.8 | %-6.0 | 25 | %64 | -1.25 (-1.6) | 2/5 | 0.29 | — | 0.62 / %+82.2 | ❌ kanıt yok | ⚪ POZİSYON YOK |
| XAU | Momentum (zaman serisi) (60) · 1d · sadece alış · SL 3.0×ATR · TP 6.0×ATR | 1.38 | %+16.7 | %-2.1 | 16 | %56 | 0.13 (+0.2) | 3/5 | 0.61 | — | 0.84 / %+50.6 | ❌ kanıt yok | 🟢 AL |

_Sharpe/getiri/DD/işlem: adayın son 730 gündeki net sonucu. WF-OOS: her dilimde YALNIZCA geçmişte en iyi olanı seçip bir sonraki dilimde ölçen prosedürün dışı-örneklem sonucu — yüzlerce aday arasından seçim yapmanın bedeli dahildir; t ≥ 2 istatistiksel anlamlılık eşiğidir. DSR: etkin deneme sayısına göre düzeltilmiş 'gerçek Sharpe > 0' olasılığı._

## 2) Strateji aileleri (6 varlık ortalaması)

| Zaman dilimi | Aile | En iyi Sharpe | Medyan Sharpe | WF-OOS Sharpe | WF pozitif varlık |
|---|---|---|---|---|---|
| 1d | RSI ortalamaya dönüş | 1.01 | -0.04 | 0.50 | 5/6 |
| 1d | EMA kesişimi | 1.16 | 0.12 | 0.46 | 6/6 |
| 1d | Keltner volatilite kırılımı | 0.72 | -0.05 | 0.39 | 6/6 |
| 1d | EMA trend filtresi | 0.83 | -0.19 | -0.05 | 3/6 |
| 1d | Bollinger ortalamaya dönüş | 0.84 | -0.27 | -0.14 | 3/6 |
| 1d | Momentum (zaman serisi) | 1.23 | -0.08 | -0.18 | 3/6 |
| 1d | Donchian kırılımı | 0.89 | -0.01 | -0.47 | 2/6 |

## 3) En sağlam çok-varlıklı konfigürasyonlar (stopsuz, tüm varlıklarda aynı ayar)

| Konfigürasyon | Ort. Sharpe | Pozitif varlık |
|---|---|---|
| 1d · tsmom · 60 · LO · none | 0.76 | 6/6 |
| 1d · rsi_mr · 2-5-95 · LO · none | 0.69 | 6/6 |
| 1d · tsmom · 120 · LO · none | 0.63 | 6/6 |
| 1d · ema_trend · 200 · LO · none | 0.63 | 6/6 |
| 1d · ema_cross · 10-30 · LO · none | 0.58 | 6/6 |
| 1d · ema_trend · 200 · LS · none | 0.49 | 6/6 |
| 1d · ema_cross · 20-50 · LS · none | 0.49 | 6/6 |
| 1d · ema_trend · 50 · LO · none | 0.47 | 6/6 |
| 1d · ema_cross · 50-200 · LS · none | 0.41 | 6/6 |
| 1d · keltner · 20-1.5 · LO · none | 0.41 | 6/6 |
| 1d · tsmom · 120 · LS · none | 0.38 | 6/6 |
| 1d · keltner · 20-2.5 · LO · none | 0.34 | 6/6 |

_Kıyas: aynı dönemde al-tut ortalama Sharpe 0.57. 'Sadece alış' (LO) stratejilerin pozitifliğinin bir kısmı piyasanın genel yükselişinden gelir; asıl soru al-tut'tan daha iyi risk/getiri verip vermediğidir._

## 4) Varlık bazında ilk 10 konfigürasyon (tam pencere — seçim yanlılığı İÇERİR, tek başına kanıt değildir)

**BTC — Bitcoin** · pencere 2024-09-29 → 2026-09-29 · 208 konfigürasyon

| # | Konfigürasyon | Sharpe | Getiri | Maks. DD | İşlem | Kazanma |
|---|---|---|---|---|---|---|
| 1 | RSI ortalamaya dönüş (2/10/90) · 1d · sadece alış · SL 1.5×ATR · TP 3.0×ATR | 1.37 | %+60.8 | %-14.6 | 42 | %76 |
| 2 | RSI ortalamaya dönüş (2/10/90) · 1d · sadece alış · SL 2.0×ATR · TP 4.0×ATR | 1.37 | %+63.2 | %-15.3 | 42 | %76 |
| 3 | RSI ortalamaya dönüş (2/10/90) · 1d · sadece alış · SL 3.0×ATR · TP 6.0×ATR | 1.29 | %+63.3 | %-14.4 | 42 | %79 |
| 4 | Bollinger ortalamaya dönüş (20/2.0) · 1d · çift yönlü · SL 2.0×ATR · TP 4.0×ATR | 0.86 | %+40.4 | %-16.7 | 30 | %63 |
| 5 | Bollinger ortalamaya dönüş (20/2.0) · 1d · çift yönlü · SL 3.0×ATR · TP 6.0×ATR | 0.82 | %+43.3 | %-19.4 | 30 | %70 |
| 6 | Momentum (zaman serisi) (60) · 1d · çift yönlü · SL 3.0×ATR · TP 6.0×ATR | 0.80 | %+41.9 | %-16.7 | 25 | %52 |
| 7 | Momentum (zaman serisi) (60) · 1d · çift yönlü · SL 2.0×ATR · TP 4.0×ATR | 0.73 | %+28.2 | %-11.2 | 25 | %52 |
| 8 | RSI ortalamaya dönüş (2/5/95) · 1d · sadece alış · SL 1.5×ATR · TP 3.0×ATR | 0.70 | %+19.6 | %-18.6 | 20 | %70 |
| 9 | RSI ortalamaya dönüş (2/10/90) · 1d · çift yönlü · SL 1.5×ATR · TP 3.0×ATR | 0.67 | %+35.5 | %-18.3 | 75 | %64 |
| 10 | RSI ortalamaya dönüş (2/10/90) · 1d · sadece alış · sinyalle çıkış | 0.65 | %+36.8 | %-32.0 | 43 | %79 |

_Walk-forward dilim getirileri: %-24.1, %-4.2, %-3.8, %+18.0, %-8.5_

**ETH — Ethereum** · pencere 2024-09-29 → 2026-09-29 · 208 konfigürasyon

| # | Konfigürasyon | Sharpe | Getiri | Maks. DD | İşlem | Kazanma |
|---|---|---|---|---|---|---|
| 1 | Donchian kırılımı (20) · 1d · çift yönlü · sinyalle çıkış | 1.11 | %+356.2 | %-48.2 | 15 | %67 |
| 2 | Momentum (zaman serisi) (60) · 1d · çift yönlü · sinyalle çıkış | 1.05 | %+303.5 | %-36.4 | 25 | %40 |
| 3 | EMA kesişimi (10/30) · 1d · çift yönlü · sinyalle çıkış | 0.91 | %+243.3 | %-41.3 | 17 | %41 |
| 4 | Keltner volatilite kırılımı (20/2.5) · 1d · çift yönlü · SL 3.0×ATR · TP 6.0×ATR | 0.84 | %+96.9 | %-22.2 | 27 | %56 |
| 5 | Keltner volatilite kırılımı (20/1.5) · 1d · çift yönlü · sinyalle çıkış | 0.79 | %+165.7 | %-38.0 | 36 | %39 |
| 6 | RSI ortalamaya dönüş (2/5/95) · 1d · sadece alış · sinyalle çıkış | 0.78 | %+64.1 | %-31.2 | 19 | %68 |
| 7 | RSI ortalamaya dönüş (2/10/90) · 1d · sadece alış · sinyalle çıkış | 0.78 | %+82.1 | %-33.3 | 39 | %77 |
| 8 | Keltner volatilite kırılımı (20/2.5) · 1d · çift yönlü · sinyalle çıkış | 0.77 | %+148.5 | %-33.2 | 27 | %52 |
| 9 | RSI ortalamaya dönüş (2/10/90) · 1d · sadece alış · SL 3.0×ATR · TP 6.0×ATR | 0.77 | %+60.4 | %-15.6 | 38 | %76 |
| 10 | Momentum (zaman serisi) (20) · 1d · çift yönlü · sinyalle çıkış | 0.74 | %+178.1 | %-40.7 | 85 | %32 |

_Walk-forward dilim getirileri: %+18.1, %+8.2, %+16.8, %-11.8, %+0.0_

**NQ — Nasdaq 100** · pencere 2024-09-29 → 2026-09-29 · 208 konfigürasyon

| # | Konfigürasyon | Sharpe | Getiri | Maks. DD | İşlem | Kazanma |
|---|---|---|---|---|---|---|
| 1 | Momentum (zaman serisi) (60) · 1d · sadece alış · sinyalle çıkış | 1.18 | %+38.0 | %-7.8 | 19 | %37 |
| 2 | RSI ortalamaya dönüş (2/10/90) · 1d · sadece alış · sinyalle çıkış | 0.87 | %+26.6 | %-10.5 | 40 | %82 |
| 3 | Momentum (zaman serisi) (5) · 1d · sadece alış · sinyalle çıkış | 0.78 | %+23.9 | %-13.0 | 60 | %40 |
| 4 | Momentum (zaman serisi) (60) · 1d · çift yönlü · sinyalle çıkış | 0.72 | %+35.0 | %-14.7 | 37 | %35 |
| 5 | Keltner volatilite kırılımı (50/2.0) · 1d · sadece alış · sinyalle çıkış | 0.71 | %+19.7 | %-11.5 | 15 | %27 |
| 6 | Keltner volatilite kırılımı (20/1.5) · 1d · sadece alış · sinyalle çıkış | 0.61 | %+15.6 | %-13.1 | 22 | %36 |
| 7 | Momentum (zaman serisi) (60) · 1d · sadece alış · SL 2.0×ATR · TP 4.0×ATR | 0.53 | %+4.8 | %-3.4 | 19 | %47 |
| 8 | Momentum (zaman serisi) (20) · 1d · sadece alış · sinyalle çıkış | 0.53 | %+14.7 | %-14.8 | 37 | %40 |
| 9 | EMA trend filtresi (50) · 1d · sadece alış · sinyalle çıkış | 0.52 | %+14.9 | %-17.9 | 25 | %20 |
| 10 | Keltner volatilite kırılımı (20/2.5) · 1d · sadece alış · sinyalle çıkış | 0.46 | %+10.9 | %-12.2 | 17 | %35 |

_Walk-forward dilim getirileri: %+7.5, %-1.2, %+3.4, %+0.5, %-2.0_

**SPX — S&P 500** · pencere 2024-09-29 → 2026-09-29 · 208 konfigürasyon

| # | Konfigürasyon | Sharpe | Getiri | Maks. DD | İşlem | Kazanma |
|---|---|---|---|---|---|---|
| 1 | RSI ortalamaya dönüş (2/5/95) · 1d · sadece alış · sinyalle çıkış | 1.37 | %+27.2 | %-2.6 | 27 | %70 |
| 2 | RSI ortalamaya dönüş (2/5/95) · 1d · sadece alış · SL 3.0×ATR · TP 6.0×ATR | 1.18 | %+22.7 | %-3.7 | 27 | %70 |
| 3 | RSI ortalamaya dönüş (2/5/95) · 1d · sadece alış · SL 2.0×ATR · TP 4.0×ATR | 1.05 | %+16.1 | %-4.5 | 27 | %67 |
| 4 | RSI ortalamaya dönüş (2/10/90) · 1d · sadece alış · sinyalle çıkış | 1.00 | %+23.7 | %-8.7 | 45 | %76 |
| 5 | EMA trend filtresi (50) · 1d · sadece alış · SL 1.5×ATR · TP 3.0×ATR | 0.99 | %+8.7 | %-5.4 | 20 | %60 |
| 6 | Momentum (zaman serisi) (60) · 1d · sadece alış · sinyalle çıkış | 0.97 | %+20.1 | %-5.7 | 15 | %47 |
| 7 | RSI ortalamaya dönüş (2/5/95) · 1d · sadece alış · SL 1.5×ATR · TP 3.0×ATR | 0.89 | %+11.3 | %-3.8 | 27 | %67 |
| 8 | EMA trend filtresi (50) · 1d · sadece alış · sinyalle çıkış | 0.89 | %+18.2 | %-7.3 | 20 | %30 |
| 9 | EMA trend filtresi (50) · 1d · sadece alış · SL 2.0×ATR · TP 4.0×ATR | 0.75 | %+8.2 | %-5.4 | 20 | %45 |
| 10 | Bollinger ortalamaya dönüş (20/2.0) · 1d · çift yönlü · SL 3.0×ATR · TP 6.0×ATR | 0.68 | %+11.0 | %-9.9 | 24 | %71 |

_Walk-forward dilim getirileri: %-5.9, %+1.2, %+0.0, %-5.1, %-5.1_

**XAG — Gümüş** · pencere 2024-09-29 → 2026-09-29 · 208 konfigürasyon

| # | Konfigürasyon | Sharpe | Getiri | Maks. DD | İşlem | Kazanma |
|---|---|---|---|---|---|---|
| 1 | Momentum (zaman serisi) (20) · 1d · sadece alış · SL 1.5×ATR · TP 3.0×ATR | 0.82 | %+20.8 | %-6.0 | 25 | %64 |
| 2 | Momentum (zaman serisi) (5) · 1d · sadece alış · SL 3.0×ATR · TP 6.0×ATR | 0.80 | %+55.5 | %-17.9 | 71 | %46 |
| 3 | Momentum (zaman serisi) (5) · 1d · sadece alış · SL 2.0×ATR · TP 4.0×ATR | 0.75 | %+44.8 | %-20.2 | 71 | %48 |
| 4 | Momentum (zaman serisi) (20) · 1d · sadece alış · sinyalle çıkış | 0.74 | %+74.6 | %-43.1 | 25 | %44 |
| 5 | RSI ortalamaya dönüş (2/5/95) · 1d · sadece alış · sinyalle çıkış | 0.70 | %+30.2 | %-16.5 | 24 | %88 |
| 6 | RSI ortalamaya dönüş (2/5/95) · 1d · sadece alış · SL 1.5×ATR · TP 3.0×ATR | 0.66 | %+25.5 | %-16.0 | 22 | %86 |
| 7 | Momentum (zaman serisi) (10) · 1d · sadece alış · SL 3.0×ATR · TP 6.0×ATR | 0.60 | %+30.7 | %-15.0 | 44 | %36 |
| 8 | Keltner volatilite kırılımı (20/1.5) · 1d · sadece alış · SL 2.0×ATR · TP 4.0×ATR | 0.56 | %+16.4 | %-12.5 | 22 | %50 |
| 9 | Keltner volatilite kırılımı (20/1.5) · 1d · sadece alış · sinyalle çıkış | 0.54 | %+46.5 | %-37.1 | 22 | %36 |
| 10 | Momentum (zaman serisi) (20) · 1d · sadece alış · SL 2.0×ATR · TP 4.0×ATR | 0.50 | %+16.3 | %-13.7 | 25 | %60 |

_Walk-forward dilim getirileri: %+2.1, %-4.4, %+6.0, %-51.0, %-6.6_

**XAU — Altın** · pencere 2024-09-29 → 2026-09-29 · 208 konfigürasyon

| # | Konfigürasyon | Sharpe | Getiri | Maks. DD | İşlem | Kazanma |
|---|---|---|---|---|---|---|
| 1 | Momentum (zaman serisi) (60) · 1d · sadece alış · SL 3.0×ATR · TP 6.0×ATR | 1.38 | %+16.7 | %-2.1 | 16 | %56 |
| 2 | EMA kesişimi (10/30) · 1d · çift yönlü · sinyalle çıkış | 0.99 | %+60.1 | %-19.5 | 21 | %33 |
| 3 | Momentum (zaman serisi) (60) · 1d · sadece alış · sinyalle çıkış | 0.94 | %+48.2 | %-22.0 | 16 | %50 |
| 4 | Momentum (zaman serisi) (20) · 1d · sadece alış · SL 3.0×ATR · TP 6.0×ATR | 0.91 | %+21.9 | %-10.4 | 39 | %41 |
| 5 | EMA trend filtresi (100) · 1d · çift yönlü · sinyalle çıkış | 0.84 | %+48.4 | %-23.0 | 18 | %22 |
| 6 | Momentum (zaman serisi) (20) · 1d · sadece alış · sinyalle çıkış | 0.81 | %+36.6 | %-15.2 | 39 | %36 |
| 7 | Momentum (zaman serisi) (5) · 1d · sadece alış · SL 3.0×ATR · TP 6.0×ATR | 0.80 | %+23.2 | %-16.9 | 64 | %42 |
| 8 | EMA trend filtresi (50) · 1d · sadece alış · sinyalle çıkış | 0.76 | %+34.2 | %-20.0 | 21 | %33 |
| 9 | Momentum (zaman serisi) (60) · 1d · sadece alış · SL 2.0×ATR · TP 4.0×ATR | 0.70 | %+6.8 | %-3.1 | 16 | %50 |
| 10 | Momentum (zaman serisi) (60) · 1d · çift yönlü · sinyalle çıkış | 0.67 | %+37.3 | %-24.0 | 31 | %32 |

_Walk-forward dilim getirileri: %+8.6, %+0.2, %+9.4, %-5.0, %-9.2_

