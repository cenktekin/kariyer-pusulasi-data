#!/usr/bin/env python3
"""
fetch_yokatlas.py — YÖK Atlas API'den tüm üniversite program verilerini çeker,
mevcut JSON formatında department bazlı dosyalara kaydeder.

Kullanım:
    pip install -r requirements.txt
    python fetch_yokatlas.py --check           # API şemasını doğrula (dosya yazmaz)
    python fetch_yokatlas.py                   # tüm veriyi indir
    python fetch_yokatlas.py --prune           # + artık üretilmeyen bölüm dosyalarını arşivle
    python fetch_yokatlas.py --metadata-only   # metadata.json'u mevcut dosyalardan üret

Çıktı: universite_json/bolum_*.json + universite_json/metadata.json
"""

import httpx
import json
import os
import time
import sys
import re
import glob
import shutil
import argparse
from datetime import datetime, timezone

# ─── Config ────────────────────────────────────────────────────────────────
BASE_URL = "https://yokatlas.yok.gov.tr"
SEARCH_PATH = "/api/tercih-kilavuz/search"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "universite_json")
ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), "archive")
PAGE_SIZE = 500  # Max programs per page request
RATE_LIMIT_DELAY = 0.3  # Seconds between pagination requests

# Kılavuz yılı: her yeni tercih döneminde burayı güncelle.
GUIDE_YEAR = "2026"
YEARS = [str(int(GUIDE_YEAR) - offset) for offset in range(4)]

HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json",
    "User-Agent": "kariyer-pusulasi/1.0",
}

# Categories to fetch: (puan_turu, birim_turu_id, label)
CATEGORIES = [
    ("SAY", 46, "SAY/Lisans"),
    ("EA", 46, "EA/Lisans"),
    ("SÖZ", 46, "SÖZ/Lisans"),
    ("DİL", 46, "DİL/Lisans"),
    ("TYT", 47, "TYT/Önlisans"),
]

# Turkish character mapping for filename normalization
TURKISH_CHARS = str.maketrans({
    'ç': 'c', 'Ç': 'C', 'ğ': 'g', 'Ğ': 'G', 'ı': 'i', 'İ': 'I',
    'ö': 'o', 'Ö': 'O', 'ş': 's', 'Ş': 'S', 'ü': 'u', 'Ü': 'U',
})


# ─── Helpers ──────────────────────────────────────────────────────────────

def normalize_filename(text: str) -> str:
    """Convert department name to filename-safe format (matching JS version)."""
    text = text.translate(TURKISH_CHARS)
    text = re.sub(r'[().]', '', text)
    text = text.strip().replace(' ', '_')
    text = text.rstrip('_')
    return text


def build_search_body(puan_turu, birim_turu_id, page=0, size=PAGE_SIZE):
    """Build the POST body for the search API."""
    filters = {}
    if puan_turu:
        filters["puanTuru"] = puan_turu
    if birim_turu_id:
        filters["birimTuruId"] = birim_turu_id
    return {
        "filters": filters,
        "page": page,
        "size": size,
        "sortBy": "basariSirasi",
        "direction": "ASC",
    }


