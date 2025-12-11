# tests/test_folder_catalog.py
import sys
import csv
from pathlib import Path
import pytest
# Add project root (FolderHeist) to sys.path
ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))
from services import folder_catalog


class FakeOp:
    """Wrapper that mimics googleapiclient .execute() behavior."""
    def __init__(self, fn):
        self._fn = fn

    def execute(self):
        return self._fn()


class FakeFiles:
    """files() stub: returns operations for get/list/create."""

    def __init__(self, drive):
        self.drive = drive

    def get(self, fileId, fields=None):
        return FakeOp(lambda: self.drive.handle_get(fileId, fields))

    def list(self, q=None, fields=None, pageSize=None):
        return FakeOp(lambda: self.drive.handle_list(q, fields, pageSize))

    def create(self, body=None, fields=None):
        return FakeOp(lambda: self.drive.handle_create(body, fields))


class FakeDrive:
    """
    Minimal fake Drive client that supports:
    - files().get().execute()
    - files().list().execute()
    - files().create().execute()
    """

    def __init__(self, folders_by_id=None, folders_by_name=None, parent_id="PARENT123"):
        # id -> metadata dict
        self.folders_by_id = folders_by_id or {}
        # name -> id
        self.folders_by_name = folders_by_name or {}
        self.parent_id = parent_id

        # Tracking
        self.created_bodies = []
        self.list_queries = []

    def files(self):
        return FakeFiles(self)

    # Handlers used by FakeFiles

    def handle_get(self, file_id, fields):
        meta = self.folders_by_id.get(file_id)
        if not meta:
            # Simulate HttpError-ish behavior by raising KeyError
            # (folder_catalog catches HttpError only when verifying IDs,
            # but for happy-path tests we don't need error simulation.)
            raise KeyError(f"No such file_id: {file_id}")
        return meta

    def handle_list(self, q, fields, pageSize):
        self.list_queries.append(q or "")
        # Very simple parser: look for name = 'X'
        name = None
        marker = "name = '"
        if marker in (q or ""):
            name = q.split(marker, 1)[1].split("'", 1)[0]

        if name and name in self.folders_by_name:
            folder_id = self.folders_by_name[name]
            meta = self.folders_by_id[folder_id]
            return {"files": [meta]}
        return {"files": []}

    def handle_create(self, body, fields):
        # Simulate folder creation
        new_id = f"F_{len(self.folders_by_id) + 1}"
        meta = {
            "id": new_id,
            "name": body.get("name"),
            "mimeType": folder_catalog.FOLDER_MIME,
            "trashed": False,
            "parents": body.get("parents") or [],
        }
        self.folders_by_id[new_id] = meta
        self.folders_by_name[meta["name"]] = new_id
        self.created_bodies.append(body)
        return {"id": new_id}


# -------------------------------------------------------------------
# Tests for load_catalog / save_catalog
# -------------------------------------------------------------------


def test_load_and_save_catalog_roundtrip(tmp_path, monkeypatch):
    csv_path = tmp_path / "folders.csv"
    rows = [
        {"label": "Invoices", "folder_id": "AAA", "description": "All invoice docs"},
        {"label": "Taxes", "folder_id": "BBB", "description": "Tax filings"},
    ]

    # Write initial CSV
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "folder_id", "description"])
        writer.writeheader()
        writer.writerows(rows)

    # Point folder_catalog to our temp CSV
    monkeypatch.setattr(folder_catalog, "FOLDER_CATALOG_CSV", str(csv_path))

    loaded = folder_catalog.load_catalog()
    assert loaded == rows

    # Modify and save
    loaded[0]["description"] = "Updated description"
    folder_catalog.save_catalog(loaded)

    # Reload and assert change persisted
    reloaded = folder_catalog.load_catalog()
    assert reloaded[0]["description"] == "Updated description"


# -------------------------------------------------------------------
# Tests for ensure_folders_from_csv behavior
# -------------------------------------------------------------------


