# ICU Multi-Agent Orchestrator

Top-level control plane for `deadyboy/docx_work` and `deadyboy/pdf_work`.

This repository intentionally contains **no LangGraph dependency and no medical extraction logic**. It classifies patient inputs, dispatches to the two domain pipelines through their `icu-agent/v1` CLI adapters, and aggregates branch results.

## Layout

- `icu_orchestrator/routing.py` — coarse DOCX/image/PDF/mixed routing.
- `icu_orchestrator/adapters.py` — subprocess adapters for the two repositories.
- `icu_orchestrator/orchestrator.py` — mixed-input staging, execution and aggregation.
- `icu_orchestrator/cli.py` — command-line entry point.

## Plan without running models

```bash
python orchestrate.py /data/patient_001 --plan-only
```

## Execute

Assuming `multi-agent`, `docx_work`, and `pdf_work` are sibling checkouts:

```bash
python orchestrate.py /data/patient_001 --output-dir results/patient_001
```

Explicit repository locations can also be supplied:

```bash
python orchestrate.py /data/patient_001 \
  --docx-repo /opt/icu/docx_work \
  --pdf-repo /opt/icu/pdf_work \
  --output-dir /data/results/patient_001
```

Each business pipeline writes an `icu-agent/v1` envelope; this repository writes `orchestration.json` containing all branch envelopes and the aggregate status.

See `ARCHITECTURE.md` for the convergence boundary.
