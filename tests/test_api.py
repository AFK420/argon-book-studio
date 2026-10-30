"""
Integration Test Suite for Argon Book Studio FastAPI Endpoints.
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
    assert data["specs"]["trim_width_in"] == 6.0
    assert data["specs"]["trim_height_in"] == 9.0

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
    assert len(b1["manifest"]["assets"]) >= 1

def test_api_book_all_profiles():
    for bid in ["book01", "book02", "book03", "book04", "book05"]:
        r = client.get(f"/api/book/{bid}")
        assert r.status_code == 200
        data = r.json()
        assert data["book_id"] == bid
        assert len(data["pagination"]["spreads"]) > 0

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
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    assert abs(doc[0].rect.width - 432.0) < 5.0
    assert abs(doc[0].rect.height - 648.0) < 5.0
    doc.close()

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
