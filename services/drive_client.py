# services/drive_client.py

"""
Google Drive client utilities.

- get_drive()          -> authenticated Drive client
- move_file(...)       -> move an existing Drive file between folders
- upload_file_to_folder(...) -> upload local file into Drive folder

Google API imports are done lazily so that unit tests can import this
module without having google-auth libraries installed.
"""

import json
from pathlib import Path
from typing import Any

from config import SCOPES, TOKEN_FILE, CLIENT_SECRET_FILE


# -------------------------------------------------------------------
# Internal: lazy Google imports
# -------------------------------------------------------------------


def _google_auth():
    """
    Lazy-import Google auth and client libraries.

    We only call this inside functions that actually need Google APIs,
    so importing this module in tests won't crash if the libraries
    are not installed.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    return InstalledAppFlow, Request, Credentials, build


def _google_http():
    """
    Lazy-import HTTP helpers like MediaFileUpload.
    """
    from googleapiclient.http import MediaFileUpload

    return MediaFileUpload


# -------------------------------------------------------------------
# Credentials & Drive client
# -------------------------------------------------------------------


def _load_credentials() -> Any:
    """
    Load OAuth credentials from TOKEN_FILE if present.
    If missing or invalid, run the OAuth flow and save new credentials.

    This is the standard "installed app" Drive pattern.
    """
    InstalledAppFlow, Request, Credentials, _ = _google_auth()

    creds = None
    token_path = Path(TOKEN_FILE)

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    # If there are no valid credentials, run the flow.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CLIENT_SECRET_FILE,
                SCOPES,
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return creds


def get_drive():
    """
    Return an authenticated Drive API client (v3).
    """
    _, _, _, build = _google_auth()
    creds = _load_credentials()
    service = build("drive", "v3", credentials=creds)
    return service


# -------------------------------------------------------------------
# File operations
# -------------------------------------------------------------------


def move_file(drive, file_id: str, target_folder_id: str) -> None:
    """
    Move an existing Drive file into a different folder.

    - drive: result of get_drive()
    - file_id: ID of the file to move
    - target_folder_id: ID of the destination folder
    """
    # Get current parents
    meta = (
        drive.files()
        .get(fileId=file_id, fields="parents")
        .execute()
    )
    prev_parents = ",".join(meta.get("parents", []))

    # Update parents: remove old, add new
    drive.files().update(
        fileId=file_id,
        addParents=target_folder_id,
        removeParents=prev_parents,
        fields="id, parents",
    ).execute()

    print(f"[DRIVE] Moved file {file_id} -> {target_folder_id}")


def upload_file_to_folder(drive, local_path: Path, folder_id: str) -> str:
    """
    Upload a local file into a specific Drive folder.

    - drive: result of get_drive()
    - local_path: pathlib.Path to the file on disk
    - folder_id: ID of the Drive folder where it should go

    Returns:
        The new file's Drive ID.
    """
    MediaFileUpload = _google_http()

    body = {
        "name": local_path.name,
        "parents": [folder_id],
    }

    media = MediaFileUpload(str(local_path), resumable=True)

    file = (
        drive.files()
        .create(body=body, media_body=media, fields="id, parents")
        .execute()
    )

    file_id = file.get("id")
    print(f"[DRIVE] Uploaded {local_path.name} -> {folder_id}, id={file_id}")
    return file_id
