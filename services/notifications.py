# services/notifications.py

"""
Lightweight API layer.

Right now this module only exposes a couple of simple routes:
- GET /health  -> quick status check
- GET /folders -> read folders.csv and return its contents as JSON

This is a starting point for your future "manage CSV via web UI" work.
No Drive webhooks, no watch channels.
"""

from flask import Blueprint, jsonify

from services.folder_catalog import load_catalog


def register_routes(app):
    bp = Blueprint("api", __name__)

    @bp.get("/health")
    def health():
        return jsonify({"status": "ok"})

    @bp.get("/folders")
    def get_folders():
        """
        Return the current folder catalog (folders.csv) as JSON.
        Structure:
        [
          {"label": "...", "folder_id": "...", "description": "..."},
          ...
        ]
        """
        rows = load_catalog()
        return jsonify(rows)

    app.register_blueprint(bp)
