"""
Test Suite for Argon Book Studio Desktop Publishing Engine.
Verifies all publishing rules, theme profiles, parsers, filters, paginators, settings, and exporters.
"""

import os
import json
import pytest
from app.profiles import BOOK_PROFILES, UNIVERSAL_PUBLISHING_SPECS
from app.settings import settings_manager, DEFAULT_TRIM_PRESETS
from app.parser import parse_markdown_manuscript
from app.manifest import ManifestManager
from app.filters import (
    filter_cyanotype_silver_plate,
    filter_charcoal_lithograph,
    filter_blueprint_halftone,
    filter_sepia_bioluminescent_amber,
    filter_desert_ochre_uv,
    render_vector_callouts,
    generate_procedural_placeholder,
    generate_preview_base64
)
from app.paginator import paginate_manuscript
from app.front_back_matter import generate_front_matter_data
from app.exporters.pdf_exporter import export_pdf
from app.exporters.docx_exporter import export_docx
from app.exporters.epub_exporter import export_epub
import pymupdf
import docx
from PIL import Image


def test_universal_publishing_specs():
    specs = UNIVERSAL_PUBLISHING_SPECS
    assert specs["trim_width_in"] == 6.0
    assert specs["trim_height_in"] == 9.0
    assert specs["bleed_in"] == 0.125
    assert specs["margins"]["inside_gutter_in"] == 0.875
    assert specs["margins"]["outside_margin_in"] == 0.625
    assert specs["margins"]["top_margin_in"] == 0.75
    assert specs["margins"]["bottom_margin_in"] == 0.875
    assert specs["grid_rules"]["orphans"] == 3
    assert specs["grid_rules"]["widows"] == 3
    assert specs["grid_rules"]["first_p_indent_in"] == 0.0
    assert specs["grid_rules"]["subsequent_p_indent_in"] == 0.25
    assert specs["grid_rules"]["chapter_sinkage_in"] == 1.75
    assert specs["grid_rules"]["running_header_font_size_pt"] == 8.5


def test_five_book_profiles_configured():
    assert len(BOOK_PROFILES) == 5
    expected_books = ["book01", "book02", "book03", "book04", "book05"]
    for b_id in expected_books:
        assert b_id in BOOK_PROFILES
        p = BOOK_PROFILES[b_id]
        assert "body_font" in p
        assert "display_font" in p
        assert "scene_break_svg" in p
        assert "<svg" in p["scene_break_svg"]
        assert "tailpiece_svg" in p
        assert "<svg" in p["tailpiece_svg"]
        assert len(p["containers"]) >= 2
        assert "filter_preset" in p


def test_settings_manager_and_presets():
    assert "6x9" in DEFAULT_TRIM_PRESETS
    assert "5.5x8.5" in DEFAULT_TRIM_PRESETS
    
    # Reset book01 settings to ensure default verification
    settings_manager.reset_settings("book01")
    s = settings_manager.get_settings("book01")
    assert s["trim_width_in"] == 6.0
    assert s["margins"]["inside_gutter_in"] == 0.875
    assert s["typography"]["body_font_size_pt"] == 11.0


def test_profile_specific_containers():
    p1 = BOOK_PROFILES["book01"]
    tags1 = [c["tag"] for c in p1["containers"]]
    assert "inquest-writ" in tags1
    assert "sensory-draw" in tags1

    p2 = BOOK_PROFILES["book02"]
    tags2 = [c["tag"] for c in p2["containers"]]
    assert "welsh-slate" in tags2
    assert "telemetry-equation" in tags2

    p3 = BOOK_PROFILES["book03"]
    tags3 = [c["tag"] for c in p3["containers"]]
    assert "audio-transcript" in tags3
    assert "fsk-payload" in tags3

    p4 = BOOK_PROFILES["book04"]
    tags4 = [c["tag"] for c in p4["containers"]]
    assert "pelham-journal" in tags4
    assert "oscilloscope-readout" in tags4

    p5 = BOOK_PROFILES["book05"]
    tags5 = [c["tag"] for c in p5["containers"]]
    assert "cuneiform-tablet" in tags5
    assert "cedar-sliver" in tags5


def test_markdown_parser_with_containers():
    sample_md = """# The Alchemical Inquest
*Being the Case of the Salt-Cellar Murders*
*By A. E. Sterling*

## Chapter 1: Wapping Basin
The Thames did not surrender its dead.
Vane kneeled beside the deal planks.
:::inquest-writ
Coroner's Writ: Acute antimony poisoning.
:::
The frost held fast.
***
The fog rolled inland.
"""
    parsed = parse_markdown_manuscript(sample_md)
    assert parsed["title"] == "The Alchemical Inquest"
    assert len(parsed["chapters"]) == 1
    ch = parsed["chapters"][0]
    elems = ch["elements"]
    assert elems[0]["id"] == "ch01_p01"
    assert elems[0]["is_first_after_break"] == True
    assert elems[2]["type"] == "container"
    assert elems[2]["tag"] == "inquest-writ"


