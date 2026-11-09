import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fetch_yokatlas as fy


class RebuildMetadataTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output_dir = self.tmp.name

        self.original_output = fy.OUTPUT_DIR
        fy.OUTPUT_DIR = self.output_dir
        self.addCleanup(self.restore_output_dir)

    def restore_output_dir(self):
        fy.OUTPUT_DIR = self.original_output

    def write_department(self, name, program_count):
        with open(os.path.join(self.output_dir, name), "w", encoding="utf-8") as handle:
            json.dump({"yks": [{"Program Kodu": str(i)} for i in range(program_count)]}, handle)

    def write_metadata(self, payload):
        with open(os.path.join(self.output_dir, "metadata.json"), "w", encoding="utf-8") as handle:
            json.dump(payload, handle)

    def read_metadata(self):
        with open(os.path.join(self.output_dir, "metadata.json"), encoding="utf-8") as handle:
            return json.load(handle)

    def test_totals_come_from_department_files(self):
        self.write_department("bolum_Tip.json", 3)
        self.write_department("bolum_Hukuk.json", 4)

        meta = fy.rebuild_metadata()

        self.assertEqual(meta["total_programs"], 7)
        self.assertEqual(meta["department_files"], 2)
        self.assertEqual(meta["guide_year"], fy.GUIDE_YEAR)
        self.assertEqual(meta["categories"], [label for _, _, label in fy.CATEGORIES])
        self.assertTrue(meta["fetched_at"])
        self.assertEqual(self.read_metadata()["total_programs"], 7)

    def test_missing_department_files_returns_none(self):
        self.assertIsNone(fy.rebuild_metadata())
        self.assertFalse(os.path.exists(os.path.join(self.output_dir, "metadata.json")))

    def test_unchanged_dataset_keeps_fetched_at(self):
        self.write_department("bolum_Tip.json", 2)
        first = fy.rebuild_metadata()

        second = fy.rebuild_metadata()

        self.assertEqual(second["fetched_at"], first["fetched_at"])
        with open(os.path.join(self.output_dir, "metadata.json"), "rb") as handle:
            after_first = handle.read()
        fy.rebuild_metadata()
        with open(os.path.join(self.output_dir, "metadata.json"), "rb") as handle:
            after_third = handle.read()
        self.assertEqual(after_first, after_third)

    def test_changed_dataset_recomputes_fetched_at(self):
        self.write_department("bolum_Tip.json", 2)
        self.write_metadata({
            "guide_year": fy.GUIDE_YEAR,
            "fetched_at": "2020-01-01T00:00:00+00:00",
            "total_programs": 999,
            "department_files": 1,
            "categories": [],
        })

        meta = fy.rebuild_metadata()

        self.assertEqual(meta["total_programs"], 2)
        self.assertNotEqual(meta["fetched_at"], "2020-01-01T00:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
