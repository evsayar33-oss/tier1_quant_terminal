# 📊 Canlı Performans Karnesi (örneklem dışı, ileriye dönük)

_Son güncelleme: 2026-09-30T00:09:52.321262+00:00 · döngü: 19 · kayıt: 86 (notlanan: 76)_

Bu sayfa sistemin **yayınladığı nihai sinyalleri** gerçekleşen fiyatla notlar. Model bu sayfadan öğrenmez; sadece hakemdir. Bir satırın güvenilir olması için en az **30** bağımsız (çakışmayan) örnek gerekir.

**Nasıl okunur:** *isabet* = yön doğru tahmin oranı · *ort bps* = sinyal yönünde ortalama getiri (1 bps = %0,01) · *alt sınır* = %95 güvenle gerçek isabetin en az bu kadar olduğu değer. Model, **Hep AL** ve **Trend takibi** (fiyatın gidişine bakan reaktif yöntem) ile AYNI anlarda karşılaştırılır.

## Genel
### 4 saat sonrası
- **Model:** %70.0 isabet · ort +18 bps · n=50 (bağımsız 35, alt sınır %56)
- Hep AL: %30.0 isabet · ort -18 bps · n=50 (bağımsız 35, alt sınır %19)
- Trend takibi: %40.4 isabet · ort -1 bps · n=47 (bağımsız 34, alt sınır %28)
- Sadece giriş izni verilenler: %65.5 isabet · ort +26 bps · n=29 (bağımsız 19, alt sınır %47) ⚠️az bağımsız örnek
- Zamanlama notu A: %69.6 isabet · ort +22 bps · n=23 (bağımsız 15, alt sınır %48) ⚠️az bağımsız örnek
- Zamanlama notu B: %53.8 isabet · ort +6 bps · n=13 (bağımsız 10, alt sınır %30) ⚠️az bağımsız örnek
- Zamanlama notu C: %85.7 isabet · ort +22 bps · n=14 (bağımsız 13, alt sınır %64) ⚠️az bağımsız örnek
- Sonuç: ✅ Kanıtlanmış avantaj: en iyi basit yöntemden +29.6 puan iyi ve alt güven sınırı %50'nin üzerinde.

### 24 saat sonrası
- **Model:** %64.4 isabet · ort +8 bps · n=45 (bağımsız 8, alt sınır %36) ⚠️az bağımsız örnek
- Hep AL: %35.6 isabet · ort -8 bps · n=45 (bağımsız 8, alt sınır %15) ⚠️az bağımsız örnek
- Trend takibi: %35.7 isabet · ort -25 bps · n=42 (bağımsız 8, alt sınır %15) ⚠️az bağımsız örnek
- Sadece giriş izni verilenler: %55.6 isabet · ort -5 bps · n=27 (bağımsız 6, alt sınır %26) ⚠️az bağımsız örnek
- Zamanlama notu A: %57.1 isabet · ort +2 bps · n=21 (bağımsız 4, alt sınır %23) ⚠️az bağımsız örnek
- Zamanlama notu B: %50.0 isabet · ort -12 bps · n=10 (bağımsız 4, alt sınır %18) ⚠️az bağımsız örnek
- Zamanlama notu C: %85.7 isabet · ort +32 bps · n=14 (bağımsız 6, alt sınır %52) ⚠️az bağımsız örnek
- Sonuç: Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### 72 saat sonrası
- **Model:** %100.0 isabet · ort +337 bps · n=2 (bağımsız 2, alt sınır %43) ⚠️az bağımsız örnek
- Hep AL: %0.0 isabet · ort -337 bps · n=2 (bağımsız 2, alt sınır %0) ⚠️az bağımsız örnek
- Trend takibi: %50.0 isabet · ort +263 bps · n=2 (bağımsız 2, alt sınır %12) ⚠️az bağımsız örnek
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: %100.0 isabet · ort +337 bps · n=2 (bağımsız 2, alt sınır %43) ⚠️az bağımsız örnek
- Sonuç: Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### 120 saat sonrası
- **Model:** — (veri yok)
- Hep AL: — (veri yok)
- Trend takibi: — (veri yok)
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: — (veri yok)
- Sonuç: Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

