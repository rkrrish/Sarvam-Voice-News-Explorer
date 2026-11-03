import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY", "").strip()
NEWSAPI_KEY = os.getenv("NEWSAPI_KEY", "").strip()

# Check if running in Vercel or Serverless environment
IS_VERCEL = os.getenv("VERCEL") == "1" or os.getenv("NOW_REGION") is not None

# Determine writable data directory
if IS_VERCEL:
    DATA_DIR = Path("/tmp/data")
else:
    DATA_DIR = BASE_DIR / os.getenv("DATA_DIR", "data")

AUDIO_DIR = DATA_DIR / "audio"
LEDGER_DIR = DATA_DIR / "ledgers"
LEDGER_FILE = DATA_DIR / "ledger.json"

# Models
SARVAM_STT_MODEL = os.getenv("SARVAM_STT_MODEL", "saaras:v3")
SARVAM_LLM_MODEL = os.getenv("SARVAM_LLM_MODEL", "sarvam-105b-conversations")
SARVAM_TTS_MODEL = os.getenv("SARVAM_TTS_MODEL", "bulbul:v3")
SARVAM_TRANSLATION_MODEL = os.getenv("SARVAM_TRANSLATION_MODEL", "sarvam-translate:v1")

# Default speaker voices per language for Sarvam Bulbul:v3 TTS
# Valid speakers: aditya, ritu, ashutosh, priya, neha, rahul, pooja, rohan, simran, kavya,
# amit, dev, ishita, shreya, ratan, varun, manan, sumit, roopa, kabir, aayan, shubh,
# advait, anand, tanya, tarun, sunny, mani, gokul, vijay, shruti, suhani, mohit, kavitha, rehan, soham, rupali
LANGUAGE_SPEAKER_MAP = {
    "en-IN": "kavya",
    "hi-IN": "aayan",
    "bn-IN": "anand",
    "gu-IN": "pooja",
    "kn-IN": "rohan",
    "mr-IN": "ishita",
    "pa-IN": "anand",
    "ta-IN": "vijay",
    "te-IN": "kavitha",
    "ml-IN": "shreya",
    "od-IN": "priya",
}

# Ensure storage directories exist safely
def init_storage():
    try:
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        if not LEDGER_FILE.exists():
            with open(LEDGER_FILE, "w", encoding="utf-8") as f:
                f.write("[]")
    except Exception as e:
        # On strictly read-only serverless filesystems where /tmp isn't mounted yet
        print(f"Notice: Storage init warning ({e}). Falling back to in-memory mode if needed.")

init_storage()
