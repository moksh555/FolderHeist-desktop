import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional

from googleapiclient.errors import HttpError

from config import FOLDER_CATALOG_CSV, FOLDER_MIME, DRIVE_PARENT_ID


def _q_escape(value: str) -> str:
    """
    Escape quotes and backslashes for use in Drive query strings.
    """
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _search_folder_by_name(drive, name: str, parent_id: str) -> Optional[str]:
    """
    Look for a folder with the given name under the given parent in Drive.
    Returns the folder ID if found, else None.
    """
    safe = _q_escape(name)
    q = (
        f"name = '{safe}' and "
        f"'{parent_id}' in parents and "
        f"mimeType = '{FOLDER_MIME}' and "
        f"trashed = false"
    )
    resp = drive.files().list(
        q=q,
        fields="files(id, name)",
        pageSize=1,
    ).execute()

    files = resp.get("files", [])
    if not files:
        return None
    return files[0]["id"]


def ensure_folder(drive, label: str, existing_id: Optional[str], parent_id: str) -> str:
    """
    Ensure a folder exists for the given label under parent_id.

    Priority:
    1. If existing_id is provided and valid, reuse it.
    2. Else, try to find a folder with the label as its name.
    3. Else, create a new folder and return its ID.
    """
    # 1) If we already have a folder_id in CSV, verify it still exists
    if existing_id:
        try:
            meta = drive.files().get(
                fileId=existing_id,
                fields="id, name, mimeType, trashed, parents",
            ).execute()

            if (
                meta.get("mimeType") == FOLDER_MIME
                and not meta.get("trashed", False)
                and parent_id in (meta.get("parents") or [])
            ):
                # Existing ID is valid and under the correct parent
                return existing_id

            print(
                f"[FOLDERS] Existing folder_id for '{label}' is not valid under parent; "
                f"will search by name instead."
            )
        except HttpError as e:
            print(
                f"[FOLDERS] Error checking existing folder_id for '{label}': {e}. "
                f"Will search/create instead."
            )

    # 2) Try to find by name
    found_id = _search_folder_by_name(drive, label, parent_id)
    if found_id:
        print(f"[FOLDERS] Found existing folder for '{label}': {found_id}")
        return found_id

    # 3) Create a new folder
    body = {
        "name": label,
        "mimeType": FOLDER_MIME,
        "parents": [parent_id],
    }
    created = drive.files().create(
        body=body,
        fields="id",
    ).execute()
    folder_id = created["id"]
    print(f"[FOLDERS] Created folder for '{label}': {folder_id}")
    return folder_id


# --------------------------------------------------------------------
# CSV helpers (will be handy for future web UI)
# --------------------------------------------------------------------

def load_catalog(csv_path: str | None = None) -> List[Dict[str, str]]:
    """
    Load folders.csv and return a list of rows:
    [{ 'label': ..., 'folder_id': ..., 'description': ... }, ...]
    """
    path = Path(csv_path or FOLDER_CATALOG_CSV)
    if not path.exists():
        raise FileNotFoundError(
            f"Folder catalog CSV not found at {path}. "
            "Expected headers: label, folder_id, description."
        )

    rows: List[Dict[str, str]] = []
    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if "label" not in reader.fieldnames or "folder_id" not in reader.fieldnames:
            raise ValueError(
                "folders.csv must have at least 'label' and 'folder_id' headers."
            )

        for row in reader:
            rows.append({
                "label": (row.get("label") or "").strip(),
                "folder_id": (row.get("folder_id") or "").strip(),
                "description": (row.get("description") or "").strip(),
            })

    return rows


def save_catalog(rows: List[Dict[str, str]], csv_path: str | None = None) -> None:
    """
    Save rows back to folders.csv with headers: label, folder_id, description.
    """
    path = Path(csv_path or FOLDER_CATALOG_CSV)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["label", "folder_id", "description"],
        )
        writer.writeheader()
        writer.writerows(rows)


# --------------------------------------------------------------------
# Public entrypoint: ensure all folders exist & return mappings
# --------------------------------------------------------------------

def ensure_folders_from_csv(drive, csv_path: str | None = None,
                            parent_id: str | None = None
                            ) -> Tuple[Dict[str, str], Dict[str, str], List[str]]:
    """
    Ensure that for every label in folders.csv, a corresponding Drive folder
    exists under parent_id (defaults to DRIVE_PARENT_ID).

    - If folder_id is present and valid, it is used.
    - If folder_id is missing or invalid, a folder is searched/created.
    - Updated folder_ids are written back to the CSV.

    Returns:
        label_to_id: { label -> folder_id }
        label_desc: { label -> description }
        allowed:    [label1, label2, ...]
    """
    parent_id = parent_id or DRIVE_PARENT_ID
    rows = load_catalog(csv_path)

    for row in rows:
        label = row["label"]
        if not label:
            continue

        current_id = row["folder_id"] or None
        folder_id = ensure_folder(drive, label, current_id, parent_id)
        row["folder_id"] = folder_id
        # description already stripped in load_catalog()

    save_catalog(rows, csv_path)

    label_to_id: Dict[str, str] = {
        r["label"]: r["folder_id"] for r in rows if r["label"] and r["folder_id"]
    }
    label_desc: Dict[str, str] = {
        r["label"]: r["description"] for r in rows if r["label"] and r.get("description")
    }
    allowed: List[str] = [r["label"] for r in rows if r["label"]]

    print(
        f"[FOLDERS] hydrated {len(allowed)} labels, "
        f"{len(label_to_id)} folder IDs, {len(label_desc)} descriptions."
    )

    return label_to_id, label_desc, allowed
