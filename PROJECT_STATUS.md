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
* 2026-10-23: `system_health.py` eklendi. Sistem kendi hatalarını `health_log.csv` dosyasına yazar.
