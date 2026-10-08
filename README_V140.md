# v14.0 — Bakır Laboratuvarı (COPPERUSDT)

Workflow: **Tier-1 Bakır Lab v14** (`copper_lab.yml`) → sonuçlar `copperlab` dalında ve Artifacts → copper-lab-results.

Bitget'teki COPPERUSDT geçmişi kısa olduğu için test, kontratın izlediği **COMEX bakır vadelisi (HG=F, 2000→bugün)**
üzerinde yapılır; Bitget kontratı ayrıca kontrol edilir (fiyat oranı, günlük korelasyon, fonlama maliyeti).

Denenenler (her biri çift yön / yalnız long / yalnız short):
- **Trend:** MA kesişimleri, fiyat>MA, 5 gün–12 ay momentum, momentum topluluğu, Donchian/kaplumbağa, MACD (hızlı, yavaş, sıfır), EMA eğimi, ADX filtreli momentum
- **Ortalamaya dönüş:** RSI(2), RSI(14), Bollinger, 5 günlük z-skoru, IBS, seri sonrası dönüş
- **Kırılım:** oynaklık sıkışması, ATR genişlemesi
- **Mevsimsellik:** ay ve haftanın günü (yalnız geçmiş yıllarla, ileri yürüyen), ay dönümü
- **Temel/makro:** bakır/altın oranı, dolar (DXY ve geniş), yuan, AUD, reel faiz, enflasyon beklentisi, petrol, S&P trendi,
  Çin hisseleri, madencilerin öncülüğü, getiri eğrisi, kredi spreadi, VIX, NFCI, OECD öncü göstergeleri (Çin/ABD), sanayi üretimi
- **Pozisyonlanma:** CFTC COT (spekülatör ve fon pozisyonları; yayın tarihinden sonra kullanılır)
- **Makine öğrenmesi:** her yıl yalnız geçmişle yeniden eğitilen gradient boosting
- **ATVS kuralları** bakırda (kaynak belge metallerde çalışmadığını söylüyor; burada kontrol ediliyor)
- **İkili kombinasyonlar** (trend/dönüş × makro/COT filtresi), **çıkış katmanları** (iz süren ATR stopu, oynaklık hedefi)
- **Portföye katkı:** mevcut risk paritesi vs bakır eklenmiş vs bakır zamanlanmış
- **Saatlik keşif** (son ~2 yıl; seçimde kullanılmaz)

Kurallar: seçim yalnız 2000–2016 · 2017+ mühürlü sınav · maliyet + long fonlama farkı · Deflated Sharpe · bakırı tutmaya göre alfa t.
Testler: dikilmiş avantajı bulur, saf gürültüde sahte avantaj bulmaz, ileriye bakmaz, COT yayın gecikmesine uyar.
