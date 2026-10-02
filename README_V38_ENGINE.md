# v3.8 — Aşama 2: Sürekli motor (2026-10-02)
GitHub'ın 30 dakikalık zamanlayıcısı pratikte 1-6 saatte bir çalışıyordu. Artık:
- `tier1_engine_loop.yml`: tek iş ~5 saat 40 dk açık kalır, **her saatlik bar kapandıktan 90 sn sonra** tam döngüyü
  çalıştırır ve sonucu `state` dalına yayımlar. Saatlik zamanlayıcı (her saatin 7. dakikası) sıradaki işi kuyruğa alır;
  biri bitince diğeri başlar → kesintisiz. Hafta sonu da çalışır (kripto).
- Eski tracker workflow'unun zamanlayıcısı kaldırıldı (elle çalıştırma yedeği olarak duruyor). Aynı eşzamanlılık
  grubu → durumu tek bir iş yazar.
- **`signals.json` (bot sözleşmesi, şema tier1.signals.v1):** her varlık için yön, model aşaması, kanıt durumu,
  giriş izni/notu, son kapanış, 1s ATR, stop/hedef (şimdilik geçici 1.5×ATR / 2.5×ATR — Aşama 4 kanıtla değiştirecek)
  ve `tradeable`. `tradeable = true` ancak walk-forward kanıtı VAR (ACTIVE) ve giriş kapısı AÇIK ise.
- **`bot_status.json` (kalp atışı):** uygulamada "🟢 Motor: son döngü … · sıradaki …" satırı. 75 dk'dan eskiyse 🟡,
  3 saatten eskiyse 🔴.
- Herkese açık repoda Actions dakikaları ücretsiz. Not: bu kullanım GitHub şartlarında gri alanda; durdurulursa
  aynı `bot_loop.py` Oracle ücretsiz sunucuda değişiklik yapılmadan çalışır.
- v3.7.1 (fiyat payı ≤ %30 sınırı) bu pakete dahil.

## 📱 Yapman gerekenler
1. Zip'teki dosyaları yükle (`.github/workflows/` içindeki 2 dosya dahil). Reboot app.
2. Actions → **"Tier-1 Engine Loop (sürekli motor)" → Run workflow** (ilk işi hemen başlatmak için; sonrası otomatik).
3. Birkaç saat sonra uygulamadaki motor satırının 🟢 olduğunu kontrol et.
