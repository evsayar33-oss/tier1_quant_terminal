# v15.0 — Piyasa Yapıcı Mantığı: Dealer Gamma Haritası + "Volatilite Yön Değildir" Düzeltmesi

## 1) Videodaki eksik parça

Video bir NQ grafiğini gösterir. Fiyat bir seviyeyi 4 kez dener. Fiyat seviyeyi kıramaz. Sonra birkaç dakikada seviyeyi kırar.
Videonun cevabı: 0DTE opsiyonlar ve piyasa yapıcının (dealer) hedge akışı.

* Dealer net **uzun gama (+Γ)** ise fiyat yükselince satar, fiyat düşünce alır. Hareket sıkışır. Büyük strike'lar duvar olur.
* Dealer net **kısa gama (−Γ)** ise fiyat yükselince alır, fiyat düşünce satar. Hareket hızlanır.
* Duvar emilince veya fiyat **gamma flip** seviyesini geçince dealer akışı yön değiştirir. Kırılım bu yüzden hızlıdır.

Sistemde bu parça yoktu. Sistemdeki her faktör bir **değişimdi** (oran z-skoru, momentum, vade eğrisi). Hiçbir faktör bir **seviye** değildi.
Yeni modül: `dealer_gamma.py`.

## 2) Mumlar nasıl oluşur? (kök neden analizi)

Bir mum, bir açık artırmanın sonucudur. Fiyat, karşı tarafta likidite bulana kadar hareket eder.
Piyasa yapıcı bu likiditenin büyük kısmını verir. Piyasa yapıcı yön tahmini yapmaz. Piyasa yapıcı envanterini ve gamasını yönetir.
Bu yüzden şu üç bilgi, mumun **nasıl** oluşacağını belirler:

1. Dealer gamasının işareti (sıkışma mı, hızlanma mı).
2. Seviyeler (duvarlar, flip, pin).
3. Zaman (0DTE gaması vade kapanışına doğru sıfıra iner).

Sistemin kendi 50.406 satırlık walk-forward paneli (`validation_reports/factor_panel.csv.gz`, 2024-10 → 2026-09) incelendi.
Dönem 3 eşit parçaya bölündü. Bir bulgu, sadece 3 parçanın hepsinde aynı yöndeyse kabul edildi.

### Kök neden 1 — Volatilite bilgisi YÖN skoruna giriyordu
Sistem "korku yüksek → sat" varsayımını kullanıyordu. Veri bunun tersini söylüyor.

| Faktör (işareti düzeltilmiş) | 1. dönem | 2. dönem | 3. dönem | Sonuç |
|---|---|---|---|---|
| SPX `vix_term` IC 24s | −0.067 | −0.214 | −0.088 | 3/3 TERS |
| NQ `vix_term` IC 24s | −0.034 | −0.210 | −0.077 | 3/3 TERS |
| SPX `vix_strain` IC 24s | −0.001 | −0.093 | −0.048 | ters / sıfır |
| SPX `vix_term` → hareketin BÜYÜKLÜĞÜ | −0.126 | −0.300 | −0.055 | 3/3 güçlü |

Yorum: implied volatilite sigortanın fiyatıdır. Volatilite, hareketin **büyüklüğünü** bilir. Volatilite, hareketin **yönünü** bilmez.
Korku zirvesinde dealer kısa gamadadır ve fiyat zaten aşırı hareket etmiştir. Sonra IV düşer. Dealer put hedge'lerini geri alır (vanna akışı). Fiyat toparlanır.

### Kök neden 2 — Aynı değişken üç kez sayılıyordu
`vix_term` ile `vix_term_lead` arasındaki sıra korelasyonu **1.00**. Bu iki faktör aynı sinyaldir.
`vix_strain` ile korelasyon 0.75. SPX skorunda VIX seviyesi toplam ~1.85 ağırlıkla, yanlış işaretle oy kullanıyordu.

### Kök neden 3 — En büyük ağırlık, piyasa yapıcının emdiği harekete veriliyordu
`asset_direction` (4 saatlik fiyat ivmesi) en büyük ağırlığa sahipti (1.10). IC'si sıfıra yakın (SPX: +0.010 / −0.047 / −0.010).
Dealer çoğu gün uzun gamadadır. Son saatlerin hareketi dealer hedge'i ile emilir. Bu yüzden "son 4 saat yükseldi → al" kuralı çalışmaz.
Performans karnesindeki "Trend takibi %47-49 isabet" sonucu da bunu gösterir.

