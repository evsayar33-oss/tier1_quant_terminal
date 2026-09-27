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
- `stateful_adaptive_controller.py` içindeki mevcut `DynamicXAU_XAGModel`
  kullanımı olduğu gibi bırakıldı; onu da `dynamic_pair_model.py`'ye taşımak
  (kod tekrarını azaltmak için) küçük, düşük riskli bir takip işi.

---

# 2026-09-26 — SPX simetrik faktör, BTC/ETH ayrışma adaleti, XAU RVOL/ATR, self-improving loop

## 1) SPX/NQ simetrik faktör
`SPX_NQ_MODEL` eklendi (ayrı bir SPX~NQ regresyonu — NQ~SPX'in ters işareti
değil, kendi rezidüelini minimize eden bağımsız bir fit). `config.py`'ye
SPX için `nq_relative_divergence` faktörü eklendi, `gatekeeper.py`'ye
hesaplaması bağlandı.

## 2) "BTC'nin çok ayrışması" — kök neden ve düzeltme
İki ayrı kök neden bulundu:

a) `dynamic_pair_model.py`'de her çift aynı sabit `divergence_z=1.75`
   eşiğini kullanıyordu. Artık her çiftin `residual_z` geçmişi
   `AdaptiveThresholdStore`'a besleniyor ve gerçek ayrışma barı
   (`divergence_z_used`) o çiftin KENDİ ampirik dağılımından (P90)
   türüyor — soğuk başlangıçta eski 1.75 sabiti aynen korunuyor.

b) Daha önemlisi: `gatekeeper.py` içindeki eski fiyat-uzlaştırma mekanizması
   (`evaluate_all_assets_harmonized` ve `reconcile_pairs_post_adaptive`)
   üç çift için FARKLI, elle ayarlanmış `evidence_z` eşikleri kullanıyordu:
   SPX/NQ=1.25, XAU/XAG=1.35, **BTC/ETH=1.20**. BTC/ETH en düşük bara
   sahipti, yani "gerçek ayrışma" olarak teyit edilmesi diğer ikisinden
   sistematik olarak daha kolaydı — bu da ekranda BTC/ETH'nin sürekli
   "ayrışmış" görünmesinin doğrudan nedeniydi. Bu iki metod artık ortak bir
   `_pair_price_supported()` yardımcısı üzerinden, üç çift için de AYNI
   adaptif `DynamicPairModel` testini kullanıyor. Eski spread-z yöntemi
   sadece model için yeterli veri yokken devreye giren bir fallback olarak
   kaldı (ve fallback'teki BTC/ETH bar'ı da 1.35'e çekildi, artık ayrıcalıklı
   değil).

## 3) XAU için RVOL/ATR hesaplanamaması
`data_engine.py`'de "LIVE" (canlı) veri sayılma eşiği tüm semboller için
sabit 150 dakikaydı. Altın (GC=F) diğer sembollere göre daha uzun
sessiz/ince-kotasyon aralıkları verebildiğinden, veri aslında sorunsuzken
"STALE" (bayat) sayılıp `evaluate_trade_entry_gate` RVOL/ATR'yi 0.0 ile
reddediyordu — "Canlı Verileri Yenile" butonuna basınca an itibarıyla taze
veri geldiği için sorun geçici olarak kayboluyordu.

Düzeltme: her sembolün "LIVE" eşiği artık kendi gözlemlenen bar-yaşı
dağılımından adaptif olarak genişliyor (`_live_cutoff_seconds`,
`data_freshness_state.json`). Taban 150dk'nın ALTINA asla inmiyor (soğuk
başlangıçta hiçbir sembol için davranış değişmiyor), tavan 360dk'da sabit
(gerçek bir çok-saatlik kesinti hâlâ doğru şekilde STALE sayılır — eşik
"öğrenerek" kesintiyi normalleştiremez).

