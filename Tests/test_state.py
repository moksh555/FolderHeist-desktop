# Tests/test_state.py

import sys
from pathlib import Path as _Path

# Ensure project root is on sys.path
ROOT_DIR = _Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from services import state  # type: ignore


def test_initial_state_is_empty():
    # Before we set anything, everything should be empty / falsey
    assert state.LABEL_TO_ID == {}
    assert state.LABEL_DESC == {}
    assert state.ALLOWED == []
    assert state.is_initialized() is False


def test_set_label_mappings_populates_globals():
    label_to_id = {"Invoices": "F_INVOICES", "Taxes": "F_TAXES"}
    label_desc = {"Invoices": "All invoice docs", "Taxes": "Tax-related docs"}
    allowed = ["Invoices", "Taxes"]

    state.set_label_mappings(label_to_id, label_desc, allowed)

    assert state.is_initialized() is True

    # Check globals
    assert state.LABEL_TO_ID == label_to_id
    assert state.LABEL_DESC == label_desc
    assert state.ALLOWED == allowed

    # Check helpers
    assert state.get_folder_id("Invoices") == "F_INVOICES"
    assert state.get_description("Taxes") == "Tax-related docs"
    assert state.get_folder_id("Unknown") is None
    assert state.get_description("Unknown") is None

    # get_allowed_labels should return a copy, not the same list object
    allowed_copy = state.get_allowed_labels()
    assert allowed_copy == allowed
    assert allowed_copy is not allowed  # ensure it’s a copy, not alias
