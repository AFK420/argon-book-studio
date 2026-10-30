"""
Argon Book Studio - Manuscript Parser for Markdown (.md) and Word (.docx).
Deconstructs manuscripts into structured Chapters and uniquely indexed Paragraphs
(ch01_p01, ch01_p02, etc.) while preserving custom in-world containers, scene breaks,
run-level styling (em, strong, sub, sup), and semantic block types:
- body (standard indented body paragraph)
- body_first (flush-left first paragraph after heading/break)
- chapter_subtitle (timestamp/location headers)
- inworld_writ (parchment/double-rule legal warrant box)
- welsh_slate (dark basalt box #1E2229 with rough chalk serif)
- audio_transcript (monospace DAW log box with decibel ruler)
- archival_journal (1928 ledger / diary entry)
- scientific_formula (centered equation / telemetry callout)
- cuneiform_clause (epigraphic transliteration table)
"""

import html
import os
import re
from typing import Dict, Any, List, Optional
import docx

TAG_TO_BLOCK_TYPE = {
    "inquest-writ": "inworld_writ",
    "inworld_writ": "inworld_writ",
    "sensory-draw": "inworld_writ",
    "welsh-slate": "welsh_slate",
    "welsh_slate": "welsh_slate",
    "audio-transcript": "audio_transcript",
    "audio_transcript": "audio_transcript",
    "fsk-payload": "audio_transcript",
    "pelham-journal": "archival_journal",
    "archival_journal": "archival_journal",
    "cedar-sliver": "archival_journal",
    "telemetry-equation": "scientific_formula",
    "scientific_formula": "scientific_formula",
    "oscilloscope-readout": "scientific_formula",
    "cuneiform-tablet": "cuneiform_clause",
    "cuneiform_clause": "cuneiform_clause",
    "chapter_subtitle": "chapter_subtitle",
    "chapter-subtitle": "chapter_subtitle",
}


def markdown_inline_to_html(text: str) -> str:
    """Converts inline markdown (bold, italic, sub, sup, code) to safe HTML."""
    escaped = html.escape(text)
    # Bold
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', escaped)
    escaped = re.sub(r'__(.+?)__', r'<strong>\1</strong>', escaped)
    # Italic
    escaped = re.sub(r'\*([^\*]+?)\*', r'<em>\1</em>', escaped)
    escaped = re.sub(r'_([^_]+?)_', r'<em>\1</em>', escaped)
    # Subscript / Superscript
    escaped = re.sub(r'~([^~]+?)~', r'<sub>\1</sub>', escaped)
    escaped = re.sub(r'\^([^\^]+?)\^', r'<sup>\1</sup>', escaped)
    # Monospace code
    escaped = re.sub(r'`([^`]+?)`', r'<code>\1</code>', escaped)
    return escaped


def docx_paragraph_to_html(p) -> str:
    """Extracts run-level formatting (bold, italic, sub, sup) from docx paragraph to HTML."""
    parts = []
    for r in p.runs:
        t = html.escape(r.text)
        if not t:
            continue
        if r.bold:
            t = f"<strong>{t}</strong>"
        if r.italic:
            t = f"<em>{t}</em>"
        if getattr(r.font, "subscript", False):
            t = f"<sub>{t}</sub>"
        if getattr(r.font, "superscript", False):
            t = f"<sup>{t}</sup>"
        parts.append(t)
    return "".join(parts) if parts else html.escape(p.text)