**Persisted vs. canlı analiz sorusu:** Sayfa açıldığında gösterilen,
`terminal_state.json`'daki bir önceki KAYITLI durumdur (dakikalar/saatler
eski olabilir). "Canlı Verileri Yenile" her zaman daha güncel ve daha
güvenilirdir; yukarıdaki düzeltme ikisi arasındaki en büyük tutarsızlık
kaynağını (XAU'nun yanlış "bayat" etiketlenmesi) gideriyor.

## 4) Reliability store'un self-improving döngüsü
`timeframe_confluence.TimeframeReliabilityStore`'a `record_prediction()` /
`settle_due_predictions()` eklendi:
- `gatekeeper.refresh_market()` her döngü başında, ufku dolmuş eski
  tahminleri bu döngünün taze kapanış fiyatlarıyla karşılaştırıp
  `record_outcome()`'a besliyor (yalnızca gerçek fiyat mevcutsa; yoksa
  tahmin beklemede kalıyor, asla tahmin edilmiyor).
- `evaluate_asset_direction()`, her confluence okumasından sonra o anki
  kapanış fiyatını referans alarak yeni bir tahmin kaydediyor (ufuk:
  LTF_1H→4s, MTF_4H→12s, HTF_1D→24s). Aynı (varlık, rejim, zaman dilimi)
  için zaten bekleyen bir tahmin varsa yenisi kuyruğa eklenmiyor.

Yerel veriyle uçtan uca test edildi: 10 tahmin kaydedildi, geriye
tarihlendirilip `settle_due_predictions()` ile hepsi doğru şekilde
sonuçlandırıldı ve reliability hücreleri güncellendi.

## Test durumu
Mevcut 30 test + bu turdaki tüm yeni/değişen davranış yerel
`ohlcv_history/*.csv` verisiyle uçtan uca doğrulandı (sohbet geçmişinde
tam çıktılar mevcut): SPX'in yeni simetrik faktörü, üç çiftin de artık aynı
adaptif barı kullanması, adaptif LIVE eşiğinin soğuk başlangıçta tam 150dk
kalması ve kalıcı bir kesintide 360dk tavanına oturması, ve tahmin
kaydet→sonuçlandır döngüsünün tam çalışması.

## Bu ortamda DOĞRULANAMAYAN kısımlar (ağ erişimi kapalı)
- Adaptif LIVE eşiğinin gerçek yfinance gecikme davranışıyla (özellikle
  GC=F/SI=F için) birkaç günlük canlı çalışma sonrası gerçekten genişleyip
  genişlemediği yalnızca canlı dağıtımda gözlemlenebilir
  (`data_freshness_state.json`'daki `BAR_AGE_SECONDS::GC=F` serisine bakın).


---

# 2026-09-26 (devam) — Öncü (leading) opsiyon-piyasası göstergeleri

## Sorun
`asset_direction` (ham fiyat momentumu) her varlıkta Cluster E'nin en büyük
tek faktörüydü ve SPX/NQ/XAG'da gerçek anlamda "öncü" (fiyattan bağımsız,
geleceğe dair) hiçbir Cluster E faktörü yoktu — hepsi fiyat/oran türeviydi.

## Çözüm: `leading_indicators.py` (yeni dosya)
CBOE opsiyon-türevi volatilite endekslerinden iki jenerik, kendi kendini
kalibre eden sinyal türü:
- `compute_vol_term_structure_lead`: VIX/VIX3M vade yapısı eğimi.
  Backwardation (yakın vade > 3 ay) güçlü, asimetrik bir stres sinyali;
  contango sadece "stressiz" okunuyor, güçlü bir "boğa" sinyali sayılmıyor.
- `compute_relative_vol_premium_lead`: bir varlığın kendi opsiyon-volatilite
  endeksinin (VXN, GVZ, VXSLV), kendi geçmiş normundan (kayan pencere
  z-score, sabit eşik değil) ne kadar saptığı — isteğe bağlı bir benchmark'a
  (VXN-VIX gibi) göre de ölçülebiliyor.

`data_engine.py`'nin çektiği sembol listesine `^VXN`, `^GVZ`, `^VXSLV`
eklendi (VIX/VIX3M zaten çekiliyordu, hiç faktörde kullanılmıyordu).

## Yeni faktörler
- SPX: `vix_term_lead` (w=0.70)
- NQ: `vix_term_lead` (w=0.60) + `tech_vol_premium_lead` (VXN vs VIX, w=0.55)
- XAU: `gold_vol_premium_lead` (GVZ, w=0.65)
- XAG: `silver_vol_premium_lead` (VXSLV, w=0.60)

## Ölçülebilir etki
"Reaktif (fiyat-tabanlı)" vs "öncü/pozisyon-akış" ağırlık payı:

