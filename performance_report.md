# 📊 Canlı Performans Karnesi (örneklem dışı, ileriye dönük)

_Son güncelleme: 2026-11-21T18:02:56.147082+00:00 · döngü: 1035 · kayıt: 3000 (notlanan: 2976)_

Bu sayfa sistemin **yayınladığı nihai sinyalleri** gerçekleşen fiyatla notlar. Model bu sayfadan öğrenmez; sadece hakemdir. Bir satırın güvenilir olması için en az **30** bağımsız (çakışmayan) örnek gerekir.

**Nasıl okunur:** *isabet* = yön doğru tahmin oranı · *ort bps* = sinyal yönünde ortalama getiri (1 bps = %0,01) · *alt sınır* = %95 güvenle gerçek isabetin en az bu kadar olduğu değer. Model, **Hep AL** ve **Trend takibi** (fiyatın gidişine bakan reaktif yöntem) ile AYNI anlarda karşılaştırılır.

## Genel
### 4 saat sonrası
- **Model:** %57.5 isabet · ort +22 bps · n=1150 (bağımsız 304, alt sınır %53)
- Hep AL: %42.4 isabet · ort -22 bps · n=1150 (bağımsız 304, alt sınır %38)
- Trend takibi: %57.7 isabet · ort +21 bps · n=1123 (bağımsız 301, alt sınır %53)
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: — (veri yok)
- Sonuç: 🔴 Model basit yöntemlerin gerisinde (-0.2 puan) — bu varlık/ufuk için sinyal henüz güvenilir değil.

### 24 saat sonrası
- **Model:** %68.6 isabet · ort +124 bps · n=1049 (bağımsız 60, alt sınır %58)
- Hep AL: %31.4 isabet · ort -124 bps · n=1049 (bağımsız 60, alt sınır %22)
- Trend takibi: %65.0 isabet · ort +107 bps · n=1022 (bağımsız 60, alt sınır %54)
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: — (veri yok)
- Sonuç: 🟡 Yön isabeti betimsel olarak olumlu (+3.7 puan); eşleştirilmiş üstünlük testi ve maliyet sonrası işlem kanıtı yok.

### 72 saat sonrası
- **Model:** %80.9 isabet · ort +263 bps · n=915 (bağımsız 26, alt sınır %66) ⚠️az bağımsız örnek
- Hep AL: %19.1 isabet · ort -263 bps · n=915 (bağımsız 26, alt sınır %10) ⚠️az bağımsız örnek
- Trend takibi: %73.2 isabet · ort +243 bps · n=894 (bağımsız 26, alt sınır %57) ⚠️az bağımsız örnek
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: — (veri yok)
- Sonuç: Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### 120 saat sonrası
- **Model:** %74.3 isabet · ort +297 bps · n=681 (bağımsız 17, alt sınır %54) ⚠️az bağımsız örnek
- Hep AL: %25.7 isabet · ort -297 bps · n=681 (bağımsız 17, alt sınır %13) ⚠️az bağımsız örnek
- Trend takibi: %62.2 isabet · ort +210 bps · n=661 (bağımsız 17, alt sınır %42) ⚠️az bağımsız örnek
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: — (veri yok)
- Sonuç: Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

## Varlık bazında (24 saat ve 72 saat)
### BTC
- 24s Model: %62.6 isabet · ort +91 bps · n=187 (bağımsız 11, alt sınır %38) ⚠️az bağımsız örnek
  - Hep AL: %37.4 isabet · ort -91 bps · n=187 (bağımsız 11, alt sınır %18) ⚠️az bağımsız örnek · Trend: %62.6 isabet · ort +91 bps · n=187 (bağımsız 11, alt sınır %38) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %91.6 isabet · ort +339 bps · n=178 (bağımsız 4, alt sınır %50) ⚠️az bağımsız örnek
  - Hep AL: %8.4 isabet · ort -339 bps · n=178 (bağımsız 4, alt sınır %1) ⚠️az bağımsız örnek · Trend: %91.6 isabet · ort +339 bps · n=178 (bağımsız 4, alt sınır %50) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### ETH
