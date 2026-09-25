# 2026-09-25 — Ayrışma tespiti, HTF/LTF confluence, adaptif rejim eşikleri

## Yeni dosyalar
- `dynamic_pair_model.py` — `xau_xag_dynamic_pair.py`'deki recency-weighted
  ridge regresyon + robust rezidüel z-score modelinin genelleştirilmiş hali.
  Artık NQ~SPX ve ETH~BTC çiftlerinde de aynı matematikle çalışıyor
  (`NQ_SPX_MODEL`, `ETH_BTC_MODEL`, `XAG_XAU_MODEL`). `blended_anchor_signal()`
  eski sabit eşikli (|z|<1.5) iki-rejimli blend'i, rezidüele göre yumuşak
  geçiş yapan sürekli bir fonksiyonla değiştiriyor.
- `timeframe_confluence.py` — daha önce repoda hiç var olmayan HTF/MTF/LTF
  confluence motoru. 1H barları 4H/1D'ye resample ederek (ayrı network
  çağrısı gerektirmeden, senkron kayması olmadan) ağırlıklı bir confluence
  skoru üretiyor. Ağırlıklar `TimeframeReliabilityStore` üzerinden
  (varlık, rejim, zaman dilimi) hücresi bazında kendini güncelliyor.
- `adaptive_regime_thresholds.py` — `macro_regime_engine.py`'deki sabit
  z-score eşiklerini (1.5, -1.0, 2.0 vb.) her indikatörün kendi
  recency-weighted ampirik dağılımından türeyen, Bayesian shrinkage ile
  soğuk başlangıçta eski sabit değerlere eşit davranan eşiklerle
  değiştiriyor.

## Değişen dosyalar
- `gatekeeper.py`: `gold_sympathy`, `btc_sympathy`, `eth_btc_beta`
  faktörleri artık ilgili `DynamicPairModel` fit'ini kullanıyor (önceden
  `eth_btc_beta` düz fiyat-oranı MAD z-score'uydu, `btc_sympathy` ise
  yanlışlıkla BTC'nin kendi momentumunu tekrar kullanıyordu). Yeni
  `spx_relative_divergence` (NQ) ve `gold_divergence_residual` (XAG)
  faktörleri eklendi. Giriş kapısına (`evaluate_asset_direction`) HTF/LTF
  confluence kontrolü eklendi: gerçek günlük veri mevcutsa ve confluence
  yetersizse `entry_allowed=False` olur; günlük veri yoksa eski davranış
  aynen korunur (regresyon yok).
- `config.py`: NQ'ya `spx_relative_divergence`, XAG'a
  `gold_divergence_residual` faktörleri eklendi.
- `data_engine.py`: `fetch_single_ticker_daily()` eklendi — HTF (1D) barları
  için ayrı, kendi persistence anahtarına (`{symbol}_1D`) yazan bir çekim
  yolu. 1H geçmişiyle çakışmaz.
- `macro_regime_engine.py`: R1–R5 tetikleyicilerindeki sabit sayılar
  `adaptive_regime_thresholds.AdaptiveThresholdStore` üzerinden okunuyor;
  her `evaluate()` çağrısı önce o günün gerçek z-skorlarını store'a
  besliyor (`th()` yardımcı fonksiyonu).

## Test durumu
`test_suite.py`, `test_stateful_adaptive.py`, `test_xau_signal_fix.py`,
`test_data_integrity_fix.py`, `test_ohlcv_history.py`,
`test_delay_false_positive_adaptation.py` içindeki mevcut 30 test de
(pytest kurulu olmadığından basit bir runner ile) tekrar çalıştırıldı,
hepsi geçti — mevcut davranışta regresyon yok.

Yeni modüller ayrıca repodaki gerçek `ohlcv_history/*.csv` dosyalarına karşı
ayrı ayrı test edildi (bkz. sohbet geçmişi): NQ~SPX residual_z≈2.08 ile
canlı bir ayrışma yakalandı, XAU~XAG ve ETH~BTC ise normal uyum
gösterdi — modelin ayırt etme gücü çalışıyor.

## Bu ortamda DOĞRULANAMAYAN kısımlar (ağ erişimi kapalı)
- `fetch_single_ticker_daily()`'nin canlı yfinance çağrısı hiç
  çalıştırılamadı — yalnızca statik olarak yazıldı, mevcut
  `fetch_single_ticker_1h` ile aynı desende. İlk canlı Streamlit/GitHub
  Actions çalıştırmasında `ohlcv_history/*_1D.csv` dosyalarının oluştuğunu
  ve `grid_daily` sözlüğünün dolduğunu doğrulayın.
- FRED tabanlı büyük tarihsel makro serileri bu ortamda çekilemediği için
  `adaptive_regime_thresholds` sadece 1H grid'den beslenen z-skorlarla test
  edildi; canlı ortamda birkaç haftalık gerçek veri birikince eşiklerin
  gerçekten kaymaya başladığını (diagnostics() ile n_observations/trust
  değerlerinden) izlemeniz önerilir.

## Kapsam dışı bırakılanlar (bilinçli, sonraki tur için)
- SPX tarafına simetrik `nq_relative_divergence` eklenmedi (NQ tarafı
  eklendi, SPX benzer şekilde genişletilebilir).
- `stateful_adaptive_controller.py` içindeki mevcut `DynamicXAU_XAGModel`
  kullanımı olduğu gibi bırakıldı; onu da `dynamic_pair_model.py`'ye taşımak
  (kod tekrarını azaltmak için) küçük, düşük riskli bir takip işi.
- `TimeframeReliabilityStore.record_outcome()` çağrısı henüz hiçbir
  periyodik job'a bağlanmadı (`stateful_background_tracker.py`'nin yaptığı
  işin bir benzeri gerekiyor) — ağırlıklar şu an sadece prior ile başlıyor,
  gerçek anlamda "kendini geliştirmesi" için bu bağlantının kurulması lazım.
