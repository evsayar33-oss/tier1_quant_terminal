# v4.0 — Strateji Laboratuvarı, hızlı açılış, kuyruk düzeltmesi, aracı kurum seçimi

## Yükleme (telefondan, `main` dalına, klasör yapısını koruyarak)

| Dosya | Durum |
|---|---|
| `strategy_lab.py`, `test_strategy_lab.py` | YENİ: geniş strateji taraması |
| `.github/workflows/strategy_lab.yml` | YENİ: "Tier-1 Strategy Lab (strateji testi)" |
| `.github/workflows/stateful_adaptive_tracker.yml` | DEĞİŞTİ: artık "Tier-1 Motoru Şimdi Yeniden Başlat (manuel)" |
| `.github/workflows/tier1_engine_loop.yml` | DEĞİŞTİ: lab sonuçlarını da yükler |
| `app.py` | DEĞİŞTİ: anında açılış, lab sütunu ve tabloları |
| `bot_loop.py`, `paper_broker.py`, `state_sync.py` | DEĞİŞTİ: lab sinyali → sinyal sözleşmesi → paper defter |
| `test_engine_loop.py`, `test_paper_broker.py` | DEĞİŞTİ: yeni testler |
| `lab_report.md`, `lab_results.json`, `lab_playbook.json` | ÖN İZLEME sonuçları (ilk lab çalışması bunların yerine geçer) |

Sonra sırayla:
1. Streamlit → **Manage app → ⋮ → Reboot app**.
2. Actions → **Tier-1 Strategy Lab (strateji testi)** → **Run workflow** (5-10 dk). Bitince özet tablo işin sayfasında da görünür.
3. Actions → **Tier-1 Motoru Şimdi Yeniden Başlat (manuel)** → **Run workflow**. Çalışan motoru durdurur, yeni kodu ve lab sonuçlarını hemen kullanan yeni motoru başlatır. Kuyrukta beklemez.

## 1) Strateji testi ve getiri tabloları
`strategy_lab.py` her varlık için 7 strateji ailesini, 3 zaman dilimini (1s, 4s, 1g), çift yönlü ve sadece-alış versiyonlarını ve 4 çıkış kuralını dener: toplam ~4.000 konfigürasyon, tüm sonuçlar maliyet sonrası.
Şans eseri kazananlar şöyle elenir:
- **Walk-forward seçim testi:** her dilimde sadece geçmişte en iyi olan seçilir, sonraki dilimde ölçülür.
- **Deflated Sharpe:** etkin deneme sayısıyla düzeltilir.
- **10 yıllık günlük veride ikinci bağımsız test.**

Uygulamada **"🧪 Strateji Laboratuvarı — test ve getiri tabloları"** bölümünde dört tablo var: varlık özeti, strateji aileleri, çok-varlıklı sağlam ayarlar ve varlık başına ilk 10. Tarama her cumartesi kendini yeniler.

## 2) Sürekli NÖTR / kanıtsız sinyaller
Makro model skorları ±0.1–0.2 civarında, giriş eşiği ise ~0.6. Model zayıf sinyal ürettiği için sistem doğru olarak işlem önermiyor. Eşiği düşürmek gürültüyü sinyal gibi gösterirdi.
Yeni **"🎯 Strateji Lab Sinyali"** sütunu her varlık için lab'in o anki adayını, yönünü ve kanıt durumunu gösterir. Bot yalnızca KANITLI olan sinyali işlem yapılabilir sayar. Kanıtsız aday paper defterde "🧪 Strateji Lab adayı" olarak gölge işlemle sınanır.

## 3) Manuel tracker kuyrukta bekliyordu
Sürekli motor zaten her saat aynı tracker döngüsünü çalıştırıyor. Ayrı manuel tracker aynı kuyruk grubunda olduğu için hep motorun bitmesini bekliyordu.
Bu iş akışı artık **"Motoru Şimdi Yeniden Başlat"**: kuyruğu atlar, motoru yeni kodla hemen yeniden başlatır.
Actions listesinde motorun arkasında "Queued" bir iş görmek normaldir; bu, sıradaki saatin işidir.

## 4) Site beyaz ekran / geç açılma
- Sayfa artık hesaplama yapmadan motorun yayınladığı son döngüyü gösterir (test: 0.4 sn).
- Eski sürüm, uyanan uygulamada önce koddaki eski durum dosyasını okuyup sonra senkronize ediyordu. Bu yüzden 2 Ekim'e ait eski veri görünebiliyordu. Sıra düzeltildi.
- Üstte **"📡 Gösterilen veri: … TSİ (… dk önce)"** satırı verinin tazeliğini gösterir.
- "⚡ Canlı Verileri Yenile" düğmesi en yeni döngüyü indirir (saniyeler). Eski tam hesaplama "🔬 Gelişmiş" bölümünde duruyor.

Hâlâ beyaz kalırsa: Streamlit'in uykudan uyanması 1-2 dk sürebilir. Ekranda "Yes, get this app back up" görünürse ona bas. Devam ederse **Manage app → Logs** ekranının görüntüsünü gönder.

## 5) Aracı kurum (borsa) seçimi
Türkiye'de lisanslı kripto platformlarında 13 Mart 2025'ten beri kaldıraç, türev ve açığa satış yasak. OKX TR, Binance TR ve Bybit TR bu yüzden sadece spot sunuyor.

| Seçenek | 6 varlığın hepsi | Açığa satış | API | GitHub Actions uyumu | Not |
|---|---|---|---|---|---|
| **Hyperliquid** (merkeziyetsiz borsa) | ✅ (S&P/Nasdaq/altın/gümüş HIP-3 piyasalarıyla) | ✅ | Ücretsiz + testnet | En iyi (anahtar ile imza, ağ geçidi yok) | KYC yok. Endeks/emtia piyasaları büyük ölçüde tek bir üçüncü taraf operatöre bağlı. Yatırımcı koruması yok. |
| Kraken Derivatives | BTC, ETH, SPY, QQQ, GLD perp (gümüş doğrulanmadı) | ✅ | Ücretsiz + demo | Muhtemelen iyi | Türkiye hariç tutulanlar listesinde değil |
| Binance global / Bybit global | ✅ | ✅ | Ücretsiz + testnet | ❌ GitHub sunucularının ABD IP'lerini engelliyor | Ancak ABD dışı bir sunucuyla çalışır |
| Interactive Brokers | ✅ (mikro vadeli MES/MNQ/MGC/SIL) | ✅ | Ücretsiz; veri ~1.55$/ay | Zayıf (Java ağ geçidi + 2FA) | En düzenlenmiş seçenek |
| OKX TR (mevcut) | Sadece BTC/ETH spot | ❌ | Ücretsiz, demo yok | İyi | Sadece "sadece-alış" stratejiler için |

**Öneri:**
- Paper aşaması bitene kadar hiçbirine para yatırmaya gerek yok.
- Kanıtlı bir strateji çıkarsa:
  - sadece-alış kripto için mevcut **OKX TR** yeterli;
  - 6 varlıkta çift yönlü işlem için teknik olarak en uygun seçenek **Hyperliquid**, ancak yasal ve operasyonel riskleri var: yurt dışı platform gri alanda, SPK erişim engeli koyabilir, MASAK transfer limitleri uygulanıyor.

Karar senin. Bu bir yatırım veya hukuk tavsiyesi değildir.
