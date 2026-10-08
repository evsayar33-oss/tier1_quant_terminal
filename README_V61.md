# v6.1 — Yeni çıkış kuralları: başa baş, kısmi kâr alma, volatiliteye uyumlu hedef

## Yükleme
`strategy_lab.py` ve `test_strategy_lab.py` dosyalarını `main` dalına yükle → Actions → **Tier-1 Strategy Lab** → Run workflow.
(v6.0 yüklenmediyse önce v6.0 paketindeki `.github/workflows/strategy_lab.yml` dosyasını da yükle.)

## Çıkış kuralları (ATR girişte sabitlenir)
**Kısa ufuklar (1 saat, 4 saat) — 14 kural:**
- sinyalle çıkış
- SL/TP 1.5/3, 2/4, 3/6 ×ATR
- iz süren stop 2 ve 3 ×ATR
- 4 ve 24 saat tutma
- **başa baş:** SL 2 / TP 4 ×ATR, fiyat 1×ATR lehe gidince stop giriş fiyatına çekilir (ayrıca 3/6/1.5 versiyonu)
- **kısmi kâr alma:** SL 2×ATR, pozisyonun yarısı 2×ATR kârda kapanır; kalan yarı için stop girişe çekilir ve 3×ATR iz süren stopla takip edilir (ayrıca 3/3/3 versiyonu)
- **volatiliteye uyumlu hedef:** SL 2×ATR, TP 4×ATR × (ATR / son 30 günün medyan ATR'si, 0.5–2 arasında sınırlı); volatilite artarken hedef genişler (ayrıca 3/6 versiyonu)

**Uzun ufuklar (1 gün, 1 hafta, 1 ay) — 6 kural:** sinyal, SL/TP 3/6, iz süren 3, başa baş 3/6/1.5, kısmi kâr 3/3/3, volatiliteye uyumlu 3/6.

## Temkinli varsayımlar
- Aynı mum hem stopa hem hedefe değerse stop sayılır.
- Kısmi kârdan sonra aynı mum giriş fiyatına geri dönmüşse, kalan yarı girişte kapanmış sayılır.
- Boşlukla açılışta dolum açılış fiyatından yapılır.
- Tüm kurallar satır satır yazılmış bağımsız bir referans simülatörle birebir doğrulandı.
- Rastgele fiyat verisinde hiçbir kural sahte kâr üretmedi (bias testi).
