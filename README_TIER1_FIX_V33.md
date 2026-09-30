# v3.3 — XAU / ETH giriş ve sinyal denetimi (2026-09-28)

Kullanıcı şikâyeti: "ETH model sinyali ve giriş analizi normal görünmüyor; XAU giriş analizi normal değil."
Sonuç: **3 gerçek hata + 2 mantık hatası** bulundu ve düzeltildi. Model ağırlıkları, rejim eşikleri ve
yön motorları DEĞİŞMEDİ.

## 🔴 Hatalar
1. **RVOL patlaması (ETH/BTC).** Yahoo kripto saatlik barlarının ~%50'sinde Volume=0 geliyor. 20 barlık taban
   0 olunca RVOL = hacim / 1e-12 → canlı `rvol_climax` ETH 1.6e19, BTC 3.7e18. "Hacim climax" filtresi fiilen
   kapalıydı. Artık 0 hacim = raporlanmamış (eksik) veri.
2. **Yarım bar (XAU).** Saat 10:35'teki çalışma, 35 dakikalık oluşmakta olan 10:00 barını tam barlarla
   kıyaslıyordu → RVOL 0.31x (P6) "likidite yok" görünümü. Artık beklenen tam bar hacmi = gözlenen +
   kalan süre × taban (shrinkage tahmini; 1/frac ile şişirme yok).
3. **Seans etkisi (XAU/XAG/NQ/ES).** Vadeli hacim ABD seansında Asya'nın 5-20 katı. 20 barlık düz ortalama her
   Asya barını "düşük likidite", her ABD açılışını "climax" sayıyordu. Taban artık **aynı saatin son ~10
   seanstaki medyanı** (gün-içi mevsimsellik), yedek: pozitif hacimlerin kayan medyanı.
   → Canlı veride XAU RVOL 0.31x (P6) → **1.05x (P57)**, NQ 0.13x (P3, giriş reddi) → 1.03x (P54).

## 🔎 Tüm varlıklar taraması (v3.3.1)
Aynı hata ikinci bir yerde de vardı: `quant_processor._adaptive_entry_profile` (ekranda gösterilen "Hacim"
değeri ve ilk giriş kapısı). O da artık aynı yöntemi kullanıyor; iki yol aynı sonucu veriyor.

| Varlık | Eski RVOL | Yeni RVOL | Eski climax eşiği | Yeni climax eşiği |
|---|---|---|---|---|
| SPX | 0.13x (P20) | 1.07x (P54) | 5.57 | 11.54 |
| NQ | 0.13x (P3) → giriş reddi | 1.03x (P54) | 5.99 | 8.31 |
| XAU | 0.31x (P6) | 1.05x (P57) | 3.59 | 2.60 |
| XAG | 0.25x (P7) | 0.99x (P47) | 3.69 | 3.47 |
| BTC | 1.25x (P45) | 1.46x (P54)* | 3.7e18 | 14.39 |
| ETH | 2.83x (P64) | 9.26x (P96) | 1.6e19 | 15.48 |

*BTC'de barların yarısında hacim yok; ekrandaki eski kapı 60 geçerli gözlem ister (şu an 52) ve dolana kadar
sahte sayı yerine "tarihçe yetersiz" gösterir. Hacim kullanan başka faktör/modül yok (tarandı).

## 🟠 Mantık hataları
4. **ETH: "YÖN SİNYALİ YOK" ile "Dinamik giriş uygun" aynı anda.** Son kapı yön NÖTR iken giriş
   gerekçesini güncellemiyordu. Artık: "Model yönü NÖTR → giriş yok. (Piyasa koşulu işlem yapılabilir: …)".
5. **ETH: 1D/4H/1H hepsi aşağıyken "🟢🟢 GÜÇLÜ YUKARI".** Canlı yön (1-4 saat) bilinçli olarak hızlı bir
   momentum okumasıdır; +%0.45'lik tepki gerçekti ama 4H ve 1D yapısının tersineydi. Artık ikisinin de
   tersine olan kısa vadeli hareket en fazla HAFİF seviyesinde gösterilir ve "↩ TERS-TREND TEPKİ" etiketi alır
   (`live_counter_trend`).

## 🟡 XAU faktörleri
6. **"Merkez Bankası & Jeopolitik Rezerv Talebi" üç kez aynı bilgiyi sayıyordu.** Altın düşerken faktör
   `altın_ROC×1.1 − 0.5×reel_faiz_z` idi: yani ivme faktörü + reel faiz faktörünün kopyası, −1.8 sınırında
   saplı. Artık gerçek bir **ayrışma artığı**: volatiliteyle normalize altın hareketi − reel faiz ve DXY'nin
   ima ettiği hareket. Canlı değer yaklaşık −1.8 → −1.0/−1.3.
7. **Altın/Petrol yanlış seriyi kullanıyordu.** "CL" anahtarı hiç yok → her zaman USO (yalnız ABD seansı)
   kullanılıyordu. Artık CL=F (altınla aynı ~23 saat seans), yoksa USO.
8. **A notu hacim katılımı istiyor:** aynı saate göre RVOL alt %20'deyse A → B ("pozisyon küçük").

