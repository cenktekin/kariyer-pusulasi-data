#!/usr/bin/env python3
"""
analyze_ui.py — YÖK Atlas verisi için yerel analiz arayüzü.

HTTP handler + CLI. Arayüz dosyaları static/ altındadır:
    static/index.html · static/app.js · static/style.css

Kullanım:
    python analyze_ui.py [--port 8005]
"""

import argparse
import http.server
import json
import os
import socketserver
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "universite_json")
STATIC_DIR = os.path.join(BASE_DIR, "static")
DEFAULT_PORT = 8005

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}

TURKISH_UPPER = str.maketrans({
    "i": "İ", "ı": "I", "ş": "Ş", "ğ": "Ğ", "ç": "Ç", "ö": "Ö", "ü": "Ü",
})


# ─── Veri yardımcıları ────────────────────────────────────────────────────

def list_department_files():
    """universite_json/ altındaki bölüm dosyalarının adlarını döndürür."""
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(
        name for name in os.listdir(DATA_DIR)
        if name.startswith("bolum_") and name.endswith(".json")
    )


def read_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def get_departments():
    return [
        {"id": name, "name": name[6:-5].replace("_", " ")}
        for name in list_department_files()
    ]


def get_all_cities():
    """Bölüm dosyalarındaki şehirleri Türkçe büyük harfe çevirip tekilleştirir."""
    cities = set()
    for name in list_department_files():
        try:
            data = read_json(os.path.join(DATA_DIR, name))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Sehir listesi okunamadi ({name}): {exc}")
            continue
        for item in data.get("yks", []):
            city = (item.get("Şehir") or "").strip()
            if city:
                cities.add(city)

    unique = {}
    for city in cities:
        unique.setdefault(city.translate(TURKISH_UPPER).upper(), None)
    return sorted(unique)


# ─── HTTP handler ─────────────────────────────────────────────────────────

class YokAtlasHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/departments":
            self.send_json(get_departments())
        elif path == "/api/cities":
            self.send_json(get_all_cities())
        elif path == "/api/metadata":
            self.send_metadata()
        elif path.startswith("/api/department/"):
            self.send_department(path[len("/api/department/"):])
        elif path in STATIC_FILES:
            self.send_static(*STATIC_FILES[path])
        else:
            self.send_error(404, "Not found")

    def send_body(self, body, content_type):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, data):
        self.send_body(
            json.dumps(data, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def send_metadata(self):
        path = os.path.join(DATA_DIR, "metadata.json")
        if not os.path.exists(path):
            self.send_json({})
            return
        try:
            self.send_json(read_json(path))
        except (OSError, json.JSONDecodeError) as exc:
            self.send_error(500, f"Error reading metadata: {exc}")

    def send_department(self, filename):
        if "/" in filename or "\\" in filename or ".." in filename or not filename.endswith(".json"):
            self.send_error(400, "Invalid filename")
            return
        path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(path):
            self.send_error(404, "Department not found")
            return
        try:
            self.send_json(read_json(path))
        except (OSError, json.JSONDecodeError) as exc:
            self.send_error(500, f"Error reading file: {exc}")

    def send_static(self, name, content_type):
        try:
            with open(os.path.join(STATIC_DIR, name), "rb") as handle:
                self.send_body(handle.read(), content_type)
        except OSError as exc:
            self.send_error(500, f"Static file error: {exc}")


# ─── CLI ──────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="YÖK Atlas yerel analiz arayüzünü başlatır.")
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Dinlenecek port (varsayılan {DEFAULT_PORT})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", args.port), YokAtlasHandler) as httpd:
        print("YÖK Atlas Karargahı başlatıldı!")
        print(f"-> Arayüze erişmek için tarayıcınızdan açın: http://127.0.0.1:{args.port}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer durduruldu.")


if __name__ == "__main__":
    main()
