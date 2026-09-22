# Tier1 Quant Terminal — Data Integrity & XAU/XAG/UI Fix v3.2

Bu paket mevcut Stateful Adaptive v3.1 sisteminin üzerine uygulanacak düzeltme paketidir.
Workflow değiştirilmez.

## Üretimde üzerine yazılacak dosyalar

- `app.py`
- `stateful_adaptive_controller.py`
- `stateful_adaptive_model.py`
- `stateful_direction_engine.py`
- `stateful_factor_quality.py` (YENİ)
- `quant_processor.py`

## Test/legacy uyumluluk dosyaları

- `v21_patch.py` (eski test helper'ı; üretim engine'i değildir)
- `test_data_integrity_fix.py`
- `test_xau_signal_fix.py`

## Düzeltilen noktalar

1. **UI TypeError**
   `adaptive_factor_weights` nested dict yapısının `float(v)` ile render edilmesi düzeltildi.

2. **Eksik veri = 0 problemi**
   Kaynak yoksa factor artık `0.00` gibi gösterilmiyor; `VERİ YETERSİZ` olarak işaretleniyor ve adaptive score hesabına alınmıyor.

3. **Gerçek 0 ile eksik veri ayrımı**
   Kaynak mevcut ve ölçüm gerçekten sıfırsa `MEVCUT / NÖTR` olarak korunuyor.

4. **Model veri kapsamı**
   Geçerli factor ağırlığı / toplam factor ağırlığı üzerinden coverage ölçülüyor. Çok düşük coverage'da model güvenli moda geçiyor ve skor `VERİ YETERSİZ` olarak sınıflandırılıyor.

5. **XAG relative-value double counting**
   Gold sympathy + XAG/XAU + XAG/HG + HG/XAU gibi korelasyonlu relative factor katkıları sınırsız şekilde üst üste binmiyor; bounded contribution cap uygulanıyor.

6. **Relative-value denominator bug**
   `compute_ratio_z()` artık yanlışlıkla numerator kolonlarını kontrol edip denominator `Open` benzeri ilk kolonu kullanamıyor; gerçek `denominator.Close` kullanılıyor.

7. **Warm-up değerleri**
   İlk gözlemlerde istatistiksel olarak hesaplanamayan `Score Z`, `Velocity`, `Acceleration` artık sahte `0.00` yerine `WARM-UP`/`—` gösteriliyor.

8. **Adaptive factor tablosu**
   Gösterilen factor katkıları artık gerçekten adaptive score modelinin kullandığı final contribution'lardan geliyor; eski/stale katkılar ekranda kalmıyor.

9. **XAU/XAG pair modeli korunuyor**
   Dinamik beta/residual modeli kaldırılmadı. Bu paket XAG'yi XAU'ya zorla eşitlemez; yalnızca relative factorların model içinde aşırı baskın olmasını sınırlar.

## Doğrulama

Mevcut repo dosyalarıyla birleşik test ortamında:

`38 passed`

Python syntax/import kontrolü de geçti.

## Kurulum

ZIP'i repo köküne açın ve yukarıdaki üretim dosyalarını mevcut Stateful Adaptive v3.1 sürümlerinin üzerine yazın.

Mevcut `.github/workflows/stateful_adaptive_tracker.yml` değiştirilmez.
`config.py`, `data_engine.py`, `dynamic_entry_engine.py`, `stateful_memory_store.py`, `stateful_regime_controller.py` ve `xau_xag_dynamic_pair.py` mevcut sürümleriyle bırakılabilir.
