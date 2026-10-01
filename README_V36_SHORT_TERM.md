# v3.6 — "Kısa Vade Yön (1-4 Saat)" (2026-10-01)
Eski "Canlı Fiyat Yönü" adına rağmen ~%100 son 1-2 saatin fiyat itkisinden oluşuyordu (model katkısı en fazla ±0.35);
bu yüzden tek bir tepki mumunda "GÜÇLÜ AŞAĞI" → "YATAY" dönüyordu. Projenin ilkesi (fiyat payı %10-30) yalnız Model
Sinyali'nde geçerliydi (kendi fiyat ivmesi payı %6-11).

Yeni sütun: **⏱️ Kısa Vade Yön (1-4 Saat)** = sonraki 1-4 saatlik mumun olası yönü (TAHMİN).
- Tahmin = 0.70 × model (çok faktörlü, z) + 0.30 × fiyat itkisi (z). İki bileşen tipik büyüklüklerine göre normalize
  (config.SHORT_TERM_SCALES) — ham ölçekte fiyat yine baskın olurdu.
- Kendini geliştiren: haftalık walk-forward işi bu iki ağırlığı GERÇEK 4 saatlik sonuçlardan, örneklem dışında öğrenir
  (negatif ağırlık yok); t ≥ 2 ve isabet ≥ 70/30 ise canlıya alır, değilse 70/30 kalır. Rapora "⏱️ Kısa Vade Yön"
  tablosu eklendi (öğrenilmiş / 70/30 / yalnız fiyat / Hep AL, aynı zaman damgalarında). Panel artık 1s ve 4s
  sonuçları ve fiyat skorunu da kaydeder.
- Etiketteki yüzde artık açıkça "son 1s %…" (geçmiş bilgi), etiket ise tahmin.
- Eşik dağılımları yeni ölçekte sıfırdan başlar (SHORT:: önekiyle); sabit anlam çapası ve histerezis aynen geçerli.
Not: data_engine.py v3.5.1 düzeltmelerini (kripto ekstra satır + OKX hacmi) içerir.
