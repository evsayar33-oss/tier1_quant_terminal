# v3.4.1 — İlk gerçek walk-forward sonucu ve düzeltmeler (2026-10-01)

## Ne oldu?
30 Eylül'deki 700 günlük replay (8.401 döngü) kendi faktör ağırlıklarını öğrendi. Sonuç: **6 varlığın hiçbiri**
örneklem dışında anlamlı avantaj gösteremedi; "kanıt yok → sinyal yok" kuralı da bütün tabloyu NÖTR'e, hız/kalıcılığı 0'a çekti.

## Bu bir hata mı? — Gerçek panel üzerinde 11 farklı kurgu denendi
Faktörler (24s/72s), fiyat momentum/dönüş, yalnız rejim eğilimi, eşit ağırlık, güçlü ridge, ekonomik işaret korumalı,
varlıklar arası havuzlanmış model. **Hiçbirinde |t| ≥ 2 yok.** En iyileri XAG t=1.8, XAU t=1.6.
- Rejime göre öğrenilen eğilim örneklem dışında TERS çalışıyor (BTC IC −0.13): rejim sınıflandırması geç kalıyor.
- Fiyat momentum/dönüş ilişkisi aylar arasında yön değiştiriyor.
Sonuç: bu faktör seti 24–72 saat ufkunda kalıcı avantaj taşımıyor. Sistemin "kanıt yok" demesi doğru; sorun bunun
tabloyu işlevsiz göstermesiydi.

## Düzeltmeler
1. **Danışma modu (varsayılan, `LEARNED_MODEL_POLICY="advisory"`):** kanıtsız varlıkta eski model hesaplanmaya ve
   gösterilmeye devam eder (yön/aşama/hız/kalıcılık canlı), sinyal "· kanıtsız" etiketi alır, işleme giriş KAPALI.
   "abstain" (hiç sinyal yok) ve "legacy" seçenekleri config.py'de.
2. **Model ailesi seçimi (kendini optimize eden):** her varlık için 4 aile (ridge+rejim, ridge, ekonomik işaret korumalı,
   eşit ağırlık) × 2 ufuk (24s, 72s) = 8 aday örneklem dışında sınanır, en iyisi seçilir. En iyiyi seçmenin şans payı
   için eşik Bonferroni ile t ≥ 2.73. Rapor tüm adayları gösterir.
3. **Rejim anahtarı karışıklığı:** CSV'de "3" ve 3 / "3.0" ayrı rejim sayılıyordu → normalize edildi.
4. "Aday Rejim: None" → "Yok". Gece ABD nakit seansı kapalıyken ETF/endeksler "STALE" yerine "SEANS KAPALI".
5. Kanıt sütunu ve giriş gerekçesi kısa: "⚠️ Kanıtsız · bilgi amaçlı (t=1.6/2.73)".
6. `validation_reports/learned_model.json` gerçek panelden yeni yöntemle üretildi (hafta sonu iş yeniden üretir).

Not: hız/kalıcılık önceki çekimser dönemde hafızaya yazılan sıfırlar yüzünden birkaç döngü düşük görünür, kendiliğinden düzelir.
