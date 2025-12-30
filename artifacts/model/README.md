# FDE Model Artifacts

This directory stores all model-related outputs.

## 1. Layout

- `checkpoints/`
  - Raw training checkpoints (epoch / step).
  - Typically **ignored by Git** (large binaries).
- `exported/`
  - Clean, versioned models ready for use in the engine
    (e.g. ONNX, pickled, TorchScript, etc.).
- `configs/`
  - YAML / JSON configs describing:
    - model hyperparameters
    - persona wiring (which model used by which persona)
    - risk & router settings for a given experiment.
- `reports/`
  - Training logs, evaluation summaries, plots, and JSON metrics.

## 2. Versioning Convention

Suggested pattern:

- `checkpoints/run_<YYYYMMDD>_<tag>/`
- `exported/fde_alpha_v<major>.<minor>.onnx`
- `configs/fde_experiment_<YYYYMMDD>_<tag>.yaml`
- `reports/fde_experiment_<YYYYMMDD>_<tag>.json`

Example tag: `20251229_sp500_intraday_alpha`.
