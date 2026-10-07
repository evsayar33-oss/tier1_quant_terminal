# v4.1 — "KANITLI" artık al-tut'u geçmeyi de şart koşuyor

## Neden
İlk gerçek Strategy Lab çalışmasında SPX ve NQ "KANITLI (B)" çıktı. Ama ileriye dönük test Sharpe değerleri
(0.71 / 0.86) aynı dönemde **sadece tutmanın** Sharpe değerine (0.72 / 0.82) eşitti.
Yani bu stratejiler nakitte beklemekten iyiydi, ama varlığı alıp tutmaktan daha iyi değildi.

## Ne değişti
- **Alfa testi (iki kanıt yolunda da):** dışı-örneklem getiri al-tut'a göre regresyonla ayrıştırılır. Alfa t ≥ 2 değilse "KANITLI ALFA" verilmez.
- **🛡️ RİSK AZALTICI sınıfı:** al-tut'a yakın Sharpe (≥ %80) ve çok daha küçük düşüş (≤ %60) gösteren kurallar için.
  Bunlar sinyal sözleşmesinde işlem yapılabilir **sayılmaz**, ama görünür olur.
- **📈 Tüm varlıklarda en tutarlı tek kural:** varlık başına ayar yapılmadan 6 varlıkta birden en tutarlı çıkan kural.
  Şu an 60 günlük momentum, sadece alış. Paper defterde "📈 Tutarlı trend kuralı" adıyla ileriye dönük sınanır.
- **İndirme:**
  - Uygulamada lab bölümünde ⬇️ Rapor (.md), Tüm sonuçlar (.json) ve Paper defter (.json) düğmeleri var.
  - Actions iş sayfasında tam rapor ve **Artifacts → strategy-lab-results** dosyası bulunur.

## Yükleme
1. Zip'teki dosyaları `main` dalına yükle → Streamlit **Reboot app**.
2. Actions → **Tier-1 Strategy Lab (strateji testi)** → Run workflow (yeni sınıflandırma için).
3. Bittikten sonra Actions → **Tier-1 Motoru Şimdi Yeniden Başlat (manuel)** → Run workflow.
