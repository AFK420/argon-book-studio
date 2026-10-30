"""
Argon Book Studio - Manuscript Parser for Markdown (.md) and Word (.docx).
Deconstructs manuscripts into structured Chapters and uniquely indexed Paragraphs
(ch01_p01, ch01_p02, etc.) while preserving custom in-world containers, scene breaks,
and typography runs.
"""

import os
import re
from typing import Dict, Any, List, Optional
import docx


def parse_markdown_manuscript(content: str) -> Dict[str, Any]:
    """
    Parses a Markdown manuscript into chapters, paragraphs, scene breaks, and containers.
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
                current_chapter["elements"].append({
                    "id": pid,
                    "type": "container",
                    "tag": container_tag,
                    "content": raw_text,
                    "is_opening": (p_counter == 1)
                })
            container_tag = ""
            container_buffer = []
            continue
            
        if in_container:
            container_buffer.append(line)
            continue
            
        # Check for Chapter heading (## Chapter X: Title)
        if stripped.startswith("## ") or stripped.startswith("# Chapter"):
            # New chapter
            ch_counter += 1
            p_counter = 0
            raw_heading = stripped.lstrip("#").strip()
            
            # Extract chapter title
            ch_title = raw_heading
            ch_num = str(ch_counter)
            if ":" in raw_heading:
                parts = raw_heading.split(":", 1)
                ch_title = parts[1].strip()
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
                    "content": "***"
                })
            continue
            
        # Regular paragraph
        if stripped:
            if current_chapter is None:
                # If no chapter yet, start default Chapter 1
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
            
            # Check if this paragraph is right after chapter opening or scene break
            is_first_after_break = (
                p_counter == 1 or 
                (len(current_chapter["elements"]) > 0 and current_chapter["elements"][-1]["type"] in ["scene_break", "container"])
            )
            
            current_chapter["elements"].append({
                "id": pid,
                "type": "paragraph",
                "text": stripped,
                "is_first_after_break": is_first_after_break,
                "word_count": len(stripped.split())
            })

    # Fallback if no chapters parsed
    if not chapters:
        chapters = [{
            "chapter_index": 1,
            "chapter_number": "1",
            "title": "Chapter 1",
            "raw_heading": "Chapter 1",
            "elements": [{
                "id": "ch01_p01",
                "type": "paragraph",
                "text": "Manuscript text empty.",
                "is_first_after_break": True,
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
    Parses a Microsoft Word (.docx) manuscript into chapters and numbered paragraphs.
    """
    doc = docx.Document(file_path)
    
    book_title = "Untitled Word Manuscript"
    book_subtitle = ""
    book_author = "Argon Studio Author"
    
    chapters: List[Dict[str, Any]] = []
    current_chapter: Optional[Dict[str, Any]] = None
    ch_counter = 0
    p_counter = 0
    
    for p in doc.paragraphs:
        text = p.text.strip()
        if not text:
            continue
            
        style_name = p.style.name.lower() if p.style else ""
        
        # Detect Title / Subtitle
        if "title" in style_name and book_title == "Untitled Word Manuscript":
            book_title = text
            continue
        elif "subtitle" in style_name and not book_subtitle:
            book_subtitle = text
            continue
        elif "author" in style_name:
            book_author = text
            continue
            
        # Detect Heading 1 or Heading 2 as Chapter start
        if "heading 1" in style_name or "heading 2" in style_name or text.lower().startswith("chapter "):
            ch_counter += 1
            p_counter = 0
            ch_title = text
            ch_num = str(ch_counter)
            if ":" in text:
                parts = text.split(":", 1)
                ch_title = parts[1].strip()
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
        if text in ["***", "---", "* * *"]:
            if current_chapter is not None:
                p_counter += 1
                current_chapter["elements"].append({
                    "id": f"ch{ch_counter:02d}_p{p_counter:02d}",
                    "type": "scene_break",
                    "content": "***"
                })
            continue
            
        # Check custom container prefix (e.g. [INQUEST-WRIT] ... or :::tag)
        if text.startswith(":::") or text.startswith("[CONTAINER"):
            container_tag = "custom-container"
            match = re.search(r":::(\S+)", text)
            if match:
                container_tag = match.group(1)
            p_counter += 1
            if current_chapter is None:
                ch_counter = 1
                current_chapter = {"chapter_index": 1, "chapter_number": "1", "title": "Opening", "elements": []}
                chapters.append(current_chapter)
            current_chapter["elements"].append({
                "id": f"ch{ch_counter:02d}_p{p_counter:02d}",
                "type": "container",
                "tag": container_tag,
                "content": text.replace(f":::{container_tag}", "").strip(),
                "is_opening": (p_counter == 1)
            })
            continue
            
        # Normal body paragraph
        if current_chapter is None:
            ch_counter = 1
            current_chapter = {"chapter_index": 1, "chapter_number": "1", "title": "Chapter 1", "elements": []}
            chapters.append(current_chapter)
            
        p_counter += 1
        is_first = (p_counter == 1 or (len(current_chapter["elements"]) > 0 and current_chapter["elements"][-1]["type"] in ["scene_break", "container"]))
        current_chapter["elements"].append({
            "id": f"ch{ch_counter:02d}_p{p_counter:02d}",
            "type": "paragraph",
            "text": text,
            "is_first_after_break": is_first,
            "word_count": len(text.split())
        })

    if not chapters:
        chapters = [{
            "chapter_index": 1,
            "chapter_number": "1",
            "title": "Chapter 1",
            "elements": [{"id": "ch01_p01", "type": "paragraph", "text": "Document contains no text.", "is_first_after_break": True, "word_count": 4}]
        }]

    return {
        "title": book_title,
        "subtitle": book_subtitle,
        "author": book_author,
        "chapters": chapters,
        "total_chapters": len(chapters),
        "total_paragraphs": sum(len(ch["elements"]) for ch in chapters)
    }
