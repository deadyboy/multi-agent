# ICU Agent convergence architecture

## Principle

`multi-agent` is a deterministic **control plane**, not a third clinical extraction pipeline and not another LangGraph graph.

```text
patient input
    |
    v
multi-agent / orchestrator
    |
    +-- DOCX ----------------> docx_work / PatientState / field retry
    |
    +-- image or PDF --------> pdf_work  / ImageProcessingState / image retry
    |
    `-- mixed ---------------> split by media, execute branches, aggregate envelopes
```

## Boundary

The orchestrator knows only the `icu-agent/v1` envelope:

```json
{
  "schema_version": "icu-agent/v1",
  "pipeline": "docx | vision",
  "status": "succeeded | partial | failed",
  "input_path": "...",
  "result": {},
  "errors": {},
  "meta": {}
}
```

It does **not** import `PatientState`, `ImageProcessingState`, extractor functions, prompts, LangGraph nodes, or medical QC rules.

## Mixed inputs

- DOCX files are staged together and sent once to `docx_work`.
- Images are staged together and sent once to `pdf_work`, preserving cross-page merging.
- Each PDF is currently sent as its own vision branch because `pdf_work` accepts one PDF path per graph invocation.
- The final `orchestration.json` retains every branch envelope rather than flattening domain results into an ambiguous schema.

## Why subprocess adapters

The two repositories currently have incompatible Python package layouts (`docx_work.agent` vs top-level `agent`). A subprocess + JSON envelope boundary avoids import-name collisions and prevents either business repository from depending on the other. Packaging can be normalized later without changing the orchestration contract.
