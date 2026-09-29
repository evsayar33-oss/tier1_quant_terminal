# 📊 Canlı Performans Karnesi (örneklem dışı, ileriye dönük)

_Son güncelleme: 2026-09-29T09:28:53.920338+00:00 · döngü: 16 · kayıt: 68 (notlanan: 62)_

Bu sayfa sistemin **yayınladığı nihai sinyalleri** gerçekleşen fiyatla notlar. Model bu sayfadan öğrenmez; sadece hakemdir. Bir satırın güvenilir olması için en az **30** bağımsız (çakışmayan) örnek gerekir.

**Nasıl okunur:** *isabet* = yön doğru tahmin oranı · *ort bps* = sinyal yönünde ortalama getiri (1 bps = %0,01) · *alt sınır* = %95 güvenle gerçek isabetin en az bu kadar olduğu değer. Model, **Hep AL** ve **Trend takibi** (fiyatın gidişine bakan reaktif yöntem) ile AYNI anlarda karşılaştırılır.

## Genel
### 4 saat sonrası
- **Model:** %74.5 isabet · ort +23 bps · n=47 (bağımsız 32, alt sınır %60)
- Hep AL: %25.5 isabet · ort -23 bps · n=47 (bağımsız 32, alt sınır %15)
- Trend takibi: %43.2 isabet · ort +3 bps · n=44 (bağımsız 31, alt sınır %30)
- Sadece giriş izni verilenler: %67.9 isabet · ort +28 bps · n=28 (bağımsız 18, alt sınır %48) ⚠️az bağımsız örnek
- Zamanlama notu A: %72.7 isabet · ort +28 bps · n=22 (bağımsız 14, alt sınır %51) ⚠️az bağımsız örnek
- Zamanlama notu B: %63.6 isabet · ort +14 bps · n=11 (bağımsız 8, alt sınır %36) ⚠️az bağımsız örnek
- Zamanlama notu C: %85.7 isabet · ort +22 bps · n=14 (bağımsız 13, alt sınır %64) ⚠️az bağımsız örnek
- Sonuç: ✅ Kanıtlanmış avantaj: en iyi basit yöntemden +31.3 puan iyi ve alt güven sınırı %50'nin üzerinde.

### 24 saat sonrası
- **Model:** %80.0 isabet · ort +49 bps · n=20 (bağımsız 6, alt sınır %47) ⚠️az bağımsız örnek
- Hep AL: %20.0 isabet · ort -49 bps · n=20 (bağımsız 6, alt sınır %5) ⚠️az bağımsız örnek
- Trend takibi: %35.0 isabet · ort -21 bps · n=20 (bağımsız 6, alt sınır %13) ⚠️az bağımsız örnek
- Sadece giriş izni verilenler: %72.7 isabet · ort +31 bps · n=11 (bağımsız 5, alt sınır %37) ⚠️az bağımsız örnek
- Zamanlama notu A: %60.0 isabet · ort +23 bps · n=10 (bağımsız 4, alt sınır %25) ⚠️az bağımsız örnek
- Zamanlama notu B: %100.0 isabet · ort +49 bps · n=4 (bağımsız 2, alt sınır %43) ⚠️az bağımsız örnek
- Zamanlama notu C: %100.0 isabet · ort +93 bps · n=6 (bağımsız 3, alt sınır %53) ⚠️az bağımsız örnek
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
- 24s Model: %60.0 isabet · ort +30 bps · n=5 (bağımsız 1, alt sınır %10) ⚠️az bağımsız örnek
  - Hep AL: %40.0 isabet · ort -30 bps · n=5 (bağımsız 1, alt sınır %5) ⚠️az bağımsız örnek · Trend: %20.0 isabet · ort -100 bps · n=5 (bağımsız 1, alt sınır %1) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: — (veri yok)
  - Hep AL: — (veri yok) · Trend: — (veri yok)
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### ETH
- 24s Model: %50.0 isabet · ort -38 bps · n=4 (bağımsız 1, alt sınır %7) ⚠️az bağımsız örnek
  - Hep AL: %50.0 isabet · ort +38 bps · n=4 (bağımsız 1, alt sınır %7) ⚠️az bağımsız örnek · Trend: %0.0 isabet · ort -109 bps · n=4 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: — (veri yok)
  - Hep AL: — (veri yok) · Trend: — (veri yok)
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### NQ
- 24s Model: %100.0 isabet · ort +48 bps · n=3 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %0.0 isabet · ort -48 bps · n=3 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek · Trend: %0.0 isabet · ort -48 bps · n=3 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: — (veri yok)
  - Hep AL: — (veri yok) · Trend: — (veri yok)
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### SPX
- 24s Model: %100.0 isabet · ort +47 bps · n=2 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %0.0 isabet · ort -47 bps · n=2 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek · Trend: %0.0 isabet · ort -47 bps · n=2 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %100.0 isabet · ort +74 bps · n=1 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %0.0 isabet · ort -74 bps · n=1 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek · Trend: %0.0 isabet · ort -74 bps · n=1 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAG
- 24s Model: %100.0 isabet · ort +152 bps · n=3 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %0.0 isabet · ort -152 bps · n=3 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek · Trend: %100.0 isabet · ort +152 bps · n=3 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %100.0 isabet · ort +600 bps · n=1 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %0.0 isabet · ort -600 bps · n=1 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek · Trend: %100.0 isabet · ort +600 bps · n=1 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAU
- 24s Model: %100.0 isabet · ort +98 bps · n=3 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %0.0 isabet · ort -98 bps · n=3 (bağımsız 1, alt sınır %0) ⚠️az bağımsız örnek · Trend: %100.0 isabet · ort +98 bps · n=3 (bağımsız 1, alt sınır %27) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: — (veri yok)
  - Hep AL: — (veri yok) · Trend: — (veri yok)
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

## Rejim bazında (Model)
- Rejim 3: 24s %80.0 isabet · ort +49 bps · n=20 (bağımsız 6, alt sınır %47) ⚠️az bağımsız örnek · 72s %100.0 isabet · ort +337 bps · n=2 (bağımsız 2, alt sınır %43) ⚠️az bağımsız örnek

## Veri sağlığı (faktör bazında erişilebilirlik)
- Tüm faktörler son döngülerde %80+ oranında veri aldı. ✅

## Durum dosyası olayları (yedekleme / göç)
- Kayıt yok ✅
