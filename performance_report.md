# 📊 Canlı Performans Karnesi (örneklem dışı, ileriye dönük)

_Son güncelleme: 2026-11-28T14:02:49.187469+00:00 · döngü: 1206 · kayıt: 3000 (notlanan: 2976)_

Bu sayfa sistemin **yayınladığı nihai sinyalleri** gerçekleşen fiyatla notlar. Model bu sayfadan öğrenmez; sadece hakemdir. Bir satırın güvenilir olması için en az **30** bağımsız (çakışmayan) örnek gerekir.

**Nasıl okunur:** *isabet* = yön doğru tahmin oranı · *ort bps* = sinyal yönünde ortalama getiri (1 bps = %0,01) · *alt sınır* = %95 güvenle gerçek isabetin en az bu kadar olduğu değer. Model, **Hep AL** ve **Trend takibi** (fiyatın gidişine bakan reaktif yöntem) ile AYNI anlarda karşılaştırılır.

⚠️ Eski as-of ölçüm yaklaşımı; kesin ufuk, eşleşmiş kanıt veya işlem performansı değildir.
Güncel bileşen kanıtı: component_research_report.json. Pooled alt sınırlar istatistiksel üstünlük kanıtı değildir.

## Genel
### 4 saat sonrası
- **Model:** %54.4 isabet · ort +11 bps · n=1282 (bağımsız 341, alt sınır %48)
- Hep AL: %45.5 isabet · ort -11 bps · n=1282 (bağımsız 341, alt sınır %42)
- Trend takibi: %56.0 isabet · ort +14 bps · n=1226 (bağımsız 335, alt sınır %47)
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: — (veri yok)
- Sonuç: Eski trend örneklemi farklı; kesin üstünlük/başarısızlık kararı verilemez.

### 24 saat sonrası
- **Model:** %62.8 isabet · ort +78 bps · n=1284 (bağımsız 72, alt sınır %45)
- Hep AL: %37.2 isabet · ort -78 bps · n=1284 (bağımsız 72, alt sınır %37)
- Trend takibi: %61.9 isabet · ort +69 bps · n=1228 (bağımsız 72, alt sınır %43)
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: — (veri yok)
- Sonuç: Eski trend örneklemi farklı; kesin üstünlük/başarısızlık kararı verilemez.

### 72 saat sonrası
- **Model:** %74.5 isabet · ort +259 bps · n=1184 (bağımsız 32, alt sınır %58)
- Hep AL: %25.5 isabet · ort -259 bps · n=1184 (bağımsız 32, alt sınır %17)
- Trend takibi: %68.3 isabet · ort +240 bps · n=1145 (bağımsız 32, alt sınır %42)
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: — (veri yok)
- Sonuç: Eski trend örneklemi farklı; kesin üstünlük/başarısızlık kararı verilemez.

### 120 saat sonrası
- **Model:** %84.6 isabet · ort +441 bps · n=1087 (bağımsız 18, alt sınır %71) ⚠️az bağımsız örnek
- Hep AL: %15.4 isabet · ort -441 bps · n=1087 (bağımsız 18, alt sınır %4) ⚠️az bağımsız örnek
- Trend takibi: %77.2 isabet · ort +385 bps · n=1063 (bağımsız 18, alt sınır %59) ⚠️az bağımsız örnek
- Sadece giriş izni verilenler: — (veri yok)
- Zamanlama notu A: — (veri yok)
- Zamanlama notu B: — (veri yok)
- Zamanlama notu C: — (veri yok)
- Sonuç: Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

