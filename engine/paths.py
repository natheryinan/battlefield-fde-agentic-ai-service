
# engine/paths.py
from pathlib import Path

# repo_root:  .../FDE PROJECTS/ (根据你现在这个层级往上两级基本就对了)
REPO_ROOT = Path(__file__).resolve().parents[1]

ARTIFACTS_DIR = REPO_ROOT / "artifacts"
DATA_DIR = ARTIFACTS_DIR / "data"
MODEL_DIR = ARTIFACTS_DIR / "model"

DATA_RAW_DIR = DATA_DIR / "raw"
DATA_FEATURES_DIR = DATA_DIR / "features"
BACKTESTS_DIR = DATA_DIR / "backtests"

MODEL_CHECKPOINTS_DIR = MODEL_DIR / "checkpoints"
MODEL_EXPORTED_DIR = MODEL_DIR / "exported"
MODEL_CONFIGS_DIR = MODEL_DIR / "configs"
MODEL_REPORTS_DIR = MODEL_DIR / "reports"
