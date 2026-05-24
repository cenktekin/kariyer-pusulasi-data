#!/usr/bin/env python3
"""
fetch_yokatlas.py — YÖK Atlas API'den tüm üniversite program verilerini çeker,
mevcut JSON formatında department bazlı dosyalara kaydeder.

Kullanım:
    source /tmp/yokatlas-venv/bin/activate
    python3 fetch_yokatlas.py

Çıktı: universite_json/bolum_*.json
"""

import httpx
import json
import os
import time
import sys
import re

# ─── Config ────────────────────────────────────────────────────────────────
BASE_URL = "https://yokatlas.yok.gov.tr"
SEARCH_PATH = "/api/tercih-kilavuz/search"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "universite_json")
PAGE_SIZE = 500  # Max programs per page request
RATE_LIMIT_DELAY = 0.3  # Seconds between pagination requests

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
                    return all_programs

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

    return all_programs


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
    # Year data mapping
    years = ["2025", "2024", "2023", "2022"]
    
    # Historical kontenjan: gk1=2024, gk2=2023, gk3=2022
    kontenjan_values = [
        str(p.get("kontenjan") or ""),       # 2025
        str(p.get("gk1") or ""),              # 2024
        str(p.get("gk2") or ""),              # 2023
        str(p.get("gk3") or ""),              # 2022
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
        "Yıl": years,
        "Kontenjan": kontenjan_values,
        "Yerleşen": [""] * 4,  # Not available from search API
        "Taban Sıralama": siralama_values,
        "Taban Puan": puan_values,
        "Şehir": (p.get("uniIlAdi") or "").strip(),
        "Ücret": ucret,
    }


# ─── Main ─────────────────────────────────────────────────────────────────

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    client = httpx.Client()
    all_programs = []
    total_fetched = 0

    # Phase 1: Fetch all programs
    print("=" * 60)
    print("Phase 1: Fetching programs from YÖK Atlas API")
    print("=" * 60)

    for puan_turu, birim_turu_id, label in CATEGORIES:
        print(f"\nFetching {label}...")
        progs = fetch_category(client, puan_turu, birim_turu_id, label)
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
    for norm_name in sorted(dept_groups.keys()):
        display_name = dept_name_map[norm_name]
        programs = dept_groups[norm_name]

        # Convert all programs for this department
        converted = [convert_program(p) for p in programs]

        file_data = {"yks": converted}
        file_path = os.path.join(OUTPUT_DIR, f"bolum_{norm_name}.json")

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(file_data, f, ensure_ascii=False, indent=2)

        saved += 1
        if saved % 100 == 0:
            print(f"  {saved}/{len(dept_groups)} files saved...")

    print(f"  Total files saved: {saved}")

    # Phase 4: Summary
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