def test_ensure_folders_uses_existing_valid_ids(tmp_path, monkeypatch):
    """
    If CSV has a valid folder_id and it points to a folder under the parent,
    ensure_folders_from_csv should reuse it and NOT create a new folder.
    """
    parent_id = "PARENT123"
    csv_path = tmp_path / "folders.csv"

    # Prepare CSV: Invoices already has a folder_id
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "folder_id", "description"])
        writer.writeheader()
        writer.writerow({"label": "Invoices", "folder_id": "F_INVOICES", "description": "Invoices folder"})

    monkeypatch.setattr(folder_catalog, "FOLDER_CATALOG_CSV", str(csv_path))
    monkeypatch.setattr(folder_catalog, "DRIVE_PARENT_ID", parent_id)

    # Fake Drive has a folder with that ID under the parent
    folders_by_id = {
        "F_INVOICES": {
            "id": "F_INVOICES",
            "name": "Invoices",
            "mimeType": folder_catalog.FOLDER_MIME,
            "trashed": False,
            "parents": [parent_id],
        }
    }
    drive = FakeDrive(folders_by_id=folders_by_id, parent_id=parent_id)

    label_to_id, label_desc, allowed = folder_catalog.ensure_folders_from_csv(
        drive, csv_path=str(csv_path), parent_id=parent_id
    )

    # Should reuse existing ID
    assert label_to_id == {"Invoices": "F_INVOICES"}
    assert "Invoices" in allowed
    assert label_desc["Invoices"] == "Invoices folder"
    # No folders should have been created
    assert drive.created_bodies == []


def test_ensure_folders_fills_missing_id_from_existing_name(tmp_path, monkeypatch):
    """
    If folder_id is empty but a folder exists in Drive with that label under the parent,
    it should find and use that folder_id instead of creating a new folder.
    """
    parent_id = "PARENT123"
    csv_path = tmp_path / "folders.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "folder_id", "description"])
        writer.writeheader()
        writer.writerow({"label": "Invoices", "folder_id": "", "description": "Invoices folder"})

    monkeypatch.setattr(folder_catalog, "FOLDER_CATALOG_CSV", str(csv_path))
    monkeypatch.setattr(folder_catalog, "DRIVE_PARENT_ID", parent_id)

    # Drive has an existing folder named "Invoices" under the parent
    folders_by_id = {
        "F_INVOICES": {
            "id": "F_INVOICES",
            "name": "Invoices",
            "mimeType": folder_catalog.FOLDER_MIME,
            "trashed": False,
            "parents": [parent_id],
        }
    }
    folders_by_name = {"Invoices": "F_INVOICES"}
    drive = FakeDrive(
        folders_by_id=folders_by_id,
        folders_by_name=folders_by_name,
        parent_id=parent_id,
    )

    label_to_id, label_desc, allowed = folder_catalog.ensure_folders_from_csv(
        drive, csv_path=str(csv_path), parent_id=parent_id
    )

    assert label_to_id == {"Invoices": "F_INVOICES"}
    assert drive.created_bodies == []  # found, not created

    # CSV should now be updated with F_INVOICES
    rows = folder_catalog.load_catalog(str(csv_path))
    assert rows[0]["folder_id"] == "F_INVOICES"


def test_ensure_folders_creates_new_folder_when_missing(tmp_path, monkeypatch):
    """
    If folder_id is empty and no folder exists by that label, ensure_folders_from_csv
    should create a new folder and update the CSV.
    """
    parent_id = "PARENT123"
    csv_path = tmp_path / "folders.csv"

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["label", "folder_id", "description"])
        writer.writeheader()
        writer.writerow({"label": "Invoices", "folder_id": "", "description": "Invoices folder"})

    monkeypatch.setattr(folder_catalog, "FOLDER_CATALOG_CSV", str(csv_path))
    monkeypatch.setattr(folder_catalog, "DRIVE_PARENT_ID", parent_id)

    drive = FakeDrive(parent_id=parent_id)

    label_to_id, label_desc, allowed = folder_catalog.ensure_folders_from_csv(
        drive, csv_path=str(csv_path), parent_id=parent_id
    )

    # One folder should have been created
    assert len(drive.created_bodies) == 1
    created_body = drive.created_bodies[0]
    assert created_body["name"] == "Invoices"
    assert created_body["parents"] == [parent_id]

    # The generated ID is internal to FakeDrive (e.g., "F_1"), so just assert it exists
    assert "Invoices" in label_to_id
    new_id = label_to_id["Invoices"]
    assert new_id in drive.folders_by_id

    # CSV should now be updated
    rows = folder_catalog.load_catalog(str(csv_path))
    assert rows[0]["folder_id"] == new_id
