# Tier-1 Stateful Adaptive Direction v3.1

Bu paket gecikme–false-positive dengesini iyileştirir.

## Dosya işlemleri

**Mevcut dosyaları replace et:**
- `app.py`
- `stateful_memory_store.py`
- `stateful_adaptive_model.py`
- `stateful_adaptive_controller.py`
- `stateful_background_tracker.py`
- `.github/workflows/stateful_adaptive_tracker.yml`

**Yeni dosya ekle:**
- `stateful_direction_engine.py`

`test_delay_false_positive_adaptation.py` yalnızca doğrulama içindir; production runtime tarafından import edilmez.

## Kritik davranış değişikliği

Direction artık `entry_allowed` değerine bakmaz.

`entry_allowed=False` olsa bile model uygun şartlar oluştuğunda `EARLY` veya `CONFIRMED` yön üretebilir. Execution gate daha sonra ayrı değerlendirilir.

## Adaptasyon

- 4H realized outcomes: score threshold + factor calibration
- 1H realized outcomes: early-direction reliability
- score velocity / acceleration: canlı threshold modulation
- persistence: orta kuvvette tek-bar false-positive azaltımı
- strong impulse: gecikmeyi sınırlı biçimde azaltan bypass
- hysteresis: yön churn'ünü azaltır
- hard threshold envelopes: modelin tek cycle'da kontrolden çıkmasını önler
- persistent runtime: restart sonrası direction memory kaybolmaz

## Doğrulama

```bash
pytest -q test_delay_false_positive_adaptation.py
```

Beklenen: `5 passed`.
