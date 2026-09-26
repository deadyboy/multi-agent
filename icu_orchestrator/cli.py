from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Optional

from .adapters import DocxCommandAdapter, VisionCommandAdapter
from .orchestrator import Orchestrator
from .routing import build_plan


def _default_sibling(name: str) -> Path:
    return Path(__file__).resolve().parents[2] / name


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Top-level ICU extraction orchestrator")
    parser.add_argument("input_path")
    parser.add_argument("--output-dir", default="orchestrator_output")
    parser.add_argument("--docx-repo", default=os.environ.get("DOCX_WORK_REPO", str(_default_sibling("docx_work"))))
    parser.add_argument("--pdf-repo", default=os.environ.get("PDF_WORK_REPO", str(_default_sibling("pdf_work"))))
    parser.add_argument("--docx-model", default="qwen3:8b")
    parser.add_argument("--docx-backend", choices=["ollama", "vllm"], default="ollama")
    parser.add_argument("--pdf-model", default="Qwen/Qwen2.5-VL-72B-Instruct")
    parser.add_argument("--pdf-backend", choices=["ollama", "vllm"], default="vllm")
    parser.add_argument("--pdf-base-url", default="http://127.0.0.1:8000/v1")
    parser.add_argument("--timeout", type=int, default=7200)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args(argv)

    if args.plan_only:
        input_type, branches = build_plan(args.input_path)
        result = {
            "input_type": input_type,
            "input_path": str(Path(args.input_path).expanduser().resolve()),
            "branches": [b.to_dict() for b in branches],
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if branches else 2

    orchestrator = Orchestrator(
        DocxCommandAdapter(args.docx_repo, model=args.docx_model, backend=args.docx_backend, timeout_s=args.timeout),
        VisionCommandAdapter(args.pdf_repo, model=args.pdf_model, backend=args.pdf_backend, base_url=args.pdf_base_url, timeout_s=args.timeout),
    )
    result = orchestrator.run(args.input_path, args.output_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0 if result["status"] in {"succeeded", "partial"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
