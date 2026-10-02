# v3.7 — Aşama 1: Dosya büyümesi kalıcı olarak çözüldü (2026-10-02)

## Sorun
Tracker her çalışmada ~1.6 MB durum dosyasını `main`'e commit ediyordu (23 günde 373 commit). Git her sürümü sonsuza
kadar saklar → repo yılda yüzlerce MB büyür (GitHub önerilen sınır ~1 GB). Ayrıca Streamlit her commit'te uygulamayı
yeniden yüklüyordu (günde ~16 kez).

## Yeni düzen
| Dal | İçerik | Büyüme |
|---|---|---|
| `main` | Yalnız kod | Sadece sen yükleme yapınca değişir |
| `state` | Canlı durum + `state_bundle.tar.gz` (~260 KB) | Her çalışmada TEK commit olarak üzerine yazılır → büyümez |
| `reports` | Haftalık walk-forward çıktıları | Aynı şekilde tek commit |

- Tracker başlangıçta `state` + `reports` dallarını geri yükler, çalışır, sonucu `state` dalına yayımlar.
- Uygulama durumu `state` dalındaki tek paketten indirir (en fazla 2 dakikada bir; butona basınca hemen).
- Büyüme sınırları: geçmiş CSV'leri son 5000 satır, `state_backups` son 10 dosya, performans defteri 3000 kayıt.
- İlk çalışmada dallar yoksa `main`'deki mevcut dosyalar başlangıç olarak kullanılır — hiçbir öğrenilmiş bilgi kaybolmaz.

Yerel sahte GitHub deposunda iki ardışık çalışmayla doğrulandı: `main` 1 commit'te, `state` 1 commit'te kaldı;
ikinci çalışma durumu `state` dalından geri yükledi; paket 257 KB / 58 dosya. 82/82 test.

## 📱 Yapman gerekenler
1. Zip'teki dosyaları yükle (`.github/workflows/` içindeki iki dosya dahil).
2. GitHub → repo → **Settings → Actions → General → Workflow permissions → "Read and write permissions"**
   seçili olsun (büyük olasılıkla zaten öyle; tracker şu an da push yapıyor).
3. **Actions → "Tier-1 Stateful Adaptive Quant Tracker v3.7" → Run workflow** (bir kez elle). Bitince repoda
   `state` dalı görünür.
4. Streamlit'te **Reboot app**.
Bundan sonra `main`'e otomatik commit gelmez; repo büyümez.
