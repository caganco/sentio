Revizyon talebi — LOCAL_MACRO_SPEC.md güncelle:
CDS kaynağı değişikliği:

Trading Economics API (primary) → kaldır, ücretli
worldgovernmentbonds.com HTML scraping → PRIMARY
BeautifulSoup ile tablo parse
URL: http://www.worldgovernmentbonds.com/cds-historical-data/turkey/5-years/

LOCAL_MACRO_SPEC.md — BI Yabancı Takas bileşeni revize et:
Kaynak değişikliği:

datastore.borsaistanbul.com → ücretli, iptal
Yeni kaynak: isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/Temel-Degerler-Ve-Oranlar.aspx → Yabancı Oranlar tablosu
HTML scraping, BeautifulSoup
Günlük güncelleniyor, hisse bazında yabancı % oranı

Sinyal mantığı güncelle:

Ham net alış/satış TL yerine → günlük yabancı % oranı değişimi kullan
3 gün üst üste % düşüş → yabancı satış sinyali → Bull Trap flag
Threshold: günlük -%0.5'ten fazla düşüş → anlamlı satış