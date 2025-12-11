# services/state.py

"""
Runtime state for label/folder mappings.

This module acts as a simple in-memory registry that other parts of the
application can read from:

- LABEL_TO_ID:  { label -> folder_id }
- LABEL_DESC:   { label -> description }
- ALLOWED:      [ label1, label2, ... ]
"""

from typing import Dict, List, Optional

# Global mappings populated at startup by labels.py
LABEL_TO_ID: Dict[str, str] = {}
LABEL_DESC: Dict[str, str] = {}
ALLOWED: List[str] = []

_INITIALIZED: bool = False


def set_label_mappings(
    label_to_id: Dict[str, str],
    label_desc: Dict[str, str],
    allowed: List[str],
) -> None:
    """
    Replace the global label mappings with new values.

    This is typically called once at startup by labels.hydrate_labels(drive),
    but can be called again if the CSV is edited and reloaded.
    """
    global LABEL_TO_ID, LABEL_DESC, ALLOWED, _INITIALIZED

    LABEL_TO_ID = dict(label_to_id)
    LABEL_DESC = dict(label_desc)
    ALLOWED = list(allowed)
    _INITIALIZED = True

    print(
        f"[STATE] set_label_mappings: "
        f"{len(ALLOWED)} labels, "
        f"{len(LABEL_TO_ID)} folder IDs, "
        f"{len(LABEL_DESC)} descriptions."
    )


def is_initialized() -> bool:
    """
    Return True if label mappings have been set at least once.
    """
    return _INITIALIZED


def get_folder_id(label: str) -> Optional[str]:
    """
    Get the Drive folder_id for a given label, or None if unknown.
    """
    return LABEL_TO_ID.get(label)


def get_description(label: str) -> Optional[str]:
    """
    Get the description for a given label, or None if not present.
    """
    return LABEL_DESC.get(label)


def get_allowed_labels() -> List[str]:
    """
    Return a copy of the allowed label list.
    """
    return list(ALLOWED)