## ✅ Sorun olmayanlar (kontrol edildi)
- XAU SAT kararı: 14 faktörün 5 kümesinden 4'ü negatif (E −2.3, B −1.95, D −1.3, A −1.1); tüm zaman dilimleri
  aşağı. Tutarlı.
- Altın/Petrol −1.77 ve Bakır/Altın +1.8 gerçek piyasa hareketi (altın 24 saatte ~%3 düştü, petrol yükseldi).
- ETH NÖTR: kümeler bölünmüş (E +0.83, C +0.74, A −1.70, B −0.41). NÖTR doğru sonuç.
- Bilinen tasarım sınırı (değiştirilmedi, tüm varlıkları etkiler): oran faktörleri 24-48 barlık seviye
  MAD-z kullandığı için trendlerde ±1.8'e doygunlaşıyor. İleride "oran değişimi z-skoru"na geçilebilir.

## Test
52/52 test geçti (46 eski + 6 yeni: `test_entry_xau_eth_v33.py`). Gerçek OHLCV + dondurulmuş saat
(2026-09-28 10:35 UTC) ile uçtan uca tam döngü çalıştırıldı.

## 📱 Yükleme
Zip'teki dosyaları repoya yükle (üzerine yaz). Canlı durum dosyaları pakette YOK; repodakiler korunur.
Değişen dosyalar: `dynamic_entry_engine.py`, `gatekeeper.py`, `quant_processor.py`,
`test_entry_xau_eth_v33.py`, `README_TIER1_FIX_V33.md`.

## v3.3.2 — ETH canlı yön kademesi + tek RVOL
- Canlı yön gücü artık kademeli: 4S **ve** 1G ters → en fazla HAFİF + "↩ TERS-TREND TEPKİ";
  yalnız 4S ters → "GÜÇLÜ" yazılmaz, "YUKARI/AŞAĞI · 4S teyitsiz". (11:40 UTC ETH: 1S +0.22, 4S −0.25,
  1G −0.11 → eski kural devreye girmiyordu, "GÜÇLÜ YUKARI" kalıyordu.)
