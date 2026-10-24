# 🧪 Tarihsel Doğrulama Raporu (walk-forward, zaman-noktası doğru)

_Son güncelleme: 2026-10-24T11:55:00.642172+00:00 · döngü: 8401 · kayıt: 39647 (notlanan: 39640)_

Bu sayfa sistemin **yayınladığı nihai sinyalleri** gerçekleşen fiyatla notlar. Model bu sayfadan öğrenmez; sadece hakemdir. Bir satırın güvenilir olması için en az **30** bağımsız (çakışmayan) örnek gerekir.

**Nasıl okunur:** *isabet* = yön doğru tahmin oranı · *ort bps* = sinyal yönünde ortalama getiri (1 bps = %0,01) · *alt sınır* = %95 güvenle gerçek isabetin en az bu kadar olduğu değer. Model, **Hep AL** ve **Trend takibi** (fiyatın gidişine bakan reaktif yöntem) ile AYNI anlarda karşılaştırılır.

## Genel
### 4 saat sonrası
- **Model:** %47.8 isabet · ort -1 bps · n=12051 (bağımsız 6138, alt sınır %47)
- Hep AL: %52.3 isabet · ort +1 bps · n=12051 (bağımsız 6138, alt sınır %51)
- Trend takibi: %48.9 isabet · ort -1 bps · n=11177 (bağımsız 5818, alt sınır %48)
- Sadece giriş izni verilenler: %46.1 isabet · ort -1 bps · n=4182 (bağımsız 2488, alt sınır %44)
- Zamanlama notu A: %45.9 isabet · ort -1 bps · n=2989 (bağımsız 1736, alt sınır %44)
- Zamanlama notu B: %47.1 isabet · ort -1 bps · n=2926 (bağımsız 1826, alt sınır %45)
- Zamanlama notu C: %49.1 isabet · ort -0 bps · n=6136 (bağımsız 3514, alt sınır %48)
- Sonuç: 🔴 Model basit yöntemlerin gerisinde (-4.5 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### 24 saat sonrası
- **Model:** %47.1 isabet · ort +2 bps · n=12050 (bağımsız 1233, alt sınır %45)
- Hep AL: %53.1 isabet · ort -1 bps · n=12050 (bağımsız 1233, alt sınır %51)
- Trend takibi: %48.8 isabet · ort +3 bps · n=11175 (bağımsız 1217, alt sınır %46)
- Sadece giriş izni verilenler: %45.1 isabet · ort -7 bps · n=4180 (bağımsız 820, alt sınır %42)
- Zamanlama notu A: %43.5 isabet · ort -9 bps · n=2985 (bağımsız 528, alt sınır %40)
- Zamanlama notu B: %49.2 isabet · ort +5 bps · n=2925 (bağımsız 730, alt sınır %46)
- Zamanlama notu C: %47.9 isabet · ort +5 bps · n=6140 (bağımsız 1006, alt sınır %45)
- Sonuç: 🔴 Model basit yöntemlerin gerisinde (-6.1 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### 72 saat sonrası
- **Model:** %45.2 isabet · ort -4 bps · n=12129 (bağımsız 597, alt sınır %42)
- Hep AL: %54.8 isabet · ort +6 bps · n=12129 (bağımsız 597, alt sınır %51)
- Trend takibi: %47.7 isabet · ort +3 bps · n=11250 (bağımsız 594, alt sınır %44)
- Sadece giriş izni verilenler: %43.6 isabet · ort -12 bps · n=4198 (bağımsız 469, alt sınır %40)
- Zamanlama notu A: %43.0 isabet · ort -13 bps · n=3002 (bağımsız 306, alt sınır %38)
- Zamanlama notu B: %45.5 isabet · ort -15 bps · n=2947 (bağımsız 455, alt sınır %42)
- Zamanlama notu C: %46.0 isabet · ort +5 bps · n=6180 (bağımsız 542, alt sınır %43)
- Sonuç: 🔴 Model basit yöntemlerin gerisinde (-9.7 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### 120 saat sonrası
- **Model:** %45.4 isabet · ort -19 bps · n=12049 (bağımsız 419, alt sınır %41)
- Hep AL: %55.3 isabet · ort +22 bps · n=12049 (bağımsız 419, alt sınır %51)
- Trend takibi: %47.6 isabet · ort +2 bps · n=11173 (bağımsız 417, alt sınır %44)
- Sadece giriş izni verilenler: %45.6 isabet · ort -15 bps · n=4169 (bağımsız 358, alt sınır %41)
- Zamanlama notu A: %45.7 isabet · ort -1 bps · n=2988 (bağımsız 239, alt sınır %40)
- Zamanlama notu B: %46.0 isabet · ort -30 bps · n=2929 (bağımsız 350, alt sınır %42)
- Zamanlama notu C: %45.0 isabet · ort -23 bps · n=6132 (bağımsız 395, alt sınır %41)
- Sonuç: 🔴 Model basit yöntemlerin gerisinde (-9.9 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

## Varlık bazında (24 saat ve 72 saat)
### BTC
- 24s Model: %46.8 isabet · ort -3 bps · n=2486 (bağımsız 239, alt sınır %42)
  - Hep AL: %52.9 isabet · ort +1 bps · n=2486 (bağımsız 239, alt sınır %48) · Trend: %48.1 isabet · ort +4 bps · n=2344 (bağımsız 238, alt sınır %43)
  - 🔴 Model basit yöntemlerin gerisinde (-6.1 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.
- 72s Model: %45.0 isabet · ort -16 bps · n=2483 (bağımsız 106, alt sınır %37)
  - Hep AL: %54.3 isabet · ort +14 bps · n=2483 (bağımsız 106, alt sınır %46) · Trend: %47.2 isabet · ort +19 bps · n=2341 (bağımsız 106, alt sınır %39)
  - 🔴 Model basit yöntemlerin gerisinde (-9.3 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### ETH
- 24s Model: %49.5 isabet · ort +26 bps · n=2796 (bağımsız 270, alt sınır %45)
  - Hep AL: %50.5 isabet · ort -24 bps · n=2796 (bağımsız 270, alt sınır %46) · Trend: %46.5 isabet · ort +17 bps · n=2609 (bağımsız 265, alt sınır %41)
  - 🔴 Model basit yöntemlerin gerisinde (-1.0 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.
- 72s Model: %50.2 isabet · ort +31 bps · n=2787 (bağımsız 117, alt sınır %43)
  - Hep AL: %50.6 isabet · ort -24 bps · n=2787 (bağımsız 117, alt sınır %43) · Trend: %46.8 isabet · ort +3 bps · n=2600 (bağımsız 116, alt sınır %39)
  - 🔴 Model basit yöntemlerin gerisinde (-0.4 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### NQ
- 24s Model: %51.0 isabet · ort +8 bps · n=1907 (bağımsız 201, alt sınır %45)
  - Hep AL: %50.3 isabet · ort -3 bps · n=1907 (bağımsız 201, alt sınır %45) · Trend: %51.6 isabet · ort +4 bps · n=1779 (bağımsız 201, alt sınır %46)
  - 🔴 Model basit yöntemlerin gerisinde (-0.6 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.
- 72s Model: %45.1 isabet · ort +5 bps · n=1939 (bağımsız 102, alt sınır %37)
  - Hep AL: %55.9 isabet · ort +1 bps · n=1939 (bağımsız 102, alt sınır %48) · Trend: %46.9 isabet · ort -14 bps · n=1810 (bağımsız 102, alt sınır %39)
  - 🔴 Model basit yöntemlerin gerisinde (-10.7 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### SPX
- 24s Model: %46.7 isabet · ort -4 bps · n=1784 (bağımsız 187, alt sınır %41)
  - Hep AL: %53.9 isabet · ort +7 bps · n=1784 (bağımsız 187, alt sınır %48) · Trend: %52.4 isabet · ort -1 bps · n=1576 (bağımsız 181, alt sınır %46)
  - 🔴 Model basit yöntemlerin gerisinde (-7.1 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.
- 72s Model: %42.4 isabet · ort -5 bps · n=1786 (bağımsız 92, alt sınır %34)
  - Hep AL: %58.2 isabet · ort +9 bps · n=1786 (bağımsız 92, alt sınır %50) · Trend: %46.7 isabet · ort -12 bps · n=1583 (bağımsız 91, alt sınır %38)
  - 🔴 Model basit yöntemlerin gerisinde (-15.8 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### XAG
- 24s Model: %39.6 isabet · ort -23 bps · n=1367 (bağımsız 147, alt sınır %33)
  - Hep AL: %58.9 isabet · ort +19 bps · n=1367 (bağımsız 147, alt sınır %52) · Trend: %44.9 isabet · ort -20 bps · n=1267 (bağımsız 146, alt sınır %38)
  - 🔴 Model basit yöntemlerin gerisinde (-19.3 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.
- 72s Model: %41.1 isabet · ort -34 bps · n=1399 (bağımsız 78, alt sınır %32)
  - Hep AL: %57.6 isabet · ort +29 bps · n=1399 (bağımsız 78, alt sınır %48) · Trend: %47.4 isabet · ort +0 bps · n=1293 (bağımsız 78, alt sınır %38)
  - 🔴 Model basit yöntemlerin gerisinde (-16.5 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### XAU
- 24s Model: %45.5 isabet · ort -12 bps · n=1710 (bağımsız 189, alt sınır %40)
  - Hep AL: %55.7 isabet · ort +14 bps · n=1710 (bağımsız 189, alt sınır %50) · Trend: %49.7 isabet · ort +1 bps · n=1600 (bağımsız 186, alt sınır %44)
  - 🔴 Model basit yöntemlerin gerisinde (-10.2 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.
- 72s Model: %43.4 isabet · ort -29 bps · n=1735 (bağımsız 102, alt sınır %36)
  - Hep AL: %55.4 isabet · ort +30 bps · n=1735 (bağımsız 102, alt sınır %47) · Trend: %52.2 isabet · ort +17 bps · n=1623 (bağımsız 101, alt sınır %44)
  - 🔴 Model basit yöntemlerin gerisinde (-12.0 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

## Rejim bazında (Model)
- Rejim 1: 24s %50.7 isabet · ort +64 bps · n=840 (bağımsız 88, alt sınır %42) · 72s %45.9 isabet · ort +35 bps · n=859 (bağımsız 49, alt sınır %35)
- Rejim 2: 24s %46.2 isabet · ort +6 bps · n=4704 (bağımsız 527, alt sınır %43) · 72s %45.7 isabet · ort +32 bps · n=4684 (bağımsız 285, alt sınır %41)
- Rejim 3: 24s %46.9 isabet · ort -10 bps · n=4986 (bağımsız 539, alt sınır %43) · 72s %46.6 isabet · ort -21 bps · n=5043 (bağımsız 274, alt sınır %42)
- Rejim 4: 24s %47.0 isabet · ort -15 bps · n=1218 (bağımsız 147, alt sınır %40) · 72s %37.5 isabet · ort -106 bps · n=1234 (bağımsız 91, alt sınır %30)
- Rejim REJIMSIZ_GECIS: 24s %53.6 isabet · ort +15 bps · n=302 (bağımsız 33, alt sınır %40) · 72s %42.1 isabet · ort +11 bps · n=309 (bağımsız 17, alt sınır %25) ⚠️az bağımsız örnek

## Veri sağlığı (faktör bazında erişilebilirlik)
Aşağıdaki faktörler son döngülerin önemli kısmında **veri alamadı** ve skora katılmadı:
- BTC|OKX/Bybit Spot & Vadeli Taker Akışı: %0 erişilebilir
- BTC|Türev Fonlama Oranı (Kaldıraç Riski): %0 erişilebilir
- BTC|⚠️ Likidasyon & Kaldıraç Sıkışması Riski: %0 erişilebilir
- BTC|💵 Kripto-Yerel USD Likiditesi & Taker İştahı: %0 erişilebilir
- ETH|Canlı ETH Fonlama Oranı (Funding Riski): %0 erişilebilir
- ETH|OKX/Bybit ETH Taker Alış Akışı: %0 erişilebilir
- ETH|⚠️ ETH Türev Kaldıraç & Sıkışma Riski: %0 erişilebilir
- ETH|💵 Kripto-Yerel USD Likiditesi & Stabilcoin Akışı: %0 erişilebilir

## Tarihsel tekrar oynatma (walk-forward) — kapsam ve sınırlar
- Dönem: 2024-11-22 20:00:00+00:00 → 2026-10-23 20:00:00+00:00 · adım: 2.0 saat · döngü: 8401 · hata: 0
- Sistem her an için SADECE o ana kadar var olan veriyle, canlı arka plan döngüsünün birebir aynısıyla çalıştırıldı (saat dondurularak).
- Tüm adaptif hafızalar dönem başında sıfırdan başladı ve sadece geçmişten öğrendi.
- ⚠️ OKX/Bybit taker akışı & fonlama oranı geçmişi olmadığı için BTC/ETH'de bu öncü faktörler replay'de yok (tutucu yanlılık).
- ⚠️ FRED serileri güncel vintage ile kullanıldı (piyasa serileri nadiren revize edilir).

## 🤖 Kendini optimize eden model (walk-forward, örneklem dışı)
Her varlık için 8 aday model (ridge + rejim sapmaları, ridge (rejimsiz), ekonomik işaret korumalı, eşit ağırlık (öğrenmesiz) × ufuk [24, 72]) yalnız o güne kadarki veriyle eğitilip hiç görülmemiş veride sınandı; eğitim ile test arasında ufuk kadar ambargo var.
**Canlıya alma kuralı:** en iyi adayın t(IC) ≥ 2.73 (en iyiyi seçmenin şans payı düzeltilmiş eşik), isabet ≥ Hep AL ve ortalama getiri > 0. Sağlamayan varlıkta sinyal **bilgi amaçlı (KANITSIZ)** gösterilir, işleme giriş izni verilmez.

| Varlık | Durum | En iyi aday | IC | t | Öğrenilmiş | Eski model | Hep AL | Trend |
|---|---|---|---|---|---|---|---|---|
| BTC | ⛔ kanıt yok | eşit ağırlık (öğrenmesiz), 72s | +0.022 | +0.3 | %49.8 / +14bps | %49.6 / +6bps | %50.6 / -8bps | %47.2 / +2bps |
| ETH | ⛔ kanıt yok | eşit ağırlık (öğrenmesiz), 72s | +0.005 | +0.1 | %48.2 / +19bps | %46.0 / -12bps | %50.2 / -6bps | %46.4 / -1bps |
| NQ | ⛔ kanıt yok | eşit ağırlık (öğrenmesiz), 72s | +0.018 | +0.2 | %48.9 / -1bps | %53.8 / +3bps | %57.1 / +15bps | %50.5 / -9bps |
| SPX | ⛔ kanıt yok | eşit ağırlık (öğrenmesiz), 72s | +0.002 | +0.0 | %49.5 / +0bps | %47.8 / -4bps | %57.4 / +12bps | %49.3 / -9bps |
| XAG | ⛔ kanıt yok | ridge (rejimsiz), 24s | +0.068 | +1.7 | %55.3 / +16bps | %42.6 / -7bps | %54.3 / +10bps | %48.8 / -7bps |
| XAU | ⛔ kanıt yok | ridge + rejim sapmaları, 24s | +0.025 | +0.6 | %50.9 / +0bps | %49.1 / +1bps | %52.7 / +6bps | %48.1 / -0bps |

**Tüm adaylar (t değeri):**
- **BTC**: ridge + rejim sapmaları/24s -1.0, ridge (rejimsiz)/24s -0.5, ekonomik işaret korumalı/24s -0.5, eşit ağırlık (öğrenmesiz)/24s -0.2, ridge + rejim sapmaları/72s -1.1, ridge (rejimsiz)/72s -1.2, ekonomik işaret korumalı/72s -0.2, eşit ağırlık (öğrenmesiz)/72s +0.3
- **ETH**: ridge + rejim sapmaları/24s -0.7, ridge (rejimsiz)/24s -0.9, ekonomik işaret korumalı/24s -0.6, eşit ağırlık (öğrenmesiz)/24s -0.2, ridge + rejim sapmaları/72s -0.1, ridge (rejimsiz)/72s -0.9, ekonomik işaret korumalı/72s -0.4, eşit ağırlık (öğrenmesiz)/72s +0.1
- **NQ**: ridge + rejim sapmaları/24s -1.0, ridge (rejimsiz)/24s -0.7, ekonomik işaret korumalı/24s -0.7, eşit ağırlık (öğrenmesiz)/24s -0.4, ridge + rejim sapmaları/72s -1.8, ridge (rejimsiz)/72s -1.3, ekonomik işaret korumalı/72s -1.0, eşit ağırlık (öğrenmesiz)/72s +0.2
- **SPX**: ridge + rejim sapmaları/24s -1.4, ridge (rejimsiz)/24s -1.1, ekonomik işaret korumalı/24s -0.8, eşit ağırlık (öğrenmesiz)/24s -0.8, ridge + rejim sapmaları/72s -1.6, ridge (rejimsiz)/72s -1.0, ekonomik işaret korumalı/72s -1.1, eşit ağırlık (öğrenmesiz)/72s +0.0
- **XAG**: ridge + rejim sapmaları/24s +1.1, ridge (rejimsiz)/24s +1.7, ekonomik işaret korumalı/24s -0.1, eşit ağırlık (öğrenmesiz)/24s -1.3, ridge + rejim sapmaları/72s +0.9, ridge (rejimsiz)/72s +1.2, ekonomik işaret korumalı/72s -1.4, eşit ağırlık (öğrenmesiz)/72s -0.6
- **XAU**: ridge + rejim sapmaları/24s +0.6, ridge (rejimsiz)/24s -0.7, ekonomik işaret korumalı/24s -1.9, eşit ağırlık (öğrenmesiz)/24s -0.1, ridge + rejim sapmaları/72s +0.1, ridge (rejimsiz)/72s -0.8, ekonomik işaret korumalı/72s -0.9, eşit ağırlık (öğrenmesiz)/72s -0.1

## ⏱️ Kısa Vade Yön — sonraki 4 saatlik mum tahmini (walk-forward, örneklem dışı)
Kısa vade tahmini = model (çok faktörlü) + fiyat itkisi. Varsayılan ağırlık 70/30; öğrenilmiş ağırlık yalnız t ≥ 2 ve isabet ≥ 70/30 ise canlıya alınır.

| Varlık | Durum | Öğrenilmiş model/fiyat | IC | t | Öğrenilmiş | 70/30 | Yalnız fiyat | Hep AL |
|---|---|---|---|---|---|---|---|---|
| BTC | 70/30 | None/None | -0.027 | -1.7 | %48.0 | %48.2 | %49.1 | %50.4 |
| ETH | 70/30 | 0.2664/0.7336 | -0.028 | -1.7 | %47.7 | %48.3 | %48.6 | %50.9 |
| NQ | 70/30 | 0.0/1.0 | +0.015 | +0.9 | %50.5 | %50.2 | %50.1 | %53.2 |
| SPX | 70/30 | 0.0/1.0 | +0.015 | +0.9 | %50.1 | %48.7 | %49.6 | %53.2 |
| XAG | 70/30 | 1.0/0.0 | -0.002 | -0.1 | %48.6 | %48.5 | %48.7 | %51.9 |
| XAU | 70/30 | 1.0/0.0 | +0.002 | +0.1 | %50.1 | %49.3 | %50.2 | %51.6 |

## Faktör bilgi katsayısı (IC) — hangi faktör gerçekten öncü?
IC = faktörün (işareti düzeltilmiş) değeri ile sonraki getirinin sıra korelasyonu. **+0,03 ve üzeri** kurumsal ölçekte anlamlı kabul edilir; negatif IC = faktör ters çalışıyor. t = IC·√(bağımsız örnek); |t| ≥ 2 istatistiksel olarak güvenilir.

### BTC
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n | 3 dönem IC 24s | Tanı |
|---|---|---|---|---|---|---|---|
| Fed Net Dolar Likiditesi (NDL) | A | +0.041 | +0.064 | +1.0 | 8372 | +0.008 +0.074 -0.013 | 〰️ kararsız |
| BTC Dominansı / Altcoin Rotasyonu | E | +0.040 | +0.049 | +0.8 | 8372 | +0.102 +0.000 +0.014 | 〰️ kararsız |
| DXY Dolar Likidite Baskısı | A | +0.025 | +0.032 | +0.5 | 8372 | +0.067 -0.011 +0.009 | 〰️ kararsız |
| Geleneksel Bankacılık Kaçışı (KRE Ters) | C | +0.022 | +0.015 | +0.2 | 8372 | +0.022 +0.054 -0.002 | 〰️ kararsız |
| 🪤 Likidite Avı (Stop Süpürme) Sinyali | E | +0.004 | +0.014 | +0.2 | 8372 | +0.030 +0.017 -0.032 | 〰️ kararsız |
| USD/JPY Carry & Risk-On Likiditesi | A | +0.012 | +0.010 | +0.2 | 8372 | -0.036 +0.057 +0.013 | 〰️ kararsız |
| Reel Getiri Baskısı (TIP) | B | -0.026 | +0.008 | +0.1 | 8372 | -0.058 +0.069 -0.071 | 〰️ kararsız |
| 🤖 CTA Trend Fonu Pozisyonu (Tahmini) | E | -0.013 | -0.027 | -0.4 | 8372 | -0.051 -0.026 -0.044 | ⛔ 3/3 TERS (rol: durum?) |
| TLT Küresel Tahvil Likidite Baskısı | B | -0.061 | -0.035 | -0.5 | 8372 | -0.102 +0.012 -0.098 | 〰️ kararsız |
| BTC 4H Anlık Fiyat İvmesi | E | -0.023 | -0.044 | -0.7 | 8372 | -0.038 -0.018 -0.021 | 〰️ kararsız |
| Sistemik Volatilite Baskısı | C | -0.055 | -0.047 | -0.7 | 8372 | -0.052 -0.025 -0.075 | ⛔ 3/3 TERS (rol: durum?) |
| Küresel Likidite İştahı (HYG/LQD) | C | -0.017 | -0.050 | -0.8 | 8372 | -0.028 -0.077 +0.049 | 〰️ kararsız |

### ETH
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n | 3 dönem IC 24s | Tanı |
|---|---|---|---|---|---|---|---|
| Fed Net Dolar Likiditesi (NDL) | A | +0.033 | +0.045 | +0.7 | 8372 | -0.053 +0.127 -0.014 | 〰️ kararsız |
| DXY Dolar Likidite Baskısı | A | +0.019 | +0.040 | +0.6 | 8372 | +0.061 -0.006 -0.009 | 〰️ kararsız |
| 🪤 Likidite Avı (Stop Süpürme) Sinyali | E | +0.036 | +0.026 | +0.4 | 8372 | +0.035 +0.000 +0.080 | 〰️ kararsız |
| Reel Getiri Baskısı (TIP) | B | -0.020 | +0.024 | +0.4 | 8372 | -0.057 +0.066 -0.061 | 〰️ kararsız |
| 🤖 CTA Trend Fonu Pozisyonu (Tahmini) | E | +0.009 | +0.014 | +0.2 | 8372 | +0.002 +0.027 -0.011 | 〰️ kararsız |
| USD/JPY Carry Likiditesi | A | -0.001 | +0.001 | +0.0 | 8372 | -0.049 +0.037 +0.006 | 〰️ kararsız |
| Kurumsal Kredi & Likidite | C | +0.010 | -0.015 | -0.2 | 8372 | -0.015 -0.021 +0.074 | 〰️ kararsız |
| ⚡ Bitcoin İtici Gücü (BTC Beta) | E | -0.013 | -0.016 | -0.2 | 8372 | -0.034 +0.021 -0.029 | 〰️ kararsız |
| Sistemik Volatilite Baskısı | C | -0.030 | -0.024 | -0.4 | 8372 | +0.003 -0.014 -0.075 | 〰️ kararsız |
| TLT Likidite Baskısı | B | -0.053 | -0.038 | -0.6 | 8372 | -0.063 +0.013 -0.126 | 〰️ kararsız |
| ETH 4H Anlık Fiyat İvmesi | E | -0.024 | -0.051 | -0.8 | 8372 | -0.063 +0.033 -0.051 | 〰️ kararsız |
| ETH/BTC Göreceli Güç (Risk İştahı) | E | -0.044 | -0.076 | -1.2 | 8372 | -0.089 -0.005 -0.039 | 〰️ kararsız |

### NQ
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n | 3 dönem IC 24s | Tanı |
|---|---|---|---|---|---|---|---|
| 🔮 CBOE SKEW Kuyruk Riski Fiyatlaması (Öncü) | E | +0.044 | +0.070 | +1.1 | 8351 | +0.005 -0.045 +0.160 | 〰️ kararsız |
| ARKK/QQQ Yüksek Beta Spekülasyon | E | +0.035 | +0.065 | +1.0 | 8351 | +0.065 +0.070 -0.028 | 〰️ kararsız |
| Teknoloji Değerleme / Reel Getiri Baskısı | B | +0.025 | +0.056 | +0.9 | 8351 | +0.022 +0.118 -0.040 | 〰️ kararsız |
| Finansal Sistem Likidite Stresi (KRE) | C | +0.037 | +0.050 | +0.8 | 8351 | +0.079 +0.037 -0.007 | 〰️ kararsız |
| Çip & Yüksek Beta Ayrışması | E | +0.041 | +0.038 | +0.6 | 8351 | +0.078 -0.042 +0.072 | 〰️ kararsız |
| Fed Net Dolar Likiditesi (NDL) | A | +0.004 | +0.028 | +0.4 | 8351 | -0.065 +0.054 +0.009 | 〰️ kararsız |
| Petrol / Enerji Baskısı | D | -0.016 | +0.025 | +0.4 | 8351 | +0.025 -0.071 -0.032 | 〰️ kararsız |
| DXY Dolar Likidite Sıkışması | A | +0.021 | +0.022 | +0.3 | 8351 | +0.018 +0.025 +0.012 | 〰️ kararsız |
| 🔮 VXN/VIX Teknoloji Volatilite Primi (Öncü) | E | -0.011 | +0.020 | +0.3 | 8351 | -0.015 +0.012 -0.024 | 〰️ kararsız |
| XLU/QQQ Kurumsal Defansif Kaçış | E | -0.044 | +0.010 | +0.2 | 8351 | -0.031 -0.092 -0.012 | 〰️ kararsız |
| SMH Çip / AI Sektör İvmesi | E | +0.014 | +0.008 | +0.1 | 8351 | +0.041 -0.057 +0.040 | 〰️ kararsız |
| Kredi Piyasası Gücü (HYG/LQD) | C | -0.004 | -0.004 | -0.1 | 8351 | +0.050 -0.100 +0.005 | 〰️ kararsız |
| USD/JPY Carry Tasfiye Riski | A | -0.020 | -0.012 | -0.2 | 8351 | +0.020 -0.091 +0.010 | 〰️ kararsız |
| NQ 4H Anlık Fiyat Hızı | E | -0.026 | -0.016 | -0.2 | 8351 | -0.014 -0.081 +0.003 | 〰️ kararsız |
| TLT Tahvil Süre Duyarlılığı | B | +0.011 | -0.018 | -0.3 | 8351 | -0.033 +0.107 -0.041 | 〰️ kararsız |
| 🎯 NQ/SPX Adaptif Ayrışma (Rezidüel) | E | -0.019 | -0.029 | -0.4 | 8351 | -0.026 -0.064 +0.029 | 〰️ kararsız |
| 🪤 Likidite Avı (Stop Süpürme) Sinyali | E | -0.024 | -0.033 | -0.5 | 8351 | -0.024 -0.016 -0.030 | 〰️ kararsız |
| ⚖️ Volatilite Hedefli Fon Akışı (Tahmini) | C | -0.023 | -0.035 | -0.5 | 8351 | +0.110 -0.095 -0.091 | 〰️ kararsız |
| Teknoloji Volatilite Baskısı | C | -0.029 | -0.043 | -0.7 | 8351 | +0.042 -0.115 -0.033 | 〰️ kararsız |
| 🤖 CTA Trend Fonu Pozisyonu (Tahmini) | E | -0.030 | -0.083 | -1.3 | 8351 | -0.028 -0.072 -0.015 | 〰️ kararsız |
| VIX Vade Eğrisi & Gamma Stresi | C | -0.072 | -0.110 | -1.7 | 8351 | +0.011 -0.193 -0.074 | 〰️ kararsız |
| 🔮 VIX Vade Yapısı Öncü Sinyali (Backwardation/Contango) | E | -0.072 | -0.110 | -1.7 | 8351 | +0.012 -0.195 -0.074 | 〰️ kararsız |

### SPX
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n | 3 dönem IC 24s | Tanı |
|---|---|---|---|---|---|---|---|
| 🔮 CBOE SKEW Kuyruk Riski Fiyatlaması (Öncü) | E | +0.036 | +0.075 | +1.1 | 8351 | +0.023 -0.063 +0.133 | 〰️ kararsız |
| KRE/SPY Bölgesel Bankacılık Likiditesi | C | +0.029 | +0.059 | +0.9 | 8351 | +0.082 +0.026 -0.027 | 〰️ kararsız |
| 10Y Reel Faiz Değerleme Baskısı | B | +0.016 | +0.040 | +0.6 | 8351 | +0.013 +0.128 -0.070 | 〰️ kararsız |
| Fed Net Dolar Likiditesi (NDL) | A | +0.004 | +0.036 | +0.6 | 8351 | -0.067 +0.048 +0.026 | 〰️ kararsız |
| 🪤 Likidite Avı (Stop Süpürme) Sinyali | E | +0.019 | +0.034 | +0.5 | 8351 | +0.029 +0.037 -0.008 | 〰️ kararsız |
| 🎯 SPX/NQ Adaptif Ayrışma (Rezidüel) | E | +0.012 | +0.025 | +0.4 | 8351 | -0.002 +0.045 -0.010 | 〰️ kararsız |
| DXY Kısa Vade Dolar Baskısı | A | +0.025 | +0.021 | +0.3 | 8351 | +0.031 +0.016 +0.019 | 〰️ kararsız |
| XLU/SPY Kurumsal Defansif Kaçış | E | -0.036 | +0.011 | +0.2 | 8351 | -0.063 -0.060 +0.016 | 〰️ kararsız |
| HYG/LQD Kredi Gücü & İştahı | C | -0.004 | +0.001 | +0.0 | 8351 | +0.045 -0.080 +0.001 | 〰️ kararsız |
| Petrol / Ticaret (IYT) Şoku | D | -0.026 | -0.001 | -0.0 | 8351 | +0.040 -0.092 -0.059 | 〰️ kararsız |
| USD/JPY Carry & Küresel Likidite | A | -0.032 | -0.005 | -0.1 | 8351 | -0.010 -0.082 -0.002 | 〰️ kararsız |
| RSP/SPY Piyasa Katılım Genişliği | E | -0.002 | -0.017 | -0.3 | 8351 | -0.044 +0.020 +0.006 | 〰️ kararsız |
| SMH Çip / AI Sektör İvmesi | E | +0.001 | -0.017 | -0.3 | 8351 | +0.012 -0.052 +0.030 | 〰️ kararsız |
| ES 4H Anlık Fiyat Hızı | E | -0.022 | -0.019 | -0.3 | 8351 | -0.011 -0.063 +0.001 | 〰️ kararsız |
| TLT/SHY Uzun Vade Tahvil Süre Riski | B | +0.017 | -0.020 | -0.3 | 8351 | -0.012 +0.128 -0.068 | 〰️ kararsız |
| XLY/XLP Tüketici Talebi & Büyüme | E | -0.026 | -0.032 | -0.5 | 8351 | +0.023 -0.064 -0.049 | 〰️ kararsız |
| VIX Opsiyon Korku Primi | C | -0.041 | -0.062 | -1.0 | 8351 | +0.017 -0.120 -0.039 | 〰️ kararsız |
| ⚖️ Volatilite Hedefli Fon Akışı (Tahmini) | C | -0.029 | -0.064 | -1.0 | 8351 | +0.054 -0.104 -0.055 | 〰️ kararsız |
| 🤖 CTA Trend Fonu Pozisyonu (Tahmini) | E | -0.058 | -0.134 | -2.1 | 8351 | -0.037 -0.118 -0.095 | ⛔ 3/3 TERS (rol: durum?) |
| VIX/VIX3M Dealer Gamma & Vade Eğrisi | C | -0.086 | -0.148 | -2.3 | 8351 | -0.021 -0.186 -0.087 | ⛔ 3/3 TERS (rol: durum?) |
| 🔮 VIX Vade Yapısı Öncü Sinyali (Backwardation/Contango) | E | -0.085 | -0.148 | -2.3 | 8351 | -0.019 -0.187 -0.086 | 〰️ kararsız |

### XAG
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n | 3 dönem IC 24s | Tanı |
|---|---|---|---|---|---|---|---|
| 🤖 CTA Trend Fonu Pozisyonu (Tahmini) | E | +0.053 | +0.068 | +1.0 | 8350 | -0.146 +0.058 -0.088 | 〰️ kararsız |
| Gümüş / Bakır Sanayi Rotasyonu | D | -0.017 | +0.036 | +0.5 | 8350 | -0.063 +0.040 -0.085 | 〰️ kararsız |
| 10Y Reel Faiz Baskısı (TIP) | B | +0.010 | +0.034 | +0.5 | 8350 | -0.037 +0.023 +0.023 | 〰️ kararsız |
| USD Gücü & Dolar Baskısı | A | -0.003 | +0.028 | +0.4 | 8350 | -0.039 +0.001 +0.013 | 〰️ kararsız |
| Gümüş 4H/24H Trend İvmesi | E | -0.007 | +0.025 | +0.4 | 8350 | -0.046 +0.013 -0.044 | 〰️ kararsız |
| 🥈 Gümüş Parasal Yakalama & Değerleme İvmesi | E | +0.016 | +0.020 | +0.3 | 8350 | -0.012 +0.074 -0.041 | 〰️ kararsız |
| 🥇 Altın Çapa / Beta (Adaptif) | E | -0.029 | +0.006 | +0.1 | 8350 | -0.068 -0.036 -0.046 | ⛔ 3/3 TERS (rol: durum?) |
| Küresel Kredi & Sanayi İştahı | C | +0.028 | +0.001 | +0.0 | 8350 | +0.069 -0.012 +0.032 | 〰️ kararsız |
| Bakır/Altın Sanayi Talebi | D | +0.031 | -0.019 | -0.3 | 8350 | +0.080 +0.010 +0.068 | 〰️ kararsız |
| 🎯 XAU/XAG Adaptif Ayrışma (Rezidüel) | E | +0.002 | -0.022 | -0.3 | 8350 | -0.002 +0.008 -0.003 | 〰️ kararsız |
| 🪤 Likidite Avı (Stop Süpürme) Sinyali | E | +0.007 | -0.026 | -0.4 | 8350 | +0.023 +0.003 +0.011 | 〰️ kararsız |
| Fed Net Dolar Likiditesi (NDL) | A | -0.040 | -0.028 | -0.4 | 8350 | -0.006 -0.125 -0.041 | 〰️ kararsız |
| TLT Tahvil Getiri Baskısı | B | -0.040 | -0.029 | -0.4 | 8350 | -0.141 +0.028 -0.032 | 〰️ kararsız |
| 🔮 GVZ Çapraz-Volatilite Rejimi (Öncü) | E | -0.068 | -0.072 | -1.1 | 8350 | +0.037 -0.020 -0.095 | 〰️ kararsız |
| Enflasyon Beklenti Kalkanı | B | -0.089 | -0.123 | -1.9 | 8350 | -0.036 -0.140 -0.053 | ⛔ 3/3 TERS (rol: durum?) |
| 🔮 VXSLV Opsiyon Volatilite Primi (Öncü) | E | -0.115 | -0.129 | -1.6 | 5842 | +0.020 -0.014 -0.083 | 〰️ kararsız |

### XAU
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n | 3 dönem IC 24s | Tanı |
|---|---|---|---|---|---|---|---|
| 🤖 CTA Trend Fonu Pozisyonu (Tahmini) | E | +0.059 | +0.071 | +1.1 | 8350 | -0.103 +0.034 -0.142 | 〰️ kararsız |
| Bakır/Altın Sanayi Döngüsü | D | +0.014 | +0.051 | +0.8 | 8350 | -0.030 +0.068 -0.051 | 〰️ kararsız |
| Dolar Rezerv / Net Likidite İvmesi | A | +0.030 | +0.039 | +0.6 | 8350 | +0.058 -0.023 -0.023 | 〰️ kararsız |
| 10Y Reel Faiz (TIPS Ters Oran) | B | +0.027 | +0.034 | +0.5 | 8350 | +0.006 +0.007 +0.027 | 〰️ kararsız |
| Jeopolitik & Güvenli Liman | C | +0.041 | +0.022 | +0.3 | 8350 | +0.005 +0.023 +0.087 | 〰️ kararsız |
| 🪤 Likidite Avı (Stop Süpürme) Sinyali | E | +0.007 | +0.017 | +0.3 | 8350 | -0.025 -0.014 +0.058 | 〰️ kararsız |
| Altın / Petrol Şoku (Stagflasyon) | D | -0.006 | +0.016 | +0.2 | 8350 | +0.021 +0.032 -0.125 | 〰️ kararsız |
| Altın Hızlı 2H/16H Anlık İvme | E | +0.009 | +0.013 | +0.2 | 8350 | +0.004 +0.008 -0.035 | 〰️ kararsız |
| 🥇 DXY/Tahvil Öncü Altın İmpulsu | E | +0.007 | +0.009 | +0.1 | 8350 | +0.040 -0.012 -0.008 | 〰️ kararsız |
| DXY Spot Dolar Baskısı | A | -0.009 | +0.003 | +0.0 | 8350 | -0.028 +0.000 -0.017 | 〰️ kararsız |
| Bankacılık Güven Krizi Primi (KRE) | C | +0.026 | -0.008 | -0.1 | 8350 | -0.010 +0.043 +0.055 | 〰️ kararsız |
| 🔮 GVZ Opsiyon Volatilite Primi (Öncü) | E | -0.029 | -0.008 | -0.1 | 8350 | +0.068 +0.024 -0.038 | 〰️ kararsız |
| 🏛️ Merkez Bankası & Jeopolitik Rezerv Talebi | E | -0.021 | -0.013 | -0.2 | 8350 | -0.030 -0.034 -0.045 | ⛔ 3/3 TERS (rol: durum?) |
| Altın/Gümüş Rasyosu (GSR) | D | -0.011 | -0.034 | -0.5 | 8350 | +0.071 -0.085 +0.008 | 〰️ kararsız |
| TLT Uzun Vade Tahvil Gücü | B | -0.058 | -0.037 | -0.6 | 8350 | -0.127 -0.029 -0.042 | ⛔ 3/3 TERS (rol: durum?) |
| Enflasyon Beklenti Kalkanı | B | -0.044 | -0.052 | -0.8 | 8350 | +0.041 -0.006 -0.113 | 〰️ kararsız |

