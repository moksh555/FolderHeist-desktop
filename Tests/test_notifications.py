import sys
from pathlib import Path as _Path

ROOT_DIR = _Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR))

from flask import Flask
from services.notifications import register_routes
from services import folder_catalog  # type: ignore
import json


def test_health_route():
    app = Flask(__name__)
    register_routes(app)
    client = app.test_client()

    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_folders_route(monkeypatch, tmp_path):
    # Prepare a temporary folders.csv via folder_catalog
    csv_path = tmp_path / "folders.csv"
    csv_path.write_text("label,folder_id,description\nInvoices,F1,Invoice docs\n", encoding="utf-8")

    monkeypatch.setattr(folder_catalog, "FOLDER_CATALOG_CSV", str(csv_path))

    app = Flask(__name__)
    register_routes(app)
    client = app.test_client()

    resp = client.get("/folders")
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, list)
    assert data[0]["label"] == "Invoices"
