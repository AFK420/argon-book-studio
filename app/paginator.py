"""
Argon Book Studio - Universal Typesetting & Pagination Engine.
Implements the 6.0 x 9.0 inch book layout rules (and dynamic custom trim sizes):
- Mirrored print margins (@page :left inside gutter, outside margin, top, bottom).
- First-paragraph indent suppression (0in), subsequent paragraph indent (0.25in, 0 margin-bottom).
- Chapter opening fresh page break + top sinkage.
- Running headers: Verso (even) = Book Title (8.5pt small-caps), Recto (odd) = Chapter Title (8.5pt small-caps).
- Running header/footer suppression on chapter openers, full-page plates, front matter.
- Short chapter ending detection (< 18 lines on final page).
- 2-Page Spread packaging (Verso + Recto pairs).
- Dynamic mathematical line-capacity calculation from live geometry settings.
- Filmstrip thumbnail metadata generation.
"""

import math
from typing import Dict, Any, List, Optional
from app.profiles import UNIVERSAL_PUBLISHING_SPECS, BOOK_PROFILES


class BookPage:
    def __init__(self, page_number: int, page_type: str = "body"):
        self.page_number = page_number
        self.is_verso = (page_number % 2 == 0)
        self.is_recto = (page_number % 2 == 1)
        self.page_type = page_type  # body, chapter_opener, full_plate, front_matter, end_matter, blank
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
        self.has_plate = False

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
            "has_plate": self.has_plate,
            "elements": self.elements
        }


def calculate_line_capacity(
    trim_width_in: float,
    trim_height_in: float,
    top_margin_in: float,
    bottom_margin_in: float,
    inside_gutter_in: float,
    outside_margin_in: float,
    chapter_sinkage_in: float,
    body_leading_pt: float,
    body_font_size_pt: float
) -> Dict[str, int]:
    """
    Computes true mathematical page capacity based on geometry.
    """
    header_footer_buffer_in = 0.40
    usable_height_in = max(3.0, trim_height_in - top_margin_in - bottom_margin_in - header_footer_buffer_in)
    leading_in = max(0.12, body_leading_pt / 72.0)
    
    full_page_lines = max(12, int(usable_height_in / leading_in))
    
    usable_opener_height = max(1.5, usable_height_in - chapter_sinkage_in)
    opener_lines = max(6, int(usable_opener_height / leading_in))
    
    usable_width_in = max(2.5, trim_width_in - inside_gutter_in - outside_margin_in)
    # Average character width is approx 0.48 to 0.54 * font_size in points (72 pt / inch)
    char_width_in = (body_font_size_pt * 0.50) / 72.0
    chars_per_line = max(35, int(usable_width_in / char_width_in))
    
    return {
        "lines_per_full_page": full_page_lines,
        "lines_per_chapter_opener": opener_lines,
        "chars_per_line": chars_per_line
    }


