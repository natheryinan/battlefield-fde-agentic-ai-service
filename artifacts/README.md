

# FDE Artifacts

This directory stores **data and model artifacts** that the FDE engine
and kernel read from and write to.

- `data/`  – canonical store for raw and processed datasets
- `model/` – model weights, configs, and training / eval reports

Heavy binary files (raw vendor data, large model weights) should be
excluded from Git and managed via storage (S3, etc.) or LFS.
