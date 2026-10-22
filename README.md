# kariyer-pusulasi-data

YÖK Atlas tercih kılavuzu verilerinin yerel kopyası ve bu veriyi karşılaştırmak için
çalışan tek dosyalık bir analiz arayüzü.

Veri seti, YÖK Atlas'ın genel arama API'sinden çekilir; her bölüm ayrı bir JSON
dosyasına yazılır. Arayüz harici bir bağımlılık kullanmaz, veriyi yalnızca yerel
makineden okur ve hiçbir yere göndermez.

## Veri seti

| Alan | Değer |
| :--- | :--- |
| Kılavuz yılı | 2026 |
| Bölüm dosyası | 641 |
| Program | 21.621 |
| Format | `universite_json/bolum_<bölüm_adı>.json` |
| Meta | `universite_json/metadata.json` (`guide_year`, `fetched_at`, `total_programs`) |

Her program kaydı şu alanları taşır:

`Program Kodu`, `Üniversite`, `Fakülte`, `Üniversite Türü`, `Program Adı`,
`Öğretim Türü`, `Yıl`, `Kontenjan`, `Yerleşen`, `Taban Sıralama`, `Taban Puan`,
`Şehir`, `Ücret`, `Puan Türü`

`Kontenjan`, `Taban Sıralama` ve `Taban Puan` dizileri kılavuz yılından geriye
dört yılı içerir (2026, 2025, 2024, 2023).

## Kurulum

```bash
pip install -r requirements.txt
```

## Arayüz

```bash
python analyze_ui.py
```

Ardından `http://127.0.0.1:8005` adresini açın. Sunucu yalnızca yerel arayüze
(`127.0.0.1`) bağlanır; `/api/*` dışındaki yollar 404 döner.

Özellikler: bölüm seçimi (seçim tarayıcıda saklanır), puan türü / süre / üniversite
türü / şehir / burs türü filtreleri, öğrencinin sıralaması ve puanına göre eleme,
sıralama-puan sütunlarına göre sıralama, Markdown raporu indirme.

## Veriyi yenileme

```bash
python fetch_yokatlas.py --check           # API şemasını tek sayfayla doğrular, dosya yazmaz
python fetch_yokatlas.py                   # tüm veriyi indirir
python fetch_yokatlas.py --prune           # ek olarak artık üretilmeyen bölüm dosyalarını archive/ altına taşır
python fetch_yokatlas.py --metadata-only   # metadata.json'u mevcut dosyalardan yeniden üretir
```

Yeni tercih döneminde `fetch_yokatlas.py` içindeki `GUIDE_YEAR` sabiti
güncellenmelidir; veri dosyalarındaki `Yıl` alanı bu sabitten üretilir.

`--prune` yalnızca tüm kategoriler eksiksiz indiğinde çalışır; kısmi indirmede
mevcut dosyalara dokunmaz.

## Kaynak

Veriler [YÖK Atlas](https://yokatlas.yok.gov.tr) tercih kılavuzundan alınmıştır.
Veri sahipliği ve doğruluğu YÖK'e aittir; bu depo yalnızca yerel analiz için bir
kopya tutar.
