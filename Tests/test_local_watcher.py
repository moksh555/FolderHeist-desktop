# Tests/test_local_watcher.py

import sys
from pathlib import Path as _Path

# Ensure project root is on sys.path
ROOT_DIR = _Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from services import local_watcher  # type: ignore
from services import processing      # type: ignore


class DummyDrive:
    pass


class FakeEvent:
    def __init__(self, src_path: str, is_directory: bool = False):
        self.src_path = src_path
        self.is_directory = is_directory


class FakeObserver:
    """
    Minimal fake Observer to capture how start_local_watch schedules things.
    """

    def __init__(self):
        self.scheduled = []
        self.started = False

    def schedule(self, handler, path, recursive=False):
        self.scheduled.append((handler, path, recursive))

    def start(self):
        self.started = True

    def stop(self):
        self.started = False

    def join(self, timeout=None):
        pass


def test_make_event_handler_calls_process_local_file(tmp_path, monkeypatch):
    """
    Given a created file event, the event handler should call
    processing.process_local_file with the drive and file path.
    """
    calls = []

    def fake_process_local_file(drive, path):
        calls.append((drive, path))

    monkeypatch.setattr(processing, "process_local_file", fake_process_local_file)

    # We don't actually want real watchdog, so monkeypatch _watchdog
    class DummyFileSystemEventHandler:
        def __init__(self, *args, **kwargs):
            pass

    def fake_watchdog():
        # Observer is unused here, just return placeholder
        return FakeObserver, DummyFileSystemEventHandler

    monkeypatch.setattr(local_watcher, "_watchdog", fake_watchdog)

    drive = DummyDrive()
    handler = local_watcher.make_event_handler(drive)

    # Create a real file in a temp dir
    file_path = tmp_path / "test_doc.pdf"
    file_path.write_bytes(b"content")

    event = FakeEvent(str(file_path), is_directory=False)

    handler.on_created(event)

    # One call to process_local_file with correct args
    assert len(calls) == 1
    d, p = calls[0]
    assert d is drive
    assert p == file_path


def test_start_local_watch_uses_watch_dir_and_observer(tmp_path, monkeypatch):
    """
    start_local_watch should:

    - ensure LOCAL_WATCH_DIR exists,
    - construct an event handler,
    - schedule it on an Observer,
    - start the Observer,
    - and return the observer.
    """
    # Override LOCAL_WATCH_DIR in the local_watcher module to our temp path
    monkeypatch.setattr(local_watcher, "LOCAL_WATCH_DIR", str(tmp_path))

    # Fake processing handler via make_event_handler
    handler_instances = []

    def fake_make_event_handler(drive):
        class H:
            pass
        h = H()
        handler_instances.append(h)
        return h

    monkeypatch.setattr(local_watcher, "make_event_handler", fake_make_event_handler)

    # Provide a fake watchdog Observer
    def fake_watchdog():
        return FakeObserver, object  # FileSystemEventHandler type not used here

    monkeypatch.setattr(local_watcher, "_watchdog", fake_watchdog)

    drive = DummyDrive()
    obs = local_watcher.start_local_watch(drive)

    # Folder should exist
    assert tmp_path.exists()
    # Observer should be our FakeObserver
    assert isinstance(obs, FakeObserver)
    # It should have started
    assert obs.started is True
    # It should have one scheduled handler
    assert len(obs.scheduled) == 1
    handler, path, recursive = obs.scheduled[0]
    assert handler is handler_instances[0]
    assert path == str(tmp_path)
    assert recursive is False