- 24s Model: %56.3 isabet · ort +70 bps · n=158 (bağımsız 8, alt sınır %30) ⚠️az bağımsız örnek
  - Hep AL: %43.7 isabet · ort -70 bps · n=158 (bağımsız 8, alt sınır %20) ⚠️az bağımsız örnek · Trend: %56.1 isabet · ort +69 bps · n=157 (bağımsız 8, alt sınır %30) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %84.1 isabet · ort +389 bps · n=151 (bağımsız 4, alt sınır %43) ⚠️az bağımsız örnek
  - Hep AL: %15.9 isabet · ort -389 bps · n=151 (bağımsız 4, alt sınır %3) ⚠️az bağımsız örnek · Trend: %84.0 isabet · ort +390 bps · n=150 (bağımsız 4, alt sınır %43) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### NQ
- 24s Model: %71.6 isabet · ort +155 bps · n=204 (bağımsız 11, alt sınır %47) ⚠️az bağımsız örnek
  - Hep AL: %28.4 isabet · ort -155 bps · n=204 (bağımsız 11, alt sınır %12) ⚠️az bağımsız örnek · Trend: %59.5 isabet · ort +89 bps · n=195 (bağımsız 11, alt sınır %36) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %78.3 isabet · ort +176 bps · n=161 (bağımsız 5, alt sınır %42) ⚠️az bağımsız örnek
  - Hep AL: %21.7 isabet · ort -176 bps · n=161 (bağımsız 5, alt sınır %5) ⚠️az bağımsız örnek · Trend: %59.5 isabet · ort +98 bps · n=158 (bağımsız 5, alt sınır %27) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### SPX
- 24s Model: %67.0 isabet · ort +58 bps · n=185 (bağımsız 11, alt sınır %43) ⚠️az bağımsız örnek
  - Hep AL: %33.0 isabet · ort -58 bps · n=185 (bağımsız 11, alt sınır %15) ⚠️az bağımsız örnek · Trend: %62.9 isabet · ort +43 bps · n=175 (bağımsız 11, alt sınır %39) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %78.6 isabet · ort +104 bps · n=154 (bağımsız 4, alt sınır %39) ⚠️az bağımsız örnek
  - Hep AL: %21.4 isabet · ort -104 bps · n=154 (bağımsız 4, alt sınır %4) ⚠️az bağımsız örnek · Trend: %41.7 isabet · ort +59 bps · n=144 (bağımsız 4, alt sınır %14) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAG
- 24s Model: %78.0 isabet · ort +219 bps · n=227 (bağımsız 12, alt sınır %54) ⚠️az bağımsız örnek
  - Hep AL: %22.0 isabet · ort -219 bps · n=227 (bağımsız 12, alt sınır %9) ⚠️az bağımsız örnek · Trend: %75.5 isabet · ort +215 bps · n=220 (bağımsız 12, alt sınır %52) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %75.0 isabet · ort +369 bps · n=184 (bağımsız 6, alt sınır %42) ⚠️az bağımsız örnek
  - Hep AL: %25.0 isabet · ort -369 bps · n=184 (bağımsız 6, alt sınır %7) ⚠️az bağımsız örnek · Trend: %82.5 isabet · ort +367 bps · n=177 (bağımsız 6, alt sınır %49) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAU
- 24s Model: %76.1 isabet · ort +109 bps · n=88 (bağımsız 7, alt sınır %45) ⚠️az bağımsız örnek
  - Hep AL: %23.9 isabet · ort -109 bps · n=88 (bağımsız 7, alt sınır %7) ⚠️az bağımsız örnek · Trend: %76.1 isabet · ort +109 bps · n=88 (bağımsız 7, alt sınır %45) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %74.7 isabet · ort +109 bps · n=87 (bağımsız 3, alt sınır %31) ⚠️az bağımsız örnek
  - Hep AL: %25.3 isabet · ort -109 bps · n=87 (bağımsız 3, alt sınır %5) ⚠️az bağımsız örnek · Trend: %74.7 isabet · ort +109 bps · n=87 (bağımsız 3, alt sınır %31) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

## Rejim bazında (Model)
- Rejim 2: 24s %91.7 isabet · ort +470 bps · n=12 (bağımsız 4, alt sınır %51) ⚠️az bağımsız örnek · 72s — (veri yok)
- Rejim 3: 24s %68.4 isabet · ort +120 bps · n=1037 (bağımsız 58, alt sınır %58) · 72s %80.9 isabet · ort +263 bps · n=915 (bağımsız 26, alt sınır %66) ⚠️az bağımsız örnek

## Veri sağlığı (faktör bazında erişilebilirlik)
- Tüm faktörler son döngülerde %80+ oranında veri aldı. ✅

## Durum dosyası olayları (yedekleme / göç)
- Kayıt yok ✅
