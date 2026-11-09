# Project Tracker

**Proje:** kariyer-pusulasi-data — YÖK Atlas tercih kılavuzu verisi + yerel analiz arayüzü
**Repo:** `github.com/cenktekin/kariyer-pusulasi-data` (PUBLIC)
**Son tur:** 2026-11-09

## Durum

| Alan | Değer |
| :--- | :--- |
| Kılavuz yılı | 2026 |
| Bölüm dosyası | 632 |
| Program | 21.491 |
| Veri tazeliği (`fetched_at`) | 2026-11-09T17:13:00+00:00 |
| Test | 31 (stdlib `unittest`, ağ yok) |
| CI | `.github/workflows/ci.yml` — compile → test → metadata tekrar üretilebilirlik |
| `analyze_ui.py` | 172 satır (hedef < 400) |
| Sunucu | `127.0.0.1:8005`, bilinmeyen yol 404 |

## Bu turda kapanan kalemler

| # | Kalem | Kanıt |
| :--- | :--- | :--- |
| N1 | Test iskelesi + CI | `tests/` 3 dosya / 31 test; `.github/workflows/ci.yml` |
| N2 | Monolit bölme | `analyze_ui.py` 1.368 → 172; `static/{index.html,app.js,style.css}`; `node --check` temiz |
| N3 | Doküman seti | `CHANGELOG.md`, `TECHNICAL_NOTES.md`, `PROJECT_TRACKER.md`; README'den bağlı |
| N4 | Dinamik yıl etiketleri | `guide_year=2027` ile başlıklar 27/26/25; 2026 çıktısı değişmedi |
| N5 | `--prune` gerçek indirme | 632 dosya yenilendi; stale yok; 21.491 program |
| N6 | `Yerleşen` alanı | Kaynak API'de yok (66 alan, detay ucu 403) — README + notlar |

## Açık kalemler

Yok. Aşağıdakiler bilinçli olarak ertelendi.

## Ertelenen (bilinçli)

- Bölüm bazlı karşılaştırma grafikleri, PDF çıktısı, çoklu yıl trend grafiği — tablo + Markdown yeterli.
- Framework geçişi (Flask/FastAPI), veritabanı (SQLite), hesap sistemi — kazanç/efor düşük.
- `Yerleşen` alanını doldurmak — kaynakta veri yok; uydurma/yeniden hesaplama yapılmaz.

## Kararlar

1. **Bağımlılık minimal:** üretimde yalnızca `httpx`; testler ve sunucu stdlib. CI bu yüzden hızlı ve kırılgan değil.
2. **Tek handler, kapalı yüzey:** bilinmeyen her yol 404. Yeni bir uç eklenirse `STATIC_FILES` /
   `do_GET` listesine bilinçli olarak eklenmeli.
3. **Yıl tek kaynaktan:** `fetch_yokatlas.py:GUIDE_YEAR` → veri → `metadata.json` → arayüz. Arayüzde sabit yıl yok.
4. **`fetched_at` = veri yaşı:** veri kümesi değişmedikçe korunur; dosya mtime'ı tek başına tazelik sayılmaz.
5. **Veri dosyası anahtar sırası sabit:** `convert_program` sırası mevcut dosyalarla aynı; yenileme diff'i
   yalnızca gerçek veri değişimini gösterir.
6. **`--prune` kapısı:** yalnız tüm kategoriler eksiksiz indiğinde çalışır; aksi halde mevcut dosyalara dokunmaz.

## Doğrulama

```powershell
cd kariyer-pusulasi-data
python -m py_compile analyze_ui.py fetch_yokatlas.py
python -m unittest discover -s tests -v
python fetch_yokatlas.py --check
python fetch_yokatlas.py --metadata-only
git diff --exit-code -- universite_json/metadata.json
python analyze_ui.py
# /api/departments = 632 · /api/cities = 83 · /api/department/bolum_Tip.json = 242 program
# /README.md = 404 · /api/department/../metadata.json = 404
# Commit öncesi sızıntı taraması: mutlak yol / kullanıcı adı desenleri boş dönmeli
```

## Not

`NEXT_ACTIONS.md`, `archive/`, `scratch/` repoya girmez (`.gitignore`). Repo PUBLIC olduğu için
commit öncesi sızıntı taraması zorunludur.