| Varlık | Önce (reaktif payı) | Şimdi (reaktif payı) |
|---|---|---|
| SPX | ~%54 | **%46** |
| NQ  | ~%53 | **%47** |
| XAG | ~%51 | **%42** |
| XAU | ~%18 | **%15** (zaten iyiydi) |

(BTC/ETH zaten funding/taker-flow gibi gerçek pozisyon verisiyle %73-83
öncü ağırlıklıydı, dokunulmadı.)

## Bilinçli olarak YAPILMAYAN
Kullanıcı bu turda sadece "eksik öncü veri türlerini ekle" seçeneğini
seçti; `asset_direction`'ın ağırlığını azaltmak veya fiyat-onay kapısını
gevşetmek (diğer iki seçenek) bu turun kapsamı dışında bırakıldı — istenirse
ayrı bir turda yapılabilir.

## Test durumu
Mevcut 30 test + 5 yeni faktörün senkron sentetik VIX/VIX3M/VXN/GVZ/VXSLV
verisiyle gatekeeper üzerinden uçtan uca çalıştığı doğrulandı (backwardation,
contango, ani implied-vol sıçraması ve "anormal yok" senaryoları dahil).

## Bu ortamda DOĞRULANAMAYAN kısım
`^VXN`, `^GVZ`, `^VXSLV` sembollerinin yfinance üzerinden gerçekten veri
döndürdüğü CBOE/Google Finance kaynaklarıyla doğrulandı, ancak ağ erişimim
olmadığı için canlı `yf.download()` çağrısını bu ortamda test edemedim. İlk
canlı çalıştırmada bu üç sembol için `data_quality`'nin "UNAVAILABLE"
dönmediğini kontrol edin; dönerse (nadir de olsa bir CBOE endeksi
Yahoo'dan kaldırılmış/yeniden adlandırılmış olabilir) ilgili faktör
otomatik olarak 0.0 ile nötr kalır, sistemi bozmaz.

---

# 2026-09-26 (devam 2) — asset_direction ağırlık kesintisi + fiyat-onay kapısının yumuşatılması

## Sorun
Önceki turda eklenen öncü faktörler, reaktif payını sadece "yeni ağırlık
eklenerek seyreltme" yoluyla %5-10 düşürmüştü — kullanıcı haklı olarak bunun
yetersiz olduğunu belirtti. Ayrıca `reconcile_pairs_post_adaptive` içinde
daha önce fark edilmemiş, çift-uzlaştırmadan bile daha agresif bir mekanizma
bulundu: "Model Sinyali (24s-1hafta) uzlaştırması" fiyat teyit etmediğinde
takipçi varlığın TÜM AL/SAT verdict'ini NÖTR'e siliyordu.

## Düzeltme 1: asset_direction ağırlığı doğrudan kesildi (6 varlığın hepsi)
| Varlık | Önce | Şimdi |
|---|---|---|
| SPX | 2.50 | 1.10 |
| NQ  | 2.50 | 1.10 |
| XAU | 1.60 | 0.70 |
| XAG | 1.20 | 0.55 |
| BTC | 1.70 | 0.75 |
| ETH | 1.70 | 0.75 |

Sonuç (reaktif/fiyat-tabanlı pay):
SPX %46→%39, NQ %47→%40, XAG %42→%38, XAU %15→%7, BTC %17→%9, ETH %28→%20.

## Düzeltme 2: "opposite_one_sided" tam susturma → düşük-güven öncü sinyal
`gatekeeper.py::reconcile_pairs_post_adaptive`: fiyat teyit etmeyen tek
taraflı bir model verdict'i artık NÖTR'e silinmiyor. verdict/forecast_
direction/skor OLDUĞU GİBİ kalıyor (`conviction: "DÜŞÜK (fiyat teyidi
bekleniyor)"` etiketiyle); yalnızca otomatik giriş izni (`entry_allowed`)
ayrıca kapatılıyor. Görüntüleme (öncü sinyal görünür) ile yürütme (teyitsiz
otomatik giriş yok) birbirinden ayrıştırıldı.

## Bilinçli olarak yapılmayan
`app.py`'de yeni `conviction` alanını ayrıca vurgulayan bir UI elemanı
eklenmedi (veri artık dönen sözlükte var, dilerseniz ayrı bir turda arayüze
bağlarız).

## Test durumu
Mevcut 30 test geçti.
