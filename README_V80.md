# v8.0 — Uzun Dönem Laboratuvarı (~10 yıl, son 2 yıl mühürlü sınav)

## Dosyalar (repo köküne, aynı isimle)
| Dosya | Durum |
|---|---|
| `long_replay.py` | **YENİ** — gerçek üretim hattını 10 yıl boyunca günde bir kez, zaman-noktası doğru çalıştırır |
| `long_lab.py` | **YENİ** — dar kural evreni, eğitim/sınav ayrımı, yıllık walk-forward, tek seferlik sınav |
| `test_long_lab.py` | **YENİ** — 5 test (ileriye bakmama, mühürlü sınav, simülatör, gürültü elenir, gerçek sinyal bulunur) |
| `.github/workflows/long_lab.yml` | **YENİ** — iş akışı |
| `alt_data.py` | değişti — v7.1 (COT için CFTC açık veri API yedeği) + uzun COT geçmişi |
| `test_strategy_lab.py` | değişti — v7.1 testi |
| `strategy_lab.py` | değişti — rapordaki tablo kayması düzeltildi (`|z|` → `∣z∣`) |

## Nasıl çalışır
1. **Sistem 10 yıl geriye oynatılır** (günlük saat): her gün 00:30 UTC'de, yalnızca bir önceki gün kapanmış
   barlar ve en az 1 gün önce yayımlanmış FRED verileriyle sistemin tüm çıktıları üretilir. Adaptif hafızalar
   sıfırdan başlar. Not: canlı sistem saatlik çalışır; burada içindeki "N mum" hesapları "N gün" olur.
2. **CFTC COT** ~13 yıl (haftalık, cumartesiden itibaren kullanılır).
3. **Kural evreni dar:** her sistem çıktısı, faktör, COT ve 7 klasik trend kuralı × 3 ufuk (gün/hafta/ay)
   × işaret / güçlü × normal / TERS × long+short / long / short × sinyalle çıkış / 3×ATR iz süren stop.
4. **Son 2 yıl mühürlü:** hiçbir seçim, sıralama, eşik o döneme bakmaz. Seçim eğitim döneminde yapılır,
   sınav bir kez uygulanır. Uygulama ertesi gün açılış fiyatıyla; komisyon/kayma ve fonlama düşülür.
5. **Kanıt şartı (önceden sabit):** eğitimde yıllık walk-forward t ≥ 2 ve yılların ≥ %60'ı pozitif,
   DSR ≥ 0.90, sınavda t ≥ 1.5 ve sürekli long'a karşı alfa t ≥ 1.0.

## Rapor
* **1)** varlık bazında seçilen kural ve sınav sonucu
* **2)** eğitimin en iyi 20 kuralı sınavda ne yaptı (geçmiş test getirileri neden yanıltıcı — doğrudan görülür)
* **3)** aile bazında sınav (seçim yanlılığı neredeyse yok): ör. "faktörler · 1 ay" ailesinin tamamı sınavda kazandı mı?
* **4)** eğitimden seçilen ikili kombinasyonların sınavı · **5)** yıllık seçimler · **6)** kaldıraç

## Çalıştırma
Actions → **Tier-1 Long Lab (10 yıl, mühürlü son 2 yıl)** → Run workflow (`replay: yes`).
İki aşama: yeniden oynatma (~1-2 saat) → laboratuvar (~10-30 dk). `FRED_API_KEY` secret'ı kullanılır.
Sonuç: çalışma sayfası Summary + Artifacts `long-lab-results` + `longlab` dalı zip bağlantısı.
