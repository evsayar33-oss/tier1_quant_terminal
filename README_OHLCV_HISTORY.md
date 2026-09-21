# Persistent OHLCV History — Minimal Update

Bu paket sadece gerçek OHLCV tarihçesinin süreçler/redeploy'lar arasında kalıcı birikmesini sağlar.
Giriş mantığına, MODEL_DIRECTION'a, SPX/NQ skoruna, XAU/XAG mantığına, macro kararlarına veya UI'a dokunmaz.

## Değiştirilecek / eklenecek dosyalar

- `data_engine.py` — mevcut dosyanın TAM yeni sürümü. Tek değişiklik alanı, başarılı DIRECT OHLCV'nin kalıcı history store'a yazılması ve canlı fetch başarısız olduğunda aynı tarihin STALE/analysis-only olarak okunabilmesidir.
- `ohlcv_history.py` — YENİ. Her sembol için `ohlcv_history/<symbol>.csv` altında gerçek OHLCV barlarını birleştirir ve son 200 barı tutar.
- `.github/workflows/intraday_tracker.yml` — mevcut workflow'un TAM sürümü. `ohlcv_history/` klasörünü state/history ile birlikte commit eder; kalıcı birikimi sağlar.
- `test_ohlcv_history.py` — YENİ regression testleri.

## Neden 200 bar?

Giriş motorunun kendi 150-bar dinamik penceresi değiştirilmez. Store 200 bar tutarak bu 150 barlık pencere için küçük bir güvenlik tamponu bırakır. Store katmanı giriş eşiği hesaplamaz.

## Güvenlik

- Yalnızca doğrudan alınan gerçek OHLCV yazılır.
- Sentetik satır üretilmez.
- Volume yoksa NaN olarak kalır; sahte volume oluşturulmaz.
- Aynı timestamp'teki yeni gerçek bar eskisinin yerine geçer.
- Live fetch başarısızsa persisted history `STALE` işaretlenir ve execution uygunluğu false kalır.
- Bozuk history dosyası canlı motoru çökertmez.

## Kurulum

Sadece belirtilen dört dosyayı aktar. Diğer production dosyalarına dokunma. Daha sonra GitHub Actions'ı manuel çalıştır.
