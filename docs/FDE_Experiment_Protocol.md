# FDE Experiment Protocol (v1)

## Purpose
Experiments exist to validate **sovereign routing behavior** under regime shifts:
- signal normalization integrity
- ticker alias resolution correctness
- regime_router stability and determinism
- Alpha final authority + Guardian breach behavior

## Non-Negotiables
1. **Ticker Canonicalization First**
   - All inputs resolve through `ticker_aliases` → canonical symbol set.
2. **Normalization Before Routing**
   - Raw signals must pass `normalizer` before any regime inference.
3. **Routing Is Advisory**
   - `regime_router` proposes; **Alpha decides**.
4. **Breach Overrides**
   - Guardian breach forces hard enforcement (freeze, unwind, deny, etc.).

## Experiment Lifecycle
1. Load `experiment.yaml`
2. Resolve tickers → canonical
3. Load data window (or synthetic feed)
4. Normalize signals
5. Infer regime + route proposal
6. Apply risk gates (Guardian)
7. Alpha decision + execution plan
8. Log artifacts + metrics

## Expected Outputs (Artifacts)
- `artifacts/runs/<run_id>/config_resolved.yaml`
- `artifacts/runs/<run_id>/signals_snapshot.parquet`
- `artifacts/runs/<run_id>/regime_trace.jsonl`
- `artifacts/runs/<run_id>/decisions.jsonl`
- `artifacts/runs/<run_id>/metrics.json`
- `artifacts/runs/<run_id>/run_report.md`
