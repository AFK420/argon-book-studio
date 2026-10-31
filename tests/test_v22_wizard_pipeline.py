"""
Tests for Argon Book Studio Pro v2.2:
5-Step Sequential Pipeline (Wizard-First Architecture)
Verifies:
1. POST /api/manuscript/{book_id}/auto-style (consecutive container merging, Vesper sensory trace, flush-left indents, matter defaults)
2. POST /api/tailpiece/auto-balance-all (batch tailpiece whitespace balancing on short chapter endings)
3. POST /api/manifest/{book_id}/import with use_builtin (smart anchor binding for built-in 16-asset blueprints)
4. Frontend Stepper & 5-Step Workspace HTML structure
"""

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