## Varlık bazında (24 saat ve 72 saat)
### BTC
- 24s Model: %57.9 isabet · ort +50 bps · n=202 (bağımsız 10, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %42.1 isabet · ort -50 bps · n=202 (bağımsız 10, alt sınır %27) ⚠️az bağımsız örnek · Trend: %60.7 isabet · ort +56 bps · n=196 (bağımsız 10, alt sınır %27) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %84.7 isabet · ort +298 bps · n=183 (bağımsız 4, alt sınır %36) ⚠️az bağımsız örnek
  - Hep AL: %15.3 isabet · ort -298 bps · n=183 (bağımsız 4, alt sınır %6) ⚠️az bağımsız örnek · Trend: %84.2 isabet · ort +297 bps · n=183 (bağımsız 4, alt sınır %36) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### ETH
- 24s Model: %53.9 isabet · ort +32 bps · n=165 (bağımsız 8, alt sınır %25) ⚠️az bağımsız örnek
  - Hep AL: %46.1 isabet · ort -32 bps · n=165 (bağımsız 8, alt sınır %25) ⚠️az bağımsız örnek · Trend: %54.3 isabet · ort +32 bps · n=164 (bağımsız 8, alt sınır %25) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %81.8 isabet · ort +330 bps · n=165 (bağımsız 4, alt sınır %36) ⚠️az bağımsız örnek
  - Hep AL: %18.2 isabet · ort -330 bps · n=165 (bağımsız 4, alt sınır %6) ⚠️az bağımsız örnek · Trend: %81.1 isabet · ort +330 bps · n=164 (bağımsız 4, alt sınır %36) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### NQ
- 24s Model: %65.9 isabet · ort +114 bps · n=267 (bağımsız 15, alt sınır %39) ⚠️az bağımsız örnek
  - Hep AL: %34.1 isabet · ort -114 bps · n=267 (bağımsız 15, alt sınır %22) ⚠️az bağımsız örnek · Trend: %58.3 isabet · ort +72 bps · n=247 (bağımsız 15, alt sınır %28) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %77.2 isabet · ort +252 bps · n=246 (bağımsız 6, alt sınır %50) ⚠️az bağımsız örnek
  - Hep AL: %22.8 isabet · ort -252 bps · n=246 (bağımsız 6, alt sınır %4) ⚠️az bağımsız örnek · Trend: %61.3 isabet · ort +172 bps · n=230 (bağımsız 6, alt sınır %12) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### SPX
- 24s Model: %61.0 isabet · ort +38 bps · n=200 (bağımsız 13, alt sınır %46) ⚠️az bağımsız örnek
  - Hep AL: %39.0 isabet · ort -38 bps · n=200 (bağımsız 13, alt sınır %15) ⚠️az bağımsız örnek · Trend: %62.7 isabet · ort +39 bps · n=193 (bağımsız 13, alt sınır %46) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %77.0 isabet · ort +172 bps · n=191 (bağımsız 6, alt sınır %35) ⚠️az bağımsız örnek
  - Hep AL: %23.0 isabet · ort -172 bps · n=191 (bağımsız 6, alt sınır %12) ⚠️az bağımsız örnek · Trend: %48.4 isabet · ort +138 bps · n=184 (bağımsız 6, alt sınır %12) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAG
- 24s Model: %69.6 isabet · ort +137 bps · n=303 (bağımsız 16, alt sınır %26) ⚠️az bağımsız örnek
  - Hep AL: %30.4 isabet · ort -137 bps · n=303 (bağımsız 16, alt sınır %36) ⚠️az bağımsız örnek · Trend: %67.4 isabet · ort +129 bps · n=288 (bağımsız 16, alt sınır %26) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %66.1 isabet · ort +350 bps · n=274 (bağımsız 7, alt sınır %41) ⚠️az bağımsız örnek
  - Hep AL: %33.9 isabet · ort -350 bps · n=274 (bağımsız 7, alt sınır %10) ⚠️az bağımsız örnek · Trend: %73.3 isabet · ort +361 bps · n=262 (bağımsız 7, alt sınır %41) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

### XAU
- 24s Model: %61.9 isabet · ort +34 bps · n=147 (bağımsız 10, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %38.1 isabet · ort -34 bps · n=147 (bağımsız 10, alt sınır %27) ⚠️az bağımsız örnek · Trend: %66.4 isabet · ort +45 bps · n=140 (bağımsız 10, alt sınır %35) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).
- 72s Model: %59.2 isabet · ort +53 bps · n=125 (bağımsız 5, alt sınır %27) ⚠️az bağımsız örnek
  - Hep AL: %40.8 isabet · ort -53 bps · n=125 (bağımsız 5, alt sınır %14) ⚠️az bağımsız örnek · Trend: %59.8 isabet · ort +56 bps · n=122 (bağımsız 5, alt sınır %27) ⚠️az bağımsız örnek
  - Karar için henüz yeterli bağımsız örnek yok (gereken: 30).

## Rejim bazında (Model)
- Rejim 2: 24s %40.5 isabet · ort -60 bps · n=336 (bağımsız 23, alt sınır %21) ⚠️az bağımsız örnek · 72s %25.3 isabet · ort -177 bps · n=229 (bağımsız 9, alt sınır %30) ⚠️az bağımsız örnek
- Rejim 3: 24s %70.7 isabet · ort +127 bps · n=948 (bağımsız 51, alt sınır %51) · 72s %86.3 isabet · ort +363 bps · n=955 (bağımsız 25, alt sınır %69) ⚠️az bağımsız örnek

## Veri sağlığı (faktör bazında erişilebilirlik)
- Tüm faktörler son döngülerde %80+ oranında veri aldı. ✅

## Durum dosyası olayları (yedekleme / göç)
- Kayıt yok ✅