### Kök neden 4 — Doğrusal toplama, rejimden bağımsızdı
Skor = Σ ağırlık × işaret × z. Bir faktör her rejimde aynı işaretle oy kullanır.
Piyasa yapıcı mantığında rejim bir **çarpandır**, bir terim değildir. +Γ'da kırılım söner. −Γ'da kırılım uzar.
Sistem rejimi ADX ile ölçüyordu. ADX geçmiş fiyattan türer. Dealer gaması ise gelecekteki zorunlu hedge akışını gösterir.

### Kök neden 5 — Seviye ve zaman kavramı yoktu
Sistem saatlik barla çalışır. Sistem bir fiyat seviyesini (strike, flip, önceki gün tepesi) bilmez.
Gece 03:00 UTC barı ile 13:30 UTC nakit açılış barı aynı muameleyi görür.

## 3) Yapılan değişiklikler

### A. `dealer_gamma.py` (YENİ) — eksik parça
* CBOE gecikmeli opsiyon zincirini okur (`_NDX`+`QQQ` → NQ, `_SPX`+`SPY` → ES). CBOE yoksa yfinance kullanır. Veri yoksa `None` döner. Sahte veri üretmez.
* Black–Scholes gaması ile dealer dolar gamasını hesaplar ($ / %1 hareket).
* Bütün seviyeleri **vadeli fiyat uzayına** taşır (baz farkı dahil). Endeks ve ETF zincirleri toplanır.
* Çıktılar: rejim (+Γ / −Γ), **gamma flip**, **yapısal call/put duvarları** (≥1 gün vade, Γ fiyat strike'a geldiğinde ölçülür), **0DTE gün içi duvarlar**, **0DTE pin**, 0DTE gama payı, ATM IV ve **piyasa yapıcının fiyatladığı 1 günlük hareket**.
* `level_pressure()`: videodaki olayı ölçer. Bir duvarın kaç kez test edildiğini ve testler arasında diplerin yükselip yükselmediğini sayar. Yükselen dipler = emilen likidite azalıyor.

### B. Kendi kendini notlayan defter — `DealerGammaLedger`
* Her döngüde haritayı `dealer_gamma_history.csv` dosyasına yazar. Aynı saati iki kez yazmaz.
* 24 saat sonra gerçekleşen fiyatla notlar.
* Önceden tanımlı iki önermeyi test eder (sonradan seçim yok):
  1. **Sıkışma:** +Γ günlerinde gerçekleşen aralık / beklenen hareket, −Γ günlerinden küçük mü?
  2. **Duvar:** fiyat call duvarına yakınken duvar 24 saat tutuyor mu? (taban %50)
* Günde bir bağımsız gözlem sayılır. Kanıt eşiği: n ≥ 30, t ≥ 2.
* Kanıt oluşmadan harita giriş iznini **kaldırmaz**. Politika `config.DEALER_GAMMA_POLICY = "advisory"`.
* Kanıt oluşunca `"active"` politikası pin riskinde girişi kapatabilir. Harita hiçbir zaman giriş izni **vermez** ve yönü **değiştirmez**.

### C. Faktör rolü: `"role": "state"` (`config.py`)
* SPX ve NQ için `asset_direction`, `vix_strain`, `vix_term`, `vix_term_lead` artık **durum değişkenidir**.
* Durum değişkeni hesaplanır, ekranda görünür, replay paneline yazılır, öğrenilmiş modele verilir. Öğrenilmiş model bu faktörü **her iki işaretle** kullanabilir.
* Durum değişkeni elle ağırlıklı **yön** skoruna oy vermez (`gatekeeper.py`, `stateful_adaptive_model.py`, `stateful_factor_quality.py`).
* Etki (aynı panelde, 3 dönem × 24s/72s = 12 hücre): SPX ve NQ skor IC'si **12/12 hücrede** iyileşti.
  * SPX 24s: +0.054 / −0.068 / −0.052 → +0.063 / +0.010 / −0.015
  * NQ 72s: +0.009 / −0.025 / +0.025 → +0.049 / +0.023 / +0.110

### D. Haftalık replay raporunda kendi kendine tanı (`historical_replay.py`)
* IC tablosuna "3 dönem IC 24s" ve "Tanı" sütunları eklendi.
* Kural her hafta aynıdır: 3/3 dönemde ters → `⛔ 3/3 TERS (rol: durum?)`. 3/3 dönemde doğru → `✅ 3/3 kararlı`.
* Bu analiz bu kez elle yapıldı. Artık sistem bu analizi her hafta kendisi yapar.

### E. Bağlantılar
* `stateful_background_tracker.py`: nihai giriş kapısından sonra haritayı çalıştırır. Sonuç `terminal_state.json → dealer_gamma` alanına yazılır. Her SPX/NQ kararına `dealer_gamma` bloğu eklenir.
* `state_sync.py`: `dealer_gamma_history.csv` state dalına kaydedilir (öğrenme kaybolmaz).
* `app.py`: "🧲 Dealer Gamma Haritası" bölümü eklendi (salt okunur).

## 4) Bilinçli olarak yapılmayanlar

* **VIX işareti ters çevrilmedi.** "Korkuda al" kuralı sadece 2. dönemde güçlü (Nisan 2025 tarife çöküşü ve toparlanması). 1. dönemde sıfıra yakın. Tek bir olaya uydurma olurdu. İşareti öğrenilmiş model belirler (model SPX için `vix_term` ağırlığını kendi başına −0.251 öğrendi).
* **XAU, XAG, BTC, ETH faktörlerine dokunulmadı.** Bu varlıklarda sonuçlar dönemden döneme değişiyor. Kanıt yok, değişiklik yok.
* **Gama haritası yön skoruna eklenmedi.** Tarihsel opsiyon zinciri ücretsiz değil. Haritanın geçmiş performansı ölçülemez. Defter kanıtı canlı veriden toplar.

## 5) Dürüst durum

* Model hâlâ kanıtlı bir avantaja sahip değil. Düzeltme, SPX/NQ skorunun IC'sini negatiften küçük pozitife taşıdı. Bu, t ≥ 2 eşiğini geçmez.
* Bu sürüm sistemin **mantık hatasını** düzeltir ve **eksik veriyi** toplamaya başlar. Avantajın kanıtı defterden ve haftalık replay'den gelecek.

## 6) Kalan eksik parçalar (öncelik sırasıyla)

1. **Gün içi zaman ölçeği.** 5 dakikalık bar ve seans yapısı: nakit açılış (13:30 UTC), öğle sakinliği, son 2 saat (0DTE gaması hızla düşer, charm akışı), kapanış imbalance'ı. Videodaki "birkaç dakikada kırılım" saatlik barda görünmez.
2. **Opsiyon takvimi.** Aylık OPEX (3. Cuma), VIX vadesi (Çarşamba), çeyrek sonu JPM collar yenilemesi. OPEX sonrası gama "serbest kalır" ve volatilite artar.
3. **Vanna ve charm akışları.** IV düşünce ve zaman geçince dealer hedge'i değişir. Bu, ralli/tükeniş yönünü açıklar. Harita bu alanlara genişletilebilir.
4. **Likidite seviyeleri.** Önceki gün tepe/dip, gece aralığı, VWAP, yuvarlak sayılar. Stop emirleri bu seviyelerde birikir. Seviye kırılınca stoplar tetiklenir (likidite avı).
5. **Sistematik akışlar.** CTA tetik seviyeleri ve volatilite hedefli fonlar. Bu fonlar gerçekleşen volatiliteye göre mekanik alım/satım yapar.
6. **Kripto gaması.** Deribit BTC/ETH opsiyonları aynı mantıkla haritalanabilir.

## 7) Telefondan yapılacaklar

1. Bu dalı ana dala birleştir.
2. Bir şey yapmana gerek yok. Saatlik motor (`tier1_engine_loop.yml`) haritayı her döngüde kendisi çalıştırır.
3. Streamlit uygulamasında en altta "🧲 Dealer Gamma Haritası" bölümünü aç.
4. ~6 hafta sonra (≈30 işlem günü) bölümdeki "Kanıt" sütununa bak. "KANITLANDI" görürsen `config.py` içinde `DEALER_GAMMA_POLICY = "active"` yap.
5. Haftalık "Historical Validation" çalıştıktan sonra replay raporundaki "Tanı" sütununa bak. `⛔ 3/3 TERS` görünen yeni bir faktör varsa onu da bana bildir.

## Test
* Yeni: `test_dealer_gamma.py` (13 test): BS gaması sonlu farkla doğrulanır; CBOE OCC sembolleri okunur; duvar/flip/rejim kurulmuş zincirde bulunur; endeks ve ETF aynı vadeli seviyelerini verir; 0DTE ve yapısal duvarlar ayrılır; vadesi geçmiş seriler atılır; seviye testi sayılır; defter aynı saati tekrar saymaz; defter gerçek etkiyi bulur ve etkisiz veride kanıt üretmez; politika `advisory` iken giriş asla değişmez; harita asla giriş izni vermez; durum faktörü yön skorunu değiştirmez; replay tanı kuralı.
