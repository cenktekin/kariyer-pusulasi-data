# Changelog

Bu dosya projedeki kullanıcı tarafından görülebilir değişiklikleri tarih sırasıyla (yeniden eskiye) listeler.
Veri yenilemelerinin tarihi `universite_json/metadata.json` içindeki `fetched_at` alanındadır.

## 2026-11-09 — Test + CI, monolit bölme, dinamik yıl, ilk gerçek `--prune`

### Eklenen
- `tests/` altında 31 test (ağ yok): `test_fetch.py` (normalize_filename, burs_to_ucret,
  convert_program şeması/biçimlendirme, build_search_body, prune), `test_metadata.py`
  (rebuild_metadata toplamları ve `fetched_at` koruma davranışı), `test_server.py`
  (HTTP uçları, 404/400 sızıntı testleri).
- `.github/workflows/ci.yml`: `push`/`pull_request` → bağımlılıklar → `py_compile` →
  `unittest discover` → `--metadata-only` sonrası `git diff --exit-code`. `continue-on-error` yok.
- `static/index.html`, `static/app.js`, `static/style.css`: arayüz kaynağı ayrı dosyalara taşındı.
- `CHANGELOG.md`, `TECHNICAL_NOTES.md`, `PROJECT_TRACKER.md`; README'den bağlandı.

### Değişen
- `analyze_ui.py` 1.368 satırdan 172 satıra indi: yalnız HTTP handler + CLI. `/`, `/app.js`,
  `/style.css` `static/` altından okunur; diğer tüm yollar 404 (sızıntı koruması korundu).
- Tablo başlıkları ve yıl etiketleri artık `metadata.guide_year`'dan türetiliyor
  (`Kontenjan (26/25/24)`, `Başarı Sırası (2026)`, satır altı `2025: / 2024:`, trend ipuçları,
  Markdown başlığı). Metadata yoksa/geçersizse 2026'ya düşer; 2026 çıktısı değişmedi.
- `fetch_yokatlas.py`: JSON dosyaları `newline="\n"` ile yazılır (Windows'ta CRLF sızıntısı bitti);
  `convert_program` anahtar sırası mevcut veri setiyle aynı tutuldu (veri diff'i okunabilir kaldı).
- `rebuild_metadata()`: veri kümesi (dosya sayısı + program sayısı + kılavuz yılı) değişmediyse
  mevcut `fetched_at` korunur. Böylece yalnızca dosya mtime'ı değiştiği için tazelik bilgisi
  yanlışlıkla ilerlemez ve CI'da ağaç kirlenmez.

### Veri
- İlk gerçek tam indirme + `--prune`: **632 bölüm dosyası / 21.491 program**
  (önceki: 622 / 21.467). 2026 taban sıralama ve taban puan değerleri doldu.
- 10 yeni bölüm dosyası oluştu, hiçbir dosya stale çıkmadı (`archive/` boş kaldı).
- Program kodu tekrarı yok; SAY kategorisi `--check` çıktısıyla uyumlu (5.744).

### Belgelenen
- `Yerleşen` alanı kaynakta yok: arama API'si 66 alan döndürüyor, yerleşen sayısı içermiyor
  (aday alanlar: `kontenjan`, `gk1..gk3`). Program detay uçları 403 verdi. Alan boş dizi olarak
  kalacak; README'de "kaynakta yok" notu eklendi.

## 2026-10-22 — Güvenlik sertleştirmesi, veri tazeliği, depo hijyeni

- Sunucu `0.0.0.0` yerine `127.0.0.1`'e bağlanıyor; bilinmeyen yollar 404 (dizin sızıntısı kapandı).
- API'den gelen adlar `innerHTML`'e escape edilerek yazılıyor (XSS).
- `metadata.json` + `/api/metadata` + arayüzde veri tazeliği rozeti.
- Bölüm seçimi `localStorage`'da kalıcı (`yokatlas_selected_departments`).
- `fetch_yokatlas.py --prune`: üretilmeyen bölüm dosyalarını `archive/stale_<ts>/` altına taşır;
  yalnızca tüm kategoriler eksiksiz indiğinde çalışır.
- `GUIDE_YEAR = "2026"` sabiti; `Yıl`, `Kontenjan`, `Taban Sıralama`, `Taban Puan` dizileri buradan üretilir.
- 2026 kılavuz verisi (622 bölüm / 21.467 program) ve README.

## 2026-05-25 — YÖK Atlas 2025 verilerinin yeniden çekilmesi

- 2025 kılavuzu için tüm bölüm dosyaları yenilendi (commit `a18c329`).

## 2026-04-11 — Otomatik veri senkronizasyonu

- `universite_json` verisi senkronize edildi (commit `0001e3a`, `[skip-ci]`).

## 2025-08-21 — İlk sürüm

- İlk veri seti ve tek dosyalık analiz arayüzü (commit `3b05dea`, `8f2602d`).
