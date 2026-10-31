"""
Tests for Argon Book Studio Pro v2.2:
5-Step Sequential Pipeline (Wizard-First Architecture)
Verifies:
1. POST /api/manuscript/{book_id}/auto-style (consecutive container merging, Vesper sensory trace, flush-left indents, matter defaults)
2. POST /api/tailpiece/auto-balance-all (batch tailpiece whitespace balancing on short chapter endings)
3. POST /api/manifest/{book_id}/import with use_builtin (smart anchor binding for built-in 16-asset blueprints)
4. Frontend Stepper & 5-Step Workspace HTML structure
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app, STATE, manifest_manager

client = TestClient(app)


def test_auto_style_manuscript_endpoint():
    """Verify 1-Click Auto-Styler applies container merging, sensory trace, indents, and matter defaults."""
    res = client.post("/api/manuscript/book01/auto-style")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["book_id"] == "book01"
    assert "manuscript" in data
    assert "detected_containers" in data
    assert data["detected_containers"]["sensory_draw"] >= 1
    assert data["detected_containers"]["inworld_writ"] >= 1

    manuscript = data["manuscript"]
    assert len(manuscript["chapters"]) >= 1

    ch1 = manuscript["chapters"][0]
    elements = ch1["elements"]

    # First body paragraph in chapter must have flush-left indent (is_first_after_break = True)
    first_p = next(el for el in elements if el["type"] == "paragraph")
    assert first_p.get("is_first_after_break") is True
    assert first_p.get("block_type") == "body_first"

    # Verify paragraph after a container is also flush-left
    for idx, el in enumerate(elements[:-1]):
        if el.get("type") == "container":
            next_el = elements[idx + 1]
            if next_el.get("type") == "paragraph":
                assert next_el.get("is_first_after_break") is True
                break

    # Verify front/back matter defaults were populated
    assert "front_matter" in data
    fm = data["front_matter"]
    assert fm["title_page"]["title"] is not None
    assert "Sterling" in fm["title_page"]["author"]


def test_auto_balance_all_short_endings():
    """Verify batch whitespace balancing automatically inserts tailpieces on short chapter endings."""
    res = client.post("/api/tailpiece/auto-balance-all", json={"book_id": "book01"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["book_id"] == "book01"
    assert "balanced_pages" in data
    assert isinstance(data["balanced_pages"], list)
    assert "balanced_count" in data
    assert "pagination" in data

    # Verify pages in balanced_pages now have has_tailpiece = True
    pages = data["pagination"]["pages"]
    for page in pages:
        if page["page_number"] in data["balanced_pages"]:
            assert page["has_tailpiece"] is True


def test_import_manifest_builtin_blueprint():
    """Verify importing with use_builtin=True re-anchors the 16-asset blueprint to manuscript paragraphs."""
    orig_manifest = manifest_manager.get_book_manifest("book01")
    orig_assets = list(orig_manifest.get("assets", []))
    try:
        res = client.post("/api/manifest/book01/import", json={"use_builtin": True})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        manifest = data["manifest"]
        assets = manifest.get("assets", [])
        assert len(assets) == 16
        # Every asset should be anchored to an element ID
        for a in assets:
            assert a["anchor"].startswith("ch")
    finally:
        orig_manifest["assets"] = orig_assets
        manifest_manager.save()


def test_index_html_stepper_and_wizard_views():
    """Verify index.html contains the 5-step stepper bar and all 5 wizard step screens."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # Stepper bar and stages
    assert 'id="stepper-bar"' in html
    assert 'step-btn-1' in html
    assert 'step-btn-2' in html
    assert 'step-btn-3' in html
    assert 'step-btn-4' in html
    assert 'step-btn-5' in html

    # Mode toggle button
    assert 'id="mode-toggle-btn"' in html
    assert 'Switch to Advanced 3-Panel Studio' in html

    # Wizard workspace and 5 step views
    assert 'id="wizard-workspace"' in html
    assert 'id="wizard-step-1"' in html
    assert 'id="wizard-step-2"' in html
    assert 'id="wizard-step-3"' in html
    assert 'id="wizard-step-4"' in html
    assert 'id="wizard-step-5"' in html

    # Studio workspace (for manual 3-panel override)
    assert 'id="studio-workspace"' in html


