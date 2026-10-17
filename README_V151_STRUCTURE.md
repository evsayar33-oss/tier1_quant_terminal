# v15.1 — Karar Özeti, Önerilen Stop, Piyasa Yapısı ve Bot Kalıntılarının Silinmesi

## 1) Sistemin amacı (netleştirildi)

Bu sistem bir al-sat botu DEĞİLDİR. Bu sistem şunları analiz eder:
* kısa vade yön tahmini (sonraki 1-4 saat),
* uzun vade yön tahmini (24 saat-1 hafta),
* doğru giriş zamanı.

Daha önce bir al-sat botu denendi. Sonuç kârsız oldu. Bu sürüm o denemenin bütün kalıntılarını siler.

## 2) Silinenler

| Grup | Dosyalar |
|---|---|
| İşlem katmanı | `paper_broker.py`, `signals.json` sözleşmesi (`tradeable`, `trade_side`, SL/TP, OKX sembolleri), paper trading karnesi |
| Strateji laboratuvarları | `strategy_lab`, `scalp_lab`/`scalp_data`, `xs_lab`/`xs_data`, `karma_lab`, `shock_lab`/`shock_data`, `long_lab`/`long_replay`, `copper_lab`/`copper_intraday_lab`/`copper_data`, `atvs_rules`, `alt_data`, `signal_panel` |
| Sentetik backtest | `backtest_engine.py`, `optimize_and_backtest_regimes.py` (rastgele veri üzerinde çalışıyordu) |
| Workflow | 8 laboratuvar workflow'u |
| Belgeler | `README_V39_PAPER` ve `README_V40` … `README_V140` (lab sürümleri) |

* `bot_loop.py` → `engine_loop.py`. Motor sadece analiz döngüsünü çalıştırır ve durumu yayınlar.
* `bot_status.json` → `engine_status.json` ("işlem yapılabilir" alanı yok).
* Bütün dosyalar git geçmişinde kalır. Gerekirse geri getirilebilir.

## 3) Yeni arayüz: "🎯 Karar Özeti" (sayfanın en üstü)

| Varlık | Giriş | Kısa vade (1-4 saat) | Uzun vade (24 saat-1 hafta) | Stop · kısa vade | Stop · uzun vade | Zamanlama |
|---|---|---|---|---|---|---|
| NQ | ⛔ Önerilmez · model kanıtı yok (t < 2) | 🟢 YUKARI | 🔴 SAT · kanıtsız | 24,810 (−0.42% · 1.1×ATR) | — | C · tetik yok / ters |

* **Giriş:** `✅ Giriş önerilir` sadece bütün kapılar açıksa görünür. Kapalıysa kısa sebep yazılır.
* **Kanıtsız:** öğrenilmiş model t ≥ 2 eşiğini geçmediyse yön "kanıtsız" olarak işaretlenir. Bu dürüst durumdur.
* Tablonun altında "Stop gerekçeleri, seans ve takvim" kutusu vardır.

## 4) Önerilen stop (`stop_levels.py`) — analiz çıktısı, emir değil

Piyasa yapıcı mantığı: stop emirleri belirgin seviyelerin hemen ötesinde birikir. Likidite avında ilk onlar alınır.

1. Stop, yönü geçersiz kılan en yakın **yapısal** seviyenin ötesine konur. Uzun yönde dip türü seviyeler (salınım dibi, önceki gün/hafta dibi, gece dibi, put duvarı) kullanılır. Kısa yönde tepe türü seviyeler kullanılır.
2. Seviye ile stop arasına bir **likidite avı payı** bırakılır.
3. Stop yuvarlak sayının tam üstüne veya altına konmaz.
4. Mesafe ufka uygun bir bant içinde kalır:
   * kısa vade: 0.75 – 3.0 × 1 saatlik ATR,
   * uzun vade: 0.40 – 1.75 × günlük beklenen hareket (opsiyondan; yoksa günlük ATR).
5. −Γ rejiminde pay ×1.5 olur.
6. Bantta yapısal seviye yoksa volatilite stopu kullanılır ve gerekçede yazılır.

**Kendi kendini kalibre eder** (`stop_ledger.csv`): her öneri ufuk sonunda notlanır.
"Stop avlandı" = stop tetiklendi, ama ufuk sonunda yön yine doğru çıktı.
Bu oran %10'un üstündeyse pay büyür (en çok ×2.0). Bu oran %10'un altındaysa pay küçülür (en az ×0.8). 30 bağımsız gözlemden önce çarpan 1.0'dır.

