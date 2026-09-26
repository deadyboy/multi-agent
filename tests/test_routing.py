from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from icu_orchestrator.routing import build_plan, classify_path


class RoutingTests(unittest.TestCase):
    def test_single_docx_is_staged(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "病程录.docx")
            p.touch()
            kind, plan = build_plan(p)
            self.assertEqual(kind, "docx")
            self.assertEqual(plan[0].pipeline, "docx")
            self.assertEqual(plan[0].mode, "stage")

    def test_pdf_directory_splits_per_pdf(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "a.pdf").touch()
            Path(d, "b.pdf").touch()
            kind, plan = build_plan(d)
            self.assertEqual(kind, "pdf")
            self.assertEqual(len(plan), 2)
            self.assertTrue(all(x.pipeline == "vision" for x in plan))

    def test_mixed_folder_builds_three_media_branches(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "病程录.docx").touch()
            Path(d, "page.png").touch()
            Path(d, "scan.pdf").touch()
            kind, plan = build_plan(d)
            self.assertEqual(kind, "mixed")
            self.assertEqual([x.pipeline for x in plan], ["docx", "vision", "vision"])
            self.assertEqual(plan[0].mode, "stage")
            self.assertEqual(plan[1].mode, "stage")
            self.assertEqual(plan[2].mode, "direct")


if __name__ == "__main__":
    unittest.main()