## Varlık bazında (24 saat ve 72 saat)
### BTC
- 24s Model: %44.4 isabet · ort -27 bps · n=9 (bağımsız 2, alt sınır %10) ⚠️az bağımsız örnek
  - Hep AL: %55.6 isabet · ort +27 bps · n=9 (bağımsız 2, alt sınır %15) ⚠️az bağımsız örnek · Trend: %11.1 isabet · ort -108 bps · n=9 (bağımsız 2, alt sınır %1) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: — (veri yok)
  - Hep AL: — (veri yok) · Trend: — (veri yok)
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### ETH
- 24s Model: %50.0 isabet · ort -65 bps · n=6 (bağımsız 2, alt sınır %12) ⚠️az bağımsız örnek
  - Hep AL: %50.0 isabet · ort +65 bps · n=6 (bağımsız 2, alt sınır %12) ⚠️az bağımsız örnek · Trend: %0.0 isabet · ort -89 bps · n=5 (bağımsız 2, alt sınır %0) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: — (veri yok)
  - Hep AL: — (veri yok) · Trend: — (veri yok)
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### NQ
- 24s Model: %57.1 isabet · ort +18 bps · n=7 (bağımsız 1, alt sınır %9) ⚠️az bağımsız örnek
  - Hep AL: %42.9 isabet · ort -18 bps · n=7 (bağımsız 1, alt sınır %5) ⚠️az bağımsız örnek · Trend: %33.3 isabet · ort -24 bps · n=6 (bağımsız 1, alt sınır %3) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: — (veri yok)
  - Hep AL: — (veri yok) · Trend: — (veri yok)
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### SPX
- 24s Model: %85.7 isabet · ort +25 bps · n=7 (bağımsız 1, alt sınır %20) ⚠️az bağımsız örnek
  - Hep AL: %14.3 isabet · ort -25 bps · n=7 (bağımsız 1, alt sınır %1) ⚠️az bağımsız örnek · Trend: %0.0 isabet · ort -29 bps · n=6 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %100.0 isabet · ort +74 bps · n=1 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %0.0 isabet · ort -74 bps · n=1 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek · Trend: %0.0 isabet · ort -74 bps · n=1 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAG
- 24s Model: %75.0 isabet · ort +75 bps · n=8 (bağımsız 1, alt sınır %15) ⚠️az bağımsız örnek
  - Hep AL: %25.0 isabet · ort -75 bps · n=8 (bağımsız 1, alt sınır %2) ⚠️az bağımsız örnek · Trend: %75.0 isabet · ort +75 bps · n=8 (bağımsız 1, alt sınır %15) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %100.0 isabet · ort +600 bps · n=1 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %0.0 isabet · ort -600 bps · n=1 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek · Trend: %100.0 isabet · ort +600 bps · n=1 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAU
- 24s Model: %75.0 isabet · ort +13 bps · n=8 (bağımsız 1, alt sınır %15) ⚠️az bağımsız örnek
  - Hep AL: %25.0 isabet · ort -13 bps · n=8 (bağımsız 1, alt sınır %2) ⚠️az bağımsız örnek · Trend: %75.0 isabet · ort +13 bps · n=8 (bağımsız 1, alt sınır %15) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: — (veri yok)
  - Hep AL: — (veri yok) · Trend: — (veri yok)
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

## Rejim bazında (Model)
- Rejim 3: 24s %64.4 isabet · ort +8 bps · n=45 (bağımsız 8, alt sınır %36) ⚠️az bağımsız örnek · 72s %100.0 isabet · ort +337 bps · n=2 (bağımsız 2, alt sınır %43) ⚠️az bağımsız örnek

## Veri sağlığı (faktör bazında erişilebilirlik)
- Tüm faktörler son döngülerde %80+ oranında veri aldı. ✅

## Durum dosyası olayları (yedekleme / göç)
- Kayıt yok ✅
