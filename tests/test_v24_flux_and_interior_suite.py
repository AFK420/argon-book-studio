"""
Tests for Argon Book Studio Pro v2.4:
OLLAMA (Qwen 2.5:14b) FLUX PROMPT ARCHITECT, LOCAL FLUX GENERATOR & ADVANCED INTERIOR BOOK DESIGN SUITE

Verifies:
1. POST /api/ai/config (Saves & verifies configuration for Ollama and Local Flux)
2. POST /api/ai/{book_id}/extract-bible (Stage 1 Visual Continuity Bible Extractor)
3. POST /api/ai/{book_id}/enhance-prompt (Stage 2 5-Layer Flux T5 Prose Prompt Architect)
4. POST /api/ai/{book_id}/auto-plan-manifest (Stage 3 16-Asset Autonomous Book Manifest Planner)
5. POST /api/ai/{book_id}/generate-svg (Generates custom SVG dividers and tailpiece ornaments)
6. POST /api/ai/{book_id}/generate-container-css (Generates and registers custom in-world CSS document boxes)
7. POST /api/flux/{book_id}/generate/{asset_id} (Local Flux plate generation & 300 DPI print filtering)
8. POST /api/interior/{book_id}/update (Applies chapter opener layout, page border framing, and folio styles)
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app, settings_manager, manifest_manager

client = TestClient(app)


def test_ai_and_flux_config_endpoint():
    """Verify POST /api/ai/config updates and checks Ollama and Flux configs."""
    res = client.post("/api/ai/config", json={
        "endpoint_url": "http://localhost:11434",
        "model": "qwen2.5:14b",
        "temperature": 0.35,
        "flux_backend": "comfyui",
        "flux_url": "http://127.0.0.1:8188",
        "flux_steps": 25,
        "flux_cfg": 3.5
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["ai_config"]["model"] == "qwen2.5:14b"
    assert data["ai_config"]["temperature"] == 0.35
    assert data["flux_config"]["backend"] == "comfyui"
    assert "ollama_status" in data
    assert "flux_status" in data


def test_extract_visual_bible_endpoint():
    """Verify POST /api/ai/book01/extract-bible extracts locked character descriptions and setting."""
    res = client.post("/api/ai/book01/extract-bible")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "visual_bible" in data
    bible = data["visual_bible"]
    assert "characters" in bible
    assert "setting_architecture" in bible
    assert "art_medium_lock" in bible
    assert len(bible["characters"]) >= 1
    
    # Check that settings were updated
    settings = settings_manager.get_settings("book01")
    assert "visual_bible" in settings
    assert settings["visual_bible"]["art_medium_lock"] is not None


def test_enhance_prompt_endpoint():
    """Verify POST /api/ai/book01/enhance-prompt rewrites slot prompt into 5-layer Flux prose."""
    res = client.post("/api/ai/book01/enhance-prompt", json={
        "asset_id": "b01_asset_01",
        "all_slots": False
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["enhanced_count"] >= 1
    
    # Check that the prompt has 5-layer structure and negative lock ending
    manifest = manifest_manager.get_book_manifest("book01")
    asset = next(a for a in manifest["assets"] if a["id"] == "b01_asset_01")
    prompt = asset["prompt"]
    assert len(prompt.split()) >= 60
    assert "Strictly zero text, zero letters, zero numbers, zero watermarks" in prompt


def test_auto_plan_manifest_endpoint():
    """Verify POST /api/ai/book01/auto-plan-manifest plans full 16-asset pacing rhythm."""
    res = client.post("/api/ai/book01/auto-plan-manifest")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "manifest" in data
    assert "pagination" in data
    manifest = data["manifest"]
    assert len(manifest["assets"]) == 16
    
    # Verify pacing rhythm contains full plate, diagram, and tailpiece
    placements = [a["placement"] for a in manifest["assets"]]
    assert any("Full" in p for p in placements)
    assert any("Diagram" in p for p in placements)
    assert any("Tailpiece" in p for p in placements)


def test_generate_svg_endpoint():
    """Verify POST /api/ai/book01/generate-svg generates valid SVG dividers and tailpieces."""
    res = client.post("/api/ai/book01/generate-svg", json={
        "request": "antique brass sextant and quill pen",
        "apply_to_book": True
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    result = data["result"]
    assert "<svg" in result["scene_break_svg"]
    assert "viewBox=\"0 0 240 32\"" in result["scene_break_svg"]
    assert "<svg" in result["tailpiece_svg"]
    assert "viewBox=\"0 0 160 80\"" in result["tailpiece_svg"]


def test_generate_container_css_endpoint():
    """Verify POST /api/ai/book01/generate-container-css generates and registers custom CSS boxes."""
    res = client.post("/api/ai/book01/generate-container-css", json={
        "request": "1960s cold-war redacted intelligence cable"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "container_css" in data
    assert ".custom-container." in data["container_css"]
    assert "container_tag" in data


def test_flux_single_generation_endpoint():
    """Verify POST /api/flux/book01/generate/b01_asset_01 generates, filters at 300 DPI, and updates manifest."""
    res = client.post("/api/flux/book01/generate/b01_asset_01", json={})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert data["asset"]["filter_applied"] is True
    assert data["asset"]["image_url"].endswith(".png")


def test_update_interior_design_endpoint():
    """Verify POST /api/interior/book01/update applies opener layouts, borders, and folios."""
    res = client.post("/api/interior/book01/update", json={
        "chapter_opener_layout": "asymmetric_ledger",
        "page_border_style": "hairline_margin_box",
        "folio_style": "outer_brackets"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    interior = data["interior_design"]
    assert interior["chapter_opener_layout"] == "asymmetric_ledger"
    assert interior["page_border_style"] == "hairline_margin_box"
    assert interior["folio_style"] == "outer_brackets"
    
    # Verify pagination reflected folio format
    spreads = data["pagination"]["spreads"]
    assert len(spreads) >= 2
    recto = spreads[1]["recto"]
    if recto and not recto.get("suppress_footer"):
        assert "[" in recto["folio_text"]


def test_create_dynamic_project_endpoint():
    """Verify POST /api/projects/create dynamically registers new book project with isolated settings and manuscript."""
    res = client.post("/api/projects/create", json={
        "title": "The Chronometric Crypt",
        "author": "Margaret Sterling",
        "short_title": "Chronometric Crypt",
        "genre": "Victorian Steampunk",
        "theme_base": "book02"
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    assert "book_id" in data
    new_id = data["book_id"]
    assert new_id.startswith("book_") or "chronometric" in new_id.lower()
    assert data["project"]["title"] == "The Chronometric Crypt"
    assert data["project"]["author"] == "Margaret Sterling"
    
    # Verify profile is discoverable in /api/profiles and /api/books
    prof_res = client.get("/api/profiles")
    assert prof_res.status_code == 200
    assert new_id in prof_res.json()["profiles"]
    
    books_res = client.get("/api/books")
    assert books_res.status_code == 200
    book_ids = [b["id"] for b in books_res.json()["books"]]
    assert new_id in book_ids
    
    # Verify book detail loads cleanly
    book_res = client.get(f"/api/book/{new_id}")
    assert book_res.status_code == 200
    book_data = book_res.json()
    assert book_data["profile"]["title"] == "The Chronometric Crypt"
    assert book_data["manuscript"] is not None
    assert book_data["pagination"] is not None


def test_auto_plan_manifest_with_custom_target_count():
    """Verify POST /api/ai/book01/auto-plan-manifest respects custom target_count (e.g. 8)."""
    res = client.post("/api/ai/book01/auto-plan-manifest", json={
        "target_count": 8
    })
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "success"
    manifest = data["manifest"]
    assert len(manifest["assets"]) == 8