def fetch_category(client, puan_turu, birim_turu_id, label):
    """Fetch ALL programs for one category with pagination."""
    all_programs = []
    page = 0
    retries = 3

    while True:
        body = build_search_body(puan_turu, birim_turu_id, page=page)
        for attempt in range(retries):
            try:
                resp = client.post(
                    f"{BASE_URL}{SEARCH_PATH}",
                    json=body,
                    headers=HEADERS,
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                break
            except Exception as e:
                if attempt < retries - 1:
                    wait = 2 ** attempt
                    print(f"    Retry {attempt + 1}/{retries} after {wait}s: {e}")
                    time.sleep(wait)
                else:
                    print(f"    FAILED after {retries} retries: {e}")
                    return all_programs, False

        content = data.get("content", [])
        total = data.get("totalElements", 0)

        all_programs.extend(content)
        fetched = len(all_programs)

        print(f"  Page {page}: +{len(content)} = {fetched}/{total}  [{label}]")

        # Stop if we got fewer results than requested (last page)
        if len(content) < PAGE_SIZE or fetched >= total:
            break

        page += 1
        time.sleep(RATE_LIMIT_DELAY)

    return all_programs, True


def burs_to_ucret(burs_orani_adi, universite_turu):
    """Map burs type to the Ücret field used in existing format."""
    if not burs_orani_adi:
        return "Ücretsiz"
    # Vakıf universities
    bursa = burs_orani_adi.strip()
    # Map specific values
    mapping = {
        "Burslu": "Burslu",
        "%50 İndirimli": "%50 İndirimli",
        "%25 İndirimli": "%25 İndirimli",
        "Ücretli": "Ücretli",
        "Ücretsiz": "Ücretsiz",
    }
    return mapping.get(bursa, bursa)


def convert_program(p):
    """Convert a raw API program entry to the existing JSON format."""
    # Historical kontenjan: kontenjan=GUIDE_YEAR, gk1=GUIDE_YEAR-1, gk2=-2, gk3=-3
    kontenjan_values = [
        str(p.get("kontenjan") or ""),
        str(p.get("gk1") or ""),
        str(p.get("gk2") or ""),
        str(p.get("gk3") or ""),
    ]

    # Puan values — API returns float or string, handle both
    def fmt_puan(val):
        if val is None or val == "" or val == 0:
            return ""
        try:
            v = float(val)
            if v == 0:
                return ""
            return f"{v:.3f}"
        except (ValueError, TypeError):
            return str(val)

    puan_values = [
        fmt_puan(p.get("minPuan")),
        fmt_puan(p.get("minPuan1")),
        fmt_puan(p.get("minPuan2")),
        fmt_puan(p.get("minPuan3")),
    ]

    # Siralama values - format with comma as thousands separator like existing data
    def format_siralama(val):
        if val is None:
            return ""
        try:
            return f"{int(val):,}".replace(",", ".")
        except (ValueError, TypeError):
            return str(val)

    siralama_values = [
        format_siralama(p.get("basariSirasi")),
        format_siralama(p.get("basariSirasi1")),
        format_siralama(p.get("basariSirasi2")),
        format_siralama(p.get("basariSirasi3")),
    ]

    # Ücret mapping
    ucret = burs_to_ucret(p.get("bursOraniAdi"), p.get("universiteTuru"))

    # Program adı - use birimAdi (full name) fallback to birimGrupAdi
    program_adi = p.get("birimAdi") or p.get("birimGrupAdi") or ""

    return {
        "Program Kodu": str(p.get("kilavuzKodu") or ""),
        "Üniversite": (p.get("universiteAdi") or "").strip(),
        "Fakülte": (p.get("fymkAdi") or "").strip(),
        "Üniversite Türü": "Devlet" if (p.get("universiteTuru") or "").strip().upper() == "DEVLET" else "Vakıf",
        "Program Adı": program_adi.strip(),
        "Öğretim Türü": (p.get("ogrenimTuruAdi") or "").strip(),
        "Yıl": list(YEARS),
        "Kontenjan": kontenjan_values,
        "Yerleşen": [""] * 4,  # Not available from search API
        "Taban Sıralama": siralama_values,
        "Taban Puan": puan_values,
        "Şehir": (p.get("uniIlAdi") or "").strip(),
        "Ücret": ucret,
        "Puan Türü": (p.get("puanTuru") or "").strip().upper(),
    }


# ─── Maintenance helpers ──────────────────────────────────────────────────

def check_api(client):
    """Fetch a single page and validate the API shape. Writes nothing."""
    body = build_search_body("SAY", 46, page=0, size=5)
    resp = client.post(f"{BASE_URL}{SEARCH_PATH}", json=body, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    content = data.get("content", [])
    print(f"API OK — totalElements={data.get('totalElements')} · örnek kayıt={len(content)}")
    if content:
        fields = ("universiteAdi", "birimGrupAdi", "birimAdi", "puanTuru", "basariSirasi", "kontenjan", "gk1")
        print("Örnek:", json.dumps({k: content[0].get(k) for k in fields}, ensure_ascii=False))
        missing = [k for k in fields if k not in content[0]]
        print("Eksik alan:", missing or "yok")
    return True


def prune_stale_files(written_names):
    """Move department files that were not produced by this run into archive/."""
    stale = [
        os.path.basename(path)
        for path in glob.glob(os.path.join(OUTPUT_DIR, "bolum_*.json"))
        if os.path.basename(path) not in written_names
    ]
    if not stale:
        print("  Prune: eski dosya yok.")
        return 0

    target = os.path.join(ARCHIVE_DIR, f"stale_{datetime.now():%Y%m%d_%H%M%S}")
    os.makedirs(target, exist_ok=True)
    for name in stale:
        shutil.move(os.path.join(OUTPUT_DIR, name), os.path.join(target, name))
    print(f"  Prune: {len(stale)} dosya -> {target}")
    return len(stale)


def write_metadata(department_files, total_programs, fetched_at=None):
    """Write universite_json/metadata.json so the UI can show data freshness."""
    meta = {
        "guide_year": GUIDE_YEAR,
        "fetched_at": fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total_programs": total_programs,
        "department_files": department_files,
        "categories": [label for _, _, label in CATEGORIES],
    }
    with open(os.path.join(OUTPUT_DIR, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  metadata.json yazıldı: {meta['total_programs']} program / {meta['department_files']} bölüm")
    return meta


def rebuild_metadata():
    """Recompute metadata.json from the existing department files (no network)."""
    paths = sorted(glob.glob(os.path.join(OUTPUT_DIR, "bolum_*.json")))
    if not paths:
        print("HATA: universite_json/ altında bolum_*.json yok.")
        return None
    total = 0
    for path in paths:
        with open(path, "r", encoding="utf-8") as f:
            total += len(json.load(f).get("yks", []))
    fetched_at = datetime.fromtimestamp(max(os.path.getmtime(p) for p in paths), timezone.utc)
    return write_metadata(len(paths), total, fetched_at.isoformat(timespec="seconds"))


def parse_args():
    parser = argparse.ArgumentParser(description="YÖK Atlas program verilerini indirir.")
    parser.add_argument("--check", action="store_true", help="API şemasını tek sayfayla doğrular, dosya yazmaz")
    parser.add_argument("--prune", action="store_true", help="Bu turda üretilmeyen bölüm dosyalarını archive/ altına taşır")
    parser.add_argument("--metadata-only", action="store_true", help="Yalnızca metadata.json'u mevcut dosyalardan yeniden üretir")
    return parser.parse_args()


# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    args = parse_args()
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if args.metadata_only:
        rebuild_metadata()
        return

    all_programs = []
    total_fetched = 0
    all_ok = True

    with httpx.Client() as client:
        if args.check:
            check_api(client)
            return

        # Phase 1: Fetch all programs
        print("=" * 60)
        print("Phase 1: Fetching programs from YÖK Atlas API")
        print("=" * 60)

        for puan_turu, birim_turu_id, label in CATEGORIES:
            print(f"\nFetching {label}...")
            progs, ok = fetch_category(client, puan_turu, birim_turu_id, label)
            all_ok = all_ok and ok
            print(f"  → {len(progs)} programs fetched")
            all_programs.extend(progs)
            total_fetched += len(progs)

    print(f"\n{'=' * 60}")
    print(f"Total programs fetched: {total_fetched}")
    print(f"{'=' * 60}")

    if total_fetched == 0:
        print("ERROR: No programs fetched. API may be down or changed.")
        sys.exit(1)

    # Phase 2: Group by department
    print(f"\nPhase 2: Grouping by department...")
    dept_groups = {}  # normalized_name -> list of programs
    dept_name_map = {}  # normalized_name -> display name

    ungrouped = 0
    for p in all_programs:
        dept_name = p.get("birimGrupAdi")
        if not dept_name:
            ungrouped += 1
            continue
        norm_name = normalize_filename(dept_name)
        if norm_name not in dept_groups:
            dept_groups[norm_name] = []
            dept_name_map[norm_name] = dept_name
        dept_groups[norm_name].append(p)

    print(f"  Unique departments: {len(dept_groups)}")
    print(f"  Ungrouped programs: {ungrouped}")

    # Phase 3: Convert and save to files
    print(f"\nPhase 3: Saving department files...")
    saved = 0
    written_names = set()
    for norm_name in sorted(dept_groups.keys()):
        programs = dept_groups[norm_name]

        # Convert all programs for this department
        converted = [convert_program(p) for p in programs]

        file_data = {"yks": converted}
        file_name = f"bolum_{norm_name}.json"
        file_path = os.path.join(OUTPUT_DIR, file_name)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)

        written_names.add(file_name)
        saved += 1
        if saved % 100 == 0:
            print(f"  {saved}/{len(dept_groups)} files saved...")

    print(f"  Total files saved: {saved}")

    # Phase 4: Optional prune of department files that no longer exist
    if args.prune:
        if all_ok:
            prune_stale_files(written_names)
        else:
            print("  Prune ATLANDI: en az bir kategori eksik indi.")

    # Phase 5: Metadata
    write_metadata(saved, total_fetched)

    # Phase 6: Summary
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"  Total API programs fetched: {total_fetched}")
    print(f"  Department files created:   {saved}")
    print(f"  Output directory:           {OUTPUT_DIR}")

    # Count programs per file
    sizes = [(norm_name, len(dept_groups[norm_name])) for norm_name in dept_groups]
    sizes.sort(key=lambda x: -x[1])
    print(f"\n  Top 10 departments by program count:")
    for name, count in sizes[:10]:
        print(f"    {dept_name_map[name]}: {count} programs")

    print(f"\n  Done! 🎯")


if __name__ == "__main__":
    main()
