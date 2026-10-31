"""
Tests for Argon Book Studio Pro v2.3:
Local AI Book Art Director & Layout Suite
Verifies:
1. GET /api/ai/status (Local LLM connection checking and model enumeration)
2. POST /api/ai/configure (Configuring endpoint and model settings)
3. POST /api/ai/analyze/{book_id} (Generating comprehensive typography, mandatory pages & 16-slot illustration blueprints)
4. POST /api/ai/apply/{book_id} (Autonomous application to settings, manifest, anchors, and pagination)
5. AIDirectorManager heuristic & LLM fallback engines
6. Frontend AI Hero Card, status pill, and review drawer integration
"""

import os
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.ai_director import ai_director_manager, THEME_PRESETS

client = TestClient(app)


def test_ai_status_endpoint():
    """Verify GET /api/ai/status returns valid connection structure."""
    res = client.get("/api/ai/status")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "connection" in data
    assert "config" in data
    conn = data["connection"]
    assert conn["status"] in ["online", "offline"]
    assert isinstance(conn["models"], list)
    assert len(conn["models"]) >= 1


def test_ai_configure_endpoint():
    """Verify POST /api/ai/configure updates endpoint and model parameters."""
    res = client.post("/api/ai/configure", json={
        "endpoint_url": "http://localhost:11434",
        "model": "llama3.1:8b",
        "temperature": 0.35
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["config"]["model"] == "llama3.1:8b"
    assert data["config"]["temperature"] == 0.35


def test_ai_analyze_manuscript_endpoint():
    """Verify POST /api/ai/analyze/{book_id} generates typography, mandatory pages, and 16 illustration slots."""
    res = client.post("/api/ai/analyze/book01", json={"num_illustrations": 16})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["book_id"] == "book01"
    assert "blueprint" in data

    bp = data["blueprint"]
    assert "genre_style" in bp
    assert "typography_overrides" in bp
    assert "front_back_matter" in bp
    assert "assets" in bp
    assert len(bp["assets"]) == 16

    # Verify typography recommendations
    typo = bp["typography_overrides"]
    assert "body_font_name" in typo
    assert "heading_font_name" in typo
    assert "font_size_pt" in typo
    assert "line_height" in typo

    # Verify mandatory pages (Front & Back matter)
    fbm = bp["front_back_matter"]
    assert fbm["include_title_page"] is True
    assert fbm["include_copyright"] is True
    assert fbm["include_dedication"] is True
    assert "title_page" in fbm
    assert fbm["title_page"]["title"] is not None

    # Verify illustration slots are anchored
    for idx, asset in enumerate(bp["assets"]):
        assert asset["id"].startswith("b01_asset_")
        assert len(asset["prompt"]) > 20
        assert asset["anchor"].startswith("ch")
        assert asset["chapter"] >= 1
        assert "filter_preset" in asset
        assert "placement" in asset


def test_ai_apply_blueprint_endpoint():
    """Verify POST /api/ai/apply/{book_id} updates settings, manifest, anchors and repaginates."""
    from app.manifest import manifest_manager
    try:
        # Run analysis first
        analyze_res = client.post("/api/ai/analyze/book01", json={"num_illustrations": 16})
        assert analyze_res.status_code == 200
        blueprint = analyze_res.json()["blueprint"]

        # Apply the blueprint
        apply_res = client.post("/api/ai/apply/book01", json={"blueprint": blueprint})
        assert apply_res.status_code == 200
        apply_data = apply_res.json()
        assert apply_data["status"] == "success"
        assert "manifest" in apply_data
        assert "settings" in apply_data
        assert "pagination" in apply_data

        # Verify manifest has 16 slots
        manifest = apply_data["manifest"]
        assert len(manifest["assets"]) == 16

        # Verify settings have updated typography
        settings = apply_data["settings"]
        assert "typography" in settings
        assert settings["typography"]["body_font_name"] == blueprint["typography_overrides"]["body_font_name"]

        # Verify pagination succeeded
        pagination = apply_data["pagination"]
        assert len(pagination["pages"]) > 0
    finally:
        manifest_manager.reload()


def test_ai_director_genre_detection_and_heuristics():
    """Verify heuristic engine profiles different text genres accurately."""
    # Test Gaslamp Gothic detection
    gothic_sample = {
        "title": "The Inquest of Coroner Vane",
        "author": "Sterling Vance",
        "chapters": [{
            "chapter_number": 1,
            "title": "Alembic Inquest",
            "elements": [{"type": "paragraph", "id": "ch01_p01", "text": "The vitriol burned slowly in the coroner's chamber."}]
        }]
    }
    res_gothic = ai_director_manager._analyze_via_heuristics(gothic_sample, book_id="book01", num_illustrations=8)
    assert res_gothic["theme_preset_key"] == "gaslamp_gothic"
    assert len(res_gothic["assets"]) == 8

    # Test Nautical Chronometer detection
    nautical_sample = {
        "title": "The Skerries of Ghyll",
        "author": "Isolde Thorne",
        "chapters": [{
            "chapter_number": 1,
            "title": "The Chronometer Reef",
            "elements": [{"type": "paragraph", "id": "ch01_p01", "text": "The brass barometer registered 29 inches above the skerry."}]
        }]
    }
    res_naut = ai_director_manager._analyze_via_heuristics(nautical_sample, book_id="book02", num_illustrations=8)
    assert res_naut["theme_preset_key"] == "chronometric_thriller"

    # Test Cold War Acoustic detection
    acoustic_sample = {
        "title": "Decibel Protocol",
        "author": "Klaus Mercer",
        "chapters": [{
            "chapter_number": 1,
            "title": "Tape Transceiver",
            "elements": [{"type": "paragraph", "id": "ch01_p01", "text": "The magnetic tape hiss registered a 400Hz frequency anomaly."}]
        }]
    }
    res_acoustic = ai_director_manager._analyze_via_heuristics(acoustic_sample, book_id="book03", num_illustrations=8)
    assert res_acoustic["theme_preset_key"] == "acoustic_coldwar"


def test_index_html_ai_director_ui_elements():
    """Verify Step 2 in index.html includes AI Hero Box, status pill, review drawer, and settings buttons."""
    html_path = os.path.join(os.path.dirname(__file__), "..", "app", "templates", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()

    assert "ai-hero-box" in html
    assert "ai-status-pill" in html
    assert "btn-run-ai-director" in html
    assert "ai-director-review" in html
    assert "ai-tab-btn-typo" in html
    assert "ai-tab-btn-matter" in html
    assert "ai-tab-btn-illustrations" in html


def test_app_js_ai_director_functions():
    """Verify app.js contains all required AI Director controller functions."""
    js_path = os.path.join(os.path.dirname(__file__), "..", "app", "static", "js", "app.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js = f.read()

    assert "checkLocalAIStatus" in js
    assert "openAIConfigModal" in js
    assert "runAIDirector" in js
    assert "renderAIReview" in js
    assert "applyAIDirectorBlueprint" in js
    assert "switchAITab" in js
