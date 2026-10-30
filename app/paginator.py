"""
Argon Book Studio - Universal Typesetting & Pagination Engine.
Implements the 6.0 x 9.0 inch book layout rules:
- Mirrored print margins (0.875" inside gutter, 0.625" outside margin, 0.75" top, 0.875" bottom).
- First-paragraph indent suppression (0in), subsequent paragraph indent (0.25in, 0 margin-bottom).
- Chapter opening fresh page break + 1.75in top sinkage.
- Running headers: Verso (even) = Book Title (8.5pt small-caps), Recto (odd) = Chapter Title (8.5pt small-caps).
- Running header/footer suppression on chapter openers, full-page plates, front matter.
- Short chapter ending detection (< 18 lines on final page).
- 2-Page Spread packaging (Verso + Recto pairs).
"""

import math
from typing import Dict, Any, List, Optional
from app.profiles import UNIVERSAL_PUBLISHING_SPECS, BOOK_PROFILES

# Standard line capacity calculation for 6x9 with 11pt/15pt font:
# Height = 9.0 in - 0.75in (top) - 0.875in (bottom) - 0.35in (header/footer buffer) = 7.025 in.
# At 15pt leading (15/72 = 0.208 in), full page capacity is ~33 lines.
# With chapter sinkage of 1.75 in, chapter opening page has capacity ~24 lines.
LINES_PER_FULL_PAGE = 32
LINES_PER_CHAPTER_OPENER = 22
CHARS_PER_LINE = 64  # Average for 6x9 page at 11pt EB Garamond / Baskerville


class PageElement:
    def __init__(self, elem_type: str, data: Dict[str, Any], estimated_lines: int):
        self.elem_type = elem_type
        self.data = data
        self.estimated_lines = estimated_lines


class BookPage:
    def __init__(self, page_number: int, page_type: str = "body"):
        self.page_number = page_number
        self.is_verso = (page_number % 2 == 0)
        self.is_recto = (page_number % 2 == 1)
        self.page_type = page_type  # body, chapter_opener, full_plate, front_matter, blank
        self.elements: List[Dict[str, Any]] = []
        self.running_header_text = ""
        self.suppress_header = False
        self.suppress_footer = False
        self.chapter_title = ""
        self.chapter_number = ""
        self.book_title = ""
        self.total_lines = 0
        self.has_tailpiece = False
        self.is_chapter_end = False
        self.short_ending = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "is_verso": self.is_verso,
            "is_recto": self.is_recto,
            "page_type": self.page_type,
            "suppress_header": self.suppress_header,
            "suppress_footer": self.suppress_footer,
            "running_header_text": self.running_header_text,
            "chapter_title": self.chapter_title,
            "chapter_number": self.chapter_number,
            "book_title": self.book_title,
            "total_lines": self.total_lines,
            "has_tailpiece": self.has_tailpiece,
            "is_chapter_end": self.is_chapter_end,
            "short_ending": self.short_ending,
            "elements": self.elements
        }


