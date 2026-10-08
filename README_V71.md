# v7.1 — COT verisi düzeltmesi

v7.0 ilk çalışmada Binance verisi geldi, CFTC COT gelmedi (cftc.gov tarayıcı olmayan istemcileri reddediyor).

* `alt_data.py`: tarayıcı kimliğiyle istek; zip arşivi yine engellenirse CFTC'nin ücretsiz açık veri API'sine
  (publicreporting.cftc.gov: TFF `gpe5-46if`, Disaggregated `72hh-3qpy`) otomatik geçer. Sütun eşleştirme
  en kısa eşleşen adı seçer (örn. `pct_of_open_interest_all` yerine `open_interest_all`). Hata olursa
  log'a HTTP kodu yazılır.
* `test_strategy_lab.py`: API yolu için çevrimdışı test (altın/gümüş).

Yükleme: iki dosyayı repo köküne koyun → Actions → Tier-1 Strategy Lab → Run workflow.
