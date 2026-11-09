# Technical Notes

Bu not, kodun neden bu şekilde olduğunu ve hangi kararların hangi sınırlamalarla alındığını açıklar.
Günlük değişiklikler için `CHANGELOG.md`, açık işler için `PROJECT_TRACKER.md`.

## Bileşenler

```
analyze_ui.py         HTTP handler + CLI (172 satır) — veri ve statik dosya servisi
fetch_yokatlas.py     YÖK Atlas arama API'sinden veri çekme + metadata üretimi
static/index.html     Arayüz işaretlemesi
static/app.js         Filtreleme, sıralama, seçim kalıcılığı, Markdown dışa aktarma
static/style.css      Tema
universite_json/      bolum_<bölüm>.json + metadata.json
tests/                stdlib unittest (ağ yok)
archive/              --prune ile taşınan eski dosyalar (repoya girmez)
```

## Veri akışı

1. `fetch_yokatlas.py` beş kategoriyi (`SAY/EA/SÖZ/DİL/TYT`) sayfalayarak çeker
   (`POST /api/tercih-kilavuz/search`, sayfa boyu 500, `sortBy=basariSirasi`, `direction=ASC`).
2. `convert_program` her kaydı sabit şemaya çevirir. `Yıl`, `Kontenjan`, `Taban Sıralama`,
   `Taban Puan` dizileri dört yıllıktır: `[GUIDE_YEAR, -1, -2, -3]`.
3. Kayıtlar `birimGrupAdi` (bölüm) bazında gruplanır; dosya adı `normalize_filename` ile
   Türkçe harfler ASCII'ye çevrilerek üretilir (parantez ve nokta atılır, boşluk `_` olur).
4. `metadata.json` yazılır: `guide_year`, `fetched_at`, `total_programs`, `department_files`,
   `categories`.
5. `--prune` verilmişse ve **tüm kategoriler eksiksiz indiyse**, bu turda üretilmeyen
   `bolum_*.json` dosyaları `archive/stale_<zaman>/` altına taşınır. Kısmi indirmede
   hiçbir dosyaya dokunulmaz — veri kaybı riskini bu koşul kapatır.
6. `--metadata-only` ağa çıkmadan `metadata.json`'u mevcut dosyalardan yeniden üretir.

### `fetched_at` semantiği

`fetched_at` **verinin çekildiği anı** anlatır, dosyanın disk tarihini değil. Bu yüzden
`rebuild_metadata()` veri kümesi değişmediyse (dosya sayısı, program sayısı ve kılavuz yılı aynı)
mevcut değeri korur; yalnızca küme değiştiğinde dosya mtime'ından türetir. Bu davranış CI'daki
`--metadata-only` + `git diff --exit-code` kapısının temelidir.

### Kılavuz yılı

Tek kaynak `fetch_yokatlas.py` içindeki `GUIDE_YEAR` sabitidir. Yeni tercih döneminde bu sabit
güncellenir; `YEARS` ve veri dosyalarındaki `Yıl` alanı otomatik türetilir. Arayüz hiçbir yılı
sabit yazmaz: `/api/metadata` → `guide_year` → başlıklar (`26/25/24`), satır altı yılları,
trend ipuçları ve Markdown başlığı. Metadata yoksa veya geçersizse 2026'ya düşer.

## HTTP katmanı

Tek handler (`YokAtlasHandler`, `BaseHTTPRequestHandler`), bilinen rotalar dışında **404**:

| Yol | Yanıt |
| :--- | :--- |
| `/`, `/index.html` | `static/index.html` |
| `/app.js`, `/style.css` | ilgili statik dosya |
| `/api/departments` | `[{id, name}]` |
| `/api/cities` | Türkçe büyük harfe çevrilmiş, tekilleştirilmiş şehir listesi |
| `/api/metadata` | `metadata.json` (yoksa `{}`) |
| `/api/department/<dosya>.json` | bölüm verisi |

Güvenlik kararları:

- Yalnızca `127.0.0.1` dinlenir (LAN'a açılmaz).
- `SimpleHTTPRequestHandler`'ın dizin servis eden `do_GET` davranışı **kullanılmaz**; bilinmeyen yol 404.
  Bu yüzden `/.git/config`, `/README.md`, `/analyze_ui.py` gibi yollar dışarıdan okunamaz.
- Bölüm dosyası adında `/`, `\`, `..` reddedilir; `.json` dışı uzantı 400 döner.
- Statik yanıtlarda `X-Content-Type-Options: nosniff` gönderilir.
- API'den gelen metinler arayüzde `esc()` ile HTML-escape edilir (`innerHTML` kullanılan yerler dahil).

`tests/test_server.py` bu davranışların hepsini gerçek bir soket üzerinden doğrular.

## Arayüz

- `static/app.js` tek IIFE değil, düz fonksiyonlar; durum modül seviyesinde
  (`allDepartments`, `selectedDepartments`, `programData`, `guideYear`, `sortBy/sortDirection`).
- Bölüm verisi 35'lik parçalar hâlinde önden yüklenir; seçim `localStorage`'da
  (`yokatlas_selected_departments`) tutulur ve açılışta geri yüklenir.
- Filtreler iki yerde çalışır: bölüm listesinde "eşleşen bölüm var mı" için, tabloda satır elemesi için.
- "Öğrencinin başarı sırası" ve "öğrencinin puanı" filtreleri öğrencinin kendi değerini bekler:
  taban sırası öğrencinin sırasından **geride** olan, taban puanı öğrencinin puanından **düşük** olan
  programlar listelenir.

## Bilinen sınırlamalar

- **`Yerleşen` verisi yok.** Arama API'si 66 alan döndürüyor; yerleşen sayısı içermiyor
  (`kontenjan` ve `gk1..gk3` kontenjan serisidir). Program detay uçları 403 verdi. Alan boş
  dizi olarak kalır; doluluk analizi yapılmaz.
- **Öğrenim süresi sezgisel.** `getProgramDuration` fakülte adındaki "meslek yüksek"/"myo"
  ifadesine bakar; API'nin `ogrenimSuresi` alanı veri setine yazılmıyor. Şema genişletilirse
  bu alan taşınmalı.
- **Sayfa sırası API'ye bağlı.** Dosya içindeki program sırası `basariSirasi ASC` sıralamasıdır;
  yeni veri çekildiğinde sıra değişebilir ve diff büyür (veri commit'i kabul edilen durum).
- **Kardeş proje manuel.** `kariyer-pusulasi-ai` deposu aynı şemayı kullanır; canlı bağlantı
  yoktur. Şema değişirse oradaki `universite_json` kopyası elle hizalanmalıdır.
- Arayüzde tarayıcı otomasyonu yok; doğrulama için `node --check`, sunucu uç testleri ve
  elle smoke kullanılır.
