import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Базові шляхи
BASE_DIR = Path(__file__).resolve().parent.parent
MODELS_DIR = BASE_DIR / "models"
MODEL_PATH = MODELS_DIR / "best.pt"

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "buzz_buzz_buzz")

# Параметри YOLO за замовчуванням
DEFAULT_CONFIDENCE = 0.25
DEFAULT_IOU = 0.5
TRACKER_TYPE = "botsort.yaml"  # Алгоритм трекінгу