def detect_block_type(text: str, prev_type: str = "body", is_first_p: bool = False) -> str:
    """
    Intelligent heuristic auto-detection of semantic block types from text patterns.
    """
    s = text.strip()
    upper_s = s.upper()

    # Subtitles and timestamps (e.g. RONAN: Thursday, 08:00 or TIME: 04:12)
    if (upper_s.startswith("RONAN:") or
        upper_s.startswith("TIME:") or
        upper_s.startswith("LOCATION:") or
        re.match(r'^[A-Z\s]{3,20}:\s+[A-Za-z]+,\s+\d{2}:\d{2}', s)):
        return "chapter_subtitle"

    # Welsh slate basalt notes
    if (upper_s.startswith("[SLATE") or
        upper_s.startswith("SLATE:") or
        (s.isupper() and 10 < len(s) < 180 and not upper_s.startswith("CHAPTER"))):
        return "welsh_slate"

    # Audio transcript DAW logs
    if (upper_s.startswith("[CHAMBER") or
        upper_s.startswith("[DAW") or
        upper_s.startswith("[AUDIO") or
        upper_s.startswith("[RECORDING") or
        "CHAN A" in upper_s or "CHAN B" in upper_s or
        "MIC-" in upper_s or "MIC A" in upper_s or "MIC B" in upper_s or
        re.search(r'\[\d{1,2}:\d{2}', s) or
        re.search(r'\b\d{2}:\d{2}:\d{2}\b', s) or
        ("HZ" in upper_s and "DB" in upper_s)):
        return "audio_transcript"

    # Inquest writ legal warrant
    if (upper_s.startswith("[INQUEST") or
        upper_s.startswith("[WRIT") or
        upper_s.startswith("INQUEST:") or
        upper_s.startswith("WARRANT:") or
        "CORONER'S INQUEST" in upper_s or
        "COURT OF RESIDUAL CLAIMS" in upper_s or
        "MAGISTRATE'S ORDER" in upper_s):
        return "inworld_writ"

    # Archival journal / 1928 ledger
    if (upper_s.startswith("[JOURNAL") or
        upper_s.startswith("[LEDGER") or
        upper_s.startswith("JOURNAL:") or
        re.match(r'^(?:\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)|(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?)\s+\d{4}', s, re.I)):
        return "archival_journal"

    # Scientific formula / equation
    if (upper_s.startswith("[EQUATION") or
        upper_s.startswith("[FORMULA") or
        "ΔP" in s or "Δt" in s or
        re.search(r'(\b\d+\.?\d*\s*(?:hPa|kHz|MHz|μV|mV|m/s|mbar/hr)\b|[λΔπ]\s*=|\b[fF]\s*=\s*\d+)', s)):
        return "scientific_formula"

    # Cuneiform transliteration table
    if (upper_s.startswith("[TABLET") or
        upper_s.startswith("[CUNEIFORM") or
        (re.search(r'\[(?:dingir|sign|[a-z0-9\-àáèéìíòóùú\s]+)\]', s, re.I) and ("sign" in s.lower() or "transliteration" in s.lower() or "line " in s.lower() or "/" in s))):
        return "cuneiform_clause"

    # Opening paragraph after break or chapter opener
    if is_first_p or prev_type in ["chapter_header", "scene_break", "chapter_subtitle"]:
        return "body_first"

    return "body"


