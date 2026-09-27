# 🧪 Tarihsel Doğrulama Raporu (walk-forward, zaman-noktası doğru)

_Son güncelleme: 2026-09-27T19:11:11.873008+00:00 · döngü: 16777 · kayıt: 3000 (notlanan: 2985)_

Bu sayfa sistemin **yayınladığı nihai sinyalleri** gerçekleşen fiyatla notlar. Model bu sayfadan öğrenmez; sadece hakemdir. Bir satırın güvenilir olması için en az **30** bağımsız (çakışmayan) örnek gerekir.

**Nasıl okunur:** *isabet* = yön doğru tahmin oranı · *ort bps* = sinyal yönünde ortalama getiri (1 bps = %0,01) · *alt sınır* = %95 güvenle gerçek isabetin en az bu kadar olduğu değer. Model, **Hep AL** ve **Trend takibi** (fiyatın gidişine bakan reaktif yöntem) ile AYNI anlarda karşılaştırılır.

## Genel
### 4 saat sonrası
- **Model:** %51.0 isabet · ort +0 bps · n=1360 (bağımsız 397, alt sınır %47)
- Hep AL: %51.7 isabet · ort +2 bps · n=1360 (bağımsız 397, alt sınır %48)
- Trend takibi: %49.3 isabet · ort -3 bps · n=1301 (bağımsız 394, alt sınır %45)
- Sadece giriş izni verilenler: %51.0 isabet · ort -4 bps · n=578 (bağımsız 228, alt sınır %46)
- Zamanlama notu A: %50.4 isabet · ort -2 bps · n=698 (bağımsız 222, alt sınır %45)
- Zamanlama notu B: %52.7 isabet · ort +5 bps · n=294 (bağımsız 124, alt sınır %45)
- Zamanlama notu C: %50.8 isabet · ort +0 bps · n=368 (bağımsız 151, alt sınır %44)
- Sonuç: 🔴 Model basit yöntemlerin gerisinde (-0.7 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### 24 saat sonrası
- **Model:** %50.3 isabet · ort -7 bps · n=1346 (bağımsız 100, alt sınır %42)
- Hep AL: %52.5 isabet · ort +29 bps · n=1346 (bağımsız 100, alt sınır %44)
- Trend takibi: %46.0 isabet · ort -3 bps · n=1287 (bağımsız 100, alt sınır %38)
- Sadece giriş izni verilenler: %47.5 isabet · ort -6 bps · n=571 (bağımsız 83, alt sınır %39)
- Zamanlama notu A: %40.6 isabet · ort -22 bps · n=694 (bağımsız 72, alt sınır %32)
- Zamanlama notu B: %62.2 isabet · ort +37 bps · n=291 (bağımsız 55, alt sınır %51)
- Zamanlama notu C: %59.3 isabet · ort -12 bps · n=361 (bağımsız 56, alt sınır %48)
- Sonuç: 🔴 Model basit yöntemlerin gerisinde (-2.2 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### 72 saat sonrası
- **Model:** %40.7 isabet · ort -57 bps · n=1236 (bağımsız 43, alt sınır %29)
- Hep AL: %61.3 isabet · ort +105 bps · n=1236 (bağımsız 43, alt sınır %49)
- Trend takibi: %41.6 isabet · ort -26 bps · n=1190 (bağımsız 43, alt sınır %30)
- Sadece giriş izni verilenler: %38.4 isabet · ort -35 bps · n=508 (bağımsız 38, alt sınır %27)
- Zamanlama notu A: %30.6 isabet · ort -78 bps · n=637 (bağımsız 37, alt sınır %20)
- Zamanlama notu B: %61.3 isabet · ort +27 bps · n=261 (bağımsız 28, alt sınır %46) ⚠️az bağımsız örnek
- Zamanlama notu C: %43.8 isabet · ort -82 bps · n=338 (bağımsız 30, alt sınır %30)
- Sonuç: 🔴 Model basit yöntemlerin gerisinde (-20.6 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### 120 saat sonrası
- **Model:** %39.2 isabet · ort -53 bps · n=1131 (bağımsız 22, alt sınır %24) ⚠️az bağımsız örnek
- Hep AL: %64.5 isabet · ort +141 bps · n=1131 (bağımsız 22, alt sınır %47) ⚠️az bağımsız örnek
- Trend takibi: %42.8 isabet · ort -57 bps · n=1092 (bağımsız 22, alt sınır %27) ⚠️az bağımsız örnek
- Sadece giriş izni verilenler: %35.8 isabet · ort -40 bps · n=458 (bağımsız 20, alt sınır %21) ⚠️az bağımsız örnek
- Zamanlama notu A: %36.8 isabet · ort -89 bps · n=592 (bağımsız 20, alt sınır %22) ⚠️az bağımsız örnek
- Zamanlama notu B: %44.7 isabet · ort +61 bps · n=219 (bağımsız 19, alt sınır %28) ⚠️az bağımsız örnek
- Zamanlama notu C: %39.7 isabet · ort -62 bps · n=320 (bağımsız 19, alt sınır %24) ⚠️az bağımsız örnek
- Sonuç: Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

## Varlık bazında (24 saat ve 72 saat)
### BTC
- 24s Model: %57.7 isabet · ort -8 bps · n=357 (bağımsız 23, alt sınır %41) ⚠️az bağımsız örnek
  - Hep AL: %46.8 isabet · ort +44 bps · n=357 (bağımsız 23, alt sınır %31) ⚠️az bağımsız örnek · Trend: %52.0 isabet · ort +41 bps · n=342 (bağımsız 23, alt sınır %36) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %48.8 isabet · ort -72 bps · n=326 (bağımsız 9, alt sınır %25) ⚠️az bağımsız örnek
  - Hep AL: %51.8 isabet · ort +113 bps · n=326 (bağımsız 9, alt sınır %27) ⚠️az bağımsız örnek · Trend: %61.3 isabet · ort +98 bps · n=320 (bağımsız 9, alt sınır %35) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### ETH
- 24s Model: %47.3 isabet · ort -15 bps · n=279 (bağımsız 21, alt sınır %31) ⚠️az bağımsız örnek
  - Hep AL: %54.8 isabet · ort +71 bps · n=279 (bağımsız 21, alt sınır %37) ⚠️az bağımsız örnek · Trend: %46.0 isabet · ort -24 bps · n=263 (bağımsız 21, alt sınır %30) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %33.3 isabet · ort -90 bps · n=267 (bağımsız 8, alt sınır %13) ⚠️az bağımsız örnek
  - Hep AL: %77.2 isabet · ort +260 bps · n=267 (bağımsız 8, alt sınır %48) ⚠️az bağımsız örnek · Trend: %34.5 isabet · ort -103 bps · n=255 (bağımsız 8, alt sınır %14) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### NQ
- 24s Model: %50.6 isabet · ort -3 bps · n=170 (bağımsız 12, alt sınır %29) ⚠️az bağımsız örnek
  - Hep AL: %57.6 isabet · ort +11 bps · n=170 (bağımsız 12, alt sınır %35) ⚠️az bağımsız örnek · Trend: %40.1 isabet · ort -17 bps · n=162 (bağımsız 12, alt sınır %21) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %52.0 isabet · ort -16 bps · n=171 (bağımsız 6, alt sınır %24) ⚠️az bağımsız örnek
  - Hep AL: %53.2 isabet · ort +45 bps · n=171 (bağımsız 6, alt sınır %24) ⚠️az bağımsız örnek · Trend: %45.4 isabet · ort -30 bps · n=163 (bağımsız 6, alt sınır %19) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### SPX
- 24s Model: %48.8 isabet · ort -7 bps · n=168 (bağımsız 13, alt sınır %28) ⚠️az bağımsız örnek
  - Hep AL: %51.2 isabet · ort +7 bps · n=168 (bağımsız 13, alt sınır %30) ⚠️az bağımsız örnek · Trend: %45.6 isabet · ort -12 bps · n=158 (bağımsız 13, alt sınır %26) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %26.9 isabet · ort -41 bps · n=160 (bağımsız 6, alt sınır %8) ⚠️az bağımsız örnek
  - Hep AL: %68.1 isabet · ort +33 bps · n=160 (bağımsız 6, alt sınır %36) ⚠️az bağımsız örnek · Trend: %22.7 isabet · ort -47 bps · n=150 (bağımsız 6, alt sınır %6) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAG
- 24s Model: %43.2 isabet · ort +7 bps · n=132 (bağımsız 13, alt sınır %24) ⚠️az bağımsız örnek
  - Hep AL: %58.3 isabet · ort +3 bps · n=132 (bağımsız 13, alt sınır %36) ⚠️az bağımsız örnek · Trend: %36.2 isabet · ort -47 bps · n=127 (bağımsız 13, alt sınır %19) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %37.0 isabet · ort -64 bps · n=108 (bağımsız 7, alt sınır %15) ⚠️az bağımsız örnek
  - Hep AL: %63.0 isabet · ort +49 bps · n=108 (bağımsız 7, alt sınır %34) ⚠️az bağımsız örnek · Trend: %24.3 isabet · ort -143 bps · n=103 (bağımsız 7, alt sınır %8) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAU
- 24s Model: %47.5 isabet · ort -5 bps · n=240 (bağımsız 18, alt sınır %30) ⚠️az bağımsız örnek
  - Hep AL: %52.5 isabet · ort +3 bps · n=240 (bağımsız 18, alt sınır %34) ⚠️az bağımsız örnek · Trend: %46.8 isabet · ort -5 bps · n=235 (bağımsız 18, alt sınır %29) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %40.7 isabet · ort -34 bps · n=204 (bağımsız 7, alt sınır %17) ⚠️az bağımsız örnek
  - Hep AL: %56.4 isabet · ort +28 bps · n=204 (bağımsız 7, alt sınır %28) ⚠️az bağımsız örnek · Trend: %39.2 isabet · ort -45 bps · n=199 (bağımsız 7, alt sınır %16) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

## Rejim bazında (Model)
- Rejim 1: 24s %25.3 isabet · ort -52 bps · n=297 (bağımsız 25, alt sınır %14) ⚠️az bağımsız örnek · 72s %29.5 isabet · ort -136 bps · n=298 (bağımsız 13, alt sınır %14) ⚠️az bağımsız örnek
- Rejim 2: 24s %54.3 isabet · ort +15 bps · n=173 (bağımsız 12, alt sınır %32) ⚠️az bağımsız örnek · 72s %25.0 isabet · ort -29 bps · n=76 (bağımsız 4, alt sınır %6) ⚠️az bağımsız örnek
- Rejim 3: 24s %55.7 isabet · ort +10 bps · n=528 (bağımsız 40, alt sınır %43) · 72s %36.8 isabet · ort -66 bps · n=514 (bağımsız 17, alt sınır %21) ⚠️az bağımsız örnek
- Rejim 4: 24s %61.5 isabet · ort -4 bps · n=348 (bağımsız 34, alt sınır %47) · 72s %59.5 isabet · ort +17 bps · n=348 (bağımsız 14, alt sınır %38) ⚠️az bağımsız örnek

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
- Dönem: 2024-10-26 20:00:00+00:00 → 2026-09-25 20:00:00+00:00 · adım: 1.0 saat · döngü: 16777 · hata: 0
- Sistem her an için SADECE o ana kadar var olan veriyle, canlı arka plan döngüsünün birebir aynısıyla çalıştırıldı (saat dondurularak).
- Tüm adaptif hafızalar dönem başında sıfırdan başladı ve sadece geçmişten öğrendi.
- ⚠️ OKX/Bybit taker akışı & fonlama oranı geçmişi olmadığı için BTC/ETH'de bu öncü faktörler replay'de yok (tutucu yanlılık).
- ⚠️ FRED serileri güncel vintage ile kullanıldı (piyasa serileri nadiren revize edilir).

## Faktör bilgi katsayısı (IC) — hangi faktör gerçekten öncü?
IC = faktörün (işareti düzeltilmiş) değeri ile sonraki getirinin sıra korelasyonu. **+0,03 ve üzeri** kurumsal ölçekte anlamlı kabul edilir; negatif IC = faktör ters çalışıyor. t = IC·√(bağımsız örnek); |t| ≥ 2 istatistiksel olarak güvenilir.

### BTC
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n |
|---|---|---|---|---|---|
| Fed Net Dolar Likiditesi (NDL) | A | +0.067 | +0.101 | +1.5 | 16746 |
| BTC Dominansı / Altcoin Rotasyonu | E | +0.051 | +0.056 | +0.8 | 16746 |
| DXY Dolar Likidite Baskısı | A | +0.032 | +0.028 | +0.4 | 16746 |
| Geleneksel Bankacılık Kaçışı (KRE Ters) | C | +0.021 | +0.021 | +0.3 | 16746 |
| USD/JPY Carry & Risk-On Likiditesi | A | +0.011 | +0.016 | +0.2 | 16746 |
| Reel Getiri Baskısı (TIP) | B | -0.010 | +0.001 | +0.0 | 16746 |
| BTC 4H Anlık Fiyat İvmesi | E | -0.012 | -0.028 | -0.4 | 16746 |
| Sistemik Volatilite Baskısı | C | -0.048 | -0.035 | -0.5 | 16746 |
| TLT Küresel Tahvil Likidite Baskısı | B | -0.046 | -0.041 | -0.6 | 16746 |
| Küresel Likidite İştahı (HYG/LQD) | C | -0.015 | -0.055 | -0.8 | 16746 |

### ETH
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n |
|---|---|---|---|---|---|
| Fed Net Dolar Likiditesi (NDL) | A | +0.041 | +0.055 | +0.8 | 16746 |
| DXY Dolar Likidite Baskısı | A | +0.025 | +0.042 | +0.6 | 16746 |
| USD/JPY Carry Likiditesi | A | -0.005 | +0.004 | +0.1 | 16746 |
| ⚡ Bitcoin İtici Gücü (BTC Beta) | E | -0.003 | -0.005 | -0.1 | 16746 |
| Sistemik Volatilite Baskısı | C | -0.021 | -0.015 | -0.2 | 16746 |
| Kurumsal Kredi & Likidite | C | +0.012 | -0.022 | -0.3 | 16746 |
| TLT Likidite Baskısı | B | -0.041 | -0.038 | -0.6 | 16746 |
| ETH 4H Anlık Fiyat İvmesi | E | -0.019 | -0.039 | -0.6 | 16746 |
| ⛓️ L1 Ağ Aktivitesi & DeFi Likidite İvmesi | E | -0.046 | -0.068 | -1.0 | 16746 |
| ETH/BTC Göreceli Güç (Risk İştahı) | E | -0.051 | -0.074 | -1.1 | 16746 |

### NQ
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n |
|---|---|---|---|---|---|
| ARKK/QQQ Yüksek Beta Spekülasyon | E | +0.061 | +0.081 | +1.2 | 16677 |
| Teknoloji Değerleme / Reel Getiri Baskısı | B | +0.037 | +0.052 | +0.8 | 16677 |
| Finansal Sistem Likidite Stresi (KRE) | C | +0.036 | +0.042 | +0.6 | 16677 |
| 🔮 VXN/VIX Teknoloji Volatilite Primi (Öncü) | E | -0.003 | +0.041 | +0.6 | 16677 |
| 🔮 CBOE SKEW Kuyruk Riski Fiyatlaması (Öncü) | E | +0.023 | +0.038 | +0.6 | 16677 |
| Çip & Yüksek Beta Ayrışması | E | +0.032 | +0.027 | +0.4 | 16677 |
| DXY Dolar Likidite Sıkışması | A | +0.011 | +0.014 | +0.2 | 16677 |
| Fed Net Dolar Likiditesi (NDL) | A | -0.004 | +0.012 | +0.2 | 16677 |
| XLU/QQQ Kurumsal Defansif Kaçış | E | -0.041 | +0.012 | +0.2 | 16677 |
| Kredi Piyasası Gücü (HYG/LQD) | C | +0.005 | +0.001 | +0.0 | 16677 |
| Petrol / Enerji Baskısı | D | -0.025 | +0.000 | +0.0 | 16677 |
| SMH Çip / AI Sektör İvmesi | E | +0.006 | -0.007 | -0.1 | 16677 |
| TLT Tahvil Süre Duyarlılığı | B | +0.025 | -0.007 | -0.1 | 16677 |
| NQ 4H Anlık Fiyat Hızı | E | -0.018 | -0.012 | -0.2 | 16677 |
| USD/JPY Carry Tasfiye Riski | A | -0.022 | -0.018 | -0.3 | 16677 |
| 🎯 NQ/SPX Adaptif Ayrışma (Rezidüel) | E | -0.025 | -0.027 | -0.4 | 16677 |
| Teknoloji Volatilite Baskısı | C | -0.025 | -0.046 | -0.7 | 16677 |
| 🔮 VIX Vade Yapısı Öncü Sinyali (Backwardation/Contango) | E | -0.075 | -0.114 | -1.7 | 16677 |
| VIX Vade Eğrisi & Gamma Stresi | C | -0.076 | -0.114 | -1.7 | 16677 |

### SPX
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n |
|---|---|---|---|---|---|
| KRE/SPY Bölgesel Bankacılık Likiditesi | C | +0.022 | +0.047 | +0.7 | 16676 |
| 🔮 CBOE SKEW Kuyruk Riski Fiyatlaması (Öncü) | E | +0.019 | +0.046 | +0.7 | 16676 |
| 10Y Reel Faiz Değerleme Baskısı | B | +0.028 | +0.041 | +0.6 | 16676 |
| Fed Net Dolar Likiditesi (NDL) | A | +0.000 | +0.028 | +0.4 | 16676 |
| 🎯 SPX/NQ Adaptif Ayrışma (Rezidüel) | E | +0.018 | +0.027 | +0.4 | 16676 |
| XLU/SPY Kurumsal Defansif Kaçış | E | -0.034 | +0.015 | +0.2 | 16676 |
| DXY Kısa Vade Dolar Baskısı | A | +0.017 | +0.014 | +0.2 | 16676 |
| HYG/LQD Kredi Gücü & İştahı | C | +0.002 | +0.005 | +0.1 | 16676 |
| RSP/SPY Piyasa Katılım Genişliği | E | +0.018 | +0.003 | +0.0 | 16676 |
| ES 4H Anlık Fiyat Hızı | E | -0.015 | -0.010 | -0.2 | 16676 |
| TLT/SHY Uzun Vade Tahvil Süre Riski | B | +0.030 | -0.013 | -0.2 | 16676 |
| USD/JPY Carry & Küresel Likidite | A | -0.040 | -0.014 | -0.2 | 16676 |
| SMH Çip / AI Sektör İvmesi | E | +0.002 | -0.019 | -0.3 | 16676 |
| Petrol / Ticaret (IYT) Şoku | D | -0.030 | -0.027 | -0.4 | 16676 |
| XLY/XLP Tüketici Talebi & Büyüme | E | -0.024 | -0.037 | -0.6 | 16676 |
| VIX Opsiyon Korku Primi | C | -0.039 | -0.069 | -1.1 | 16676 |
| 🔮 VIX Vade Yapısı Öncü Sinyali (Backwardation/Contango) | E | -0.091 | -0.153 | -2.3 | 16676 |
| VIX/VIX3M Dealer Gamma & Vade Eğrisi | C | -0.092 | -0.153 | -2.3 | 16676 |

### XAG
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n |
|---|---|---|---|---|---|
| Gümüş / Bakır Sanayi Rotasyonu | D | -0.010 | +0.034 | +0.5 | 16674 |
| Gümüş 4H/24H Trend İvmesi | E | -0.010 | +0.029 | +0.4 | 16674 |
| 🥈 Gümüş Parasal Yakalama & Değerleme İvmesi | E | +0.019 | +0.029 | +0.4 | 16674 |
| USD Gücü & Dolar Baskısı | A | -0.003 | +0.026 | +0.4 | 16674 |
| 10Y Reel Faiz Baskısı (TIP) | B | +0.011 | +0.025 | +0.4 | 16674 |
| 🥇 Altın Çapa / Beta (Adaptif) | E | -0.033 | +0.008 | +0.1 | 16674 |
| Küresel Kredi & Sanayi İştahı | C | +0.026 | -0.001 | -0.0 | 16674 |
| Bakır/Altın Sanayi Talebi | D | +0.036 | -0.003 | -0.0 | 16674 |
| 🎯 XAU/XAG Adaptif Ayrışma (Rezidüel) | E | +0.006 | -0.019 | -0.3 | 16674 |
| 🔮 GVZ Çapraz-Volatilite Rejimi (Öncü) | E | -0.041 | -0.031 | -0.5 | 16674 |
| TLT Tahvil Getiri Baskısı | B | -0.044 | -0.042 | -0.6 | 16674 |
| Fed Net Dolar Likiditesi (NDL) | A | -0.076 | -0.082 | -1.3 | 16674 |
| 🔮 VXSLV Opsiyon Volatilite Primi (Öncü) | E | -0.102 | -0.105 | -1.3 | 11039 |
| Enflasyon Beklenti Kalkanı | B | -0.091 | -0.129 | -2.0 | 16674 |

### XAU
| Faktör | Küme | IC 24s | IC 72s | t(72s) | n |
|---|---|---|---|---|---|
| Bakır/Altın Sanayi Döngüsü | D | +0.021 | +0.051 | +0.8 | 16674 |
| Jeopolitik & Güvenli Liman | C | +0.043 | +0.035 | +0.5 | 16674 |
| Altın Hızlı 2H/16H Anlık İvme | E | +0.021 | +0.031 | +0.5 | 16674 |
| 10Y Reel Faiz (TIPS Ters Oran) | B | +0.029 | +0.028 | +0.4 | 16674 |
| Altın / Petrol Şoku (Stagflasyon) | D | +0.007 | +0.018 | +0.3 | 16674 |
| 🔮 GVZ Opsiyon Volatilite Primi (Öncü) | E | -0.015 | +0.018 | +0.3 | 16674 |
| 🏛️ Merkez Bankası & Jeopolitik Rezerv Talebi | E | -0.004 | +0.014 | +0.2 | 16674 |
| DXY Spot Dolar Baskısı | A | -0.001 | +0.009 | +0.1 | 16674 |
| 🥇 DXY/Tahvil Öncü Altın İmpulsu | E | +0.009 | +0.004 | +0.1 | 16674 |
| Dolar Rezerv / Net Likidite İvmesi | A | +0.008 | +0.003 | +0.0 | 16674 |
| Bankacılık Güven Krizi Primi (KRE) | C | +0.026 | -0.009 | -0.1 | 16674 |
| Altın/Gümüş Rasyosu (GSR) | D | -0.015 | -0.046 | -0.7 | 16674 |
| Enflasyon Beklenti Kalkanı | B | -0.044 | -0.057 | -0.9 | 16674 |
| TLT Uzun Vade Tahvil Gücü | B | -0.064 | -0.061 | -0.9 | 16674 |

