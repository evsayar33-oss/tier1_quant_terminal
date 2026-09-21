# Stateful Adaptive Architecture — Integration

Bu paket mevcut dosyaları değiştirmeden yeni katmanları ekler. Üretim akışına almak için aşağıdaki sıralama uygulanır.

## 1. Yeni dosyaları repo köküne kopyala

- `stateful_memory_store.py`
- `stateful_regime_controller.py`
- `adaptive_score_model.py`
- `dynamic_entry_engine.py`
- `xau_xag_dynamic_pair.py`
- `stateful_adaptive_controller.py`
- `stateful_background_tracker.py`
- `.github/workflows/stateful_adaptive_tracker.yml`
- `test_stateful_adaptive.py`

## 2. İlk otomatik çalıştırmayı aç

GitHub Actions içinde **Tier-1 Stateful Adaptive Quant Tracker** workflow'unu manuel `workflow_dispatch` ile bir kez çalıştır.

Workflow şunları kalıcılaştırır:

- `stateful_adaptive_memory.json` → model hafızası
- `terminal_state.json` → mevcut Streamlit state'i
- `terminal_history_stateful.csv` → okunabilir operasyon geçmişi
- `ohlcv_history/` → mevcut gerçek OHLCV cache/history

## 3. Streamlit canlı yenilemesini aynı adaptif katmana bağla

`app.py` içinde mevcut `gk.refresh_market()` çağrısından hemen sonra:

```python
from stateful_adaptive_controller import StatefulAdaptiveController
```

ve gatekeeper oluşturulduktan sonra:

```python
stateful_controller = StatefulAdaptiveController()
```

Refresh akışında `gk.refresh_market()` sonrasında:

```python
stateful_controller.prepare_cycle(gk)
```

Mevcut:

```python
verdicts = gk.evaluate_all_assets_harmonized(prev_map)
```

satırının hemen ardından:

```python
verdicts, adaptive_diag = stateful_controller.finalize_cycle(
    gk,
    verdicts,
    previous_signals=prev_map,
)
```

ve `new_state` içine:

```python
"stateful_adaptive": adaptive_diag,
```

eklenir.

## 4. Neyi değiştirdi?

### Rejim

Ham `MacroRegimeEngine` detector aynen kalır. Yeni controller:

`candidate → persistence → confirmation → confirmed`

state'ini kalıcı tutar. `REJIMSIZ_GECIS` eski confirmed rejimi silmez. Aşırı şoklarda acil geçiş mümkündür.

### Model skoru

Mevcut factor matrix silinmez. Her factor için gerçekleşen 4 saatlik forward return'a göre exponentially decayed IC hesaplanır. IC, base weight'i `0.65–1.35x` arasında sınırlı biçimde değiştirir.

### Score threshold

Her asset + regime için score/outcome istatistiği tutulur. 90% one-sided Wilson lower confidence bound ve decayed effective sample size kullanılarak threshold seçilir. Threshold tamamen serbest bırakılmaz; regime prior ile shrink edilir.

### Giriş filtresi

Mevcut ATR/RVOL mantığı korunur fakat stateful entry engine minimum 60 geçerli gözlemle çalışır. Böylece mevcut ~82 barlık gerçek tarihçede gereksiz warm-up blokajı oluşmaz.

### XAU/XAG

Sabit `82% gold sympathy` kullanılmaz. Saatlik getirilerde:

`XAG = alpha + beta_gold*XAU + beta_copper*HG + residual`

EW ridge ile tahmin edilir. Residual z-score yüksekse gerçek ayrışmaya izin verilir; düşükse model skorları yalnızca küçük ve simetrik biçimde birbirine yaklaştırılır.

## 5. Önemli çalışma ilkesi

Bu mimari ilk kurulumda geçmişi sihirli biçimde tamamlamaz. İlk günlerde `effective_n` düşük olabilir. Model ancak gerçek forward outcomes oluştukça öğrenir. Bu nedenle `adaptive=True` ibaresi "sınırsız serbest adaptasyon" değil, kontrollü ve shrink edilmiş online adaptation anlamına gelir.
