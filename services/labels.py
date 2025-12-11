# services/labels.py

"""
Label / folder initialization logic.

This module connects the folder catalog (CSV + Drive folders)
with the in-memory state registry.

Typical usage:

    from services.drive_client import get_drive
    from services.labels import hydrate_labels

    drive = get_drive()
    hydrate_labels(drive)

After that, other modules can import from services.state:

    from services.state import LABEL_TO_ID, LABEL_DESC, ALLOWED
"""

from typing import Any

from services.folder_catalog import ensure_folders_from_csv
from services.state import (
    set_label_mappings,
    LABEL_TO_ID,
    LABEL_DESC,
    ALLOWED,
    is_initialized,
)


def hydrate_labels(drive: Any, force: bool = False) -> None:
    """
    Ensure label mappings are loaded from folders.csv and Drive.

    - If state is already initialized and force=False, this is a no-op.
    - If force=True, it will re-read CSV, re-check Drive folders, and
      update the in-memory mappings.

    This should typically be called once at startup, before processing
    any files.
    """
    if is_initialized() and not force:
        print("[LABELS] Already initialized; skipping hydrate_labels()")
        return

    label_to_id, label_desc, allowed = ensure_folders_from_csv(drive)
    set_label_mappings(label_to_id, label_desc, allowed)
    print("[LABELS] Hydration complete.")


__all__ = [
    "hydrate_labels",
    "LABEL_TO_ID",
    "LABEL_DESC",
    "ALLOWED",
]
