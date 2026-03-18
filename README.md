# 🖥️ FolderHeist Desktop — Local AI-Powered File Organizer

FolderHeist Desktop is the **local-first** version of the FolderHeist file organizer. Instead of watching a Google Drive folder via webhooks, it monitors a **local directory** on your machine using `watchdog`, classifies incoming files with Google Gemini AI (or keyword heuristics), and uploads them to the correct Google Drive category subfolder automatically.

## ✨ Features

- **Local folder watcher** — uses `watchdog` to monitor a configurable local directory (`~/Desktop/FolderHeistInbox` by default) for new files in real time
- **AI-powered classification** — sends each file's name and extracted content to Google Gemini for category assignment; falls back to regex keyword matching when Gemini is unavailable
- **Automatic Drive upload** — moves classified files directly into the appropriate Google Drive category subfolder
- **PDF and text extraction** — reads PDF content via PyPDF2 and raw text files for richer AI context
- **Hidden/temp file filtering** — automatically ignores `.DS_Store`, hidden files, and `~` temp files
- **Comprehensive test suite** — includes unit tests for all major service modules (catalog loading, labeling, local watching, notifications, processing, state management)
- **CSV-driven category mapping** — `folders.csv` defines label → Drive folder ID bindings without code changes

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Language | Python 3 |
| File Watching | `watchdog` |
| AI Classification | Google Gemini (`google-genai`) |
| Drive Upload | Google Drive API v3 (`google-api-python-client`) |
| PDF Parsing | PyPDF2 |
| Testing | `pytest` |
| Config | `python-dotenv` |

## 🚀 Setup & Installation

**Prerequisites:** Python 3.10+, a Google Cloud project with Drive API enabled

```bash
# 1. Clone the repository
git clone https://github.com/moksh555/FolderHeist-desktop.git
cd FolderHeist-desktop

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env with:
#   LOCAL_WATCH_DIR=/path/to/your/inbox    (defaults to ~/Desktop/FolderHeistInbox)
#   DRIVE_PARENT_ID=<parent Drive folder ID for category subfolders>
#   GEMINI_API_KEY=<your Gemini API key>

# 4. Add Google OAuth credentials
# Place client_secret.json in the project root

# 5. Configure folders.csv with your category labels and folder IDs
# label,folder_id,description
# Invoices,1abc...,Bills and receipts

# 6. Run the watcher
python app.py
```

## ▶️ Usage

Once running, FolderHeist Desktop:
1. Creates the inbox directory if it doesn't exist
2. Starts a `watchdog` observer on the local inbox folder
3. When any new file appears, reads its content (PDF text, plain text, or binary)
4. Classifies it with Gemini AI (or regex keywords)
5. Uploads/moves the file to the matching Google Drive category subfolder

## 🧪 Running Tests

```bash
pytest Tests/
```

Tests cover: folder catalog loading, label assignment logic, local watcher event handling, notification dispatching, file processing pipeline, and state management.

## 🏗️ Architecture

```
Local Inbox Directory
       │
  watchdog Observer (services/local_watcher.py)
       │
  NewFileHandler.on_created()
       │
  services/processing.py
  ┌────┴─────────────────────────┐
PDF/text extraction        services/ai_router.py
                                  │
                      Gemini API → keyword fallback
                                  │
                           Google Drive API
                                  │
                     Move to category subfolder
```

**Key modules:**
- `services/local_watcher.py` — `watchdog`-based observer; lazy imports for testability
- `services/processing.py` — file download, content extraction, and routing orchestration
- `services/ai_router.py` — Gemini + heuristic classification engine
- `services/folder_catalog.py` — CSV loader for label/folder mappings
- `services/state.py` — in-memory label→folder ID registry

## 🔑 Differences from FolderHeist (Drive Webhook Version)

| Feature | FolderHeist (webhook) | FolderHeist Desktop |
|---------|----------------------|---------------------|
| Trigger | Google Drive push notification | Local filesystem event (`watchdog`) |
| Requires public HTTPS URL | Yes | No |
| Source of files | Google Drive watched folder | Local `FolderHeistInbox` directory |
| Test suite | No | Yes (6 test modules) |
