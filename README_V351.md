# v3.5.1 — ETH/BTC ayrışması ve kripto RVOL (2026-10-01)
1. **ETH "YATAY (+0.25)" ama BTC "GÜÇLÜ AŞAĞI (−0.84)":** Yahoo kripto saatlik verisi bazen oluşan 08:00 barından
   sonra çekim dakikasıyla damgalı (08:49) ekstra bir satır ekliyor. Kapanmış-bar kuralı yalnız son satırı düşürdüğü için
   ETH'de oluşmakta olan 08:00 barı kullanılıyordu (+0.25% = 2676 → 2683). Arka plan işi aynı anda ETH için doğru
   değeri hesaplamıştı: GÜÇLÜ AŞAĞI (−1.39%). Artık saati dolmamış TÜM satırlar düşürülüyor.
2. **Kripto RVOL "—":** Yahoo BTC/ETH saatlik barların %47–53'ünde hacmi 0 veriyor; sahte RVOL yerine "—" gösteriliyordu.
   Artık hacim OKX'in ücretsiz, anahtarsız mum verisinden (USDT hacmi) alınıyor; fiyatlar Yahoo'dan kalıyor.
   OKX'e erişilemezse eski güvenli davranış ("—") sürer.
