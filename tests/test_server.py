import http.server
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import analyze_ui


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = cls.tmp.name
        data_dir = os.path.join(root, "universite_json")
        static_dir = os.path.join(root, "static")
        os.makedirs(data_dir)
        os.makedirs(static_dir)

        with open(os.path.join(data_dir, "bolum_Tip.json"), "w", encoding="utf-8") as handle:
            json.dump({"yks": [{"Şehir": "Ankara"}, {"Şehir": " ankara "}]}, handle)
        with open(os.path.join(data_dir, "bolum_Hukuk.json"), "w", encoding="utf-8") as handle:
            json.dump({"yks": [{"Şehir": "İzmir"}]}, handle)
        with open(os.path.join(data_dir, "metadata.json"), "w", encoding="utf-8") as handle:
            json.dump({"guide_year": "2026", "total_programs": 3}, handle)
        for name, content in (
            ("index.html", "<!DOCTYPE html><html><body>ok</body></html>"),
            ("app.js", "console.log('ok');"),
            ("style.css", "body { color: #fff; }"),
        ):
            with open(os.path.join(static_dir, name), "w", encoding="utf-8") as handle:
                handle.write(content)

        cls.original_data_dir = analyze_ui.DATA_DIR
        cls.original_static_dir = analyze_ui.STATIC_DIR
        analyze_ui.DATA_DIR = data_dir
        analyze_ui.STATIC_DIR = static_dir

        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), analyze_ui.YokAtlasHandler)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=5)
        analyze_ui.DATA_DIR = cls.original_data_dir
        analyze_ui.STATIC_DIR = cls.original_static_dir
        cls.tmp.cleanup()

    def get(self, path):
        url = f"http://127.0.0.1:{self.port}{path}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                return response.status, response.headers.get("Content-Type"), response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            return exc.code, exc.headers.get("Content-Type"), exc.read().decode("utf-8", "replace")

    def test_departments_endpoint(self):
        status, _, body = self.get("/api/departments")
        self.assertEqual(status, 200)
        departments = json.loads(body)
        self.assertEqual([d["id"] for d in departments], ["bolum_Hukuk.json", "bolum_Tip.json"])
        self.assertEqual(departments[1]["name"], "Tip")

    def test_cities_endpoint_is_deduplicated_and_uppercase(self):
        status, _, body = self.get("/api/cities")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body), ["ANKARA", "İZMİR"])

    def test_metadata_endpoint(self):
        status, _, body = self.get("/api/metadata")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["guide_year"], "2026")

    def test_department_endpoint(self):
        status, _, body = self.get("/api/department/bolum_Tip.json")
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(body)["yks"]), 2)

    def test_unknown_department_is_404(self):
        status, _, _ = self.get("/api/department/bolum_Yok.json")
        self.assertEqual(status, 404)

    def test_non_json_department_is_400(self):
        status, _, _ = self.get("/api/department/bolum_Tip.txt")
        self.assertEqual(status, 400)

    def test_static_files_are_served(self):
        for path, content_type in (
            ("/", "text/html"),
            ("/app.js", "text/javascript"),
            ("/style.css", "text/css"),
        ):
            status, served_type, _ = self.get(path)
            self.assertEqual(status, 200, path)
            self.assertIn(content_type, served_type, path)

    def test_repository_style_paths_stay_404(self):
        for path in ("/README.md", "/analyze_ui.py", "/static/app.js", "/.git/config"):
            status, _, _ = self.get(path)
            self.assertEqual(status, 404, path)


if __name__ == "__main__":
    unittest.main()
