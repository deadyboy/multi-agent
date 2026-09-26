from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from .contracts import BranchSpec, InputType

DOCX_EXTENSIONS = {".docx"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tiff", ".tif", ".webp"}
PDF_EXTENSIONS = {".pdf"}


def _files(path: Path) -> list[Path]:
    if not path.is_dir():
        return []
    return sorted(p for p in path.iterdir() if p.is_file())


def classify_path(input_path: str | Path) -> InputType:
    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        return "unknown"

    if path.is_file():
        ext = path.suffix.lower()
        if ext in DOCX_EXTENSIONS:
            return "docx"
        if ext in IMAGE_EXTENSIONS:
            return "image"
        if ext in PDF_EXTENSIONS:
            return "pdf"
        return "unknown"

    entries = _files(path)
    has_docx = any(p.suffix.lower() in DOCX_EXTENSIONS for p in entries)
    has_image = any(p.suffix.lower() in IMAGE_EXTENSIONS for p in entries)
    has_pdf = any(p.suffix.lower() in PDF_EXTENSIONS for p in entries)
    kinds = sum((has_docx, has_image, has_pdf))
    if kinds > 1:
        return "mixed"
    if has_docx:
        return "docx"
    if has_image:
        return "image"
    if has_pdf:
        return "pdf"
    return "unknown"


def build_plan(input_path: str | Path) -> Tuple[InputType, List[BranchSpec]]:
    path = Path(input_path).expanduser().resolve()
    input_type = classify_path(path)
    if input_type == "unknown":
        return input_type, []

    if path.is_file():
        if input_type == "docx":
            return input_type, [BranchSpec("docx", "docx", "stage", (str(path),))]
        return input_type, [BranchSpec(input_type, "vision", "direct", (str(path),))]

    entries = _files(path)
    docx_files = tuple(str(p) for p in entries if p.suffix.lower() in DOCX_EXTENSIONS)
    image_files = tuple(str(p) for p in entries if p.suffix.lower() in IMAGE_EXTENSIONS)
    pdf_files = tuple(str(p) for p in entries if p.suffix.lower() in PDF_EXTENSIONS)

    if input_type == "docx":
        return input_type, [BranchSpec("docx", "docx", "direct", (str(path),))]
    if input_type == "image":
        return input_type, [BranchSpec("images", "vision", "direct", (str(path),))]
    if input_type == "pdf":
        # pdf_work currently accepts one PDF path at a time. Keep that boundary
        # explicit rather than passing a PDF directory that its converter cannot open.
        return input_type, [
            BranchSpec(f"pdf-{idx:03d}", "vision", "direct", (pdf_path,))
            for idx, pdf_path in enumerate(pdf_files, 1)
        ]

    plan: List[BranchSpec] = []
    if docx_files:
        plan.append(BranchSpec("docx", "docx", "stage", docx_files))
    if image_files:
        plan.append(BranchSpec("images", "vision", "stage", image_files))
    for idx, pdf_path in enumerate(pdf_files, 1):
        plan.append(BranchSpec(f"pdf-{idx:03d}", "vision", "direct", (pdf_path,)))
    return input_type, plan
