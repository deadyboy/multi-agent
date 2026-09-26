from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Literal

PIPELINE_SCHEMA_VERSION = "icu-agent/v1"
ORCHESTRATOR_SCHEMA_VERSION = "icu-orchestrator/v1"

InputType = Literal["docx", "image", "pdf", "mixed", "unknown"]
PipelineName = Literal["docx", "vision"]
BranchMode = Literal["direct", "stage"]


@dataclass(frozen=True)
class BranchSpec:
    name: str
    pipeline: PipelineName
    mode: BranchMode
    source_paths: tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