def paginate_manuscript(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    include_front_matter: bool = True,
    auto_tailpieces: Dict[int, bool] = None
) -> Dict[str, Any]:
    """
    Simulates physical pagination conforming to all non-negotiable book-production rules.
    Returns page array and 2-page spread pairs.
    """
    profile = BOOK_PROFILES.get(profile_id, BOOK_PROFILES["book01"])
    assets_by_anchor: Dict[str, List[Dict[str, Any]]] = {}
    for a in manifest.get("assets", []):
        anchor = a.get("anchor", "")
        assets_by_anchor.setdefault(anchor, []).append(a)

    pages: List[BookPage] = []
    current_page_num = 1
    
    if auto_tailpieces is None:
        auto_tailpieces = {}

    # FRONT MATTER PAGES
    if include_front_matter:
        # Page 1: Half-Title (Recto)
        p1 = BookPage(page_number=current_page_num, page_type="front_matter")
        p1.suppress_header = True
        p1.suppress_footer = True
        p1.elements.append({
            "type": "half_title",
            "title": parsed_book.get("title", profile["title"])
        })
        pages.append(p1)
        current_page_num += 1

        # Page 2: Frontispiece / Blank (Verso)
        p2 = BookPage(page_number=current_page_num, page_type="front_matter")
        p2.suppress_header = True
        p2.suppress_footer = True
        p2.elements.append({
            "type": "frontispiece",
            "subtitle": parsed_book.get("subtitle", profile["subtitle"]),
            "ornament_svg": profile["scene_break_svg"]
        })
        pages.append(p2)
        current_page_num += 1

        # Page 3: Full Title Page (Recto)
        p3 = BookPage(page_number=current_page_num, page_type="front_matter")
        p3.suppress_header = True
        p3.suppress_footer = True
        p3.elements.append({
            "type": "title_page",
            "title": parsed_book.get("title", profile["title"]),
            "subtitle": parsed_book.get("subtitle", profile["subtitle"]),
            "author": parsed_book.get("author", profile["author"]),
            "imprint": "THE ARGON BOOK STUDIO • FINE TYPESETTING"
        })
        pages.append(p3)
        current_page_num += 1

        # Page 4: Copyright Page (Verso)
        p4 = BookPage(page_number=current_page_num, page_type="front_matter")
        p4.suppress_header = True
        p4.suppress_footer = True
        p4.elements.append({
            "type": "copyright_page",
            "title": parsed_book.get("title", profile["title"]),
            "author": parsed_book.get("author", profile["author"]),
            "year": "2026",
            "isbn": "978-1-987654-32-1",
            "colophon_summary": f"Designed and typeset in 6x9 inch format using the Argon Universal Publishing Engine. Font family: {profile['body_font_name']} and {profile['display_font_name']}."
        })
        pages.append(p4)
        current_page_num += 1

        # Page 5: Table of Contents (Recto)
        p5 = BookPage(page_number=current_page_num, page_type="front_matter")
        p5.suppress_header = True
        p5.suppress_footer = True
        p5.elements.append({
            "type": "table_of_contents",
            "chapters": [
                {"number": ch.get("chapter_number"), "title": ch.get("title")}
                for ch in parsed_book.get("chapters", [])
            ]
        })
        pages.append(p5)
        current_page_num += 1

        # Page 6: Blank or Part Divider (Verso)
        p6 = BookPage(page_number=current_page_num, page_type="blank")
        p6.suppress_header = True
        p6.suppress_footer = True
        pages.append(p6)
        current_page_num += 1

    # BODY CHAPTERS
    for ch_idx, chapter in enumerate(parsed_book.get("chapters", [])):
        ch_title = chapter.get("title", f"Chapter {ch_idx + 1}")
        ch_num = chapter.get("chapter_number", str(ch_idx + 1))
        
        # Rule: Chapter Openings always start on a fresh page
        # In professional book design, chapter openers usually start on a Recto (odd) page,
        # but starting on fresh page is mandatory.
        cur_page = BookPage(page_number=current_page_num, page_type="chapter_opener")
        cur_page.suppress_header = True  # Automatic suppression on chapter openers
        cur_page.suppress_footer = False # Page number still allowed or suppressed per config
        cur_page.chapter_title = ch_title
        cur_page.chapter_number = ch_num
        cur_page.book_title = parsed_book.get("title", profile["short_title"])
        
        # Chapter header element with 1.75" sinkage
        cur_page.elements.append({
            "type": "chapter_header",
            "chapter_number": ch_num,
            "title": ch_title,
            "sinkage_in": UNIVERSAL_PUBLISHING_SPECS["grid_rules"]["chapter_sinkage_in"],
            "ornament_svg": profile["scene_break_svg"]
        })
        cur_page_lines = 8  # Chapter header takes ~8 lines of vertical space
        page_capacity = LINES_PER_CHAPTER_OPENER
        pages.append(cur_page)
        current_page_num += 1

        # Check for Chapter Opener Vignette anchored at chXX_p01 or chapter start
        ch_anchors = [elem.get("id") for elem in chapter.get("elements", [])]
        first_anchor = ch_anchors[0] if ch_anchors else f"ch{ch_idx+1:02d}_p01"
        
        for asset in assets_by_anchor.get(first_anchor, []):
            if asset.get("placement") == "Chapter Opener Vignette":
                cur_page.elements.append({
                    "type": "illustration",
                    "placement": "Chapter Opener Vignette",
                    "asset": asset
                })
                cur_page_lines += 10

        # Iterate elements in chapter
        for elem in chapter.get("elements", []):
            elem_id = elem.get("id", "")
            elem_type = elem.get("type", "paragraph")
            
            # Check for illustrations anchored before or at this paragraph
            anchored_assets = assets_by_anchor.get(elem_id, [])
            for asset in anchored_assets:
                placement = asset.get("placement", "Inline Archival Insert")
                if placement == "Chapter Opener Vignette":
                    continue  # already placed
                elif placement == "Full-Page Recto Plate":
                    # Full page plate requires its own dedicated Recto page
                    # If current page is odd, finalize it and insert a blank verso if needed, then plate on recto
                    if cur_page.is_recto and cur_page.elements:
                        # End current recto page, insert blank verso
                        cur_page = BookPage(page_number=current_page_num, page_type="blank")
                        cur_page.suppress_header = True
                        cur_page.suppress_footer = True
                        pages.append(cur_page)
                        current_page_num += 1
                        
                    plate_page = BookPage(page_number=current_page_num, page_type="full_plate")
                    plate_page.suppress_header = True
                    plate_page.suppress_footer = True
                    plate_page.elements.append({
                        "type": "illustration",
                        "placement": "Full-Page Recto Plate",
                        "asset": asset
                    })
                    pages.append(plate_page)
                    current_page_num += 1
                    
                    # Start fresh page after plate
                    cur_page = BookPage(page_number=current_page_num, page_type="body")
                    cur_page.chapter_title = ch_title
                    cur_page.chapter_number = ch_num
                    cur_page.book_title = parsed_book.get("title", profile["short_title"])
                    cur_page.running_header_text = (
                        profile["short_title"].upper() if cur_page.is_verso else f"CHAPTER {ch_num} • {ch_title.upper()}"
                    )
                    cur_page_lines = 0
                    page_capacity = LINES_PER_FULL_PAGE
                    pages.append(cur_page)
                    current_page_num += 1
                    continue
                elif placement == "Half-Page Top":
                    # Needs ~14 lines
                    if cur_page_lines + 14 > page_capacity:
                        # push to next page
                        cur_page = BookPage(page_number=current_page_num, page_type="body")
                        cur_page.chapter_title = ch_title
                        cur_page.chapter_number = ch_num
                        cur_page.book_title = parsed_book.get("title", profile["short_title"])
                        cur_page.running_header_text = (
                            profile["short_title"].upper() if cur_page.is_verso else f"CHAPTER {ch_num} • {ch_title.upper()}"
                        )
                        cur_page_lines = 0
                        page_capacity = LINES_PER_FULL_PAGE
                        pages.append(cur_page)
                        current_page_num += 1
                    cur_page.elements.append({
                        "type": "illustration",
                        "placement": "Half-Page Top",
                        "asset": asset
                    })
                    cur_page_lines += 14
                    continue
                elif placement == "Inline Archival Insert":
                    if cur_page_lines + 10 > page_capacity:
                        cur_page = BookPage(page_number=current_page_num, page_type="body")
                        cur_page.chapter_title = ch_title
                        cur_page.chapter_number = ch_num
                        cur_page.book_title = parsed_book.get("title", profile["short_title"])
                        cur_page.running_header_text = (
                            profile["short_title"].upper() if cur_page.is_verso else f"CHAPTER {ch_num} • {ch_title.upper()}"
                        )
                        cur_page_lines = 0
                        page_capacity = LINES_PER_FULL_PAGE
                        pages.append(cur_page)
                        current_page_num += 1
                    cur_page.elements.append({
                        "type": "illustration",
                        "placement": "Inline Archival Insert",
                        "asset": asset
                    })
                    cur_page_lines += 10
                    continue

            # Process element
            if elem_type == "paragraph":
                text = elem.get("text", "")
                est_lines = max(1, math.ceil(len(text) / CHARS_PER_LINE))
                
                # Check page overflow
                if cur_page_lines + est_lines > page_capacity and cur_page.elements:
                    # New body page
                    cur_page = BookPage(page_number=current_page_num, page_type="body")
                    cur_page.chapter_title = ch_title
                    cur_page.chapter_number = ch_num
                    cur_page.book_title = parsed_book.get("title", profile["short_title"])
                    cur_page.running_header_text = (
                        profile["short_title"].upper() if cur_page.is_verso else f"CHAPTER {ch_num} • {ch_title.upper()}"
                    )
                    cur_page_lines = 0
                    page_capacity = LINES_PER_FULL_PAGE
                    pages.append(cur_page)
                    current_page_num += 1
                    
                cur_page.elements.append({
                    "id": elem_id,
                    "type": "paragraph",
                    "text": text,
                    "is_first_after_break": elem.get("is_first_after_break", False),
                    "estimated_lines": est_lines
                })
                cur_page_lines += est_lines
                
            elif elem_type == "container":
                raw_content = elem.get("content", "")
                tag = elem.get("tag", "inquest-writ")
                lines_count = len(raw_content.splitlines()) + 3
                if cur_page_lines + lines_count > page_capacity and cur_page.elements:
                    cur_page = BookPage(page_number=current_page_num, page_type="body")
                    cur_page.chapter_title = ch_title
                    cur_page.chapter_number = ch_num
                    cur_page.book_title = parsed_book.get("title", profile["short_title"])
                    cur_page.running_header_text = (
                        profile["short_title"].upper() if cur_page.is_verso else f"CHAPTER {ch_num} • {ch_title.upper()}"
                    )
                    cur_page_lines = 0
                    page_capacity = LINES_PER_FULL_PAGE
                    pages.append(cur_page)
                    current_page_num += 1
                cur_page.elements.append({
                    "id": elem_id,
                    "type": "container",
                    "tag": tag,
                    "content": raw_content,
                    "estimated_lines": lines_count
                })
                cur_page_lines += lines_count

            elif elem_type == "scene_break":
                if cur_page_lines + 3 > page_capacity and cur_page.elements:
                    cur_page = BookPage(page_number=current_page_num, page_type="body")
                    cur_page.chapter_title = ch_title
                    cur_page.chapter_number = ch_num
                    cur_page.book_title = parsed_book.get("title", profile["short_title"])
                    cur_page.running_header_text = (
                        profile["short_title"].upper() if cur_page.is_verso else f"CHAPTER {ch_num} • {ch_title.upper()}"
                    )
                    cur_page_lines = 0
                    page_capacity = LINES_PER_FULL_PAGE
                    pages.append(cur_page)
                    current_page_num += 1
                cur_page.elements.append({
                    "id": elem_id,
                    "type": "scene_break",
                    "svg": profile["scene_break_svg"]
                })
                cur_page_lines += 3

        # Mark final page of chapter
        cur_page.total_lines = cur_page_lines
        cur_page.is_chapter_end = True
        
        # Check Short Chapter Ending (< 18 lines threshold)
        threshold = UNIVERSAL_PUBLISHING_SPECS["grid_rules"]["short_ending_threshold_lines"]
        if cur_page_lines < threshold:
            cur_page.short_ending = True
            # Check if auto-inserted tailpiece is enabled for this page
            if auto_tailpieces.get(cur_page.page_number, False):
                cur_page.has_tailpiece = True
                cur_page.elements.append({
                    "type": "tailpiece_ornament",
                    "svg": profile["tailpiece_svg"],
                    "note": "Whitespace balanced via Thematic Tailpiece Ornament"
                })

    # COLOPHON PAGE AT BACK
    colophon_page = BookPage(page_number=current_page_num, page_type="colophon")
    colophon_page.suppress_header = True
    colophon_page.suppress_footer = True
    colophon_page.elements.append({
        "type": "colophon",
        "title": parsed_book.get("title", profile["title"]),
        "author": parsed_book.get("author", profile["author"]),
        "body_font": profile["body_font_name"],
        "display_font": profile["display_font_name"],
        "printer": "The Argon Studio Desktop Publishing Engine (Python + WeasyPrint/Pandoc)",
        "specs": "6.0 x 9.0 in, Mirrored Margins (0.875in / 0.625in), 300 DPI Fine Monochrome Plates."
    })
    pages.append(colophon_page)
    current_page_num += 1

    # Ensure even number of pages for standard printing signatures if needed
    if len(pages) % 2 != 0:
        trailing_blank = BookPage(page_number=current_page_num, page_type="blank")
        trailing_blank.suppress_header = True
        trailing_blank.suppress_footer = True
        pages.append(trailing_blank)

    # Group into 2-Page Spreads (Verso + Recto)
    spreads: List[Dict[str, Any]] = []
    
    # Spread 0: Single Recto (Page 1) or Two-page spreads
    idx = 0
    spread_num = 1
    
    # First page is always Recto on the right side of the spread
    spreads.append({
        "spread_index": spread_num,
        "verso": None,
        "recto": pages[0].to_dict()
    })
    spread_num += 1
    idx = 1
    
    while idx < len(pages):
        verso_page = pages[idx].to_dict() if idx < len(pages) else None
        recto_page = pages[idx + 1].to_dict() if idx + 1 < len(pages) else None
        spreads.append({
            "spread_index": spread_num,
            "verso": verso_page,
            "recto": recto_page
        })
        spread_num += 1
        idx += 2

    short_endings_found = [p.page_number for p in pages if p.short_ending and not p.has_tailpiece]

    return {
        "pages": [p.to_dict() for p in pages],
        "spreads": spreads,
        "total_pages": len(pages),
        "total_spreads": len(spreads),
        "short_endings": short_endings_found,
        "profile": profile
    }
