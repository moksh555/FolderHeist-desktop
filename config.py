import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory for relative paths
BASE_DIR = Path(__file__).resolve().parent

# --------------------------------------------------------------------
# Google Drive / Authentication
# --------------------------------------------------------------------

SCOPES = [os.getenv("SCOPES", "https://www.googleapis.com/auth/drive")]

# # Parent Drive folder that contains all category folders (from folders.csv)
DRIVE_PARENT_ID = os.getenv("DRIVE_PARENT_ID", "")

# if not DRIVE_PARENT_ID:
#     raise RuntimeError("Set DRIVE_PARENT_ID in .env (parent folder for categorized files).")

# Local files for Drive auth & watch info
TOKEN_FILE = os.getenv("TOKEN_FILE", str(BASE_DIR / "token.json"))
CLIENT_SECRET_FILE = os.getenv("CLIENT_SECRET_FILE", str(BASE_DIR / "client_secret.json"))
WATCH_ID_FILE = os.getenv("WATCH_ID_FILE", str(BASE_DIR / "watch_channel.json"))
START_TOKEN_FILE = os.getenv("START_TOKEN_FILE", str(BASE_DIR / "start_page_token.txt"))
APP_URL = os.getenv("APP_URL", "http://localhost:8000")
# --------------------------------------------------------------------
# Local folder watching
# --------------------------------------------------------------------

# Local folder to watch for new files (using Desktop on your MAC as base path)
LOCAL_WATCH_DIR = os.getenv(
    "LOCAL_WATCH_DIR",
    str(Path.home() / "Desktop" / "FolderHeistInbox")
)

# Ensure it exists
Path(LOCAL_WATCH_DIR).mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------
# Catalog CSV
# --------------------------------------------------------------------

# CSV that defines: label, folder_id, description
FOLDER_CATALOG_CSV = os.getenv(
    "FOLDER_CATALOG_CSV",
    str(BASE_DIR / "folders.csv")
)

# --------------------------------------------------------------------
# Classification / Routing
# --------------------------------------------------------------------

# Confidence threshold for Gemini result before applying heuristics
CONF_THRESHOLD = float(os.getenv("ROUTER_CONF_THRESHOLD", "0.55"))

# Google Drive MIME type constant for folder objects
FOLDER_MIME = "application/vnd.google-apps.folder"

PORT=int(os.getenv("PORT", "8000"))