## 5) Eklenen eksik parçalar

| # | Parça | Dosya | Durum |
|---|---|---|---|
| 1 | 5 dakikalık bar | `market_structure.fetch_5m` | Duvar testleri ve likidite avı 5 dk barda ölçülür. Saatlik bar 1 saat içindeki 4 testi göremez. |
| 1 | Seans saati | `market_structure.session_phase` | Asya, Avrupa, ABD açılış, gün ortası, kapanış (0DTE charm) ve kapalı. New York saatiyle, yaz/kış saati doğru. |
| 2 | Opsiyon takvimi | `market_structure.options_calendar` | Aylık OPEX (3. Cuma), üçlü vade, VIX vadesi (sonraki ayın 3. Cuması − 30 gün), ay/çeyrek sonu. |
| 3 | Vanna ve charm | `dealer_gamma` | "IV 1 puan düşerse dealer alır/satar" ve "1 gün geçerse dealer alır/satar" ($). Formüller sonlu farkla test edildi. |
| 4 | Likidite seviyeleri | `market_structure.liquidity_levels` | Önceki gün/hafta tepe-dip (CME günü 18:00 ET'de başlar), gece aralığı, seans VWAP, salınım noktaları, yuvarlak sayılar. |
| 4 | Likidite avı | `market_structure.detect_sweep` | Seviyenin içinden açılış, ötesine fitil, içinde kapanış. Düz kırılım sweep sayılmaz. |
| 5 | CTA akışı (tahmini) | `market_structure.cta_model` | 20/60/120/250 gün trend takipçisi taklidi: pozisyon, tetik seviyeleri, "fiyat sabit kalırsa akış". |
| 5 | Vol-control akışı (tahmini) | `market_structure.vol_control_model` | Hedef vol %10, EWMA gerçekleşen vol, 5 günlük kaldıraç değişimi (SPX/NQ). |
| 6 | Kripto gaması | `dealer_gamma` (Deribit) | BTC/ETH için aynı harita. Vade 08:00 UTC, sözleşme = 1 coin, 7/24 → √365. |

## 6) Kanıt nasıl toplanır (kendi kendine gelişme)

* `cta_trend_position`, `vol_control_flow`, `liquidity_sweep` artık faktör listesindedir, rolleri **durum** (`"role": "state"`).
* Bu faktörler yön skoruna oy vermez. Haftalık replay onları panele yazar.
* Replay raporundaki "Tanı" sütunu her birinin 3 dönem kararlılığını gösterir. Öğrenilmiş model bu faktörleri sadece kanıt varsa kullanır.
* Gama defteri (`dealer_gamma_history.csv`) ve stop defteri (`stop_ledger.csv`) state dalına kaydedilir. Öğrenme kaybolmaz.

## 7) Dürüst sınırlar

* CTA ve vol-control rakamları **tahmindir**. Gerçek fon pozisyonları görülemez. Model genel bir trend takipçisini taklit eder.
* Takvim ABD resmi tatillerini hesaba katmaz. OPEX bir tatile denk gelirse bir gün önce olur.
* FOMC tarihleri eklenmedi. Yanlış tarih eklemek, hiç eklememekten kötüdür.
* Kriptoda dealer işaret varsayımı daha zayıftır. Gama defteri bunu da ölçer.
* Bu ortamda ağ yoktur. Opsiyon zincirleri ve 5 dk veri ilk kez GitHub Actions'ta çekilecek.

## 8) Telefondan yapılacaklar

1. Dalı ana dala birleştir.
2. Streamlit'te **Reboot app** yap (yeni modüller yüklenir).
3. Sayfanın en üstündeki "🎯 Karar Özeti" tablosunu kullan.
4. Eski lab dalları (`lab`, `shocklab`, `karmalab`, `copperlab` …) artık kullanılmıyor. İstersen GitHub'da silebilirsin. Bu zorunlu değildir.

## Test
* Yeni `test_market_structure.py` (13 test): OPEX/VIX vade kuralları; New York saati ve CME günü; önceki gün tepe/dip; sweep ile düz kırılım ayrımı; CTA tetiği ve vol-control yönü; vanna/charm sonlu fark; vanna rallisi işareti; Deribit ayrıştırma ve √365; stop yapı ötesi + av payı; yuvarlak sayı ve −Γ genişlemesi; volatilite stopu ve günlük birim; stop defteri kalibrasyonu; karar özeti etiketleri.
* `test_engine_loop.py`: motorda işlem katmanı kalmadığı test edilir.