- Ekrandaki "Hacim (RVOL)" sütunu artık giriş kararında kullanılan RVOL ile aynı (BTC'de 0.0x görünmesi giderildi).
- ⚠️ Streamlit: kod yüklendikten sonra **Manage app → ⋮ → Reboot app** yap; aksi halde uygulama eski
  modülleri bellekte tutar (14:44'teki ekran eski koddu; arka plan döngüsü ise yeni kodla çalışıyordu).

## v3.3.3 — ETH/BTC ayrışması, BTC ATR 0.00, "modele ters" etiketi
- **ETH faktör hatası:** `eth_staking_utility_drift` ("⛓️ L1 Ağ Aktivitesi & DeFi") hiçbir zincir-üstü veri
  kullanmıyordu; 24 saatlik ETH/BTC fiyat oranının z-skoruydu. `eth_btc_beta` (regresyon artığı) aynı bilgiyi
  zaten doğru ölçüyor → aynı göreli momentum 2 kez sayılıyor, +1.8 sınırında saplı, ETH'nin en büyük katkısı
  (+1.21) oluyordu. Kaldırıldı. Gerçek zincir-üstü veri (gas, aktif adres, staking akışı) eklenirse geri gelir.
- **ETH'de reel faiz faktörü yoktu** (BTC'de var, ρ≈0.91). Aynı makro maruziyet eklendi.
- Aynı veri ve ortamda A/B: BTC–ETH skor farkı **+0.72 → +0.37**; ETH E-kümesi +1.56 → +0.34. Kalan fark
  meşru (ETH'nin BTC'ye göre gerçek göreli gücü + düşen BTC dominansının yalnız BTC'yi etkilemesi).
- **BTC ATR 0.00x:** eski giriş kapısı RVOL ısınması (54/60) yüzünden tüm profili boş döndürüyor, ATR de 0
  kalıyordu → gün-içi rejim "VOLATİLİTE BİLİNMİYOR". ATR artık stateful profilden alınıyor (BTC 1.22x).
- **Tüm varlıklar:** canlı yön model sinyaline tersse "↔ MODELE TERS (kısa tepki)" etiketi
  (`live_vs_model`); yapıya tersse "↩ TERS-TREND TEPKİ" önceliklidir.

## v3.3.4 — Çift uzlaştırması canlı yönü eziyordu (SPX/NQ, XAU/XAG, BTC/ETH)
`reconcile_pairs_post_adaptive`, çift ayrışması fiyatla teyit edilmediğinde İKİ varlığın canlı yön etiketini de
(1) çiftin ZAYIF skoruyla (min |skor|), (2) adaptif motorun dinamik eşikleri yerine sabit 0.65/1.35 ile,
(3) HAFİF kademesi olmayan ayrı bir formatlayıcıyla yeniden yazıyordu. Sonuç: etiket ile `live_tier` çelişiyordu
(12:04 UTC SPX: kademe HAFİF, etiket YATAY; 12:06 SPX: kademe HAFİF, etiket YUKARI). Aynı döngüde BTC/ETH ve
XAU/XAG da etkilenmişti. Yeni: yalnız gerçek ÇELİŞKİDE (zıt işaret) ortak-faktör küçültmesi (%50); aynı yönde
her varlık kendi adaptif etiketini korur; etiketleme canlı motorla aynı şema ve varlığın kendi eşikleriyle yapılır.

## v3.3.5 — Canlı Yön tablosunun dinamikleri (2026-09-30)
Son 22 canlı döngü ölçüldü: "rejim geçişi" SPX/BTC'de döngülerin %40'ında (9/22) tetikleniyordu; SPX eşikleri
22 döngünün yalnız 2'sinde adaptifti (NQ'da 12) → aynı çift iki farklı eşik sistemiyle etiketleniyordu; BTC
volatilitesi 6/22 döngüde "BİLİNMİYOR" idi.

1. **Rejim etiketi histerezisli** (`classify_intraday_regime`): GÜÇLÜ TREND'e ADX≥25 ile girilir, <22 ile çıkılır;
   GELİŞEN 20/17.5; YÜKSEK VOL 1.35/1.25; DÜŞÜK VOL 0.70/0.78. Eşik sınırında her döngü etiket değişmez.
2. **"since" düzeltmesi** (`stateful_memory_store`): etiketin başlama zamanı her yazımda sıfırlanıyordu.
   Artık yalnız etiket değişince yazılır ve hangi etiketten gelindiği (`changed_from`) kaydedilir.
3. **Rejim olayı yaşlanır:** eşik genişletmesi ×1.25'ten başlayıp 2 saatte doğrusal olarak sıfırlanır; yalnız kayıtlı
   gerçek değişim sayılır; "VOLATİLİTE BİLİNMİYOR" ↔ bilinen geçişi (veri kalitesi) olay değildir.
4. **Eşikler ampirik-Bayes küçültmeli:** rejim kovası (çoğunda n<10) varlığın tüm canlı skor havuzuna
   w = n/(n+12) ile çekilir; havuz da azsa bootstrap'a. Kademeler arası asgari oran 1.15 (p70≈p85 çökmesi yok).
   SPX ve NQ artık aynı yöntemle, benzer eşiklerle etiketlenir.
5. **ATR hacimden bağımsız:** BTC'de Yahoo saatlik barların yalnız ~%40'ında hacim veriyor; RVOL ısınmasında tüm
   profil boş dönüyor, ATR de kayboluyordu. Artık hacim "bilinmiyor" olur, ATR korunur (BTC 0.00x → 0.88x). Rejim
   tanımı için ATR, veri bayat olsa da gerçek 1H barlardan hesaplanır (işlem izni vermez).
Gerçek veri + gerçek hafızayla 3 ardışık döngü (11:57/12:10/15:23): sahte rejim olayı 6/6 → 0, bayat veride
ATR 0.00 + "BİLİNMİYOR" (eski) → korunuyor.

## v3.3.6 — Uygulamanın kendisi (sahte Streamlit ile birebir sayfa dökümü) üzerinden denetim
1. **Yenileme pompası (en ciddi):** yön motoru her değerlendirmede yeni örnek ekliyordu; zaman paydası alt sınırı 30 sn.
   Arka plan döngüsünden 4 dk sonra çalışan bir değerlendirme ETH yön hızını −4.47/saat, BTC'yi −1.30/saat yaptı;
   sayfa yenilemek "kalıcılık" sayacını şişirip CONFIRMED'e taşıyabiliyordu. Artık 45 dk'dan yakın değerlendirmeler
   son örneği günceller (yeni örnek eklemez); hız/ivme paydası en az 1 saat. Skor dağılımları için de aynı kural.
2. **Rejim olayı yalnız gerçek kırılmada:** YATAY ↔ GÜÇLÜ (iki kademe) veya volatilite durumu değişimi. ADX'in 20/22'yi
   geçmesi (GELİŞEN ↔ komşu) artık "⚠️ REJİM GEÇİŞİ" + eşik genişletmesi üretmez (15:34'te SPX ve XAG böyleydi).
3. **Güvenilmez hacim = "—":** hacimsiz bar oranı >%35 ise RVOL ölçüm sayılmaz (BTC'de sahte 10.85x). Aynı-saat
   tabanı en az 5 gözlem ister.
4. **Arayüz:** "GÜÇLÜ SAT" yeşil kutuda gösteriliyordu → kırmızı. Giriş filtresi yalnız "ÖNERİLMEZ" metnine bakıyordu;
   "YÖN SİNYALİ YOK / ZAMANLAMA / FİYAT TEYİDİ BEKLENİYOR" yeşil ✅ çıkıyordu → artık `entry_allowed`'a bakar.
   Giriş kapalıyken gerekçe "Dinamik giriş uygun" / "Zamanlama notu A" diye başlamaz ("Piyasa koşulu uygun (giriş yok)",
   "Zamanlama (bilgi, giriş kapalı)"). Ham kod `direction_conditions_not_met` yerine Türkçe açıklama.
