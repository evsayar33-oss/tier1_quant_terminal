# v12.0 — Şok Laboratuvarı (S&P 500 ve Nasdaq-100, 1990 → bugün)

## Dosyalar (hepsi YENİ, repo köküne)
`shock_data.py` · `shock_lab.py` · `test_shock_lab.py` · `.github/workflows/shock_lab.yml`

## Ne test ediliyor — tek tek ve kombinasyon halinde
* **~45 şok tanımı:** VIX seviyesi / sıçraması / z-skoru, VIX vade yapısı tersine dönmesi, VVIX ve SKEW uçları, günlük düşüş,
  zirveden düşüş (−5…−20%), ardışık düşüş günleri, RSI(2)/RSI(14) aşırılığı, Bollinger kırılımı, kredi spreadi şoku,
  faiz / reel faiz şoku, dolar ve petrol şoku, finansal stres endeksleri + "herhangi bir panik"
* **6 giriş zamanlaması:** şok kapanışı, ertesi açılış, ilk yeşil kapanış, VIX zirveden %10 geri çekilince,
  5 günlük ortalamayı geri alınca, 3 günde kademeli alım
* **~64 çıkış:** 5–120 gün tutma, % TP/SL ızgarası, ATR TP/SL ızgarası, % ve ATR iz süren stop,
  VIX normale dönünce, zirveye yaklaşınca, trend kırılınca
* **32 teknik ve temel filtre + tüm ikili kombinasyonları (~500):** trend, düşüş derinliği, VIX durumu,
  enflasyon beklentisi, TÜFE, reel faiz, kredi spreadi, getiri eğrisi, Fed faiz yönü, finansal koşullar,
  işsizlik başvuruları (resesyon sinyali), dolar, petrol
* **Pozisyon/kaldıraç:** sadece sinyalde 1x/3x, normalde 1x–1.5x + sinyalde 2x–3x; kaldıraç gerçek hazine bonosu faiziyle finanse edilir
* **Makine öğrenmesi kapısı** (olay günündeki tüm durum, yıllık walk-forward) ve **gün içi giriş saati** (son ~2 yıl, saatlik)

## Dürüstlük protokolü
Tüm seçimler 1990–2016 ile yapılır, **2017 sonrası mühürlü sınavdır**. Veriler yayımlandıkları tarihten önce kullanılmaz.
Rapor her ailenin "sınav fazlası"nı (aynı süre endeksi tutmaya göre ek getiri) verir.
Enflasyon hipotezi (2016–2026'da bulundu) hiç görmediği **2003–2015** verisinde ayrıca sınanır.

## Çalıştırma
Actions → **Tier-1 Shock Lab** → Run workflow (`FRED_API_KEY` secret'ı kullanılır). ~10–30 dk.
