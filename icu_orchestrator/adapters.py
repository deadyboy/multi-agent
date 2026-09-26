from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Protocol

from .contracts import PIPELINE_SCHEMA_VERSION


class PipelineAdapter(Protocol):
    pipeline: str

    def run(self, input_path: str, work_dir: Path) -> Dict[str, Any]: ...


def _failed_envelope(pipeline: str, input_path: str, message: str, *, meta: Optional[dict] = None) -> Dict[str, Any]:
    return {
        "schema_version": PIPELINE_SCHEMA_VERSION,
        "pipeline": pipeline,
        "status": "failed",
        "input_path": str(Path(input_path).resolve()),
        "result": {},
        "errors": {"__adapter": message},
        "meta": meta or {},
    }


def _read_envelope(path: Path, pipeline: str, input_path: str) -> Dict[str, Any]:
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return _failed_envelope(pipeline, input_path, f"invalid result envelope: {type(exc).__name__}: {exc}")
    if envelope.get("schema_version") != PIPELINE_SCHEMA_VERSION:
        return _failed_envelope(pipeline, input_path, f"unexpected schema_version: {envelope.get('schema_version')!r}")
    if envelope.get("pipeline") != pipeline:
        return _failed_envelope(pipeline, input_path, f"unexpected pipeline: {envelope.get('pipeline')!r}")
    if envelope.get("status") not in {"succeeded", "partial", "failed"}:
        return _failed_envelope(pipeline, input_path, f"unexpected status: {envelope.get('status')!r}")
    return envelope


class _CommandAdapter:
    pipeline: str

    def __init__(self, repo_root: str | Path, *, timeout_s: int = 7200, python_executable: str = sys.executable) -> None:
        self.repo_root = Path(repo_root).expanduser().resolve()
        self.timeout_s = timeout_s
        self.python_executable = python_executable

    def _extra_args(self, work_dir: Path) -> list[str]:
        raise NotImplementedError

    def run(self, input_path: str, work_dir: Path) -> Dict[str, Any]:
        work_dir.mkdir(parents=True, exist_ok=True)
        wrapper = self.repo_root / "agent_cli.py"
        if not wrapper.is_file():
            return _failed_envelope(self.pipeline, input_path, f"adapter entry point not found: {wrapper}")

        result_json = work_dir / f"{self.pipeline}-envelope.json"
        cmd = [
            self.python_executable,
            str(wrapper),
            str(input_path),
            "--result-json",
            str(result_json),
            *self._extra_args(work_dir),
        ]
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return _failed_envelope(self.pipeline, input_path, f"pipeline timed out after {self.timeout_s}s")
        except Exception as exc:
            return _failed_envelope(self.pipeline, input_path, f"subprocess failed: {type(exc).__name__}: {exc}")

        if not result_json.is_file():
            return _failed_envelope(
                self.pipeline,
                input_path,
                f"pipeline exited {proc.returncode} without result envelope",
                meta={"stdout": proc.stdout[-2000:], "stderr": proc.stderr[-2000:]},
            )

        envelope = _read_envelope(result_json, self.pipeline, input_path)
        envelope.setdefault("meta", {})
        envelope["meta"].update({
            "adapter_returncode": proc.returncode,
            "adapter_stdout_tail": proc.stdout[-2000:],
            "adapter_stderr_tail": proc.stderr[-2000:],
        })
        return envelope


class DocxCommandAdapter(_CommandAdapter):
    pipeline = "docx"

    def __init__(self, repo_root: str | Path, *, model: str = "qwen3:8b", backend: str = "ollama", max_retries: int = 2, timeout_s: int = 7200) -> None:
        super().__init__(repo_root, timeout_s=timeout_s)
        self.model = model
        self.backend = backend
        self.max_retries = max_retries

    def _extra_args(self, work_dir: Path) -> list[str]:
        return ["--model", self.model, "--backend", self.backend, "--max-retries", str(self.max_retries)]


class VisionCommandAdapter(_CommandAdapter):
    pipeline = "vision"

    def __init__(self, repo_root: str | Path, *, model: str = "Qwen/Qwen2.5-VL-72B-Instruct", backend: str = "vllm", base_url: str = "http://127.0.0.1:8000/v1", timeout_s: int = 7200) -> None:
        super().__init__(repo_root, timeout_s=timeout_s)
        self.model = model
        self.backend = backend
        self.base_url = base_url

    def _extra_args(self, work_dir: Path) -> list[str]:
        output_dir = work_dir / "vision-output"
        return [
            "--output-dir", str(output_dir),
            "--model", self.model,
            "--backend", self.backend,
            "--base-url", self.base_url,
        ]
