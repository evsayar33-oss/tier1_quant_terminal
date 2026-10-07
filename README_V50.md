# v5.0 — Kaldıraçlı vadeli (perp) strateji laboratuvarı: sistemin TÜM sinyalleri, tek tek ve kombinasyon halinde

## Yükleme sırası (önemli)
1. Zip'teki dosyaları `main` dalına klasör yapısını koruyarak yükle → Streamlit **Reboot app**.
2. Actions → **Tier-1 Historical Walk-Forward Validation** → Run workflow (700 gün, 2 saat; ~3-5 saat).
   Bu, sistemin geçmişteki HER çıktısını (107 sinyal/varlık/adım) `signal_panel.csv.gz` olarak kaydeder.
3. Bitince Actions → **Tier-1 Strategy Lab (strateji testi)** → Run workflow (~15-40 dk).
4. Sonra **Tier-1 Motoru Şimdi Yeniden Başlat (manuel)** → Run workflow.

## Sonuçları indirme
- Lab iş sayfası → **Summary** en üstte "Tek tıkla hepsi (zip)" bağlantısı.
- Aynı sayfanın en altında **Artifacts → strategy-lab-results** (upload-artifact@v6).
- Uygulamada lab bölümünde ⬇️ düğmeleri + lab.zip bağlantısı.
- `lab_all_configs.csv.gz`: denenen HER konfigürasyonun tek tek sonucu.

## Ne test ediliyor
- Sistemin her çıktısı (model sinyali, tahmin, kısa vade yön, kademe, aşama, tüm skorlar/z'ler/hızlar,
  çift ve küme skorları, zaman dilimi uyumu, giriş izni/notu, RVOL, ATR, ADX, tüm makro faktörler,
  rejim, USD riski, VIX...) — yön olarak (işaret ve |z|>1), sistem yönünde ve TERS; filtre olarak.
- 54 teknik kural (1s/4s/1g).
- Kombinasyonlar: sistem yönü × filtre, sistem × trend teyidi, sistem × sistem, teknik × sistem filtresi,
  teknik × sistem yönü teyidi, faktör × rejim, çoğunluk oyları; referans: sürekli long / short.
- long+short, sadece long, sadece short · 8 çıkış kuralı (sinyal, 3 SL/TP, 2 iz süren stop, 4s/24s zaman).
- Perp ekonomisi: komisyon+kayma, fonlama (long 8 saatte %0.01 öder), 1x-10x kaldıraç ve likidasyon tablosu.
- Varlık başına ~60-70 bin konfigürasyon; walk-forward seçim testi, Deflated Sharpe (etkin deneme sayısı),
  al-tut'a karşı alfa, 10 yıllık günlük ikinci test.

## Düzeltilen hata
Önizlemede, gerçek High/Low olmayan mumlarda iz süren stopun kapanış fiyatından iyi doldurulması
rastgele yürüyüşte bile kâr üretiyordu. Düzeltildi ve bunu yakalayan test eklendi.
