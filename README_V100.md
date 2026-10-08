# v10.0 — Scalping Laboratuvarı (5 dakikalık botlar)

## Dosyalar (hepsi YENİ, repo köküne)
| Dosya | Görev |
|---|---|
| `scalp_data.py` | Her ayın en çok işlem gören 30 perp'inin 5 dakikalık mumlarını Binance arşivinden indirir (o ayın başındaki bilgiyle seçilir) |
| `scalp_lab.py` | 156 bot ayarını test eder |
| `test_scalp_lab.py` | 4 test (işlem simülatörü elle, ileriye bakmama, gürültüde kâr yok, gerçek avantaj bulunur) |
| `.github/workflows/scalp_lab.yml` | İş akışı (5 dakikalık veri önbelleğe alınır) |

## Test edilen botlar (long ve short)
* **Ortalamaya dönüş:** fiyat 4 saatlik ortalamasından 2 / 2,5 / 3 standart sapma uzaklaşınca ters yöne (trend filtresi var/yok)
* **RSI(14) 20/80** (trend filtresi var/yok)
* **Likidasyon mumu tepkisi:** hacimli, 3 / 5 ATR'lik tek mum → tepki yönüne
* **Hacimli kırılım:** 4 saatlik tepe/dip kırılımı + 2x / 4x hacim → kırılım yönüne
* **Emir akışı:** 15 dakikalık agresif alım payı >%65 (<%35) → o yöne
* **Çıkış:** kâr al 0,5 / 1 / 2 ATR, stop 1 / 2 ATR, en fazla 2 veya 4 saat

## Gerçekçilik
Karar mum kapanışında, giriş bir sonraki mumun açılışında. Mum içinde stop ve hedef birlikte değerse önce STOP sayılır.
Maliyet: taker %0,05 + kayma %0,02 (gidiş-dönüş %0,14). Raporda ayrıca "hep limit emir (maker %0,02)" iyimser sonucu var.
Rapor her bot için **kazanma oranı, ortalama kazanç/kayıp, işlem başı net kâr, günlük işlem sayısı** ve mühürlü son 2 yıl sonucunu verir.

## Çalıştırma
Önce Crypto Portfolio Lab en az bir kez çalışmış olmalı (`xsdata` dalı). Sonra Actions → **Tier-1 Scalping Lab** → Run workflow.
İlk çalışma ~1700 aylık dosya indirir (~30-60 dk).
