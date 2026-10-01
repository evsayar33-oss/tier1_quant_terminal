# v3.5 — Kararsızlığın kökü ölçüldü ve düzeltildi (2026-10-01)

## Ölçülen kök nedenler
| # | Kök neden | Kanıt |
|---|---|---|
| 1 | **İki yazıcı.** Uygulamadaki her "Canlı Verileri Yenile" tam bir öğrenme döngüsü çalıştırıp hafıza + 4 durum dosyasını uygulama sunucusunda yeniden yazıyordu; arka plan işi her commit'te bunları eziyordu. | Uygulama ile workflow farklı geçmişlere bakıyordu. |
| 2 | **Oluşmakta olan saatlik bar.** Kapanmamış son bar her dakika değişiyor. | Aynı saat içinde yalnız son bar ilerlerken SPX canlı skoru −0.57 → −0.16, ETH model NÖTR → SAT. |
| 3 | **Kendine referanslı, az örnekli yüzdelik eşikler.** Her çalıştırma kendi skorunu dağılıma ekleyip eşiği kaydırıyordu; "GÜÇLÜ" = son birkaç günün en üst %15'i. | Aynı veri, aynı skor −0.88: önce AŞAĞI, bir çalıştırma sonra HAFİF AŞAĞI. NQ −2.08 "HAFİF" gösteriliyordu. |
| 4 | **Ufuk uyumsuzluğu.** 24s–1h model sinyali, hızlı saatlik faktörlerden ham olarak kuruluyordu. | 700 günlük panelde ham skor günde **2.14** kez işaret değiştiriyor; XAU 3 günde −0.88 → +0.63 → −0.61 → +0.58. |
| 5 | Yön hızı duvar saatine bağlıydı. | Aynı bar, 08:20 vs 08:41: hız −0.088 vs −0.076. |
(Kod deterministik: aynı veri + aynı hafıza + aynı saat = birebir aynı sonuç — rastgelelik yok, sorun girdilerdeydi.)

## Düzeltmeler
1. `state_mode.py`: **tek yazıcı** — uygulama `TIER1_READ_ONLY_STATE=1` ile çalışır; hafıza, rejim eşikleri, veri tazeliği,
   zaman dilimi güvenilirliği ve terminal_state yalnız arka plan işi tarafından yazılır. Her yenileme repodaki yayımlanmış
   son durumdan taze başlar; önceki sinyaller de oradan okunur.
2. **Kapanmış bar kuralı** (data_engine + replay): oluşan saatlik bar ve bugünün yarım günlük barı kullanılmaz.
   Sinyal yalnız bir bar kapandığında değişir. Replay de aynı kurala geçti (canlı ile tutarlı).
3. **Canlı yön etiketi:** öğrenilen eşikler sabit anlamlı çapanın (0.60 / 1.00 / 1.50) ±%20'si içinde kalır;
   kademe geçişinde %10 histerezis.
4. **Model sinyali yumuşatma:** 12 saat yarı ömürlü zaman tabanlı EMA. Panelde işaret değişimi 2.14 → 0.33/gün,
   örneklem dışı IC değişmedi (−0.009 → −0.006).
5. Yön motoru saati = kapanmış bar saati.

## Doğrulama (gerçek veri)
- Repodaki son 30 arka plan commit'inin kendi veri anlık görüntüsüyle zincirleme yeniden oynatma (29 gerçek döngü):
  **model sinyali değişimi 28 → 4**, canlı yön değişimi 112 → 100 (1–4s ufuklu canlı yönün döngüler arası
  değişmesi doğal).
- Uygulama aynı bar içinde 08:20 ve 08:41'de yenilendi: tablo **birebir aynı**, hiçbir durum dosyası değişmedi.
- 75/75 test.
