# v3.9 — Aşama 3: Paper Trading (kanıt toplama)

OKX TR demo API sunmadığı için kanıt kağıt üzerinde toplanır. Gerçek para, gerçek emir YOK.

## Ne yapar
- Her saatlik döngüde (bot_loop) `signals.json` üretildikten sonra `paper_broker.step()` çalışır.
- Sinyal, KAPANMIŞ mumdan sonra gelen ilk mumun AÇILIŞINDAN doldurulur (ileriye bakma yok).
- SL/TP her mumun High/Low'una göre kontrol edilir; aynı mum ikisine de değerse STOP sayılır.
- Maliyet: kripto %0.13/yön, SPX/NQ/XAU/XAG %0.04/yön. Maks. tutma 24 saat.
- 3 strateji yan yana: Model + giriş kapısı · Sadece model · Kısa Vade Yön. Karşılaştırma: al-tut.
- Kanıt eşiği: ≥30 kapanmış işlem, t ≥ 2, pozitif net beklenti, al-tut'tan iyi.
- Çıktılar `state` dalında: `paper_ledger.json` (en fazla 3000 işlem), `paper_report.md`.
- Uygulamada "📒 Paper Trading Karnesi" bölümünde görünür.

## Yükleme
Zip'teki dosyaları `main` dalına yükle → Streamlit'te Reboot. Workflow değişikliği yok; çalışan motor bir sonraki işte yeni kodu alır.
