# Araştırma Günlüğü — denenen HER yöntem buraya yazılır

Kural: bir yöntem denenir ve sonucu ne olursa olsun buraya yazılır. Başarısız denemeler silinmez.
Sebep: çok sayıda yöntem denenirse biri şans eseri iyi görünür. Toplam deneme sayısı, kanıt eşiğini (Bonferroni) belirler.
Bu sayı ancak bütün denemeler kayıtlıysa doğru olur.

| # | Tarih | Veri | Yöntem | Sonuç | Karar |
|---|---|---|---|---|---|
| 1 | 2026-09-30 | Saatlik panel 2024-10→2026-09 | Varlık başına ridge, 4 aile × 2 ufuk (walkforward_optimizer) | t(IC) −0.5…+1.6; hiçbir varlıkta t ≥ 2.73 değil | Kanıtsız, canlıda "kanıtsız" etiketi |
| 2 | 2026-10-17 | Aynı panel | Elle ağırlıklı skordan VIX kümesi + 4s momentum çıkarıldı | SPX/NQ IC 12/12 hücrede iyileşti, ama hâlâ t < 2 | v15.0'da uygulandı (rol: durum) |
| 3 | 2026-10-17 | Aynı panel | "Korkuda al" (VIX işareti ters) | Sadece 2. dönemde güçlü (Nisan 2025 olayı) | Reddedildi (tek olay) |
| 4 | 2026-10-17 | Aynı panel | Gama/stres durumuna göre momentum ↔ geri dönüş | IC +0.02…+0.07, kararsız | Reddedildi |
| 5 | 2026-10-20 | Aynı panel | Varlıklar arası HAVUZLANMIŞ ridge (ortak ağırlık + varlık sabitleri), tüm faktörler ve ortak faktörler, 24s/72s | Bütün varlıklarda Hep AL'ın altında; 72s'de BTC/ETH IC −0.08…−0.09 | Reddedildi. Sonuç: saatlik faktör kütüphanesi 24-72s YÖNÜ için bilgi taşımıyor |
| 6 | 2026-10-20 | Günlük veri, son 10 yıl (BTC 2014+, ETH 2017+) | 7 parametresiz kural (momentum 20/60/120/250 + topluluk, 200g trend al/sat ve al/bekle, stres geri dönüşü) × 1/5 gün; Hep AL'a göre zamanlama alfası; 16 test/varlık, gerekli t 2.96 | Hiçbir varlıkta kanıt yok. En iyi: XAU stres geri dönüşü t +1.19 (3/3 dönem pozitif ama zayıf), BTC momentum t ≈ +0.7. Hisse/metallerde trend kuralları Hep AL'ın altında | Reddedildi. Uzun vade için en iyi bilinen tahmin taban orandır (tarihsel yükseliş sıklığı); arayüzde "taban" olarak gösterilir |

## Sağlam bulgular (yön dışı)
* Volatilite/gama faktörleri bir sonraki hareketin BÜYÜKLÜĞÜNÜ 3/3 dönemde tahmin ediyor (IC −0.06…−0.30). Stop mesafeleri bu bilgiyi kullanıyor.
* Hisse ve metallerde 2024-2026 döneminde "Hep AL" bütün modelleri geçti. Bu dönemin yükseliş eğilimidir; bir yön modeli bu eğilimin ÜSTÜNDE değer üretmek zorundadır.
