# v13.0 — Karma Lab

Workflow: **Tier-1 Karma Lab v13** (`karma_lab.yml`). Sonuçlar `karmalab` dalına yazılır.
Kripto paneli için `xsdata` dalını kullanır (Crypto Portfolio Lab'in ürettiği dal).

Test edilen: karma portföy (50% risk paritesi SPX/NQ/altın/gümüş ×2 + 50% kripto L/S topluluk)
uç VIX paniği sırasında hisse ayağını geçici büyütünce iyileşiyor mu?
24 overlay varyantı (3 tetik × 2 makro kapı × 2 büyütme × 2 süre) önceden tanımlandı; hepsi raporda.

Değişen dosyalar: karma_lab.py (yeni), test_karma_lab.py (yeni), shock_data.py (gümüş SI=F eklendi),
.github/workflows/karma_lab.yml (yeni).
