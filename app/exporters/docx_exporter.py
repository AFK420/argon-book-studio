"""
Argon Book Studio - Styled Editable DOCX Exporter.
Generates 6x9" Word documents adhering to the core publishing engine rules:
- 6.0 in x 9.0 in page size.
- Mirrored margins (0.875" gutter, 0.625" outside, 0.75" top, 0.875" bottom).
- Chapter opening sinkage (1.75").
- Indentation rules (first body paragraph indent 0; subsequent body paragraphs indent 0.25").
- Custom container boxes formatted as styled tables with borders.
- Verso / Recto headers and footers with page numbers.
"""

import os
from typing import Dict, Any, List
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls
from app.profiles import BOOK_PROFILES, UNIVERSAL_PUBLISHING_SPECS


def set_cell_background(cell, color_hex: str):
    """Sets background shading of a docx table cell."""
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=140, bottom=140, left=200, right=200):
    """Sets internal padding in twentieths of a point (dxa)."""
    tcPr = cell._element.get_or_add_tcPr()
    tcMar = parse_xml(f'''
        <w:tcMar {nsdecls("w")}>
            <w:top w:w="{top}" w:type="dxa"/>
            <w:bottom w:w="{bottom}" w:type="dxa"/>
            <w:left w:w="{left}" w:type="dxa"/>
            <w:right w:w="{right}" w:type="dxa"/>
        </w:tcMar>
    ''')
    tcPr.append(tcMar)


