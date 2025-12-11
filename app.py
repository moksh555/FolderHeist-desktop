from flask import Flask
from threading import Thread
from config import APP_URL, PORT
from services.notifications import register_routes

from services.drive_client import get_drive
from services.labels import hydrate_labels
from services.local_watcher import start_local_watch

app = Flask(__name__)
register_routes(app)


def start_background_watcher(drive):
    def run_watcher():
        observer = start_local_watch(drive)
        observer.join()
    t = Thread(target=run_watcher, daemon=True)
    t.start()
    return t


if __name__ == "__main__":
    print(APP_URL)

    try:
        drive = get_drive()
        hydrate_labels(drive)
        start_background_watcher(drive)
    except Exception as e:
        print(f"[BOOT] initialization failed: {e}")

    app.run(host="0.0.0.0", port=PORT)