def parse_markdown_manuscript(content: str) -> Dict[str, Any]:
    """
    Parses a Markdown manuscript into chapters, paragraphs, scene breaks, and containers
    with semantic block types and rich formatting runs.
    """
    lines = content.splitlines()

    book_title = "Untitled Manuscript"
    book_subtitle = ""
    book_author = "Argon Studio Author"

    chapters: List[Dict[str, Any]] = []
    current_chapter: Optional[Dict[str, Any]] = None
    ch_counter = 0
    p_counter = 0

    in_container = False
    container_tag = ""
    container_buffer: List[str] = []

    for line in lines:
        stripped = line.strip()

        # Check for book metadata header at very beginning
        if not current_chapter and stripped.startswith("# ") and book_title == "Untitled Manuscript":
            book_title = stripped[2:].strip()
            continue
        elif not current_chapter and (
            stripped.startswith("*Being ") or
            stripped.startswith("*Subtitle:") or
            stripped.startswith("*Telemetry") or
            stripped.startswith("*The Audio") or
            stripped.startswith("*Field Studies") or
            stripped.startswith("*Neutron")
        ):
            book_subtitle = stripped.strip("*").strip()
            continue
        elif not current_chapter and (stripped.startswith("*By ") or stripped.startswith("*Author:")):
            book_author = stripped.strip("*").replace("By ", "").strip()
            continue

        # Check for custom container opening/closing :::tag
        if stripped.startswith(":::") and not in_container:
            in_container = True
            container_tag = stripped[3:].strip()
            container_buffer = []
            continue
        elif stripped.startswith(":::") and in_container:
            in_container = False
            # Flush container element into current chapter
            if current_chapter is not None:
                p_counter += 1
                pid = f"ch{ch_counter:02d}_p{p_counter:02d}"
                raw_text = "\n".join(container_buffer).strip()
                btype = TAG_TO_BLOCK_TYPE.get(container_tag, "inworld_writ")
                current_chapter["elements"].append({
                    "id": pid,
                    "type": "container",
                    "tag": container_tag,
                    "block_type": btype,
                    "content": raw_text,
                    "text": raw_text,
                    "formatted_html": markdown_inline_to_html(raw_text).replace("\n", "<br>"),
                    "page_break_before": False,
                    "keep_with_next": False,
                    "scene_break_after": "none",
                    "is_first_after_break": (p_counter == 1),
                    "is_opening": (p_counter == 1),
                    "word_count": len(raw_text.split())
                })
            container_tag = ""
            container_buffer = []
            continue

        if in_container:
            container_buffer.append(line)
            continue

        # Check for Chapter heading (## Chapter X: Title or # Chapter ...)
        if stripped.startswith("## ") or stripped.startswith("# Chapter"):
            ch_counter += 1
            p_counter = 0
            raw_heading = stripped.lstrip("#").strip()

            ch_title = raw_heading
            ch_num = str(ch_counter)
            if ":" in raw_heading:
                parts = raw_heading.split(":", 1)
                ch_title = parts[1].strip()
                prefix = parts[0].strip()
                m = re.search(r'\d+', prefix)
                if m:
                    ch_num = m.group(0)
            elif " " in raw_heading:
                parts = raw_heading.split(" ", 2)
                if len(parts) >= 2 and parts[1].isdigit():
                    ch_title = parts[2] if len(parts) > 2 else f"Chapter {parts[1]}"
                    ch_num = parts[1]

            current_chapter = {
                "chapter_index": ch_counter,
                "chapter_number": ch_num,
                "title": ch_title,
                "raw_heading": raw_heading,
                "elements": []
            }
            chapters.append(current_chapter)
            continue

        # Check for scene break (*** or ---)
        if stripped in ["***", "---", "* * *", "— — —"]:
            if current_chapter is not None:
                p_counter += 1
                pid = f"ch{ch_counter:02d}_p{p_counter:02d}"
                current_chapter["elements"].append({
                    "id": pid,
                    "type": "scene_break",
                    "block_type": "scene_break",
                    "content": "***",
                    "text": "***",
                    "page_break_before": False,
                    "keep_with_next": False,
                    "scene_break_after": "none"
                })
            continue

        # Regular paragraph
        if stripped:
            if current_chapter is None:
                ch_counter = 1
                current_chapter = {
                    "chapter_index": 1,
                    "chapter_number": "1",
                    "title": "Opening",
                    "raw_heading": "Chapter 1",
                    "elements": []
                }
                chapters.append(current_chapter)

            p_counter += 1
            pid = f"ch{ch_counter:02d}_p{p_counter:02d}"

            prev_el = current_chapter["elements"][-1] if current_chapter["elements"] else None
            prev_type = prev_el.get("type", "") if prev_el else "chapter_header"
            is_first = (p_counter == 1 or prev_type in ["scene_break", "container", "chapter_header"])

            detected_type = detect_block_type(stripped, prev_type=prev_type, is_first_p=is_first)
            formatted_html = markdown_inline_to_html(stripped)

            current_chapter["elements"].append({
                "id": pid,
                "type": "paragraph" if detected_type in ["body", "body_first", "chapter_subtitle"] else "container",
                "tag": detected_type.replace("_", "-"),
                "block_type": detected_type,
                "text": stripped,
                "content": stripped,
                "formatted_html": formatted_html,
                "is_first_after_break": is_first,
                "page_break_before": False,
                "keep_with_next": (detected_type == "chapter_subtitle"),
                "scene_break_after": "none",
                "word_count": len(stripped.split())
            })

    if not chapters:
        chapters = [{
            "chapter_index": 1,
            "chapter_number": "1",
            "title": "Chapter 1",
            "raw_heading": "Chapter 1",
            "elements": [{
                "id": "ch01_p01",
                "type": "paragraph",
                "block_type": "body_first",
                "text": "Manuscript text empty.",
                "content": "Manuscript text empty.",
                "formatted_html": "Manuscript text empty.",
                "is_first_after_break": True,
                "page_break_before": False,
                "keep_with_next": False,
                "scene_break_after": "none",
                "word_count": 3
            }]
        }]

    return {
        "title": book_title,
        "subtitle": book_subtitle,
        "author": book_author,
        "chapters": chapters,
        "total_chapters": len(chapters),
        "total_paragraphs": sum(len(ch["elements"]) for ch in chapters)
    }


