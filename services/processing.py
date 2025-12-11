# services/processing.py

import io
from pathlib import Path
from mimetypes import guess_type
from typing import Tuple, Optional

from googleapiclient.http import MediaIoBaseDownload  # used only for legacy Drive flow

from config import FOLDER_MIME, CONF_THRESHOLD
from services.ai_router import choose_folder_with_gemini
from services import state
from services import drive_client


def try_extract_pdf_text(pdf_bytes: bytes) -> str:
    """Best-effort text extraction from a PDF byte stream."""
    try:
        import PyPDF2
        reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join([(p.extract_text() or "") for p in reader.pages])
    except Exception as e:
        print("[PDF] extraction failed:", e)
        return ""


def extract_text_from_bytes(content: bytes, filename: str, mime: str) -> Tuple[str, bool]:
    """
    Returns (text, is_binary).

    - For text/* and simple extensions (.txt, .md, .csv) we decode as UTF-8.
    - For PDFs we use try_extract_pdf_text.
    - For everything else we return empty text and mark as binary.
    """
    mime = mime or ""
    name_lower = filename.lower()

    # Plain text-ish files
    if mime.startswith("text/") or name_lower.endswith((".txt", ".md", ".csv")):
        return content.decode("utf-8", errors="ignore"), False

    # PDF
    if mime == "application/pdf" or name_lower.endswith(".pdf"):
        return try_extract_pdf_text(content), True

    # Could extend here to handle docx, etc.
    return "", True


def _pick_label(filename: str, text: str) -> Tuple[Optional[str], float]:
    result = choose_folder_with_gemini(
        filename=filename,
        text=text or "",
        allowed_labels=state.ALLOWED,
        label_desc=state.LABEL_DESC,
    ) or {}

    label = result.get("label")
    conf = float(result.get("confidence") or 0.0)

    if label not in state.LABEL_TO_ID or conf < CONF_THRESHOLD:
        low = filename.lower()

        if any(k in low for k in ["invoice", "receipt"]) and "Invoices" in state.LABEL_TO_ID:
            label = "Invoices"
        elif any(k in low for k in ["transcript", "grade", "gpa"]) and "Academics" in state.LABEL_TO_ID:
            label = "Academics"
        elif any(k in low for k in ["passport", "license", " id "]) and "IDs" in state.LABEL_TO_ID:
            label = "IDs" if "IDs" in state.LABEL_TO_ID else label

        if not label or label not in state.LABEL_TO_ID:
            fallback = "Misc" if "Misc" in state.LABEL_TO_ID else next(iter(state.ALLOWED), None)
            label = fallback

    return label, conf



# --------------------------------------------------------------------
# Legacy: Drive file -> classify -> move between Drive folders
# --------------------------------------------------------------------

def process_drive_file(drive, file_meta: dict) -> None:
    """
    Legacy flow: given a Drive file metadata dict, classify and move it
    between Drive folders. Kept for compatibility; main focus is local flow.
    """
    file_id = file_meta["id"]
    name = file_meta.get("name", "")
    mime = file_meta.get("mimeType", "")

    print(f"[PROCESS] {name} ({file_id}) type={mime}")

    if mime == FOLDER_MIME:
        print(f"[SKIP] Not a file: folder '{name}'")
        return

    text = ""

    # Google Docs export
    if mime == "application/vnd.google-apps.document":
        data = drive.files().export(fileId=file_id, mimeType="text/plain").execute()
        text = data.decode("utf-8", errors="ignore")

    # Google Sheets export
    elif mime == "application/vnd.google-apps.spreadsheet":
        data = drive.files().export(fileId=file_id, mimeType="text/csv").execute()
        text = data.decode("utf-8", errors="ignore")

    # Everything else: download bytes then extract
    else:
        buf = io.BytesIO()
        req = drive.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(buf, req)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        content = buf.getvalue()
        text, _ = extract_text_from_bytes(content, name, mime)

    label, conf = _pick_label(name, text)

    if not label or label not in state.LABEL_TO_ID:
        print(f"[WARN] No valid label for {name}; ALLOWED={len(state.ALLOWED)}. Skipping move.")
        return

    target_id = state.LABEL_TO_ID[label]
    drive_client.move_file(drive, file_id, target_id)
    print(f"[ROUTE] {name} -> {label} ({target_id}) @ conf={conf:.2f}")



# --------------------------------------------------------------------
# New: Local file -> classify -> upload into Drive folder
# --------------------------------------------------------------------

def process_local_file(drive, path: Path) -> None:
    """
    New flow: given a local file path, classify it and upload it to the
    appropriate Drive folder based on LABEL_TO_ID.
    """
    if not path.is_file():
        print(f"[LOCAL] Skipping non-file: {path}")
        return

    name = path.name
    mime, _ = guess_type(name)
    mime = mime or "application/octet-stream"

    print(f"[LOCAL] Processing {name} ({path}) mime={mime}")

    with path.open("rb") as f:
        content = f.read()

    text, _ = extract_text_from_bytes(content, name, mime)
    label, conf = _pick_label(name, text)

    if not label or label not in state.LABEL_TO_ID:
        print(f"[WARN] No valid label for {name}; ALLOWED={len(state.ALLOWED)}. Skipping upload.")
        return

    target_id = state.LABEL_TO_ID[label]
    drive_client.upload_file_to_folder(drive, path, target_id)
    print(f"[UPLOAD] {name} -> {label} ({target_id}) @ conf={conf:.2f}")

