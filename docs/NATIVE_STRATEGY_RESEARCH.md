# tier1_quant_terminal — veri biriktirme, sınırlı araştırma ve ileri kanıt

Kaynak: performance_ledger, historical replay ve Tier-1 makro/mikroyapı.

Orijinal strateji mantığı: Makro likidite, gamma/pozisyonlama, çapraz-asset kırılma, vadeli signed-flow; forward grade ayrı tutulmalı.

Kabul/araştırma koruması: Historical replay tek başına bağımsız 30 günlük forward ve gerçekleşebilir fill kanıtı değil.

Bu araştırma iş akışı, üretimdeki mevcut strateji, PAPER veya LIVE
kurallarını **değiştirmez**. Repo içindeki mevcut tarihli veri ve resmi
araştırma kayıtları üzerinden kaynağın orijinal durumunu toplar.
Kayıtlar aynı SHA ile yinelendiğinde yeni örnek sayılmaz. Kaynak zamanı
geri sarılırsa fail-closed; aynı kaynak zamanı düzeltilirse revision sayılır.
Her yeni gerçek kaynak kaydının parmak izi append-only
`research/strategy-mesh-evidence/observations/strategy_mesh/observations.jsonl`
zincirinde tutulur. Günlük cron ve manuel Actions çalıştırması ayrıca
JSON/Markdown raporu ve yalnız tasarım amaçlı hipotez kuyruğu üretir.

Kullanılan araştırma motoru: `evsayar33-oss/quant_superlab` pinned
`b5ca02a12d58730ac29b84badef8601b898540fe`.
Bu kod yalnız çalıştıran repo içinde çalışır; diğer repoya veri göndermez.

Özgün mantığı bozmamak için kombinasyonlar yalnız bu repo için
önceden belirlenmiş ve ekonomik anlamı olan özellik ailelerinden gelir.
Bunlar **backtest veya doğrulanmış strateji değildir**. Sıradaki
aşamada verisi yeterli bulunan adayların t-anında bilinen özellikleri,
negatif kontroller, walk-forward, masraf/likidite stresi, ayrık holdout
ve olgunlaşmış prospective trade kanıtı bağımsız olarak tamamlanacaktır.
Bunları geçmeden otomatik PAPER/LIVE terfisi yasaktır.

GitHub Actions → *Native data-first strategy research (NO ORDERS)* →
*Run workflow* ile manuel başlatılabilir. Araştırma defteri ve kanıt
branch'i, mevcut üretim dalı ve eski PAPER kanıt dallarından bağımsızdır.
