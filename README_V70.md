# v7.0 — Sistem yönü FİLTRE + teknik TETİK, yeni bilgi kaynağı

## Değişen / yeni dosyalar (hepsini repo köküne, aynı isimle yükleyin)
| Dosya | Durum |
|---|---|
| `strategy_lab.py` | değişti — filtre+tetik ailesi, alternatif veri entegrasyonu, rapor bölüm 3b/3c |
| `alt_data.py` | **YENİ** — Binance türev konumlanması + CFTC COT indirici (ücretsiz, anahtarsız) |
| `test_strategy_lab.py` | değişti — 6 yeni test |
| `bot_loop.py` | değişti — kural alternatif veri kullanıyorsa günde bir kez `alt_recent.csv.gz` yeniler |
| `state_sync.py` | değişti — `alt_recent.csv.gz` ve `alt_recent_meta.json` state dalında taşınır |
| `.github/workflows/strategy_lab.yml` | değişti — önce alternatif veriyi indirir, sonra test eder |

## 1) Sistem yönü yalnızca filtre
Kural: **teknik tetik oluşur → yalnızca sistemin gösterdiği yönde girilir → ATR tabanlı çıkış.**
* Tetikler (1s / 4s / 1g): RSI(2) aşırılık dönüşü, Bollinger bandına dokunup dönüş, Donchian kırılımı,
  EMA20 kesişimi, MACD kesişimi, Keltner kırılımı. Tetik bir sonraki 12 / 48 / 120 saat boyunca geçerli.
* Filtreler: sistemin 15 ana yön çıktısı + tüm makro faktörler + yeni alternatif sinyaller,
  her biri anlık / günlük ortalama / haftalık ortalama hâliyle.
* Çıkışlar: sinyal, SL/TP 2/4 ATR, başa-baş, kısmi kâr, iz süren stop, volatiliteye göre SL/TP.
* Her filtreli kural, **aynı tetik + aynı çıkış + aynı yön modu** ile filtresiz hâline karşı ölçülür
  (rapor bölüm 3b, "kazanç"). Filtreye ancak pencerenin iki yarısında da kazanç veriyorsa güvenilir.

## 2) Yeni bilgi kaynağı (fiyattan ve makrodan bağımsız: "kim ne pozisyonda?")
| Kaynak | Varlık | Sinyaller | Ne zaman bilinir |
|---|---|---|---|
| Binance Vision arşivi (`data.binance.vision`) | BTC, ETH | açık pozisyon 24s/7g değişimi, büyük trader long/short, hesap long/short, agresif alış/satış oranı, perp primi (baz) | dosya günü + 30 saat |
| CFTC Commitments of Traders | 6 varlığın hepsi | kaldıraçlı fon / varlık yöneticisi / dealer net (S&P, Nasdaq, BTC, ETH); spekülatif fon / üretici / swap net (altın, gümüş); haftalık değişim; açık pozisyon değişimi | salı pozisyonu → cumartesi 00:00 UTC |

Gecikmeler, canlı botun o anda gerçekten bilebileceğinden daha erken bilgi kullanılmasın diye konuldu (testlerle doğrulandı).
Her sinyal hem ham hâliyle hem de kendi 90 gözlemlik geçmişine göre z-skoruyla test edilir; tek başına, 5 ufukta,
kombinasyonlarda ve **filtre** olarak.

## Çalıştırma
Actions → **Tier-1 Strategy Lab** → Run workflow. Sonuç: çalışma sayfasının Summary kısmı + en altta Artifacts +
`lab` dalı zip bağlantısı. Alternatif veri indirilemezse (ağ hatası) adım atlanır, test onsuz devam eder.
