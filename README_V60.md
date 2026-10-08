# v6.0 — Çok ufuklu, tek tek + kombinasyonlu strateji laboratuvarı

## Yükleme
`strategy_lab.py`, `test_strategy_lab.py`, `.github/workflows/strategy_lab.yml` dosyalarını `main` dalına yükle.
Sonra Actions → **Tier-1 Strategy Lab (strateji testi)** → Run workflow (~30-90 dk).
Sonuçlar: iş sayfası Summary'deki zip bağlantısı veya en alttaki **Artifacts → strategy-lab-results**.

## Ne eklendi
1. **5 tutma ufku:** her sinyal 1 saat, 4 saat, 1 gün, 1 hafta ve 1 ay ufkunda ayrı ayrı test edilir.
   Pozisyon yalnızca ufuk başında belirlenir ve ufuk boyunca tutulur. Böylece makro sinyaller doğru ufukta sınanır.
2. **Dönüşümler:** sinyalin son değeri veya ufuk boyunca ortalaması · işaret / güçlü (|z|>0.5, |z|>1) ·
   sistem yönünde ve TERS · long+short / sadece long / sadece short · ufka uygun çıkış kuralları.
3. **Kombinasyon keşfi:** her varlıkta en iyi 40 tekli sinyalin tüm ikili birleşimleri ve 2-7 sinyallik çoğunluk oyları.
   - Keşif: ilk %50'lik dönem.
   - Seçim: sonraki %25'lik dönem.
   - Karar: hiç kullanılmamış son %25'lik dönem.
4. **Varlık başına ~70-80 bin, toplam ~450 bin konfigürasyon.** Hepsi `lab_all_configs.csv.gz` dosyasında tek tek listelenir.
5. **Kanıt yolu C:** veriden bulunan bir kombinasyon, son dönemde t ≥ 2 ve alfa t ≥ 2 verirse bot onu kullanabilir.
