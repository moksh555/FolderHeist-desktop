# services/local_watcher.py

"""
Local folder watcher.

Watches LOCAL_WATCH_DIR for new files and sends them through the
process_local_file pipeline.

We use watchdog, but imports are lazy so tests (or environments
without watchdog installed) can still import this module.
"""

import time
from pathlib import Path
from typing import Any

from config import LOCAL_WATCH_DIR
from services import processing


def _watchdog():
    """
    Lazy-import watchdog so that unit tests and environments without
    watchdog installed can still import this module safely.
    """
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    return Observer, FileSystemEventHandler


def _ensure_watch_dir() -> Path:
    """
    Ensure the watch directory exists and return it as a Path.
    """
    watch_dir = Path(LOCAL_WATCH_DIR)
    watch_dir.mkdir(parents=True, exist_ok=True)
    return watch_dir


def _is_temp_or_hidden(path: Path) -> bool:
    """
    Optional small filter to ignore hidden/temporary files (like .DS_Store).
    """
    name = path.name
    if name.startswith("."):
        return True
    if name.endswith("~"):
        return True
    return False


def make_event_handler(drive: Any):
    """
    Create and return a FileSystemEventHandler subclass instance
    bound to a specific Drive client.

    We keep this split out to make testing easier.
    """
    Observer, FileSystemEventHandler = _watchdog()  # type: ignore[assignment]

    class NewFileHandler(FileSystemEventHandler):  # type: ignore[misc]
        def __init__(self, drive_client):
            super().__init__()
            self.drive = drive_client

        def on_created(self, event):
            # Ignore directories
            if event.is_directory:
                return

            path = Path(event.src_path)

            # Optionally ignore hidden/temp files
            if _is_temp_or_hidden(path):
                print(f"[WATCH] Ignoring temp/hidden file: {path}")
                return

            # Give the OS a moment to finish writing the file
            time.sleep(0.3)

            try:
                print(f"[WATCH] New file detected: {path}")
                processing.process_local_file(self.drive, path)
            except Exception as e:
                print(f"[WATCH] Error processing {path}: {e}")

    return NewFileHandler(drive)


def start_local_watch(drive: Any):
    """
    Start a watchdog observer on LOCAL_WATCH_DIR.

    Returns the observer so the caller can stop/join it if needed.

    Typical usage:

        drive = get_drive()
        hydrate_labels(drive)
        observer = start_local_watch(drive)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            observer.join()
    """
    Observer, _ = _watchdog()
    watch_dir = _ensure_watch_dir()

    handler = make_event_handler(drive)
    observer = Observer()
    observer.schedule(handler, str(watch_dir), recursive=False)
    observer.start()

    print(f"[WATCH] Watching local folder: {watch_dir}")
    return observer