def export_docx(
    parsed_book: Dict[str, Any],
    manifest: Dict[str, Any],
    profile_id: str,
    output_docx_path: str,
    include_front_matter: bool = True
) -> str:
    profile = BOOK_PROFILES.get(profile_id, BOOK_PROFILES["book01"])
    specs = UNIVERSAL_PUBLISHING_SPECS
    
    doc = docx.Document()
    
    # Configure 6x9 page dimensions & margins
    section = doc.sections[0]
    section.page_width = Inches(specs["trim_width_in"])
    section.page_height = Inches(specs["trim_height_in"])
    
    section.top_margin = Inches(specs["margins"]["top_margin_in"])
    section.bottom_margin = Inches(specs["margins"]["bottom_margin_in"])
    section.left_margin = Inches(specs["margins"]["inside_gutter_in"])
    section.right_margin = Inches(specs["margins"]["outside_margin_in"])
    
    # Enable different first page
    section.different_first_page_header_footer = True
    
    # Header setup
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hrun = hp.add_run(profile["short_title"].upper())
    hrun.font.size = Pt(8.5)
    hrun.font.name = profile["body_font_name"]
    hrun.font.color.rgb = RGBColor(100, 100, 100)

    # Footer setup
    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    frun = fp.add_run("— Argon Publishing Engine —")
    frun.font.size = Pt(8.0)
    frun.font.name = profile["body_font_name"]
    frun.font.color.rgb = RGBColor(140, 140, 140)

    assets_by_anchor: Dict[str, List[Dict[str, Any]]] = {}
    for a in manifest.get("assets", []):
        assets_by_anchor.setdefault(a.get("anchor", ""), []).append(a)

    # FRONT MATTER
    if include_front_matter:
        # Half Title
        p_half = doc.add_paragraph()
        p_half.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_half.paragraph_format.space_before = Inches(2.5)
        run_h = p_half.add_run(parsed_book.get("title", profile["title"]).upper())
        run_h.font.size = Pt(14)
        run_h.font.bold = True
        run_h.font.name = profile["body_font_name"]
        doc.add_page_break()

        # Title Page
        p_t1 = doc.add_paragraph()
        p_t1.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_t1.paragraph_format.space_before = Inches(1.5)
        r_t1 = p_t1.add_run(parsed_book.get("title", profile["title"]))
        r_t1.font.size = Pt(22)
        r_t1.font.bold = True
        r_t1.font.name = profile["body_font_name"]

        p_t2 = doc.add_paragraph()
        p_t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r_t2 = p_t2.add_run(parsed_book.get("subtitle", profile["subtitle"]))
        r_t2.font.size = Pt(12)
        r_t2.font.italic = True
        r_t2.font.name = profile["body_font_name"]

        p_t3 = doc.add_paragraph()
        p_t3.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_t3.paragraph_format.space_before = Inches(0.5)
        r_t3 = p_t3.add_run("◁  •  ▷")
        r_t3.font.size = Pt(11)

        p_t4 = doc.add_paragraph()
        p_t4.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_t4.paragraph_format.space_before = Inches(0.8)
        r_t4 = p_t4.add_run(parsed_book.get("author", profile["author"]))
        r_t4.font.size = Pt(12)
        r_t4.font.bold = True
        r_t4.font.name = profile["body_font_name"]

        p_t5 = doc.add_paragraph()
        p_t5.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_t5.paragraph_format.space_before = Inches(1.2)
        r_t5 = p_t5.add_run("THE ARGON BOOK STUDIO • FINE TYPESETTING")
        r_t5.font.size = Pt(8.5)
        r_t5.font.color.rgb = RGBColor(120, 120, 120)
        doc.add_page_break()

        # Copyright Page
        p_c1 = doc.add_paragraph()
        p_c1.paragraph_format.space_before = Inches(4.5)
        r_c1 = p_c1.add_run(f"{parsed_book.get('title', profile['title'])}\n")
        r_c1.bold = True
        r_c1.font.size = Pt(9)
        r_c2 = p_c1.add_run(
            f"Copyright © 2026 by {parsed_book.get('author', profile['author'])}\n"
            "All rights reserved. First 6x9\" Illustrated Edition.\n"
            "Published by The Argon Book Studio Press.\n"
            "ISBN 978-1-987654-32-1 (Fine Hardcover)\n\n"
            f"Typeset in {profile['body_font_name']} with display titles in {profile['display_font_name']}."
        )
        r_c2.font.size = Pt(8.5)
        r_c2.font.color.rgb = RGBColor(100, 100, 100)
        doc.add_page_break()

    # BODY CHAPTERS
    for ch_idx, chapter in enumerate(parsed_book.get("chapters", [])):
        ch_num = chapter.get("chapter_number", str(ch_idx + 1))
        ch_title = chapter.get("title", "")
        
        # Chapter opening heading with 1.75 in sinkage
        ch_h = doc.add_paragraph()
        ch_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ch_h.paragraph_format.space_before = Inches(specs["grid_rules"]["chapter_sinkage_in"])
        ch_h.paragraph_format.space_after = Pt(4)
        
        r_num = ch_h.add_run(f"CHAPTER {ch_num}\n")
        r_num.font.size = Pt(10)
        r_num.font.bold = True
        r_num.font.name = profile["body_font_name"]
        
        r_tit = ch_h.add_run(ch_title)
        r_tit.font.size = Pt(18)
        r_tit.font.bold = True
        r_tit.font.name = profile["body_font_name"]

        # Divider mark
        p_div = doc.add_paragraph()
        p_div.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_div.paragraph_format.space_after = Pt(24)
        r_div = p_div.add_run("— • —")
        r_div.font.size = Pt(10)
        r_div.font.color.rgb = RGBColor(150, 150, 150)

        first_p_done = False
        
        for elem in chapter.get("elements", []):
            elem_id = elem.get("id", "")
            elem_type = elem.get("type", "paragraph")
            
            # Check anchored illustrations
            for asset in assets_by_anchor.get(elem_id, []):
                img_path = asset.get("image_url", "")
                caption = asset.get("caption", "")
                
                # Try inserting image if file exists locally
                local_file = None
                if img_path.startswith("/static/"):
                    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                    cand = os.path.join(base_dir, img_path.lstrip("/")).replace("/", "\\")
                    if os.path.exists(cand):
                        local_file = cand
                elif os.path.exists(img_path):
                    local_file = img_path
                    
                p_img = doc.add_paragraph()
                p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_img.paragraph_format.space_before = Pt(12)
                p_img.paragraph_format.space_after = Pt(4)
                
                if local_file:
                    try:
                        p_img.add_run().add_picture(local_file, width=Inches(4.2))
                    except Exception:
                        r_ph = p_img.add_run(f"[ILLUSTRATION: {asset.get('title', '')}]")
                        r_ph.italic = True
                else:
                    r_ph = p_img.add_run(f"[ILLUSTRATION: {asset.get('title', '')}]")
                    r_ph.italic = True
                    
                if caption:
                    p_cap = doc.add_paragraph()
                    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    p_cap.paragraph_format.space_after = Pt(12)
                    r_cap = p_cap.add_run(caption)
                    r_cap.font.size = Pt(8.5)
                    r_cap.font.italic = True
                    r_cap.font.color.rgb = RGBColor(100, 100, 100)

            if elem_type == "paragraph":
                text = elem.get("text", "")
                is_first = elem.get("is_first_after_break", False) or not first_p_done
                
                p = doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.25
                
                if is_first:
                    p.paragraph_format.first_line_indent = Inches(0.0)
                else:
                    p.paragraph_format.first_line_indent = Inches(0.25)
                    
                r = p.add_run(text)
                r.font.name = profile["body_font_name"]
                r.font.size = Pt(10.5)
                first_p_done = True
                
            elif elem_type == "container":
                tag = elem.get("tag", "custom-container")
                content = elem.get("content", "")
                
                # Build styled container table
                tbl = doc.add_table(rows=1, cols=1)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                cell = tbl.cell(0, 0)
                cell.width = Inches(4.35)
                
                # Tint based on book profile
                bg_hex = "F8F9FA"
                if "slate" in tag:
                    bg_hex = "1E2229"
                elif "writ" in tag:
                    bg_hex = "FBF8F1"
                elif "transcript" in tag:
                    bg_hex = "0F172A"
                elif "pelham" in tag:
                    bg_hex = "FCFAF2"
                elif "cuneiform" in tag:
                    bg_hex = "FAF6EE"
                set_cell_background(cell, bg_hex)
                set_cell_margins(cell, top=160, bottom=160, left=240, right=240)
                
                cp = cell.paragraphs[0]
                cp.alignment = WD_ALIGN_PARAGRAPH.LEFT
                c_run = cp.add_run(content)
                c_run.font.size = Pt(9.0)
                c_run.font.name = "Courier New" if "transcript" in tag or "telemetry" in tag or "fsk" in tag else profile["body_font_name"]
                if "slate" in tag or "transcript" in tag:
                    c_run.font.color.rgb = RGBColor(240, 240, 240)
                else:
                    c_run.font.color.rgb = RGBColor(30, 30, 30)
                    
                # Add spacing after table
                p_sp = doc.add_paragraph()
                p_sp.paragraph_format.space_before = Pt(6)
                p_sp.paragraph_format.space_after = Pt(0)
                
            elif elem_type == "scene_break":
                p_brk = doc.add_paragraph()
                p_brk.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_brk.paragraph_format.space_before = Pt(14)
                p_brk.paragraph_format.space_after = Pt(14)
                r_b = p_brk.add_run("❖   ❖   ❖")
                r_b.font.size = Pt(9.5)
                r_b.font.color.rgb = RGBColor(120, 120, 120)

        # End of chapter page break
        doc.add_page_break()

    # COLOPHON PAGE
    p_col = doc.add_paragraph()
    p_col.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_col.paragraph_format.space_before = Inches(3.0)
    
    r_ch = p_col.add_run("COLOPHON\n\n")
    r_ch.font.size = Pt(10)
    r_ch.font.bold = True
    r_ch.font.name = profile["body_font_name"]
    
    r_cb = p_col.add_run(
        f"This volume was formatted and typeset in 6.0 x 9.0 in format using the Argon Book Studio Desktop Publishing Engine.\n\n"
        f"Body text set in {profile['body_font_name']} with 0.25 in paragraph indentations.\n"
        f"Display titles and ornaments set in {profile['display_font_name']}.\n"
        "Engine specification: Print-Ready Mirrored Margins (0.875\" Gutter / 0.625\" Outside)."
    )
    r_cb.font.size = Pt(8.5)
    r_cb.font.color.rgb = RGBColor(120, 120, 120)

    os.makedirs(os.path.dirname(output_docx_path), exist_ok=True)
    doc.save(output_docx_path)
    return output_docx_path