def test_paginator_spreads_and_filmstrip():
    sample_md = """# Test Book
## Chapter 1: The First Flight
Paragraph 1 of chapter 1.
Paragraph 2 of chapter 1.
"""
    parsed = parse_markdown_manuscript(sample_md)
    manifest = {"assets": []}
    paginated = paginate_manuscript(parsed, manifest, "book01", include_front_matter=True)
    
    assert paginated["total_pages"] >= 6
    assert len(paginated["spreads"]) >= 4
    # Check filmstrip array
    filmstrip = paginated["filmstrip"]
    assert len(filmstrip) == len(paginated["spreads"])
    assert filmstrip[0]["is_front"] == True


def test_short_ending_detection_and_tailpiece():
    sample_md = """# Test Short
## Chapter 1: Short Chapter
Only one single paragraph in this entire chapter.
"""
    parsed = parse_markdown_manuscript(sample_md)
    manifest = {"assets": []}
    
    paginated1 = paginate_manuscript(parsed, manifest, "book01", include_front_matter=False)
    chapter_pages = [p for p in paginated1["pages"] if p["is_chapter_end"]]
    assert len(chapter_pages) > 0
    short_page = chapter_pages[0]
    assert short_page["short_ending"] == True

    auto_tp = {short_page["page_number"]: True}
    paginated2 = paginate_manuscript(parsed, manifest, "book01", include_front_matter=False, auto_tailpieces=auto_tp)
    ch_p2 = [p for p in paginated2["pages"] if p["page_number"] == short_page["page_number"]][0]
    assert ch_p2["has_tailpiece"] == True


def test_pillow_filters_parameters_and_callouts(tmp_path):
    img = Image.new("RGB", (400, 300), (200, 180, 150))
    
    f1 = filter_cyanotype_silver_plate(img, contrast=1.4, grain=0.1, vignette=0.4)
    assert f1.size == (400, 300)
    
    f2 = filter_charcoal_lithograph(img, contrast=1.2)
    assert f2.size == (400, 300)

    f3 = filter_blueprint_halftone(img)
    assert f3.size == (400, 300)

    f4 = filter_sepia_bioluminescent_amber(img)
    assert f4.size == (400, 300)

    f5 = filter_desert_ochre_uv(img)
    assert f5.size == (400, 300)

    callouts = [
        {"x": 25, "y": 30, "label": "CALIPER AXIS", "type": "box"},
        {"x": 75, "y": 70, "label": "DATUM MARK", "type": "badge"},
        {"x": 50, "y": 50, "label": "TARGET PIN", "type": "crosshair"}
    ]
    with_callouts = render_vector_callouts(f1, callouts, "book01")
    assert with_callouts.size == (400, 300)


def test_pdf_export_custom_geometry(tmp_path):
    sample_md = """# Test Gaslamp Book
## Chapter 1: The Wapping Wharf
A misty night along the Thames.
"""
    parsed = parse_markdown_manuscript(sample_md)
    manifest = {"assets": []}
    out_pdf = str(tmp_path / "test_out_custom.pdf")
    
    custom_specs = {
        "trim_width_in": 5.5,
        "trim_height_in": 8.5,
        "inside_gutter_in": 0.75,
        "outside_margin_in": 0.5
    }
    export_pdf(parsed, manifest, "book01", out_pdf, bleed=False, custom_specs=custom_specs)
    assert os.path.exists(out_pdf)
    
    doc = pymupdf.open(out_pdf)
    assert len(doc) >= 1
    rect = doc[0].rect
    # 5.5 in * 72 = 396 pt, 8.5 in * 72 = 612 pt
    assert abs(rect.width - 396.0) < 5.0
    assert abs(rect.height - 612.0) < 5.0
    doc.close()


def test_docx_export_custom_specs(tmp_path):
    sample_md = """# Test Word Book
## Chapter 1: Basalt Cliffs
Wind howling over the Atlantic.
:::welsh-slate
960 hPa threshold warning.
:::
"""
    parsed = parse_markdown_manuscript(sample_md)
    manifest = {"assets": []}
    out_docx = str(tmp_path / "test_out_custom.docx")
    
    custom_specs = {
        "trim_width_in": 5.5,
        "trim_height_in": 8.5,
        "inside_gutter_in": 0.75,
        "outside_margin_in": 0.5
    }
    export_docx(parsed, manifest, "book02", out_docx, custom_specs=custom_specs)
    assert os.path.exists(out_docx)
    
    doc = docx.Document(out_docx)
    sec = doc.sections[0]
    assert abs(sec.page_width.inches - 5.5) < 0.01
    assert abs(sec.page_height.inches - 8.5) < 0.01


def test_epub_export_structure(tmp_path):
    sample_md = """# Test EPUB Book
## Chapter 1: Audio Cryptanalysis
Oscilloscope carrier frequency active at 42.4 Hz.
"""
    parsed = parse_markdown_manuscript(sample_md)
    manifest = {"assets": []}
    out_epub = str(tmp_path / "test_out.epub")
    
    export_epub(parsed, manifest, "book03", out_epub)
    assert os.path.exists(out_epub)
    assert os.path.getsize(out_epub) > 1000
