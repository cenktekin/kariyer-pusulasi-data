import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fetch_yokatlas as fy


class NormalizeFilenameTest(unittest.TestCase):
    def test_turkish_characters_become_ascii(self):
        self.assertEqual(fy.normalize_filename("Türkçe Öğretmenliği"), "Turkce_Ogretmenligi")

    def test_parentheses_and_dots_are_removed(self):
        self.assertEqual(fy.normalize_filename("Tıp (İngilizce)"), "Tip_Ingilizce")

    def test_spaces_become_underscores(self):
        self.assertEqual(fy.normalize_filename("Bilgisayar Mühendisliği"), "Bilgisayar_Muhendisligi")


class BursToUcretTest(unittest.TestCase):
    def test_missing_burs_is_free(self):
        self.assertEqual(fy.burs_to_ucret(None, "DEVLET"), "Ücretsiz")

    def test_known_values_pass_through(self):
        self.assertEqual(fy.burs_to_ucret("Burslu", "VAKIF"), "Burslu")
        self.assertEqual(fy.burs_to_ucret("%50 İndirimli", "VAKIF"), "%50 İndirimli")

    def test_unknown_value_is_preserved(self):
        self.assertEqual(fy.burs_to_ucret("Özel Burs", "VAKIF"), "Özel Burs")


class ConvertProgramTest(unittest.TestCase):
    def sample(self, **overrides):
        program = {
            "kilavuzKodu": 1001,
            "universiteAdi": "  Orta Doğu Teknik Üniversitesi ",
            "fymkAdi": "Mühendislik Fakültesi",
            "universiteTuru": "DEVLET",
            "birimAdi": "Bilgisayar Mühendisliği",
            "ogrenimTuruAdi": "Örgün Öğretim",
            "kontenjan": 80,
            "gk1": 75,
            "gk2": 70,
            "gk3": 65,
            "minPuan": 512.345,
            "minPuan1": 500,
            "minPuan2": 0,
            "minPuan3": None,
            "basariSirasi": 1500,
            "basariSirasi1": 2000,
            "basariSirasi2": None,
            "basariSirasi3": 3000,
            "uniIlAdi": "Ankara",
            "bursOraniAdi": None,
            "puanTuru": "say",
        }
        program.update(overrides)
        return program

    def test_schema_is_exact(self):
        converted = fy.convert_program(self.sample())
        self.assertEqual(
            set(converted),
            {
                "Program Kodu", "Üniversite", "Fakülte", "Üniversite Türü", "Program Adı",
                "Öğretim Türü", "Yıl", "Kontenjan", "Yerleşen", "Taban Sıralama",
                "Taban Puan", "Şehir", "Ücret", "Puan Türü",
            },
        )

    def test_year_comes_from_guide_year(self):
        expected = [
            fy.GUIDE_YEAR,
            str(int(fy.GUIDE_YEAR) - 1),
            str(int(fy.GUIDE_YEAR) - 2),
            str(int(fy.GUIDE_YEAR) - 3),
        ]
        self.assertEqual(fy.convert_program(self.sample())["Yıl"], expected)
        self.assertEqual(fy.YEARS, expected)

    def test_kontenjan_series(self):
        converted = fy.convert_program(self.sample())
        self.assertEqual(converted["Kontenjan"], ["80", "75", "70", "65"])

    def test_missing_puan_and_siralama_become_empty(self):
        converted = fy.convert_program(self.sample(minPuan=0, minPuan3=None, basariSirasi2=None))
        self.assertEqual(converted["Taban Puan"][2], "")
        self.assertEqual(converted["Taban Puan"][3], "")
        self.assertEqual(converted["Taban Sıralama"][2], "")

    def test_numeric_formatting(self):
        converted = fy.convert_program(self.sample())
        self.assertEqual(converted["Taban Puan"][0], "512.345")
        self.assertEqual(converted["Taban Sıralama"][0], "1.500")

    def test_strings_are_trimmed(self):
        converted = fy.convert_program(self.sample())
        self.assertEqual(converted["Üniversite"], "Orta Doğu Teknik Üniversitesi")
        self.assertEqual(converted["Şehir"], "Ankara")

    def test_university_type(self):
        self.assertEqual(fy.convert_program(self.sample())["Üniversite Türü"], "Devlet")
        vakif = fy.convert_program(self.sample(universiteTuru="VAKIF"))
        self.assertEqual(vakif["Üniversite Türü"], "Vakıf")

    def test_puan_turu_is_uppercase(self):
        self.assertEqual(fy.convert_program(self.sample())["Puan Türü"], "SAY")

    def test_yeralan_is_empty_source_value(self):
        self.assertEqual(fy.convert_program(self.sample())["Yerleşen"], ["", "", "", ""])


class BuildSearchBodyTest(unittest.TestCase):
    def test_filters_and_paging(self):
        body = fy.build_search_body("SAY", 46, page=2, size=10)
        self.assertEqual(body["filters"], {"puanTuru": "SAY", "birimTuruId": 46})
        self.assertEqual(body["page"], 2)
        self.assertEqual(body["size"], 10)
        self.assertEqual(body["sortBy"], "basariSirasi")
        self.assertEqual(body["direction"], "ASC")

    def test_empty_filters_are_omitted(self):
        body = fy.build_search_body(None, None)
        self.assertEqual(body["filters"], {})


class PruneStaleFilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output_dir = os.path.join(self.tmp.name, "universite_json")
        self.archive_dir = os.path.join(self.tmp.name, "archive")
        os.makedirs(self.output_dir)

        self.original_output = fy.OUTPUT_DIR
        self.original_archive = fy.ARCHIVE_DIR
        fy.OUTPUT_DIR = self.output_dir
        fy.ARCHIVE_DIR = self.archive_dir
        self.addCleanup(self.restore_paths)

    def restore_paths(self):
        fy.OUTPUT_DIR = self.original_output
        fy.ARCHIVE_DIR = self.original_archive

    def touch(self, name, programs=0):
        with open(os.path.join(self.output_dir, name), "w", encoding="utf-8") as handle:
            json.dump({"yks": [{}] * programs}, handle)

    def test_stale_files_are_moved_to_archive(self):
        self.touch("bolum_Tip.json")
        self.touch("bolum_Eski_Bolum.json")

        moved = fy.prune_stale_files({"bolum_Tip.json"})

        self.assertEqual(moved, 1)
        self.assertEqual(sorted(os.listdir(self.output_dir)), ["bolum_Tip.json"])
        archived = os.listdir(self.archive_dir)
        self.assertEqual(len(archived), 1)
        self.assertTrue(archived[0].startswith("stale_"))
        self.assertEqual(os.listdir(os.path.join(self.archive_dir, archived[0])), ["bolum_Eski_Bolum.json"])

    def test_nothing_to_prune(self):
        self.touch("bolum_Tip.json")
        self.assertEqual(fy.prune_stale_files({"bolum_Tip.json"}), 0)
        self.assertFalse(os.path.exists(self.archive_dir))


if __name__ == "__main__":
    unittest.main()
