# Tests/test_processing_local.py

import sys
from pathlib import Path as _Path

# Ensure project root is on sys.path
ROOT_DIR = _Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from services import processing  # type: ignore
from services import state       # type: ignore
from services import drive_client

class DummyDrive:
    """We don't actually talk to Drive here; this holds calls for inspection."""
    def __init__(self):
        self.upload_calls = []


def test_process_local_file_happy_path(tmp_path, monkeypatch):
    """
    Given a local file and a confident Gemini label that exists in LABEL_TO_ID,
    process_local_file should call upload_file_to_folder with correct args.
    """
    # --- Arrange ---
    # Fake local file
    file_path = tmp_path / "invoice_january.pdf"
    file_path.write_bytes(b"fake pdf content")

    # Fake state mappings
    state.LABEL_TO_ID = {"Invoices": "F_INVOICES"}
    state.LABEL_DESC = {"Invoices": "All invoice docs"}
    state.ALLOWED = ["Invoices"]

    # Fake Gemini router
    def fake_choose_folder_with_gemini(filename, text, allowed_labels, label_desc, temperature=0.15):
        return {"label": "Invoices", "confidence": 0.99, "rationale": "Test route"}

    # Fake uploader
    upload_calls = []

    def fake_upload_file_to_folder(drive, local_path, folder_id):
        upload_calls.append((drive, local_path, folder_id))
        return "NEW_FILE_ID"

    monkeypatch.setattr(processing, "choose_folder_with_gemini", fake_choose_folder_with_gemini)
    monkeypatch.setattr(drive_client, "upload_file_to_folder", fake_upload_file_to_folder)


    drive = DummyDrive()

    # --- Act ---
    processing.process_local_file(drive, file_path)

    # --- Assert ---
    assert len(upload_calls) == 1
    d, p, fid = upload_calls[0]
    assert d is drive
    assert p == file_path
    assert fid == "F_INVOICES"


def test_process_local_file_skips_when_no_valid_label(tmp_path, monkeypatch):
    """
    If Gemini returns a label not in LABEL_TO_ID and heuristics don't fix it,
    process_local_file should skip upload.
    """
    file_path = tmp_path / "random.bin"
    file_path.write_bytes(b"some binary-ish content")

    # Empty state (no allowed labels)
    state.LABEL_TO_ID = {}
    state.LABEL_DESC = {}
    state.ALLOWED = []

    def fake_choose_folder_with_gemini(filename, text, allowed_labels, label_desc, temperature=0.15):
        # Return some nonsense label
        return {"label": "UnknownLabel", "confidence": 0.1, "rationale": "Test bad"}

    upload_calls = []

    def fake_upload_file_to_folder(drive, local_path, folder_id):
        upload_calls.append((drive, local_path, folder_id))
        return "NEW_FILE_ID"

    monkeypatch.setattr(processing, "choose_folder_with_gemini", fake_choose_folder_with_gemini)
    monkeypatch.setattr(drive_client, "upload_file_to_folder", fake_upload_file_to_folder)

    drive = DummyDrive()

    processing.process_local_file(drive, file_path)

    # Should NOT have uploaded anything
    assert upload_calls == []