def paginate_manuscript(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    include_front_matter: bool = True,
    auto_tailpieces: Dict[int, bool] = None,
    custom_specs: Dict[str, Any] = None,
    custom_matter: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Simulates physical pagination conforming to all publishing engine rules,
    dynamically calculated from live geometry and matter configuration.
    """
    profile = BOOK_PROFILES.get(profile_id, BOOK_PROFILES["book01"])
    specs = UNIVERSAL_PUBLISHING_SPECS
    cs = custom_specs or {}
    cm = custom_matter or {}
    
    trim_w = float(cs.get("trim_width_in", specs["trim_width_in"]))
    trim_h = float(cs.get("trim_height_in", specs["trim_height_in"]))
    gutter = float(cs.get("margins", {}).get("inside_gutter_in", cs.get("inside_gutter_in", specs["margins"]["inside_gutter_in"])))
    outside = float(cs.get("margins", {}).get("outside_margin_in", cs.get("outside_margin_in", specs["margins"]["outside_margin_in"])))
    top = float(cs.get("margins", {}).get("top_margin_in", cs.get("top_margin_in", specs["margins"]["top_margin_in"])))
    bottom = float(cs.get("margins", {}).get("bottom_margin_in", cs.get("bottom_margin_in", specs["margins"]["bottom_margin_in"])))
    sinkage = float(cs.get("typography", {}).get("chapter_sinkage_in", cs.get("chapter_sinkage_in", specs["grid_rules"]["chapter_sinkage_in"])))
    body_size = float(cs.get("typography", {}).get("body_font_size_pt", cs.get("body_font_size_pt", 11.0)))
    body_leading = float(cs.get("typography", {}).get("body_leading_pt", cs.get("body_leading_pt", 15.0)))
    
    cap = calculate_line_capacity(
        trim_width_in=trim_w,
        trim_height_in=trim_h,
        top_margin_in=top,
        bottom_margin_in=bottom,
        inside_gutter_in=gutter,
        outside_margin_in=outside,
        chapter_sinkage_in=sinkage,
        body_leading_pt=body_leading,
        body_font_size_pt=body_size
    )
    
    lines_per_full_page = cap["lines_per_full_page"]
    lines_per_chapter_opener = cap["lines_per_chapter_opener"]
    chars_per_line = cap["chars_per_line"]
    
    assets_by_anchor: Dict[str, List[Dict[str, Any]]] = {}
    for a in manifest.get("assets", []):
        assets_by_anchor.setdefault(a.get("anchor", ""), []).append(a)

    pages: List[BookPage] = []
    current_page_num = 1
    
    if auto_tailpieces is None:
        auto_tailpieces = {}

    # FRONT MATTER PAGES
    if include_front_matter:
        # Half-Title
        if cm.get("include_half_title", True):
            p1 = BookPage(page_number=current_page_num, page_type="front_matter")
            p1.suppress_header = True
            p1.suppress_footer = True
            p1.elements.append({
                "type": "half_title",
                "title": parsed_book.get("title", profile["title"])
            })
            pages.append(p1)
            current_page_num += 1

        # Frontispiece
        if cm.get("include_frontispiece", True):
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

        # Title Page
        if cm.get("include_title_page", True):
            p3 = BookPage(page_number=current_page_num, page_type="front_matter")
            p3.suppress_header = True
            p3.suppress_footer = True
            p3.elements.append({
                "type": "title_page",
                "title": parsed_book.get("title", profile["title"]),
                "subtitle": parsed_book.get("subtitle", profile["subtitle"]),
                "author": parsed_book.get("author", profile["author"]),
                "imprint": cm.get("publisher_imprint", "THE ARGON BOOK STUDIO • PRESS")
            })
            pages.append(p3)
            current_page_num += 1

        # Copyright Page
        if cm.get("include_copyright", True):
            p4 = BookPage(page_number=current_page_num, page_type="front_matter")
            p4.suppress_header = True
            p4.suppress_footer = True
            p4.elements.append({
                "type": "copyright_page",
                "title": parsed_book.get("title", profile["title"]),
                "author": parsed_book.get("author", profile["author"]),
                "year": "2026",
                "isbn": cm.get("isbn_hardcover", "978-1-987654-32-1"),
                "colophon_summary": f"Designed and typeset using the Argon Universal Publishing Engine. Font family: {profile['body_font_name']} and {profile['display_font_name']}."
            })
            pages.append(p4)
            current_page_num += 1

        # Dedication Page (Optional)
        if cm.get("include_dedication", False):
            p_ded = BookPage(page_number=current_page_num, page_type="front_matter")
            p_ded.suppress_header = True
            p_ded.suppress_footer = True
            p_ded.elements.append({
                "type": "dedication",
                "text": cm.get("dedication_text", "To those who listen in the dark.")
            })
            pages.append(p_ded)
            current_page_num += 1

        # Epigraph Page (Optional)
        if cm.get("include_epigraph", False):
            p_epi = BookPage(page_number=current_page_num, page_type="front_matter")
            p_epi.suppress_header = True
            p_epi.suppress_footer = True
            p_epi.elements.append({
                "type": "epigraph",
                "text": cm.get("epigraph_text", "The sea does not yield its mysteries willingly."),
                "source": cm.get("epigraph_source", "— Maritime Survey 1882")
            })
            pages.append(p_epi)
            current_page_num += 1

        # Table of Contents
        if cm.get("include_toc", True):
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

        # Blank verso before Chapter 1 to ensure Chapter 1 starts clean
        if current_page_num % 2 == 0:
            p_blank = BookPage(page_number=current_page_num, page_type="blank")
            p_blank.suppress_header = True
            p_blank.suppress_footer = True
            pages.append(p_blank)
            current_page_num += 1

    # BODY CHAPTERS
    for ch_idx, chapter in enumerate(parsed_book.get("chapters", [])):
        ch_title = chapter.get("title", f"Chapter {ch_idx + 1}")
        ch_num = chapter.get("chapter_number", str(ch_idx + 1))
        
        cur_page = BookPage(page_number=current_page_num, page_type="chapter_opener")
        cur_page.suppress_header = True
        cur_page.suppress_footer = False
        cur_page.chapter_title = ch_title
        cur_page.chapter_number = ch_num
        cur_page.book_title = parsed_book.get("title", profile["short_title"])
        
        cur_page.elements.append({
            "type": "chapter_header",
            "chapter_number": ch_num,
            "title": ch_title,
            "sinkage_in": sinkage,
            "ornament_svg": profile["scene_break_svg"]
        })
        cur_page_lines = 8
        page_capacity = lines_per_chapter_opener
        pages.append(cur_page)
        current_page_num += 1

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
                cur_page.has_plate = True

        for elem in chapter.get("elements", []):
            elem_id = elem.get("id", "")
            elem_type = elem.get("type", "paragraph")
            
            # Check for anchored illustrations
            for asset in assets_by_anchor.get(elem_id, []):
                placement = asset.get("placement", "Inline Archival Insert")
                if placement == "Chapter Opener Vignette":
                    continue
                elif placement == "Full-Page Recto Plate":
                    if cur_page.is_recto and cur_page.elements:
                        cur_page = BookPage(page_number=current_page_num, page_type="blank")
                        cur_page.suppress_header = True
                        cur_page.suppress_footer = True
                        pages.append(cur_page)
                        current_page_num += 1
                        
                    plate_page = BookPage(page_number=current_page_num, page_type="full_plate")
                    plate_page.suppress_header = True
                    plate_page.suppress_footer = True
                    plate_page.has_plate = True
                    plate_page.elements.append({
                        "type": "illustration",
                        "placement": "Full-Page Recto Plate",
                        "asset": asset
                    })
                    pages.append(plate_page)
                    current_page_num += 1
                    
                    cur_page = BookPage(page_number=current_page_num, page_type="body")
                    cur_page.chapter_title = ch_title
                    cur_page.chapter_number = ch_num
                    cur_page.book_title = parsed_book.get("title", profile["short_title"])
                    cur_page.running_header_text = (
                        profile["short_title"].upper() if cur_page.is_verso else f"CHAPTER {ch_num} • {ch_title.upper()}"
                    )
                    cur_page_lines = 0
                    page_capacity = lines_per_full_page
                    pages.append(cur_page)
                    current_page_num += 1
                    continue
                elif placement == "Half-Page Top":
                    if cur_page_lines + 14 > page_capacity:
                        cur_page = BookPage(page_number=current_page_num, page_type="body")
                        cur_page.chapter_title = ch_title
                        cur_page.chapter_number = ch_num
                        cur_page.book_title = parsed_book.get("title", profile["short_title"])
                        cur_page.running_header_text = (
                            profile["short_title"].upper() if cur_page.is_verso else f"CHAPTER {ch_num} • {ch_title.upper()}"
                        )
                        cur_page_lines = 0
                        page_capacity = lines_per_full_page
                        pages.append(cur_page)
                        current_page_num += 1
                    cur_page.elements.append({
                        "type": "illustration",
                        "placement": "Half-Page Top",
                        "asset": asset
                    })
                    cur_page.has_plate = True
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
                        page_capacity = lines_per_full_page
                        pages.append(cur_page)
                        current_page_num += 1
                    cur_page.elements.append({
                        "type": "illustration",
                        "placement": "Inline Archival Insert",
                        "asset": asset
                    })
                    cur_page.has_plate = True
                    cur_page_lines += 10
                    continue

            # Process paragraph / element
            if elem_type == "paragraph":
                text = elem.get("text", "")
                est_lines = max(1, math.ceil(len(text) / chars_per_line))
                
                if cur_page_lines + est_lines > page_capacity and cur_page.elements:
                    cur_page = BookPage(page_number=current_page_num, page_type="body")
                    cur_page.chapter_title = ch_title
                    cur_page.chapter_number = ch_num
                    cur_page.book_title = parsed_book.get("title", profile["short_title"])
                    cur_page.running_header_text = (
                        profile["short_title"].upper() if cur_page.is_verso else f"CHAPTER {ch_num} • {ch_title.upper()}"
                    )
                    cur_page_lines = 0
                    page_capacity = lines_per_full_page
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
                    page_capacity = lines_per_full_page
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
                    page_capacity = lines_per_full_page
                    pages.append(cur_page)
                    current_page_num += 1
                cur_page.elements.append({
                    "id": elem_id,
                    "type": "scene_break",
                    "svg": profile["scene_break_svg"]
                })
                cur_page_lines += 3

        cur_page.total_lines = cur_page_lines
        cur_page.is_chapter_end = True
        
        threshold = specs["grid_rules"]["short_ending_threshold_lines"]
        if cur_page_lines < threshold:
            cur_page.short_ending = True
            if auto_tailpieces.get(cur_page.page_number, False):
                cur_page.has_tailpiece = True
                cur_page.elements.append({
                    "type": "tailpiece_ornament",
                    "svg": profile["tailpiece_svg"],
                    "note": "Whitespace balanced via Thematic Tailpiece Ornament"
                })

    # BACK MATTER (Acknowledgements, About Author, Colophon)
    if cm.get("include_acknowledgements", False):
        p_ack = BookPage(page_number=current_page_num, page_type="end_matter")
        p_ack.suppress_header = True
        p_ack.suppress_footer = True
        p_ack.elements.append({
            "type": "acknowledgements",
            "title": "Acknowledgements",
            "text": cm.get("acknowledgements_text", "")
        })
        pages.append(p_ack)
        current_page_num += 1

    if cm.get("include_about_author", False):
        p_aut = BookPage(page_number=current_page_num, page_type="end_matter")
        p_aut.suppress_header = True
        p_aut.suppress_footer = True
        p_aut.elements.append({
            "type": "about_author",
            "title": "About the Author",
            "text": cm.get("about_author_text", "")
        })
        pages.append(p_aut)
        current_page_num += 1

    if cm.get("include_colophon", True):
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
            "specs": f"{trim_w:.1f} x {trim_h:.1f} in, Mirrored Margins ({gutter:.3f}in / {outside:.3f}in)."
        })
        pages.append(colophon_page)
        current_page_num += 1

    if len(pages) % 2 != 0:
        trailing_blank = BookPage(page_number=current_page_num, page_type="blank")
        trailing_blank.suppress_header = True
        trailing_blank.suppress_footer = True
        pages.append(trailing_blank)

    # Group into 2-Page Spreads
    spreads: List[Dict[str, Any]] = []
    
    spreads.append({
        "spread_index": 1,
        "verso": None,
        "recto": pages[0].to_dict()
    })
    
    idx = 1
    spread_num = 2
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

    # Filmstrip array for bird's-eye bottom drawer
    filmstrip: List[Dict[str, Any]] = []
    for sp in spreads:
        v = sp["verso"]
        r = sp["recto"]
        
        has_opener = (v and v.get("page_type") == "chapter_opener") or (r and r.get("page_type") == "chapter_opener")
        has_plate = (v and v.get("has_plate")) or (r and r.get("has_plate"))
        has_short = (v and v.get("short_ending")) or (r and r.get("short_ending"))
        is_front = (v and v.get("page_type") == "front_matter") or (r and r.get("page_type") == "front_matter")
        
        filmstrip.append({
            "spread_index": sp["spread_index"] - 1, # 0-based for JS
            "display_num": sp["spread_index"],
            "verso_num": v.get("page_number") if v else None,
            "recto_num": r.get("page_number") if r else None,
            "has_opener": has_opener,
            "has_plate": has_plate,
            "has_short": has_short,
            "is_front": is_front
        })

    short_endings_found = [p.page_number for p in pages if p.short_ending and not p.has_tailpiece]

    return {
        "pages": [p.to_dict() for p in pages],
        "spreads": spreads,
        "filmstrip": filmstrip,
        "total_pages": len(pages),
        "total_spreads": len(spreads),
        "short_endings": short_endings_found,
        "profile": profile,
        "capacity_metrics": cap
    }
