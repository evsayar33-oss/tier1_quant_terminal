# ⚡ Scalping Laboratuvarı v10 — 5 dakikalık mumlar, son 2 yıl mühürlü

_Üretim: 2026-10-08T12:50 UTC · her ayın en çok işlem gören 30 perp'i (297 farklı sembol) · 156 bot ayarı · eğitim 2022-01-01 → 2024-09-30 · **sınav 2024-09-30 → 2026-09-30**_

**Maliyet:** taker %0.05 + kayma %0.02 = işlem başına gidiş-dönüş %0.14. 'Maker' sütunu her emrin limit emirle (%0.02) dolduğu iyimser üst sınırdır. Mum içinde önce stop varsayılır.

## 1) Eğitimin en iyi botu ve mühürlü sınav

| Bot | İşlem/gün | Kazanma oranı | Ort. kazanç / kayıp | İşlem başı net | Eğitim Sharpe | **Sınav Sharpe** | Sınav (maker) | Sınav getiri / DD | DSR | Durum |
|---|---|---|---|---|---|---|---|---|---|---|
| RSI(14) aşırılık (20/80) · trend yönünde · TP 2×ATR / SL 2×ATR · en fazla 4 saat | 0.5 | %54.6 | +%0.84 / −%0.96 | +2.1 bp | 0.09 | **0.37** | 1.46 | %+0.4 / %-0.5 | 0.10 | ❌ kanıt yok |

**Yıllık walk-forward:** Sharpe -0.22 (t -0.3) · 2023: +0.22 · 2024: -0.63

## 2) Bot aileleri (tüm ayarların ortalaması)

| Aile | Ayar | Kazanma oranı | İşlem başı net | Eğitim Sharpe | **Sınav Sharpe** | Sınav (maker) | Sınavda + |
|---|---|---|---|---|---|---|---|
| RSI(14) aşırılık · trend yönünde | 12 | %52.1 | -6.6 bp | -1.54 | **-1.45** | 0.47 | %33 |
| Likidasyon mumu tepkisi | 24 | %41.3 | -23.2 bp | -6.60 | **-5.16** | -3.13 | %0 |
| RSI(14) aşırılık | 12 | %48.0 | -16.5 bp | -10.97 | **-12.08** | -6.30 | %0 |
| Ortalamaya dönüş (z) · trend yönünde | 36 | %49.8 | -12.3 bp | -10.94 | **-12.52** | -3.08 | %0 |
| Hacimli kırılım | 24 | %46.2 | -19.0 bp | -26.23 | **-24.62** | -12.92 | %0 |
| Ortalamaya dönüş (z) | 36 | %47.7 | -14.9 bp | -26.69 | **-28.49** | -11.81 | %0 |
| Emir akışı (taker oranı) | 12 | %40.5 | -15.6 bp | -20.59 | **-30.33** | -16.14 | %0 |

## 3) En yüksek kazanma oranlı 10 bot — kazanma oranı kâr demek mi?

| Bot | Kazanma oranı | Ort. kazanç / kayıp | İşlem/gün | İşlem başı net | Sınav getiri | Sınav Sharpe |
|---|---|---|---|---|---|---|
| Ortalamaya dönüş (z) (|z|>3) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 4 saat | **%65.1** | +%0.33 / −%0.88 | 7.7 | -9.5 bp | %-17.6 | -5.02 |
| Ortalamaya dönüş (z) (|z|>3) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 2 saat | **%64.8** | +%0.33 / −%0.87 | 7.7 | -9.5 bp | %-17.5 | -5.05 |
| Ortalamaya dönüş (z) (|z|>2.5) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 4 saat | **%63.9** | +%0.32 / −%0.89 | 23.8 | -11.4 bp | %-49.3 | -9.46 |
| RSI(14) aşırılık (20/80) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 2 saat | **%63.8** | +%0.37 / −%0.81 | 0.5 | -5.5 bp | %-0.7 | -0.90 |
| RSI(14) aşırılık (20/80) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 4 saat | **%63.8** | +%0.37 / −%0.81 | 0.5 | -5.5 bp | %-0.7 | -0.90 |
| Ortalamaya dönüş (z) (|z|>2.5) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 2 saat | **%63.5** | +%0.32 / −%0.87 | 23.8 | -11.4 bp | %-49.0 | -9.43 |
| Ortalamaya dönüş (z) (|z|>2) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 4 saat | **%63.3** | +%0.32 / −%0.89 | 60.7 | -12.3 bp | %-82.9 | -13.31 |
| Ortalamaya dönüş (z) (|z|>2) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 2 saat | **%62.8** | +%0.32 / −%0.87 | 60.7 | -12.3 bp | %-82.6 | -13.36 |
| Ortalamaya dönüş (z) (|z|>2.5) · TP 1×ATR / SL 2×ATR · en fazla 4 saat | **%62.0** | +%0.32 / −%0.90 | 270.4 | -13.9 bp | %-100.0 | -23.21 |
| Ortalamaya dönüş (z) (|z|>2.5) · TP 1×ATR / SL 2×ATR · en fazla 2 saat | **%61.9** | +%0.32 / −%0.89 | 270.4 | -13.9 bp | %-100.0 | -23.19 |

## 4) Eğitimin en iyi 20 botu ve sınav sonuçları

