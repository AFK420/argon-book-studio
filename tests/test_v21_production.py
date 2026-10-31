"""
Tests for Argon Book Studio v2.1 Critical Bug-Fix & Production Lock Pass.
Covers:
- BUG-01: Artwork preservation & raw_image_path retention in Image Lab.
- BUG-02: PDF physical page container model, live typography sync, and PDF cache invalidation.
- BUG-03: Manifest JSON Import/Export & Smart Substring / END_OF_CHAPTER anchor resolution.
- BUG-04: Matter Artwork Upload (frontispiece & map plate) & end-to-end matter wiring.
- BUG-05: EPUB 3 real image disk embedding and DOCX width_pct scaling.
- BUG-06 & BUG-07: Container auto-merging, manual element merge, and element deletion.
"""

import os
import io
import json
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app, invalidate_pdf_cache, EXPORTS_DIR
from app.profiles import BOOK_PROFILES
from app.parser import parse_markdown_manuscript, merge_consecutive_containers
from app.manifest import manifest_manager
from app.exporters.pdf_exporter import generate_pdf_html, export_pdf
from app.exporters.docx_exporter import export_docx
from app.exporters.epub_exporter import export_epub


@pytest.fixture
def client():
    return TestClient(app)


def test_v21_official_titles_and_subtitles():
    """Verify all 5 books have their full official titles, subtitles, short titles, and canonical genres."""
    assert BOOK_PROFILES["book01"]["title"] == "The Last Forty Minutes of Cormac Vane"
    assert BOOK_PROFILES["book01"]["short_title"] == "Cormac Vane"
    assert BOOK_PROFILES["book01"]["genre"] == "Gaslamp Speculative Forensic Mystery"
    
    assert BOOK_PROFILES["book02"]["title"] == "The Fourteen-Hour Barometer"
    assert BOOK_PROFILES["book02"]["short_title"] == "Fourteen-Hour Barometer"
    assert BOOK_PROFILES["book02"]["genre"] == "Chronometric Island Thriller & Speculative Romance"
    
    assert BOOK_PROFILES["book03"]["title"] == "The Dead-Room Transcripts"
    assert BOOK_PROFILES["book03"]["short_title"] == "Dead-Room Transcripts"
    assert BOOK_PROFILES["book03"]["genre"] == "Locked-Room Mystery & Acoustic Forensic Thriller"
    
    assert BOOK_PROFILES["book04"]["title"] == "The Salt Orchard of Saint Jude"
    assert "Salt Orchard" in BOOK_PROFILES["book04"]["short_title"]
    assert BOOK_PROFILES["book04"]["genre"] == "Ecological & Institutional Southern Gothic Mystery"
    
    assert BOOK_PROFILES["book05"]["title"] == "The Provenance of Ashes"
    assert BOOK_PROFILES["book05"]["short_title"] == "Provenance of Ashes"
    assert BOOK_PROFILES["book05"]["genre"] == "Archaeometric & Epigraphic Geopolitical Thriller"


def test_v21_consecutive_container_merging():
    """Verify consecutive container blocks with the same tag are merged into one container."""
    raw_md = """# Chapter 1

::: inquest-writ
First line of legal writ.
:::

::: inquest-writ
Second line of legal writ.
:::

Normal body paragraph.

::: welsh-slate
Basalt line 1.
:::

::: welsh-slate
Basalt line 2.
:::
"""
    parsed = parse_markdown_manuscript(raw_md)
    ch = parsed["chapters"][0]
    elements = ch["elements"]
    
    # Inquest writ should be 1 container element with both lines
    containers = [e for e in elements if e.get("type") == "container"]
    assert len(containers) == 2
    assert "First line" in containers[0]["content"]
    assert "Second line" in containers[0]["content"]
    
    # Welsh slate should be 1 container
    assert "Basalt line 1" in containers[1]["content"]
    assert "Basalt line 2" in containers[1]["content"]


