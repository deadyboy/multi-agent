from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from icu_orchestrator.orchestrator import Orchestrator


class FakeAdapter:
    def __init__(self, pipeline: str, fail_on_pdf: bool = False):
        self.pipeline = pipeline
        self.fail_on_pdf = fail_on_pdf
        self.calls = []

    def run(self, input_path: str, work_dir: Path):
        p = Path(input_path)
        snapshot = sorted(x.name for x in p.iterdir()) if p.is_dir() else [p.name]
        self.calls.append((str(p), snapshot))
        failed = self.fail_on_pdf and p.suffix.lower() == ".pdf"
        return {
            "schema_version": "icu-agent/v1",
            "pipeline": self.pipeline,
            "status": "failed" if failed else "succeeded",
            "input_path": str(p),
            "result": {},
            "errors": {"x": "failed"} if failed else {},
            "meta": {},
        }


class OrchestratorTests(unittest.TestCase):
    def test_mixed_input_stages_media_separately(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            Path(src, "病程录.docx").touch()
            Path(src, "a.png").touch()
            Path(src, "b.jpg").touch()
            Path(src, "scan.pdf").touch()
            docx = FakeAdapter("docx")
            vision = FakeAdapter("vision")
            result = Orchestrator(docx, vision).run(src, out)

            self.assertEqual(result["status"], "succeeded")
            self.assertEqual(len(docx.calls), 1)
            self.assertEqual(docx.calls[0][1], ["病程录.docx"])
            self.assertEqual(len(vision.calls), 2)
            image_snapshots = [snap for path, snap in vision.calls if Path(path).is_dir()]
            self.assertEqual(image_snapshots[0], ["a.png", "b.jpg"])
            self.assertTrue(Path(out, "orchestration.json").is_file())

    def test_one_failed_branch_makes_partial(self):
        with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as out:
            Path(src, "病程录.docx").touch()
            Path(src, "scan.pdf").touch()
            result = Orchestrator(FakeAdapter("docx"), FakeAdapter("vision", fail_on_pdf=True)).run(src, out)
            self.assertEqual(result["status"], "partial")
            self.assertIn("pdf-001", result["errors"])


if __name__ == "__main__":
    unittest.main()
