#!/usr/bin/env python3
import os
import json
import http.server
import socketserver
import urllib.parse

PORT = 8005
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "universite_json")

class YokAtlasHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        path = parsed_url.path
        
        if path == "/api/departments":
            self.send_json(self.get_departments())
            return

        elif path == "/api/cities":
            self.send_json(self.get_all_cities())
            return

        elif path == "/api/metadata":
            metadata_path = os.path.join(DATA_DIR, "metadata.json")
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r", encoding="utf-8") as f:
                        self.send_json(json.load(f))
                except Exception as e:
                    self.send_error(500, f"Error reading metadata: {str(e)}")
            else:
                self.send_json({})
            return
            
        elif path.startswith("/api/department/"):
            filename = path.replace("/api/department/", "")
            if "/" in filename or ".." in filename or not filename.endswith(".json"):
                self.send_error(400, "Invalid filename")
                return
            
            filepath = os.path.join(DATA_DIR, filename)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self.send_json(data)
                except Exception as e:
                    self.send_error(500, f"Error reading file: {str(e)}")
            else:
                self.send_error(404, "Department not found")
            return
            
        elif path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(self.get_html_content().encode("utf-8"))
            return
            
        self.send_error(404, "Not found")

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def get_departments(self):
        departments = []
        if os.path.exists(DATA_DIR):
            for f in sorted(os.listdir(DATA_DIR)):
                if f.startswith("bolum_") and f.endswith(".json"):
                    name = f[6:-5].replace("_", " ")
                    departments.append({"id": f, "name": name})
        return departments

    def get_all_cities(self):
        cities = set()
        if os.path.exists(DATA_DIR):
            for f in os.listdir(DATA_DIR):
                if f.startswith("bolum_") and f.endswith(".json"):
                    try:
                        with open(os.path.join(DATA_DIR, f), "r", encoding="utf-8") as file:
                            data = json.load(file)
                            for item in data.get("yks", []):
                                city = item.get("Şehir")
                                if city:
                                    cities.add(city.strip())
                    except (OSError, json.JSONDecodeError) as exc:
                        print(f"Sehir listesi okunamadi ({f}): {exc}")
        
        # Custom Turkish upper mapping to properly deduplicate
        def turkish_upper(s):
            translation_table = str.maketrans({
                'i': 'İ',
                'ı': 'I',
                'ş': 'Ş',
                'ğ': 'Ğ',
                'ç': 'Ç',
                'ö': 'Ö',
                'ü': 'Ü'
            })
            return s.translate(translation_table).upper()

        unique_cities = {}
        for city in cities:
            key = turkish_upper(city)
            if key not in unique_cities:
                unique_cities[key] = key
        
        return sorted(list(unique_cities.keys()))

    def get_html_content(self):
        return """<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YÖK Atlas Hızlı Analiz & Filtreleme</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0b0f19;
            --bg-secondary: #161e31;
            --bg-tertiary: #1f2b48;
            --accent: #2563eb;
            --accent-hover: #3b82f6;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border: #2e3d60;
            --success: #10b981;
            --warning: #f59e0b;
            --danger: #ef4444;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-primary);
            color: var(--text-primary);
            line-height: 1.5;
            padding: 2rem;
            min-height: 100vh;
        }

        .container {
            max-width: 1750px;
            margin: 0 auto;
        }

        header {
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border);
            padding-bottom: 1.5rem;
        }

        h1 {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(to right, #60a5fa, #2563eb);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .stats-badge {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            font-size: 0.9rem;
            color: var(--text-secondary);
        }

        .stats-badge strong {
            color: var(--text-primary);
        }

        .workspace {
            display: grid;
            grid-template-columns: 300px 320px 1fr;
            gap: 1.5rem;
            align-items: start;
        }

        .panel {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 1.5rem;
            height: fit-content;
        }
        
        .sticky-panel {
            position: sticky;
            top: 2rem;
        }

        .panel-title {
            font-size: 1rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 1rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            border-bottom: 1px solid rgba(46, 61, 96, 0.4);
            padding-bottom: 0.5rem;
        }

        .search-box {
            position: relative;
            margin-bottom: 1rem;
        }

        .input-field {
            width: 100%;
            background: var(--bg-primary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.75rem 1rem;
            border-radius: 8px;
            font-family: inherit;
            font-size: 0.95rem;
            transition: all 0.2s ease;
        }

        .input-field:focus {
            outline: none;
            border-color: var(--accent);
            box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.2);
        }

        .dep-list {
            max-height: 550px;
            overflow-y: auto;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: var(--bg-primary);
        }

        .dep-item {
            padding: 0.65rem 1rem;
            cursor: pointer;
            font-size: 0.9rem;
            transition: all 0.15s ease;
            border-bottom: 1px solid rgba(46, 61, 96, 0.3);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .dep-item:hover {
            background-color: var(--bg-tertiary);
            color: var(--accent-hover);
        }

        .dep-item.active {
            background-color: var(--accent);
            color: var(--text-primary);
        }

        .dep-item-match {
            border-left: 4px solid var(--success);
        }
        
        .dep-item-no-match {
            display: none !important;
        }

        .filter-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .filter-label {
            font-size: 0.85rem; 
            color: var(--text-secondary);
            margin-top: 0.5rem;
            font-weight: 500;
        }
        
        .filter-label:first-child {
            margin-top: 0;
        }

        select.input-field {
            cursor: pointer;
            appearance: none;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 24 24' stroke='%2394a3b8'%3E%3Cpath stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='M19 9l-7 7-7-7'/%3E%3C/svg%3E");
            background-repeat: no-repeat;
            background-position: right 1rem center;
            background-size: 1.2rem;
            padding-right: 2.5rem;
        }

        .btn-export {
            background: linear-gradient(to right, #10b981, #059669);
            color: white;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            font-family: inherit;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s;
            margin-left: 1rem;
            box-shadow: 0 4px 6px -1px rgba(16, 185, 129, 0.2);
        }

        .btn-export:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }

        .btn-export:active {
            transform: translateY(0);
        }

        .btn-clear {
            background: linear-gradient(to right, #ef4444, #dc2626);
            color: white;
            border: none;
            padding: 0.6rem 1.2rem;
            border-radius: 8px;
            font-family: inherit;
            font-weight: 600;
            font-size: 0.9rem;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            transition: all 0.2s;
            margin-left: 1rem;
            box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.2);
        }

        .btn-clear:hover {
            opacity: 0.9;
            transform: translateY(-1px);
        }

        .btn-clear:active {
            transform: translateY(0);
        }

        .main-panel {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
        }

        .active-deps-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            padding: 1rem;
            border-radius: 12px;
            align-items: center;
        }

        .active-deps-label {
            font-size: 0.9rem;
            color: var(--text-secondary);
            margin-right: 0.5rem;
        }

        .tag {
            display: inline-flex;
            align-items: center;
            background: var(--bg-tertiary);
            border: 1px solid var(--border);
            color: var(--text-primary);
            padding: 0.4rem 0.8rem;
            border-radius: 6px;
            font-size: 0.85rem;
            gap: 0.5rem;
            transition: all 0.2s;
        }

        .tag button {
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-weight: bold;
            font-size: 1rem;
            line-height: 1;
        }

        .tag button:hover {
            color: var(--danger);
        }

        .card {
            background: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
        }

        .table-container {
            overflow-x: auto;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            text-align: left;
            font-size: 0.9rem;
        }

        th {
            background-color: rgba(31, 43, 72, 0.6);
            color: var(--text-secondary);
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.75rem;
            letter-spacing: 0.05em;
            padding: 1rem;
            border-bottom: 2px solid var(--border);
            white-space: nowrap;
        }

        td {
            padding: 1rem;
            border-bottom: 1px solid var(--border);
            vertical-align: middle;
            color: var(--text-primary);
        }

        tr:hover td {
            background-color: rgba(31, 43, 72, 0.3);
        }

        .val-code {
            font-family: monospace;
            color: var(--text-secondary);
            font-size: 0.85rem;
        }

        .val-uni {
            font-weight: 600;
            color: var(--text-primary);
        }

        .val-dep {
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 0.25rem;
        }

        .val-puan {
            font-weight: 500;
            color: var(--text-primary);
        }

        .val-sira {
            font-weight: 600;
            color: var(--success);
        }

        .badge-type {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            text-transform: uppercase;
        }

        .type-devlet {
            background-color: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }

        .type-vakif {
            background-color: rgba(245, 158, 11, 0.15);
            color: var(--warning);
            border: 1px solid rgba(245, 158, 11, 0.3);
        }

        .badge-duration {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .duration-4 {
            background-color: rgba(59, 130, 246, 0.15);
            color: #60a5fa;
            border: 1px solid rgba(59, 130, 246, 0.3);
        }

        .duration-2 {
            background-color: rgba(139, 92, 246, 0.15);
            color: #a78bfa;
            border: 1px solid rgba(139, 92, 246, 0.3);
        }

        .badge-score-type {
            display: inline-block;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            background-color: rgba(245, 158, 11, 0.1);
            color: #f59e0b;
            border: 1px solid rgba(245, 158, 11, 0.2);
        }

        .badge-ucret {
            display: inline-block;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            font-size: 0.8rem;
            background-color: var(--bg-tertiary);
            border: 1px solid var(--border);
        }

        .ucret-burslu {
            color: #10b981;
            border-color: rgba(16, 185, 129, 0.3);
        }

        .ucret-50 {
            color: #f59e0b;
            border-color: rgba(245, 158, 11, 0.3);
        }

        .ucret-ucretli {
            color: #ef4444;
            border-color: rgba(239, 68, 68, 0.3);
        }
        
        .trend-container {
            display: flex;
            gap: 0.25rem;
            align-items: center;
        }

        .trend-indicator {
            display: inline-flex;
            align-items: center;
            font-size: 0.8rem;
            font-weight: 500;
            padding: 0.1rem 0.3rem;
            border-radius: 4px;
            margin-top: 0.25rem;
        }
        
        .trend-up {
            background-color: rgba(239, 68, 68, 0.1);
            color: #f87171;
        }
        
        .trend-down {
            background-color: rgba(16, 185, 129, 0.1);
            color: #34d399;
        }

        ::-webkit-scrollbar {
            width: 8px;
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: var(--bg-primary);
        }
        ::-webkit-scrollbar-thumb {
            background: var(--border);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: var(--text-secondary);
        }

        .no-data {
            padding: 3rem;
            text-align: center;
            color: var(--text-secondary);
            font-size: 1.1rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>YÖK Atlas Analiz Karargahı</h1>
                <p style="color: var(--text-secondary); margin-top: 0.25rem;">Seçtiğiniz tüm bölümleri tek tabloda karşılaştırın, filtreleyin ve sıralayın.</p>
            </div>
            <div style="display: flex; align-items: center;">
                <div class="stats-badge">
                    Sistemdeki Toplam Bölüm: <strong id="total-departments-count">Yükleniyor...</strong>
                </div>
                <div class="stats-badge" style="margin-left: 0.75rem;" id="data-freshness-badge" title="Veri setinin çekildiği tarih">
                    Veri: <strong id="data-freshness">—</strong>
                </div>
                <button class="btn-clear" onclick="clearAllFiltersAndSelection()">
                    <svg style="width: 1.2rem; height: 1.2rem;" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                    Tümünü Temizle
                </button>
                <button class="btn-export" onclick="exportToMarkdown()">
                    <svg style="width: 1.2rem; height: 1.2rem;" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin='round' stroke-width='2' d='M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4'></path></svg>
                    Markdown İndir
                </button>
            </div>
        </header>

        <div class="workspace">
            <!-- Column 1: Filters -->
            <aside class="panel sticky-panel">
                <div class="panel-title">1. Filtreler</div>
                <div class="filter-group">
                    <label class="filter-label">Puan Türü</label>
                    <select id="filter-puan-turu" class="input-field">
                        <option value="all">Tümü (SAY, EA, SÖZ, DİL, TYT)</option>
                        <option value="SAY">SAY (Sayısal)</option>
                        <option value="EA">EA (Eşit Ağırlık)</option>
                        <option value="SÖZ">SÖZ (Sözel)</option>
                        <option value="DİL">DİL (Yabancı Dil)</option>
                        <option value="TYT">TYT (Önlisans)</option>
                    </select>

                    <label class="filter-label">Öğrenim Süresi</label>
                    <select id="filter-duration" class="input-field">
                        <option value="all">Tümü (Lisans + Önlisans)</option>
                        <option value="4">4 Yıllık (Lisans)</option>
                        <option value="2">2 Yıllık (Önlisans)</option>
                    </select>

                    <label class="filter-label">Üniversite Türü</label>
                    <select id="filter-type" class="input-field">
                        <option value="all">Tümü (Devlet + Vakıf)</option>
                        <option value="Devlet">Sadece Devlet</option>
                        <option value="Vakıf">Sadece Vakıf</option>
                    </select>

                    <label class="filter-label">Şehir</label>
                    <select id="filter-city" class="input-field">
                        <option value="all">Tüm Şehirler</option>
                    </select>

                    <label class="filter-label">Ücret/Burs Türü</label>
                    <select id="filter-ucret" class="input-field">
                        <option value="all">Tümü</option>
                        <option value="Burslu">Burslu</option>
                        <option value="%50 İndirimli">%50 İndirimli</option>
                        <option value="Ücretli">Ücretli / İndirimsiz</option>
                        <option value="Ücretsiz">Ücretsiz</option>
                    </select>

                    <label class="filter-label">Öğrencinin Başarı Sırası (taban sırası daha geride olan bölümler listelenir)</label>
                    <input type="number" id="filter-sira-max" class="input-field" placeholder="Örn: 100000">

                    <label class="filter-label">Öğrencinin Puanı (taban puanı daha düşük bölümler listelenir)</label>
                    <input type="number" id="filter-puan-min" class="input-field" placeholder="Örn: 400" step="0.1">

                    <label class="filter-label">Üniversite Filtresi</label>
                    <input type="text" id="search-uni" class="input-field" placeholder="Üniversite adı ara...">
                </div>
            </aside>

            <!-- Column 2: Department Selection List -->
            <aside class="panel sticky-panel">
                <div class="panel-title" style="display: flex; justify-content: space-between; align-items: center;">
                    <span>2. Bölümler</span>
                    <span id="filtered-ratio-badge" style="font-size: 0.8rem; background-color: var(--accent); color: white; padding: 0.1rem 0.5rem; border-radius: 20px;">0 / 0</span>
                </div>
                <div class="search-box">
                    <input type="text" id="search-dep" class="input-field" placeholder="Bölüm adı ara...">
                </div>
                <div class="dep-list" id="dep-list-container">
                </div>
            </aside>

            <!-- Column 3: Results Dashboard Table -->
            <main class="main-panel">
                <div class="active-deps-bar" id="active-deps-bar">
                    <span class="active-deps-label">Karşılaştırılan Bölümler:</span>
                    <span style="color: var(--text-secondary); font-size: 0.9rem;" id="no-selected-hint">Henüz bölüm seçilmedi. Soldan aratıp ekleyebilirsiniz.</span>
                </div>

                <div class="card">
                    <div class="table-container">
                        <table id="results-table">
                            <thead>
                                <tr>
                                    <th>Kod</th>
                                    <th>Üniversite / Bölüm</th>
                                    <th>Tür</th>
                                    <th>Süre</th>
                                    <th>Türü</th>
                                    <th>Şehir</th>
                                    <th>Burs/Ücret</th>
                                    <th>Kontenjan (26/25/24)</th>
                                    <th style="cursor: pointer;" onclick="changeSort('basari')">Başarı Sırası (2026) ↕</th>
                                    <th style="cursor: pointer;" onclick="changeSort('puan')">Taban Puan (2026) ↕</th>
                                </tr>
                            </thead>
                            <tbody id="table-body">
                                <tr>
                                    <td colspan="10" class="no-data">Analiz etmek istediğiniz bölümleri seçerek ekleyin. Aynı anda dilediğiniz kadar bölüm ekleyebilirsiniz!</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </main>
        </div>
    </div>

    <script>
        let allDepartments = [];
        let selectedDepartments = [];
        let programData = {};
        const SELECTION_STORAGE_KEY = 'yokatlas_selected_departments';
        let sortBy = 'basari';
        let sortDirection = 'ASC';
        let filteredRowsGlobal = [];

        const depSearch = document.getElementById('search-dep');
        const depListContainer = document.getElementById('dep-list-container');
        const activeDepsBar = document.getElementById('active-deps-bar');
        const tableBody = document.getElementById('table-body');
        const totalDepsCount = document.getElementById('total-departments-count');
        const filterPuanTuru = document.getElementById('filter-puan-turu');
        const filterDuration = document.getElementById('filter-duration');
        const filterType = document.getElementById('filter-type');
        const filterCity = document.getElementById('filter-city');
        const filterUcret = document.getElementById('filter-ucret');
        const filterSiraMax = document.getElementById('filter-sira-max');
        const filterPuanMin = document.getElementById('filter-puan-min');
        const searchUni = document.getElementById('search-uni');
        const noSelectedHint = document.getElementById('no-selected-hint');
        const filteredRatioBadge = document.getElementById('filtered-ratio-badge');
        const dataFreshness = document.getElementById('data-freshness');

        function esc(value) {
            return String(value == null ? '' : value)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        function saveSelection() {
            try {
                localStorage.setItem(SELECTION_STORAGE_KEY, JSON.stringify(selectedDepartments));
            } catch (err) {
                console.error('Secim kaydedilemedi:', err);
            }
        }

        function readSavedSelection() {
            try {
                const raw = localStorage.getItem(SELECTION_STORAGE_KEY);
                const parsed = raw ? JSON.parse(raw) : [];
                return Array.isArray(parsed) ? parsed : [];
            } catch (err) {
                console.error('Kayitli secim okunamadi:', err);
                return [];
            }
        }

        async function restoreSelection() {
            const saved = readSavedSelection().filter(id => allDepartments.some(d => d.id === id));
            if (saved.length === 0) return;
            selectedDepartments = saved;
            await Promise.all(saved.map(id => programData[id] ? null : fetchDepartmentData(id)));
            renderDepartmentList(depSearch.value);
            renderActiveTags();
            renderTable();
        }

        async function loadMetadata() {
            try {
                const response = await fetch('/api/metadata');
                const meta = await response.json();
                if (meta && meta.fetched_at) {
                    const d = new Date(meta.fetched_at);
                    dataFreshness.innerText = d.toLocaleDateString('tr-TR');
                    dataFreshness.parentElement.title =
                        `Kılavuz yılı: ${meta.guide_year || '-'} · ${meta.department_files || '-'} bölüm · ` +
                        `${(meta.total_programs || 0).toLocaleString('tr-TR')} program`;
                }
            } catch (err) {
                console.error('Veri meta bilgisi alinamadi:', err);
            }
        }

        window.addEventListener('DOMContentLoaded', async () => {
            await loadMetadata();
            await loadDepartments();
            await loadAllCities();
            await restoreSelection();
            setupEventListeners();
        });

        function getProgramDuration(facultyName) {
            const fac = facultyName.toLowerCase();
            if (fac.includes('meslek yüksek') || fac.includes('myo') || fac.endsWith('myo')) {
                return '2';
            }
            return '4';
        }

        async function loadDepartments() {
            try {
                const response = await fetch('/api/departments');
                allDepartments = await response.json();
                totalDepsCount.innerText = allDepartments.length;
                preloadAllDepartmentData();
            } catch (err) {
                console.error("Bölümler yüklenirken hata oluştu:", err);
                totalDepsCount.innerText = "Hata";
            }
        }

        async function preloadAllDepartmentData() {
            const chunk = 35;
            for (let i = 0; i < allDepartments.length; i += chunk) {
                const slice = allDepartments.slice(i, i + chunk);
                await Promise.all(slice.map(async (dep) => {
                    try {
                        const r = await fetch(`/api/department/${dep.id}`);
                        const res = await r.json();
                        programData[dep.id] = res.yks || [];
                    } catch(e) {
                        console.error(`Bolum verisi onden yuklenemedi (${dep.id}):`, e);
                    }
                }));
                renderDepartmentList(depSearch.value);
            }
        }

        // Helper to format Turkish character city names properly to uppercase
        function formatCityName(city) {
            if (!city) return '';
            // Standardize to uppercase with correct Turkish locale casing
            return city.trim().toLocaleUpperCase('tr-TR');
        }

        async function loadAllCities() {
            try {
                const response = await fetch('/api/cities');
                const rawCities = await response.json();
                
                // Deduplicate Turkish casing edge cases (like KOCAELİ vs Kocaeli or AFYON vs AFYONKARAHİSAR)
                const dedupedCities = new Set();
                rawCities.forEach(c => {
                    const formatted = formatCityName(c);
                    if (formatted) dedupedCities.add(formatted);
                });

                filterCity.innerHTML = '<option value="all">Tüm Şehirler</option>';
                Array.from(dedupedCities).sort((a,b) => a.localeCompare(b, 'tr')).forEach(city => {
                    const opt = document.createElement('option');
                    opt.value = city;
                    opt.innerText = city;
                    filterCity.appendChild(opt);
                });
            } catch (err) {
                console.error("Şehirler yüklenirken hata oluştu:", err);
            }
        }

        function getNormalizedText(txt) {
            return txt.toLocaleLowerCase('tr-TR');
        }

        function parseSiralamaVal(val) {
            if (!val || val === '-' || val === '') return Infinity;
            return parseInt(val.replace(/\\./g, ''), 10);
        }

        function renderDepartmentList(filter = '') {
            depListContainer.innerHTML = '';
            
            const filteredByName = allDepartments.filter(d => 
                getNormalizedText(d.name).includes(getNormalizedText(filter))
            );

            const puanTuruVal = filterPuanTuru.value;
            const durationVal = filterDuration.value;
            const typeVal = filterType.value;
            const cityVal = filterCity.value;
            const ucretVal = filterUcret.value;
            const siraMaxVal = filterSiraMax.value ? parseInt(filterSiraMax.value, 10) : null;
            const puanMinVal = filterPuanMin.value ? parseFloat(filterPuanMin.value) : null;
            const uniSearchVal = getNormalizedText(searchUni.value);

            const isAnyFilterActive = (puanTuruVal !== 'all' || durationVal !== 'all' || typeVal !== 'all' || cityVal !== 'all' || ucretVal !== 'all' || siraMaxVal !== null || puanMinVal !== null || uniSearchVal !== '');

            let matchingCount = 0;

            filteredByName.forEach(dep => {
                const isSelected = selectedDepartments.includes(dep.id);
                
                let matchesFilters = true;
                const list = programData[dep.id];
                
                if (isAnyFilterActive) {
                    if (list) {
                        const hasMatchingProgram = list.some(item => {
                            if (puanTuruVal !== 'all' && item['Puan Türü'] !== puanTuruVal) return false;

                            const duration = getProgramDuration(item['Fakülte']);
                            if (durationVal !== 'all' && duration !== durationVal) return false;
                            if (typeVal !== 'all' && item['Üniversite Türü'] !== typeVal) return false;
                            
                            // Handle city check case-insensitively with Turkish characters normalization
                            if (cityVal !== 'all' && formatCityName(item['Şehir']) !== cityVal) return false;
                            
                            if (ucretVal !== 'all') {
                                if (ucretVal === 'Ücretli') {
                                    if (!(item['Ücret'] || '').includes('Ücretli')) return false;
                                } else if (item['Ücret'] !== ucretVal) {
                                    return false;
                                }
                            }
                            
                            if (siraMaxVal !== null) {
                                const rawSira = item['Taban Sıralama'] ? item['Taban Sıralama'][0] : '';
                                const siraNumeric = parseSiralamaVal(rawSira);
                                // If department rank is better (smaller number) than child's rank, child cannot enter
                                if (siraNumeric === Infinity || siraNumeric < siraMaxVal) return false;
                            }
                            
                            if (puanMinVal !== null) {
                                const rawPuan = item['Taban Puan'] ? item['Taban Puan'][0] : '';
                                const puanNumeric = rawPuan ? parseFloat(rawPuan) : 0;
                                // If department points requirement is higher than child's points, child cannot enter
                                if (puanNumeric > puanMinVal) return false;
                            }

                            if (uniSearchVal) {
                                const uniName = getNormalizedText(item['Üniversite']);
                                const progName = getNormalizedText(item['Program Adı']);
                                if (!uniName.includes(uniSearchVal) && !progName.includes(uniSearchVal)) return false;
                            }
                            return true;
                        });
                        matchesFilters = hasMatchingProgram;
                    } else {
                        matchesFilters = false; 
                    }
                }

                const el = document.createElement('div');
                el.className = `dep-item ${isSelected ? 'active' : ''} ${matchesFilters ? 'dep-item-match' : 'dep-item-no-match'}`;
                el.innerText = dep.name;
                el.title = dep.name;
                el.onclick = () => toggleDepartment(dep.id, dep.name);
                
                if (matchesFilters) {
                    matchingCount++;
                }
                
                depListContainer.appendChild(el);
            });

            filteredRatioBadge.innerText = `${matchingCount} / ${filteredByName.length}`;
        }

        function setupEventListeners() {
            depSearch.addEventListener('input', (e) => {
                renderDepartmentList(e.target.value);
            });

            const filters = [filterPuanTuru, filterDuration, filterType, filterCity, filterUcret];
            filters.forEach(f => {
                f.addEventListener('change', () => {
                    renderTable();
                    renderDepartmentList(depSearch.value);
                });
            });

            const inputs = [filterSiraMax, filterPuanMin, searchUni];
            inputs.forEach(i => {
                i.addEventListener('input', () => {
                    renderTable();
                    renderDepartmentList(depSearch.value);
                });
            });
        }

        async function toggleDepartment(id, name) {
            if (selectedDepartments.includes(id)) {
                selectedDepartments = selectedDepartments.filter(item => item !== id);
            } else {
                selectedDepartments.push(id);
                if (!programData[id]) {
                    await fetchDepartmentData(id);
                }
            }
            saveSelection();
            renderDepartmentList(depSearch.value);
            renderActiveTags();
            renderTable();
        }

        async function fetchDepartmentData(id) {
            try {
                const response = await fetch(`/api/department/${id}`);
                const data = await response.json();
                programData[id] = data.yks || [];
                renderDepartmentList(depSearch.value);
            } catch (err) {
                console.error(`Bölüm verisi alınamadı (${id}):`, err);
                programData[id] = [];
            }
        }

        function renderActiveTags() {
            const tags = activeDepsBar.querySelectorAll('.tag');
            tags.forEach(t => t.remove());

            if (selectedDepartments.length === 0) {
                noSelectedHint.style.display = 'inline';
                return;
            }
            noSelectedHint.style.display = 'none';

            selectedDepartments.forEach(id => {
                const depObj = allDepartments.find(d => d.id === id);
                if (!depObj) return;

                const tag = document.createElement('span');
                tag.className = 'tag';
                tag.appendChild(document.createTextNode(depObj.name));

                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.innerHTML = '&times;';
                removeBtn.setAttribute('aria-label', `${depObj.name} bölümünü listeden çıkar`);
                removeBtn.addEventListener('click', () => removeTag(id));
                tag.appendChild(removeBtn);

                activeDepsBar.appendChild(tag);
            });
        }

        // REMOVE TAG
        function removeTag(id) {
            selectedDepartments = selectedDepartments.filter(item => item !== id);
            saveSelection();
            renderDepartmentList(depSearch.value);
            renderActiveTags();
            renderTable();
        }

        // CLEAR ALL FILTERS AND SELECTIONS
        function clearAllFiltersAndSelection() {
            selectedDepartments = [];
            saveSelection();
            filterPuanTuru.value = 'all';
            filterDuration.value = 'all';
            filterType.value = 'all';
            filterCity.value = 'all';
            filterUcret.value = 'all';
            filterSiraMax.value = '';
            filterPuanMin.value = '';
            searchUni.value = '';
            depSearch.value = '';
            
            renderDepartmentList();
            renderActiveTags();
            renderTable();
        }

        function changeSort(field) {
            if (sortBy === field) {
                sortDirection = sortDirection === 'ASC' ? 'DESC' : 'ASC';
            } else {
                sortBy = field;
                sortDirection = field === 'basari' ? 'ASC' : 'DESC';
            }
            renderTable();
        }

        function renderTable() {
            tableBody.innerHTML = '';

            if (selectedDepartments.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="10" class="no-data">Analiz etmek istediğiniz bölümleri seçerek ekleyin. Aynı anda dilediğiniz kadar bölüm ekleyebilirsiniz!</td>
                    </tr>`;
                filteredRowsGlobal = [];
                return;
            }

            let rows = [];
            selectedDepartments.forEach(id => {
                const list = programData[id] || [];
                list.forEach(item => {
                    rows.push(item);
                });
            });

            const puanTuruVal = filterPuanTuru.value;
            const durationVal = filterDuration.value;
            const typeVal = filterType.value;
            const cityVal = filterCity.value;
            const ucretVal = filterUcret.value;
            const siraMaxVal = filterSiraMax.value ? parseInt(filterSiraMax.value, 10) : null;
            const puanMinVal = filterPuanMin.value ? parseFloat(filterPuanMin.value) : null;
            const uniSearchVal = getNormalizedText(searchUni.value);

            rows = rows.filter(item => {
                if (puanTuruVal !== 'all' && item['Puan Türü'] !== puanTuruVal) return false;
                const duration = getProgramDuration(item['Fakülte']);
                if (durationVal !== 'all' && duration !== durationVal) return false;
                if (typeVal !== 'all' && item['Üniversite Türü'] !== typeVal) return false;
                if (cityVal !== 'all' && formatCityName(item['Şehir']) !== cityVal) return false;
                if (ucretVal !== 'all') {
                    if (ucretVal === 'Ücretli') {
                        if (!(item['Ücret'] || '').includes('Ücretli')) return false;
                    } else if (item['Ücret'] !== ucretVal) {
                        return false;
                    }
                }
                
                if (siraMaxVal !== null) {
                    const rawSira = item['Taban Sıralama'] ? item['Taban Sıralama'][0] : '';
                    const siraNumeric = parseSiralamaVal(rawSira);
                    // If department rank is better (smaller number) than child's rank, child cannot enter
                    if (siraNumeric === Infinity || siraNumeric < siraMaxVal) return false;
                }
                
                if (puanMinVal !== null) {
                    const rawPuan = item['Taban Puan'] ? item['Taban Puan'][0] : '';
                    const puanNumeric = rawPuan ? parseFloat(rawPuan) : 0;
                    // If department points requirement is higher than child's points, child cannot enter
                    if (puanNumeric > puanMinVal) return false;
                }

                if (uniSearchVal) {
                    const uniName = getNormalizedText(item['Üniversite']);
                    const progName = getNormalizedText(item['Program Adı']);
                    if (!uniName.includes(uniSearchVal) && !progName.includes(uniSearchVal)) return false;
                }
                return true;
            });

            rows.sort((a, b) => {
                let valA, valB;
                
                if (sortBy === 'basari') {
                    const rawA = a['Taban Sıralama'] ? a['Taban Sıralama'][0] : '';
                    const rawB = b['Taban Sıralama'] ? b['Taban Sıralama'][0] : '';
                    
                    valA = parseSiralamaVal(rawA);
                    valB = parseSiralamaVal(rawB);
                } else {
                    const rawA = a['Taban Puan'] ? a['Taban Puan'][0] : '';
                    const rawB = b['Taban Puan'] ? b['Taban Puan'][0] : '';
                    
                    valA = rawA ? parseFloat(rawA) : 0;
                    valB = rawB ? parseFloat(rawB) : 0;
                }

                if (valA === valB) return 0;
                
                if (sortDirection === 'ASC') {
                    return valA > valB ? 1 : -1;
                } else {
                    return valA < valB ? 1 : -1;
                }
            });

            filteredRowsGlobal = rows;

            if (rows.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="10" class="no-data">Seçili filtrelerle eşleşen kayıt bulunamadı.</td>
                    </tr>`;
                return;
            }

            rows.forEach(item => {
                const tr = document.createElement('tr');
                const code = item['Program Kodu'];
                const uni = item['Üniversite'];
                const programName = item['Program Adı'];
                const faculty = item['Fakülte'];
                const type = item['Üniversite Türü'] || 'Devlet';
                const city = item['Şehir'];
                const ucret = item['Ücret'];
                const puanTuru = item['Puan Türü'] || '-';
                const duration = getProgramDuration(faculty);
                
                const k25 = item['Kontenjan'] ? item['Kontenjan'][0] : '-';
                const k24 = item['Kontenjan'] ? item['Kontenjan'][1] : '-';
                const k23 = item['Kontenjan'] ? item['Kontenjan'][2] : '-';

                const s25 = item['Taban Sıralama'] ? item['Taban Sıralama'][0] : '-';
                const s24 = item['Taban Sıralama'] ? item['Taban Sıralama'][1] : '-';
                const s23 = item['Taban Sıralama'] ? item['Taban Sıralama'][2] : '-';

                const p25 = item['Taban Puan'] ? item['Taban Puan'][0] : '-';
                
                let trendHTML = '';
                const parsedS25 = parseSiralamaVal(s25);
                const parsedS24 = parseSiralamaVal(s24);

                if (parsedS25 !== Infinity && parsedS24 !== Infinity) {
                    const diff = parsedS24 - parsedS25;
                    const absoluteDiff = Math.abs(diff).toLocaleString('tr-TR');
                    if (diff > 0) {
                        trendHTML = `<span class="trend-indicator trend-up" title="2025'ten 2026'ya yükseliş trendi. Yerleşmek zorlaşmış.">▲ ${absoluteDiff} Sıra Zorlaşmış</span>`;
                    } else if (diff < 0) {
                        trendHTML = `<span class="trend-indicator trend-down" title="2025'ten 2026'ya düşüş trendi. Yerleşmek kolaylaşmış.">▼ ${absoluteDiff} Sıra Kolaylaşmış</span>`;
                    }
                }

                const typeClass = type === 'Devlet' ? 'type-devlet' : 'type-vakif';
                const durationText = duration === '4' ? '4 Yıllık' : '2 Yıllık';
                const durationClass = duration === '4' ? 'duration-4' : 'duration-2';
                
                let ucretClass = '';
                const ucretText = ucret || '';
                if (ucretText === 'Burslu') ucretClass = 'ucret-burslu';
                else if (ucretText.includes('50')) ucretClass = 'ucret-50';
                else if (ucretText.includes('Ücretli')) ucretClass = 'ucret-ucretli';

                tr.innerHTML = `
                    <td class="val-code">${esc(code)}</td>
                    <td>
                        <div class="val-uni">${esc(uni)}</div>
                        <div class="val-dep">${esc(programName)} <span style="font-size: 0.8rem; color: var(--text-secondary);">(${esc(faculty)})</span></div>
                    </td>
                    <td><span class="badge-score-type">${esc(puanTuru)}</span></td>
                    <td><span class="badge-duration ${durationClass}">${esc(durationText)}</span></td>
                    <td><span class="badge-type ${typeClass}">${esc(type)}</span></td>
                    <td>${esc(city)}</td>
                    <td><span class="badge-ucret ${ucretClass}">${esc(ucret)}</span></td>
                    <td>
                        <span style="font-weight:600; color:var(--text-primary);">${esc(k25)}</span>
                        <span style="font-size:0.8rem; color:var(--text-secondary);"> / ${esc(k24)} / ${esc(k23)}</span>
                    </td>
                    <td>
                        <div class="val-sira">${esc(s25) || 'Dolmadı'}</div>
                        <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:0.15rem;">2025: ${esc(s24) || '-'} | 2024: ${esc(s23) || '-'}</div>
                        ${trendHTML}
                    </td>
                    <td class="val-puan">${esc(p25) || 'Dolmadı'}</td>
                `;
                tableBody.appendChild(tr);
            });
        }

        // EXPORT TO MARKDOWN
        function exportToMarkdown() {
            if (filteredRowsGlobal.length === 0) {
                alert("İndirilecek veri yok! Lütfen önce bölüm seçin ve filtreleyin.");
                return;
            }

            let md = `# YÖK Atlas Tercih Karşılaştırma Raporu\\n\\n`;
            md += `*Bu rapor yerel YÖK Atlas Analiz Karargahı tarafından üretilmiştir.*\\n\\n`;
            
            md += `### Uygulanan Filtreler:\\n`;
            md += `* **Puan Türü:** ${filterPuanTuru.options[filterPuanTuru.selectedIndex].text}\\n`;
            md += `* **Öğrenim Süresi:** ${filterDuration.options[filterDuration.selectedIndex].text}\\n`;
            md += `* **Üniversite Türü:** ${filterType.options[filterType.selectedIndex].text}\\n`;
            md += `* **Şehir:** ${filterCity.options[filterCity.selectedIndex].text}\\n`;
            md += `* **Burs/Ücret:** ${filterUcret.options[filterUcret.selectedIndex].text}\\n`;
            if (filterSiraMax.value) {
                md += `* **Maksimum Sıralama Limiti:** ${filterSiraMax.value}\\n`;
            }
            if (filterPuanMin.value) {
                md += `* **Minimum Taban Puan Limiti:** ${filterPuanMin.value}\\n`;
            }
            if (searchUni.value) {
                md += `* **Üniversite Filtresi:** "${searchUni.value}"\\n`;
            }
            md += `\\n---\\n\\n`;

            md += `| Kod | Üniversite / Bölüm | Tür | Süre | Tür | Şehir | Burs/Ücret | Kont. (26/25/24) | Sıralama (2026) | Puan (2026) |\\n`;
            md += `| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |\\n`;

            filteredRowsGlobal.forEach(item => {
                const code = item['Program Kodu'];
                const uni = item['Üniversite'];
                const programName = item['Program Adı'];
                const faculty = item['Fakülte'];
                const type = item['Üniversite Türü'] || 'Devlet';
                const city = item['Şehir'];
                const ucret = item['Ücret'];
                const puanTuru = item['Puan Türü'] || '-';
                const duration = getProgramDuration(faculty) === '4' ? '4 Yıllık' : '2 Yıllık';
                
                const k25 = item['Kontenjan'] ? item['Kontenjan'][0] : '-';
                const k24 = item['Kontenjan'] ? item['Kontenjan'][1] : '-';
                const k23 = item['Kontenjan'] ? item['Kontenjan'][2] : '-';
                
                const s25 = item['Taban Sıralama'] ? item['Taban Sıralama'][0] : 'Dolmadı';
                const s24 = item['Taban Sıralama'] ? item['Taban Sıralama'][1] : '-';
                
                const puan = item['Taban Puan'] ? item['Taban Puan'][0] : 'Dolmadı';

                let trendTxt = "";
                const p25 = parseSiralamaVal(s25);
                const p24 = parseSiralamaVal(s24);
                if (p25 !== Infinity && p24 !== Infinity) {
                    const diff = p24 - p25;
                    trendTxt = diff > 0 ? ` (▲ ${Math.abs(diff).toLocaleString('tr-TR')} Sıra Zorlaştı)` : ` (▼ ${Math.abs(diff).toLocaleString('tr-TR')} Sıra Kolaylaştı)`;
                }

                const sanitizedDept = `${uni} - ${programName} (${faculty})`.replace(/\\|/g, '\\\\|');
                const kontenjanStr = `${k25}/${k24}/${k23}`;
                
                md += `| ${code} | ${sanitizedDept} | ${puanTuru} | ${duration} | ${type} | ${city} | ${ucret || '-'} | ${kontenjanStr} | ${s25}${trendTxt} | ${puan} |\\n`;
            });

            const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
            const link = document.createElement("a");
            const url = URL.createObjectURL(blob);
            link.setAttribute("href", url);
            link.setAttribute("download", `yok-atlas-tercih-raporu.md`);
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), YokAtlasHandler) as httpd:
        print("YÖK Atlas Karargahı başlatıldı!")
        print(f"-> Arayüze erişmek için tarayıcınızdan açın: http://127.0.0.1:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\nServer durduruldu.")
