# Nerede Kaldık — Proje Durumu

Her yeni sohbet ve her otomatik kontrol ÖNCE bu dosyayı okur.
Sonra şu dosyaları okur:
1. `health_report.md` ve `health_log.csv` (`state` dalı): sistemin kendi bulduğu hatalar.
2. `RESEARCH_LOG.md` (main): denenen bütün yöntemler ve sonuçları.

## Sistem nedir
* Bir al-sat botu DEĞİLDİR. Bir karar destek terminalidir.
* Arayüz (Streamlit, `app.py`) "🎯 Karar Özeti" gösterir: Giriş, Kısa vade, Uzun vade, Stop kısa/uzun, Zamanlama.
* Varlıklar: SPX, NQ, XAU, XAG, BTC, ETH.

## Mimari
* Motor: `engine_loop.py` → `stateful_background_tracker.py`. Her saat çalışır.
* Sürücü: cron-job.org, `2 * * * *` → `stateful_adaptive_tracker.yml` (workflow_dispatch). GitHub cron yedektir.
* Durum dosyaları `state` dalına yazılır (`state_sync.STATE_FILES`). Raporlar `reports` dalındadır.
* Modüller: `dealer_gamma.py` (GEX haritası), `market_structure.py` (seans, likidite, sweep, CTA, vol-control),
  `stop_levels.py` (yapısal stop + avlanma defteri), `gex_history.py` (GEX → hareket çarpanı),
  `direction_research.py` (yön kuralları, taban oran), `decision_panel.py`, `system_health.py`.

## Kanıtlanmış bulgular
* Volatilite ve gama hareketin BÜYÜKLÜĞÜNÜ tahmin eder (RESEARCH_LOG #7). Stoplar bunu kullanır.
* Hiçbir yön kuralı "Hep AL"ı geçmedi (#1, #5, #6, #8). Uzun vade için taban oran gösterilir.

## Açık işler
* 2026 sonunda `macro_calendar.FOMC_DATES` listesine 2027 FOMC tarihleri eklenmeli (sağlık kontrolü uyarır).
* Veri günü etkisini 10 yıllık günlük veriyle ve olay türüne göre (TÜFE/NFP/FOMC ayrı) test et; 1 yıllık havuzlanmış test zayıf.
* Tahmin Karnesi (RESEARCH_LOG #9): ~30 gün sonra ilk not; haftalık kontrol `forecast_scorecard` alanını okusun.
* Kanıt defterleri (`dealer_gamma_history.csv`, `stop_ledger.csv`) ~30 gün veri biriktiriyor (başlangıç 2026-10).
* Yeni bir yön yöntemi denenirse: önce RESEARCH_LOG.md'ye hipotez yaz, sonra test et.

## Otomatik kontroller (zamanlanmış görevler)
* Günlük 09:47 TSİ: sağlık ve veri kontrolü.
* Pazartesi/Perşembe 13:49 TSİ: performans ve optimizasyon kontrolü.
* Görev bir sorunu düzeltirse bu dosyanın "Son değişiklikler" bölümüne bir satır ekler.

## Kurallar
* Test sonrası şu dosyaları geri al: `git checkout -- adaptive_regime_thresholds_state.json timeframe_confluence_state.json`.
* PR birleştirirken tam 40 karakterlik SHA kullan.
* GitHub token Claude ile paylaşılmaz; yalnız cron-job.org'dadır.

## Son değişiklikler
* 2026-10-23: Makro takvim düzeltmesi: FRED 'FOMC Press Release' her günü veriyordu → FOMC karar günleri Fed takviminden (2025-2026 listesi, `macro_calendar.FOMC_DATES`). Yılda >20 tarihli olay türü veri hatası sayılır. İlk ölçüm (1 yıl, 61 veri günü): hiçbir varlıkta kanıtlı etki yok (SPX ×1.09, t 0.65).
* 2026-10-23: `macro_calendar.py`: FRED ABD veri takvimi (TÜFE, NFP, ÜFE, GSYH, PCE, perakende, FOMC). Olay günü etkisi her döngüde ölçülür (RESEARCH_LOG #10); kanıtlıysa aralık/stop çarpanı. Bugün veri varsa Basit Özet uyarır, açıklanmadan önce risk 🔴. FRED adı uyuşmazsa veya gelecek FOMC kalmazsa sağlık günlüğüne yazılır.
* 2026-10-23: Kısa vade çift tutarlılığı: SPX/NQ, XAU/XAG, BTC/ETH aynı yöndeyse ortak (ortalama) z; zıt ve belirginse "eşinden ayrışıyor" notu. 4s getiri zamana göre (yarım son bar pencereyi kısaltmaz).
* 2026-10-23: `forecast_ledger.py` (Tahmin Karnesi) eklendi. Arayüz tahminleri önceden kaydedilir, 4s/24s sonra notlanır; aralık 30 günden sonra kendini kalibre eder. Hipotezler RESEARCH_LOG #9.
* 2026-10-23: Kısa vade = son 4 saatlik getiri / normal 4s oynaklık (|z| ≥ 0.75). Sakin mi = son 20 gün ↔ son 1 yıl (medyan tabanlı σ, × GEX çarpanı). Taban oran: örneklem zaten örtüşmesiz (önceki n/5 düzeltmesi YANLIŞTI), eşik z ≥ 3 (Bonferroni ~30 test). "Önümüzdeki hafta" → "Yarın ve bu hafta" (1-5 gün taban oranları).
* 2026-10-23: Detaylı Karar Özeti ve stoplar da kanıt mantığına geçti (`stop_levels.evidence_*_side`). Kanıtsız model yön/stop yönü belirlemez; sadece "model X diyor, kanıtsız" notu olarak görünür. Yön yoksa iki senaryo stopu gösterilir.
* 2026-10-23: Basit Özet düzeltmesi: XAU/XAG sahte ayrışması giderildi. Kısa vade eğilimi kanıtsız modelden değil fiyattan; taban oran yönü sadece z ≥ 2 ise.
* 2026-10-23: Arayüze "🟢 Basit Özet" tablosu eklendi (yeni başlayanlar için sade dil).
* 2026-10-23: `system_health.py` eklendi. Sistem kendi hatalarını `health_log.csv` dosyasına yazar.