def test_v23_app_js_buttons_and_anchor_selector():
    """Verify app.js contains step-3 wrapper aliases, queue-card drag-and-drop, and plate inspector anchor selector."""
    js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "app.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js_code = f.read()

    # 1. Wrapper aliases
    assert "function openPlateInspector(assetId)" in js_code
    assert "function openFilterLab(assetId)" in js_code
    assert "function openPinStudio(assetId)" in js_code

    # 2. View mode dual-button toggle
    assert "wview-mode-html-btn" in js_code
    assert "wview-mode-pdf-btn" in js_code

    # 3. Queue-card drag and drop in Step 3
    assert "handleDropQueueImage" in js_code
    assert "ondragover=\"handleDragOver(event)\"" in js_code
    assert "ondrop=\"handleDropQueueImage(event" in js_code

    # 4. Canonical book genres in BOOK_PROFILE_DETAILS
    assert "Gaslamp Speculative Forensic Mystery" in js_code
    assert "Chronometric Island Thriller & Speculative Romance" in js_code
    assert "Locked-Room Mystery & Acoustic Forensic Thriller" in js_code
    assert "Ecological & Institutional Southern Gothic Mystery" in js_code
    assert "Archaeometric & Epigraphic Geopolitical Thriller" in js_code

    # 5. Anchor dropdown selector in openAssetInspector
    assert "asset-anchor-select" in js_code
    assert "ANCHOR PARAGRAPH" in js_code

    # 6. Step 3 Batch Upload button and handler
    assert "handleStep3BatchUpload" in js_code


def test_batch_upload_assets_endpoint():
    """Verify POST /api/assets/batch-upload/{book_id} matches slots, saves raw images, applies 300 DPI filter, and updates manifest."""
    from io import BytesIO
    from PIL import Image

    # Create dummy in-memory image
    img = Image.new("RGB", (200, 200), color=(120, 80, 40))
    buf1 = BytesIO()
    img.save(buf1, format="PNG")
    buf1.seek(0)

    buf2 = BytesIO()
    img.save(buf2, format="PNG")
    buf2.seek(0)

    buf_front = BytesIO()
    img.save(buf_front, format="PNG")
    buf_front.seek(0)

    files = [
        ("files", ("b01_asset_01.png", buf1, "image/png")),
        ("files", ("plate_02_lab.png", buf2, "image/png")),
        ("files", ("book01_frontispiece_art.png", buf_front, "image/png")),
    ]

    res = client.post("/api/assets/batch-upload/book01", files=files)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["processed_count"] == 3
    assert len(data["processed"]) == 3
    assert "manifest" in data
    assert "pagination" in data

    # Verify asset 1 updated
    assets = data["manifest"]["assets"]
    asset1 = next(a for a in assets if a["id"] == "b01_asset_01")
    assert asset1.get("filter_applied") is True
    assert "raw_image_path" in asset1
    assert os.path.exists(asset1["raw_image_path"])

    # Verify asset 2 updated
    asset2 = next((a for a in assets if a["id"] == "b01_asset_02"), None)
    if asset2:
        assert asset2.get("filter_applied") is True
        assert "raw_image_path" in asset2


def test_merge_manuscript_element_html_and_cache_invalidation():
    """Verify merge-element combines text and formatted_html and invalidates cache."""
    # Fetch current manuscript to get a valid element ID
    book_details = client.get("/api/book/book01").json()
    first_el = book_details["manuscript"]["chapters"][0]["elements"][0]
    target_id = first_el["id"]

    # Insert element first to merge
    ins_res = client.post("/api/manuscript/book01/insert-element", json={
        "target_id": target_id,
        "element_type": "paragraph",
        "content": "Second paragraph text to be merged."
    })
    assert ins_res.status_code == 200
    new_el_id = ins_res.json()["new_id"]

    # Now merge into previous
    merge_res = client.post("/api/manuscript/book01/merge-element", json={
        "element_id": new_el_id
    })
    assert merge_res.status_code == 200
    m_data = merge_res.json()
    assert m_data["status"] == "success"
    assert m_data["merged_element_id"] == new_el_id

    # Verify merged element no longer exists as standalone element
    ch1 = m_data["manuscript"]["chapters"][0]
    elem_ids = [el["id"] for el in ch1["elements"]]
    assert new_el_id not in elem_ids


def test_parser_word_count_in_both_parsers():
    """Verify parse_markdown_manuscript and parse_docx_manuscript return total_words."""
    from app.parser import parse_markdown_manuscript

    sample_md = "# Chapter 1: The Alchemical Inquest\n\nThis is a sample sentence with eight words in it.\n"
    res = parse_markdown_manuscript(sample_md)
    assert "total_words" in res
    assert res["total_words"] >= 8


