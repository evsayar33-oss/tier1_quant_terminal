# v9.0 — Kesitsel Kripto Perp Portföy Laboratuvarı

## Dosyalar (repo köküne, aynı isimle) — hepsi YENİ
| Dosya | Görev |
|---|---|
| `xs_data.py` | Binance arşivinden TÜM USDT perp'lerin günlük fiyat, hacim ve gerçek fonlama verisini indirir (kapanmış/delist olanlar dahil → hayatta kalan yanlılığı yok). Ücretsiz, anahtarsız. |
| `xs_lab.py` | Portföy stratejilerini mühürlü son 2 yıl protokolüyle test eder |
| `test_xs_lab.py` | 5 test (ileriye bakmama, P&L/fonlama/delist muhasebesi, gürültü elenir, gerçek avantaj bulunur, indirici) |
| `.github/workflows/xs_lab.yml` | İş akışı (veri `xsdata` dalında önbelleklenir; sonraki çalışmalar sadece yeni ayları indirir) |

## Ne test ediliyor (~1.250 portföy kuralı — dar ve önceden belirlenmiş)
* **Evren (o günün bilgisiyle):** son 30 gün işlem hacmine göre ilk 20 / 50 / 100 kontrat, en az 60 günlük geçmiş.
* **Sinyaller:** momentum (1, 3, 7, 14, 28, 56, 84 gün), riske göre momentum, fonlama carry (3/7/30 gün),
  düşük volatilite, ilgi (hacim 7g/30g) — her biri TERS yönüyle.
* **Portföy:** en iyi %20/%33 long + en kötü %20/%33 short (piyasa-nötr, 1x brüt) veya sadece long;
  eşit veya ters-volatilite ağırlık; günlük veya haftalık yenileme.
* **Gerçekçilik:** karar 00:00 UTC kapanışında, ertesi gün uygulanır; gerçek fonlama ödemeleri; komisyon+kayma
  (ilk 20: %0.06, ilk 50: %0.10, ilk 100: %0.15 / taraf); işlem görmeyi bırakan kontrat son fiyattan kapatılır.

## Kanıt şartı (önceden sabit)
Eğitimde yıllık walk-forward t ≥ 2 ve yılların ≥ %60'ı pozitif · DSR ≥ 0.90 · son 2 yılda (mühürlü sınav)
t ≥ 1.5 ve BTC'ye karşı alfa t ≥ 1.0. Rapor ayrıca **strateji ailelerinin** eğitim ve sınav ortalamasını verir.

## Çalıştırma
Actions → **Tier-1 Crypto Portfolio Lab** → Run workflow. İlk çalışma tüm arşivi indirir (~30-60 dk).
Kanıtlı bir strateji çıkarsa v9.1'de canlı/kâğıt işlem bağlantısı eklenecek.
