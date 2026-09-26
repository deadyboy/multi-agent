from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

from .adapters import PipelineAdapter
from .contracts import ORCHESTRATOR_SCHEMA_VERSION, BranchSpec
from .routing import build_plan


def _stage_files(paths: tuple[str, ...], destination: Path) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    used: set[str] = set()
    for idx, raw in enumerate(paths, 1):
        src = Path(raw).resolve()
        name = src.name
        if name in used:
            name = f"{idx:03d}-{name}"
        used.add(name)
        dst = destination / name
        try:
            os.link(src, dst)
        except OSError:
            shutil.copy2(src, dst)
    return destination


def _aggregate_status(branches: list[Dict[str, Any]]) -> str:
    if not branches:
        return "failed"
    statuses = [b.get("envelope", {}).get("status", "failed") for b in branches]
    if all(s == "succeeded" for s in statuses):
        return "succeeded"
    if all(s == "failed" for s in statuses):
        return "failed"
    return "partial"


class Orchestrator:
    """Deterministic control plane above the two domain-specific Agent pipelines."""

    def __init__(self, docx_adapter: PipelineAdapter, vision_adapter: PipelineAdapter) -> None:
        self.docx_adapter = docx_adapter
        self.vision_adapter = vision_adapter

    def plan(self, input_path: str | Path) -> Dict[str, Any]:
        input_type, branches = build_plan(input_path)
        return {
            "schema_version": ORCHESTRATOR_SCHEMA_VERSION,
            "input_path": str(Path(input_path).expanduser().resolve()),
            "input_type": input_type,
            "branches": [b.to_dict() for b in branches],
        }

    def run(self, input_path: str | Path, output_dir: str | Path) -> Dict[str, Any]:
        input_path = Path(input_path).expanduser().resolve()
        output_dir = Path(output_dir).expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

        input_type, specs = build_plan(input_path)
        branches: list[Dict[str, Any]] = []

        if input_type == "unknown" or not specs:
            result = {
                "schema_version": ORCHESTRATOR_SCHEMA_VERSION,
                "status": "failed",
                "input_path": str(input_path),
                "input_type": input_type,
                "branches": [],
                "errors": {"__route": "unsupported or empty input"},
            }
            self._write_result(output_dir, result)
            return result

        for idx, spec in enumerate(specs, 1):
            branch_dir = output_dir / f"{idx:02d}-{spec.name}"
            branch_dir.mkdir(parents=True, exist_ok=True)
            if spec.mode == "stage":
                run_input = _stage_files(spec.source_paths, branch_dir / "staged-input")
            else:
                run_input = Path(spec.source_paths[0])

            adapter = self.docx_adapter if spec.pipeline == "docx" else self.vision_adapter
            envelope = adapter.run(str(run_input), branch_dir)
            branches.append({
                "name": spec.name,
                "pipeline": spec.pipeline,
                "source_paths": list(spec.source_paths),
                "run_input": str(run_input),
                "envelope": envelope,
            })

        errors = {
            branch["name"]: branch["envelope"].get("errors", {})
            for branch in branches
            if branch["envelope"].get("status") == "failed"
        }
        result = {
            "schema_version": ORCHESTRATOR_SCHEMA_VERSION,
            "status": _aggregate_status(branches),
            "input_path": str(input_path),
            "input_type": input_type,
            "branches": branches,
            "errors": errors,
        }
        self._write_result(output_dir, result)
        return result

    @staticmethod
    def _write_result(output_dir: Path, result: Dict[str, Any]) -> None:
        (output_dir / "orchestration.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
