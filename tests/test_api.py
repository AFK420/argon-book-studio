"""
Integration Test Suite for Argon Book Studio Pro FastAPI Endpoints.
"""

from fastapi.testclient import TestClient
from app.main import app
import pymupdf
import docx

client = TestClient(app)

def test_root_index():
    r = client.get("/")
    assert r.status_code == 200
    assert "ARGON BOOK STUDIO" in r.text

def test_api_profiles():
    r = client.get("/api/profiles")
    assert r.status_code == 200
    data = r.json()
    assert len(data["profiles"]) == 5
    assert "trim_presets" in data

def test_api_books():
    r = client.get("/api/books")
    assert r.status_code == 200
    books = r.json()["books"]
    assert len(books) == 5

def test_api_book_book01():
    r = client.get("/api/book/book01")
    assert r.status_code == 200
    b1 = r.json()
    assert b1["profile"]["id"] == "book01"
    assert len(b1["pagination"]["spreads"]) >= 4
    assert "settings" in b1
    assert "filmstrip" in b1["pagination"]

def test_api_project_settings_update():
    r = client.post("/api/project/book01/settings", json={
        "trim_width_in": 5.5,
        "trim_height_in": 8.5,
        "margins": {"inside_gutter_in": 0.8}
    })
    assert r.status_code == 200
    data = r.json()
    assert data["settings"]["trim_width_in"] == 5.5
    assert data["settings"]["margins"]["inside_gutter_in"] == 0.8
    assert len(data["pagination"]["spreads"]) > 0

def test_api_inline_manuscript_editing():
    r = client.post("/api/manuscript/book01/edit-element", json={
        "element_id": "ch01_p02",
        "text": "The Thames river police had laid the body across five deal planks."
    })
    assert r.status_code == 200
    assert r.json()["status"] == "success"

def test_api_insert_and_wrap_element():
    r = client.post("/api/manuscript/book01/insert-element", json={
        "target_id": "ch01_p02",
        "element_type": "scene_break",
        "content": "***"
    })
    assert r.status_code == 200
    assert r.json()["status"] == "success"

    r2 = client.post("/api/manuscript/book01/wrap-container", json={
        "element_id": "ch01_p02",
        "container_tag": "inquest-writ"
    })
    assert r2.status_code == 200
    assert r2.json()["status"] == "success"

def test_api_image_lab_preview():
    r = client.post("/api/image-lab/preview", json={
        "book_id": "book01",
        "asset_id": "b01_asset_01",
        "filter_preset": "cyanotype_silver_plate",
        "contrast": 1.4,
        "grain": 0.1,
        "vignette": 0.4
    })
    assert r.status_code == 200
    assert "preview_data_uri" in r.json()
    assert r.json()["preview_data_uri"].startswith("data:image/jpeg;base64,")

def test_api_update_anchor():
    r = client.post("/api/manifest/book01/update-anchor", json={"asset_id": "b01_asset_02", "new_anchor": "ch01_p02"})
    assert r.status_code == 200
    assert r.json()["status"] == "success"

def test_api_auto_insert_tailpiece():
    r = client.post("/api/tailpiece/auto-insert", json={"book_id": "book01", "page_number": 8, "enable": True})
    assert r.status_code == 200
    assert r.json()["status"] == "success"

def test_api_export_pdf():
    r = client.post("/api/export/pdf", json={"book_id": "book01", "bleed": False})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    pdf_bytes = r.content
    assert len(pdf_bytes) > 5000

def test_api_export_docx():
    r = client.post("/api/export/docx", json={"book_id": "book01"})
    assert r.status_code == 200
    assert len(r.content) > 5000

def test_api_export_epub():
    r = client.post("/api/export/epub", json={"book_id": "book01"})
    assert r.status_code == 200
    assert len(r.content) > 1000

def test_api_export_all_zip():
    r = client.post("/api/export/all", json={"book_id": "book01"})
    assert r.status_code == 200
    assert len(r.content) > 10000

def test_api_update_paragraph_v2():
    r = client.post("/api/manuscript/book01/update-paragraph", json={
        "element_id": "ch01_p01",
        "text": "The Thames river police stood motionless in the freezing cold.",
        "block_type": "inworld_writ",
        "page_break_before": True,
        "keep_with_next": True,
        "scene_break_after": "book_svg"
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["element_id"] == "ch01_p01"
    assert "pagination" in data

def test_api_update_manifest_asset_v2():
    r = client.post("/api/manifest/book01/update-asset", json={
        "asset_id": "b01_asset_01",
        "updates": {
            "placement": "Full-Page Recto Plate",
            "frame_style": "double_brass_frame",
            "width_pct": 95,
            "max_height_in": 7.5,
            "caption": "The Thames Estuary at Twilight",
            "caption_position": "below"
        }
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "success"
    assert data["asset"]["placement"] == "Full-Page Recto Plate"
    assert data["asset"]["frame_style"] == "double_brass_frame"

def test_api_pdf_raster_preview():
    # 1. Info endpoint
    info_res = client.get("/api/pdf-info/book01")
    assert info_res.status_code == 200
    info_data = info_res.json()
    assert "total_pages" in info_data
    assert info_data["total_pages"] > 0

    # 2. Page preview endpoint
    page_res = client.get("/api/pdf-preview/book01/1?dpi=150")
    assert page_res.status_code == 200
    assert page_res.headers["content-type"] == "image/png"
    assert len(page_res.content) > 1000

