# v3.4 — Sistem kendi faktör ağırlıklarını walk-forward ile öğreniyor (2026-09-30)

## Teşhis (700 günlük, zaman-noktası doğru replay: 8.389 döngü, 39.566 sinyal)
| Ufuk | Model | Trend takibi | Hep AL |
|---|---|---|---|
| 4s | %48.3 | %49.0 | %52.6 |
| 24s | %46.6 | %47.2 | %54.0 |
| 72s | %46.5 | %46.2 | %54.9 |

1. **Model gizli bir trend takipçisi.** İsabeti her ufukta "trend takibi" ile neredeyse aynı; bu ufuklarda fiyat
   ortalamaya döndüğü için ikisi de %50'nin altında. "A notu" (tüm zaman dilimleri onaylı = en momentumlu) 72s'de en kötü (%44.7).
2. **Canlı öğrenme TERS çalışıyordu (hata).** Faktör değerleri işaretsiz (`ham_deger`) kaydediliyor, öğrenilen
   çarpan ise işaretli katkıya uygulanıyordu → `base_sign=-1` olan her faktörde (VIX, bankacılık, dolar, fonlama,
   XAU'da bakır/altın...) ters çalışan faktörün ağırlığı ARTIYOR, doğru çalışanınki AZALIYORDU.
3. **Öğrenme kutuya kapatılmıştı:** çarpan [0.65, 1.35] → IC'si −0.16 olan faktör (SPX VIX vade yapısı, t=−2.4)
   hâlâ %72 ağırlıkla yanlış yönde oy veriyordu; kapatılamıyor, ters çevrilemiyordu.
4. **Sabit terim yok:** piyasanın yukarı eğilimini (Hep AL %54) öğrenemiyordu. Öğrenme 4s getiriden, etkin örneklem ~34.

## Çözüm
- `walkforward_optimizer.py` (yeni): her varlık için hiyerarşik ridge — ortak ağırlıklar + sabit terim + rejim
  sapmaları (4 kat daha sert küçültme). Hedef: 24s getiri / volatilite. Genişleyen pencere, 24s ambargo, ceza
  gücü yalnız eğitim içinde seçilir. Ağırlıklar negatif olabilir (ters çalışan faktör çevrilir, boş olan ~0'a iner).
- **Canlıya alma kuralı:** örneklem dışı t(IC) ≥ 2, isabet ≥ Hep AL ve ortalama getiri > 0. Sağlamayan varlıkta
  sistem sinyal üretmez (`LEARNED_MODEL_POLICY = "abstain"`, config.py; "legacy" ile eski skora dönülebilir).
- `historical_replay.py`: faktör panelini (`factor_panel.csv.gz`) ve `learned_model.json`'u yazar; rapora
  "🤖 Kendini optimize eden model" tablosu (öğrenilmiş vs eski model vs Hep AL vs trend, aynı zaman damgalarında).
  Replay sırasında öğrenilmiş model KAPALI (sızıntı yok).
- Canlı döngü `validation_reports/learned_model.json`'u okur; tabloya "🧪 Model Kanıtı" sütunu, detaya kanıt satırı.
- Canlı öğrenme işaret hatası düzeltildi + eski hafıza bir kez göç ettirildi; çarpan aralığı [0, 1.6].
- Çift uzlaştırması yalnız aynı ölçekteki skorlar arasında (öğrenilmiş/eski/çekimser karışmaz).
- Workflow varsayılanı 700 gün / 2 saat (en fazla veri). Her cumartesi kendiliğinden yeniden öğrenir.

## 📱 Yapman gereken
1. Zip'teki dosyaları yükle (`.github/workflows/historical_validation.yml` dahil), Reboot app.
2. GitHub → Actions → **Tier-1 Historical Walk-Forward Validation** → Run workflow (varsayılanlar: 700 / 2).
   ~4-5 saat sürer. Bitince `validation_reports/learned_model.json` gelir ve canlı sistem onu kullanır.
   Dosya gelene kadar sistem eski davranışını sürdürür.