def parse_docx_manuscript(file_path: str) -> Dict[str, Any]:
    """
    Parses a Microsoft Word (.docx) manuscript into chapters and numbered paragraphs,
    preserving formatting runs (em, strong, sub, sup) and auto-detecting in-world containers.
    """
    doc = docx.Document(file_path)

    book_title = "Untitled Word Manuscript"
    book_subtitle = ""
    book_author = "Argon Studio Author"

    chapters: List[Dict[str, Any]] = []
    current_chapter: Optional[Dict[str, Any]] = None
    ch_counter = 0
    p_counter = 0

    chapter_pattern = re.compile(r'^(CHAPTER\s+[A-Z0-9IVXLCDM]+|PROLOGUE|EPILOGUE|ACT\s+[A-Z0-9IVXLCDM]+)', re.IGNORECASE)

    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue

        style_name = p.style.name.lower() if p.style else ""

        # Detect Title / Subtitle / Author from early document styles
        if ("title" in style_name or p_counter == 0 and not current_chapter and len(text) < 120 and text.isupper()) and book_title == "Untitled Word Manuscript":
            book_title = text
            continue
        elif ("subtitle" in style_name or "speculative" in text.lower() or "archive" in text.lower()) and not book_subtitle and not current_chapter:
            book_subtitle = text
            continue
        elif "author" in style_name and not current_chapter:
            book_author = text
            continue

        # Detect Heading or Chapter start
        is_chapter_heading = (
            "heading 1" in style_name or
            "heading 2" in style_name or
            chapter_pattern.match(text)
        )

        if is_chapter_heading:
            ch_counter += 1
            p_counter = 0
            ch_title = text
            ch_num = str(ch_counter)
            if ":" in text:
                parts = text.split(":", 1)
                ch_title = parts[1].strip()
                prefix = parts[0].strip()
                m = re.search(r'\d+', prefix)
                if m:
                    ch_num = m.group(0)
            elif " " in text:
                parts = text.split(" ", 2)
                if len(parts) >= 2 and (parts[1].isdigit() or re.match(r'^[IVXLCDM]+$', parts[1], re.I)):
                    ch_title = parts[2] if len(parts) > 2 else f"Chapter {parts[1]}"
                    ch_num = parts[1]

            current_chapter = {
                "chapter_index": ch_counter,
                "chapter_number": ch_num,
                "title": ch_title,
                "raw_heading": text,
                "elements": []
            }
            chapters.append(current_chapter)
            continue

        # Detect scene breaks
        if text in ["***", "---", "* * *", "— — —"]:
            if current_chapter is not None:
                p_counter += 1
                current_chapter["elements"].append({
                    "id": f"ch{ch_counter:02d}_p{p_counter:02d}",
                    "type": "scene_break",
                    "block_type": "scene_break",
                    "content": "***",
                    "text": "***",
                    "page_break_before": False,
                    "keep_with_next": False,
                    "scene_break_after": "none"
                })
            continue

        # Check explicit container prefix (e.g. :::tag or [CONTAINER ...])
        if text.startswith(":::") or text.startswith("[CONTAINER"):
            container_tag = "inquest-writ"
            match = re.search(r":::(\S+)", text)
            if match:
                container_tag = match.group(1)
            btype = TAG_TO_BLOCK_TYPE.get(container_tag, "inworld_writ")
            clean_content = text.replace(f":::{container_tag}", "").strip()
            
            p_counter += 1
            if current_chapter is None:
                ch_counter = 1
                current_chapter = {"chapter_index": 1, "chapter_number": "1", "title": "Opening", "elements": []}
                chapters.append(current_chapter)
                
            current_chapter["elements"].append({
                "id": f"ch{ch_counter:02d}_p{p_counter:02d}",
                "type": "container",
                "tag": container_tag,
                "block_type": btype,
                "content": clean_content,
                "text": clean_content,
                "formatted_html": docx_paragraph_to_html(p),
                "page_break_before": False,
                "keep_with_next": False,
                "scene_break_after": "none",
                "is_first_after_break": (p_counter == 1),
                "is_opening": (p_counter == 1),
                "word_count": len(clean_content.split())
            })
            continue

        # Normal body paragraph or auto-detected block
        if current_chapter is None:
            ch_counter = 1
            current_chapter = {"chapter_index": 1, "chapter_number": "1", "title": "Chapter 1", "elements": []}
            chapters.append(current_chapter)

        p_counter += 1
        prev_el = current_chapter["elements"][-1] if current_chapter["elements"] else None
        prev_type = prev_el.get("type", "") if prev_el else "chapter_header"
        is_first = (p_counter == 1 or prev_type in ["scene_break", "container", "chapter_header"])

        detected_type = detect_block_type(text, prev_type=prev_type, is_first_p=is_first)
        formatted_html = docx_paragraph_to_html(p)

        current_chapter["elements"].append({
            "id": f"ch{ch_counter:02d}_p{p_counter:02d}",
            "type": "paragraph" if detected_type in ["body", "body_first", "chapter_subtitle"] else "container",
            "tag": detected_type.replace("_", "-"),
            "block_type": detected_type,
            "text": text,
            "content": text,
            "formatted_html": formatted_html,
            "is_first_after_break": is_first,
            "page_break_before": False,
            "keep_with_next": (detected_type == "chapter_subtitle"),
            "scene_break_after": "none",
            "word_count": len(text.split())
        })

    if not chapters:
        chapters = [{
            "chapter_index": 1,
            "chapter_number": "1",
            "title": "Chapter 1",
            "elements": [{
                "id": "ch01_p01",
                "type": "paragraph",
                "block_type": "body_first",
                "text": "Document contains no text.",
                "content": "Document contains no text.",
                "formatted_html": "Document contains no text.",
                "is_first_after_break": True,
                "page_break_before": False,
                "keep_with_next": False,
                "scene_break_after": "none",
                "word_count": 4
            }]
        }]

    return {
        "title": book_title,
        "subtitle": book_subtitle,
        "author": book_author,
        "chapters": chapters,
        "total_chapters": len(chapters),
        "total_paragraphs": sum(len(ch["elements"]) for ch in chapters)
    }
