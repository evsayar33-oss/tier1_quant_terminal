# Tier-1 Stateful Direction v3.1

Bu paket mevcut Stateful Adaptive v3 üzerine gecikme/false-positive dengesini iyileştiren yön motorunu ekler.

## Değiştirilecek mevcut dosyalar

- `app.py`
- `stateful_adaptive_controller.py`
- `stateful_adaptive_model.py`
- `stateful_memory_store.py`
- `stateful_background_tracker.py`
- `.github/workflows/stateful_adaptive_tracker.yml`

## Eklenecek yeni dosya

- `stateful_direction_engine.py`

## Test

Yeni testler:

```bash
pytest -q test_delay_false_positive_adaptation.py
```

## Çalışma mantığı

```text
RAW FACTOR SCORE
      ↓
ADAPTIVE SCORE / HISTORICAL OUTCOME CALIBRATION
      ↓
LIVE VELOCITY + ACCELERATION
      ↓
EARLY DIRECTION
      ↓
PERSISTENCE / STRONG IMPULSE
      ↓
CONFIRMED DIRECTION
      ↓
SEPARATE EXECUTION GATE
```

Execution gate (`entry_allowed`) yön tahmininin girdisi değildir.

1H gerçekleşmeler erken yön eşiğinin güvenilirliğini, 4H gerçekleşmeler ise skor threshold/factor calibration katmanını günceller.

Adaptive hareketler hard envelope içinde tutulur; threshold tek cycle'da sınırsız değişemez.