| # | Bot | Kazanma | İşlem/gün | Eğitim Sharpe | Eğitim yıllık | Sınav Sharpe | Sınav (maker) | Sınav getiri |
|---|---|---|---|---|---|---|---|---|
| 1 | RSI(14) aşırılık (20/80) · trend yönünde · TP 2×ATR / SL 2×ATR · en fazla 4 saat | %55 | 0.5 | 0.09 | %+0.0 | 0.37 | 1.46 | %+0.4 |
| 2 | RSI(14) aşırılık (20/80) · trend yönünde · TP 2×ATR / SL 2×ATR · en fazla 2 saat | %55 | 0.5 | -0.03 | %-0.0 | 0.46 | 1.55 | %+0.5 |
| 3 | RSI(14) aşırılık (20/80) · trend yönünde · TP 2×ATR / SL 1×ATR · en fazla 4 saat | %40 | 0.5 | -0.15 | %-0.1 | 0.27 | 1.79 | %+0.3 |
| 4 | RSI(14) aşırılık (20/80) · trend yönünde · TP 2×ATR / SL 1×ATR · en fazla 2 saat | %40 | 0.5 | -0.29 | %-0.1 | 0.26 | 1.78 | %+0.3 |
| 5 | RSI(14) aşırılık (20/80) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 4 saat | %64 | 0.5 | -0.95 | %-0.3 | -0.90 | 0.88 | %-0.7 |
| 6 | RSI(14) aşırılık (20/80) · trend yönünde · TP 1×ATR / SL 2×ATR · en fazla 2 saat | %64 | 0.5 | -0.96 | %-0.3 | -0.90 | 0.88 | %-0.7 |
| 7 | Likidasyon mumu tepkisi (mum>5×ATR) · TP 2×ATR / SL 2×ATR · en fazla 2 saat | %48 | 5.1 | -1.52 | %-6.9 | -1.75 | -0.97 | %-22.4 |
| 8 | Likidasyon mumu tepkisi (mum>5×ATR) · TP 2×ATR / SL 2×ATR · en fazla 4 saat | %48 | 5.1 | -1.53 | %-6.9 | -1.77 | -0.99 | %-22.6 |
| 9 | RSI(14) aşırılık (20/80) · trend yönünde · TP 1×ATR / SL 1×ATR · en fazla 2 saat | %49 | 0.6 | -1.79 | %-0.6 | -1.57 | 1.08 | %-1.0 |
| 10 | RSI(14) aşırılık (20/80) · trend yönünde · TP 1×ATR / SL 1×ATR · en fazla 4 saat | %49 | 0.6 | -1.79 | %-0.6 | -1.57 | 1.08 | %-1.0 |
| 11 | Likidasyon mumu tepkisi (mum>5×ATR) · TP 2×ATR / SL 1×ATR · en fazla 2 saat | %34 | 5.1 | -2.02 | %-6.2 | -2.32 | -0.59 | %-14.3 |
| 12 | Likidasyon mumu tepkisi (mum>5×ATR) · TP 2×ATR / SL 1×ATR · en fazla 4 saat | %34 | 5.1 | -2.02 | %-6.2 | -2.32 | -0.60 | %-14.3 |
| 13 | Ortalamaya dönüş (z) (|z|>3) · trend yönünde · TP 2×ATR / SL 2×ATR · en fazla 4 saat | %52 | 7.3 | -2.06 | %-11.0 | -2.76 | 0.65 | %-14.0 |
| 14 | Ortalamaya dönüş (z) (|z|>3) · trend yönünde · TP 2×ATR / SL 2×ATR · en fazla 2 saat | %51 | 7.3 | -2.09 | %-11.1 | -3.20 | 0.35 | %-15.4 |
| 15 | RSI(14) aşırılık (20/80) · trend yönünde · TP 0.5×ATR / SL 2×ATR · en fazla 2 saat | %59 | 0.5 | -2.86 | %-0.7 | -3.01 | -0.87 | %-2.1 |
| 16 | RSI(14) aşırılık (20/80) · trend yönünde · TP 0.5×ATR / SL 2×ATR · en fazla 4 saat | %59 | 0.5 | -2.86 | %-0.7 | -3.01 | -0.87 | %-2.1 |
| 17 | RSI(14) aşırılık (20/80) · trend yönünde · TP 0.5×ATR / SL 1×ATR · en fazla 2 saat | %46 | 0.6 | -3.43 | %-1.1 | -3.89 | -1.53 | %-2.5 |
| 18 | RSI(14) aşırılık (20/80) · trend yönünde · TP 0.5×ATR / SL 1×ATR · en fazla 4 saat | %46 | 0.6 | -3.43 | %-1.1 | -3.89 | -1.53 | %-2.5 |
| 19 | Likidasyon mumu tepkisi (mum>5×ATR) · TP 1×ATR / SL 2×ATR · en fazla 2 saat | %52 | 5.1 | -3.76 | %-15.2 | -2.42 | -1.80 | %-33.9 |
| 20 | Likidasyon mumu tepkisi (mum>5×ATR) · TP 1×ATR / SL 2×ATR · en fazla 4 saat | %52 | 5.1 | -3.76 | %-15.2 | -2.42 | -1.80 | %-33.9 |
