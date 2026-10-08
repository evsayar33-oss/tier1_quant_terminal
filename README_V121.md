# v12.1 — Dinamik eşikler

Yeni workflow: **Tier-1 Shock Lab v12.1** (`shock_lab_v121.yml`). Sonuçlar **`shocklab121`** dalına yazılır, v12'nin `shocklab` dalını ezmez.

Eklenenler (`[D]` / `[WF]` önekiyle, sabit kuralların yanında aynı mühürlü sınavda):
- VIX son 1 ve 3 yılın %90/95/98/99 yüzdeliği; VIX / 200g ortalaması 1.5x/1.8x/2.2x; VVIX %98 yüzdelik
- σ-ölçekli düşüşler: günlük −2/−2.5/−3/−4σ, 5 günlük −2/−3σ, zirveden −0.5…−1.5 yıllık σ
- Kredi, faiz ve petrol şokları kendi 5 yıllık dağılımının %98'inde
- Makro filtreler, o güne kadarki tüm geçmişe göre yüzdelik olarak (enflasyon beklentisi, HY, işsizlik başvuruları, reel faiz, TÜFE, NFCI)
- Walk-forward eşikler: her ocakta yalnızca kapanmış işlemlerle yeniden seçilir
- Raporun 0. bölümü: sabit, dinamik ve walk-forward eşikler yan yana (sınav fazlası ve kalıcılık)

Testler: 5/5 geçti; yeni test dinamik eşiklerde ileriye bakma olmadığını doğruluyor.
