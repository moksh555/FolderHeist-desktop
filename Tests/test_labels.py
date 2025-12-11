# Tests/test_labels.py

import sys
from pathlib import Path as _Path

# Ensure project root is on sys.path
ROOT_DIR = _Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from services import labels  # type: ignore
from services import state   # type: ignore


class DummyDrive:
    """Placeholder object; not actually used by our fake ensure_folders_from_csv."""
    pass


def test_hydrate_labels_initializes_state(monkeypatch):
    """
    hydrate_labels should call ensure_folders_from_csv and set_label_mappings
    when state is not yet initialized.
    """
    calls = {}

    def fake_ensure_folders_from_csv(drive, csv_path=None, parent_id=None):
        calls["ensure_called"] = True
        # Return some fake mappings
        label_to_id = {"Invoices": "F_INVOICES", "Taxes": "F_TAXES"}
        label_desc = {"Invoices": "All invoice docs", "Taxes": "Tax docs"}
        allowed = ["Invoices", "Taxes"]
        return label_to_id, label_desc, allowed

    def fake_set_label_mappings(label_to_id, label_desc, allowed):
        calls["set_called"] = True
        # Actually set them in state so we can assert
        state.LABEL_TO_ID = dict(label_to_id)
        state.LABEL_DESC = dict(label_desc)
        state.ALLOWED = list(allowed)
        # Mark state as initialized
        monkeypatch.setattr(state, "_INITIALIZED", True, raising=False)

    # Reset state for this test
    state.LABEL_TO_ID = {}
    state.LABEL_DESC = {}
    state.ALLOWED = []
    monkeypatch.setattr(state, "_INITIALIZED", False, raising=False)

    monkeypatch.setattr(labels, "ensure_folders_from_csv", fake_ensure_folders_from_csv)
    monkeypatch.setattr(labels, "set_label_mappings", fake_set_label_mappings)

    drive = DummyDrive()
    labels.hydrate_labels(drive)

    assert calls.get("ensure_called") is True
    assert calls.get("set_called") is True

    assert state.LABEL_TO_ID == {"Invoices": "F_INVOICES", "Taxes": "F_TAXES"}
    assert state.ALLOWED == ["Invoices", "Taxes"]
    assert state.LABEL_DESC["Invoices"] == "All invoice docs"


def test_hydrate_labels_skips_when_already_initialized(monkeypatch):
    """
    When state is already initialized and force=False, hydrate_labels
    should be a no-op (i.e., not call ensure_folders_from_csv again).
    """
    calls = {"ensure_called": 0}

    def fake_ensure_folders_from_csv(drive, csv_path=None, parent_id=None):
        calls["ensure_called"] += 1
        return {}, {}, []

    # Pretend state is already initialized
    monkeypatch.setattr(state, "_INITIALIZED", True, raising=False)

    # Monkeypatch ensure_folders_from_csv used in labels module
    monkeypatch.setattr(labels, "ensure_folders_from_csv", fake_ensure_folders_from_csv)

    drive = DummyDrive()
    labels.hydrate_labels(drive, force=False)

    # ensure_folders_from_csv should never be called
    assert calls["ensure_called"] == 0

    # But if we force=True, it should call it
    labels.hydrate_labels(drive, force=True)
    assert calls["ensure_called"] == 1