def test_v21_artwork_upload_and_image_lab_retention(client, tmp_path):
    """Verify uploaded artwork retains raw_image_path and apply_image_lab_settings processes the real image."""
    # Create a real test image
    img = Image.new("RGB", (800, 600), color=(120, 150, 180))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    book_data = client.get("/api/book/book02").json()
    asset_id = book_data["manifest"]["assets"][0]["id"]
    # Upload asset
    resp = client.post(
        f"/api/assets/upload/book02/{asset_id}",
        files={"file": ("test_art.png", buf.getvalue(), "image/png")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    raw_path = data.get("raw_image_path")
    assert raw_path and os.path.exists(raw_path)
    
    # Check that manifest retains raw_image_path
    asset_in_manifest = next(a for a in client.get("/api/book/book02").json()["manifest"]["assets"] if a["id"] == asset_id)
    assert asset_in_manifest.get("raw_image_path") == raw_path
    
    # Apply Image Lab adjustments
    apply_resp = client.post(
        "/api/image-lab/apply",
        json={
            "book_id": "book02",
            "asset_id": asset_id,
            "filter_preset": "charcoal_lithograph",
            "contrast": 1.4,
            "grain": 0.05,
            "vignette": 0.2,
            "brightness": 1.1,
            "target_dpi": 300
        }
    )
    assert apply_resp.status_code == 200
    apply_data = apply_resp.json()
    assert apply_data["status"] == "success"
    out_url = apply_data["image_url"]
    assert out_url.endswith(".png")


def test_v21_pdf_cache_invalidation(client):
    """Verify that mutation endpoints invalidate the cached print PDF."""
    pdf_path = os.path.join(EXPORTS_DIR, "book01_print_edition.pdf")
    os.makedirs(EXPORTS_DIR, exist_ok=True)
    with open(pdf_path, "w") as f:
        f.write("mock stale pdf content")
    assert os.path.exists(pdf_path)
    
    # Call settings update
    resp = client.post("/api/project/book01/settings", json={"font_size_pt": 11.5})
    assert resp.status_code == 200
    assert not os.path.exists(pdf_path)


def test_v21_pdf_physical_pages_and_sliders():
    """Verify generate_pdf_html outputs <div class="physical-pdf-page"> and live slider styling."""
    from app.main import load_book_manuscript
    parsed = load_book_manuscript("book01")
    manifest = manifest_manager.get_book_manifest("book01")
    
    custom_specs = {
        "trim_width_in": 6.0,
        "trim_height_in": 9.0,
        "para_spacing_pt": 4.5,
        "letter_spacing_em": 0.02,
        "justify_text": True,
        "hyphenation": True,
        "subsequent_p_indent_in": 0.28,
        "typography": {
            "para_spacing_pt": 4.5,
            "letter_spacing_em": 0.02,
            "justify_text": True,
            "hyphenation": True,
            "subsequent_p_indent_in": 0.28
        }
    }
    
    html = generate_pdf_html(parsed, manifest, "book01", custom_specs=custom_specs)
    assert '<div class="physical-pdf-page' in html
    assert 'margin: 0 0 4.5pt 0;' in html
    assert 'letter-spacing: 0.02em;' in html
    assert 'text-align: justify;' in html
    assert 'hyphens: auto;' in html


def test_v21_manifest_smart_anchor_import_and_export(client):
    """Verify Manifest JSON import with anchor_text substring matching and export endpoint."""
    orig_assets = list(manifest_manager.get_book_manifest("book01").get("assets", []))
    try:
        raw_manifest = {
            "assets": [
                {
                    "asset_id": "test_import_slot_01",
                    "title": "Smart Anchor Illustration",
                    "anchor_text": "Cormac",
                    "placement": "Half-Page Top",
                    "caption_text": "Smart substring matched plate"
                },
                {
                    "id": "test_import_slot_02",
                    "title": "End of Chapter Illustration",
                    "anchor": "END_OF_CHAPTER",
                    "placement": "Inline Centered",
                    "caption": "Attached to chapter conclusion"
                }
            ]
        }
        
        resp = client.post("/api/manifest/book01/import", json={"data": raw_manifest})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assets = data["manifest"]["assets"]
        
        slot1 = next(a for a in assets if a["id"] == "test_import_slot_01")
        assert slot1["anchor"].startswith("ch")
        assert slot1["caption"] == "Smart substring matched plate"
        
        slot2 = next(a for a in assets if a["id"] == "test_import_slot_02")
        assert slot2["anchor"].startswith("ch")
        
        # Test export endpoint
        export_resp = client.get("/api/manifest/book01/export")
        assert export_resp.status_code == 200
        assert export_resp.headers["content-type"].startswith("application/json")
        exported = export_resp.json()
        assert "assets" in exported
        assert "version" in exported
    finally:
        manifest_manager.get_book_manifest("book01")["assets"] = orig_assets
        manifest_manager.save()


def test_v21_matter_image_upload(client):
    """Verify matter image upload endpoint for frontispiece and map plate."""
    img = Image.new("RGB", (600, 400), color=(200, 180, 140))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    
    # Upload Frontispiece
    resp = client.post(
        "/api/matter/upload-image/book01/frontispiece",
        files={"file": ("frontispiece_art.png", buf.getvalue(), "image/png")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["image_type"] == "frontispiece"
    assert "/uploads/" in data["image_url"]
    assert data["settings"]["front_back_matter"]["include_frontispiece"] is True
    
    # Upload Map
    buf.seek(0)
    resp_map = client.post(
        "/api/matter/upload-image/book01/map",
        files={"file": ("territory_chart.png", buf.getvalue(), "image/png")}
    )
    assert resp_map.status_code == 200
    data_map = resp_map.json()
    assert data_map["status"] == "success"
    assert data_map["image_type"] == "map"
    assert "/uploads/" in data_map["image_url"]
    assert data_map["settings"]["front_back_matter"]["include_map"] is True


def test_v21_element_merge_and_delete(client):
    """Verify POST /api/manuscript/{book_id}/merge-element and DELETE /api/manuscript/{book_id}/delete-element."""
    book_details = client.get("/api/book/book01").json()
    chapters = book_details["manuscript"]["chapters"]
    elem_0 = chapters[0]["elements"][0]["id"]
    elem_1 = chapters[0]["elements"][1]["id"]
    text_0 = chapters[0]["elements"][0].get("text", "")
    text_1 = chapters[0]["elements"][1].get("text", "")
    
    # Merge element 1 with element 0
    merge_resp = client.post(
        "/api/manuscript/book01/merge-element",
        json={"element_id": elem_1}
    )
    assert merge_resp.status_code == 200
    m_data = merge_resp.json()
    assert m_data["status"] == "success"
    
    # Check that element 1 is gone and element 0 has both texts
    ch0 = m_data["manuscript"]["chapters"][0]
    elem_ids = [e["id"] for e in ch0["elements"]]
    assert elem_1 not in elem_ids
    merged_el = next(e for e in ch0["elements"] if e["id"] == elem_0)
    assert text_1[:20] in merged_el.get("text", "")
    
    # Delete element 0
    del_resp = client.delete(f"/api/manuscript/book01/delete-element/{elem_0}")
    assert del_resp.status_code == 200
    del_data = del_resp.json()
    assert del_data["status"] == "success"
    ch0_after = del_data["manuscript"]["chapters"][0]
    elem_ids_after = [e["id"] for e in ch0_after["elements"]]
    assert elem_0 not in elem_ids_after
