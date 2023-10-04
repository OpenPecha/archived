from pathlib import Path

# Repository
AUTHOR = "10zinten"
REPO = "models"

# Directories
BASE_DIR = Path.home() / f".{REPO}"
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# Create dirs
DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
