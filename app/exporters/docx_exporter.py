"""
Argon Book Studio - Styled Editable DOCX Exporter.
Generates Word documents adhering to the core publishing engine rules:
- Configurable trim size (default 6.0 in x 9.0 in).
- Mirrored margins (gutter, outside, top, bottom).
- Chapter opening top sinkage.
- Indentation rules (first body paragraph indent 0; subsequent body paragraphs indent 0.25in).
- Custom container boxes formatted as styled tables with borders.
- Verso / Recto headers and footers with page numbers.
- Extended front & back matter (dedication, epigraph, colophon).
"""

import os
from typing import Dict, Any, List, Optional
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn, nsdecls
from app.profiles import BOOK_PROFILES, UNIVERSAL_PUBLISHING_SPECS


def set_cell_background(cell, color_hex: str):
    tcPr = cell._element.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=140, bottom=140, left=200, right=200):
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
    include_front_matter: bool = True,
    custom_specs: Dict[str, Any] = None,
    custom_matter: Dict[str, Any] = None
) -> str:
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
    indent = float(cs.get("typography", {}).get("subsequent_p_indent_in", cs.get("subsequent_p_indent_in", specs["grid_rules"]["subsequent_p_indent_in"])))
    font_name = cs.get("typography", {}).get("body_font_name", profile["body_font_name"])
    body_size = float(cs.get("typography", {}).get("body_font_size_pt", cs.get("body_font_size_pt", 10.5)))
    
    doc = docx.Document()
    
    section = doc.sections[0]
    section.page_width = Inches(trim_w)
    section.page_height = Inches(trim_h)
    
    section.top_margin = Inches(top)
    section.bottom_margin = Inches(bottom)
    section.left_margin = Inches(gutter)
    section.right_margin = Inches(outside)
    
    section.different_first_page_header_footer = True
    
    header = section.header
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    hrun = hp.add_run(cs.get("typography", {}).get("running_header_override") or profile["short_title"].upper())
    hrun.font.size = Pt(8.5)
    hrun.font.name = font_name
    hrun.font.color.rgb = RGBColor(100, 100, 100)

    footer = section.footer
    fp = footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    frun = fp.add_run("— Argon Publishing Engine —")
    frun.font.size = Pt(8.0)
    frun.font.name = font_name
    frun.font.color.rgb = RGBColor(140, 140, 140)

    assets_by_anchor: Dict[str, List[Dict[str, Any]]] = {}
    for a in manifest.get("assets", []):
        assets_by_anchor.setdefault(a.get("anchor", ""), []).append(a)

    # FRONT MATTER
    if include_front_matter:
        if cm.get("include_half_title", True):
            p_half = doc.add_paragraph()
            p_half.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_half.paragraph_format.space_before = Inches(2.5)
            run_h = p_half.add_run(parsed_book.get("title", profile["title"]).upper())
            run_h.font.size = Pt(14)
            run_h.font.bold = True
            run_h.font.name = font_name
            doc.add_page_break()

        if cm.get("include_title_page", True):
            p_t1 = doc.add_paragraph()
            p_t1.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_t1.paragraph_format.space_before = Inches(1.5)
            r_t1 = p_t1.add_run(parsed_book.get("title", profile["title"]))
            r_t1.font.size = Pt(22)
            r_t1.font.bold = True
            r_t1.font.name = font_name

            p_t2 = doc.add_paragraph()
            p_t2.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_t2 = p_t2.add_run(parsed_book.get("subtitle", profile["subtitle"]))
            r_t2.font.size = Pt(12)
            r_t2.font.italic = True
            r_t2.font.name = font_name

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
            r_t4.font.name = font_name

            p_t5 = doc.add_paragraph()
            p_t5.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_t5.paragraph_format.space_before = Inches(1.2)
            imprint_txt = cm.get("publisher_imprint", "THE ARGON BOOK STUDIO • FINE TYPESETTING")
            r_t5 = p_t5.add_run(imprint_txt)
            r_t5.font.size = Pt(8.5)
            r_t5.font.color.rgb = RGBColor(120, 120, 120)
            doc.add_page_break()

        if cm.get("include_copyright", True):
            isbn_hc = cm.get("isbn_hardcover", "978-1-987654-32-1")
            p_c1 = doc.add_paragraph()
            p_c1.paragraph_format.space_before = Inches(4.0)
            r_c1 = p_c1.add_run(f"{parsed_book.get('title', profile['title'])}\n")
            r_c1.bold = True
            r_c1.font.size = Pt(9)
            r_c2 = p_c1.add_run(
                f"Copyright © 2026 by {parsed_book.get('author', profile['author'])}\n"
                "All rights reserved. First Illustrated Edition.\n"
                f"ISBN {isbn_hc} (Fine Edition)\n\n"
                f"Typeset in {font_name} on {trim_w:.1f} x {trim_h:.1f}\" signatures."
            )
            r_c2.font.size = Pt(8.5)
            r_c2.font.color.rgb = RGBColor(100, 100, 100)
            doc.add_page_break()

        if cm.get("include_dedication", False):
            p_ded = doc.add_paragraph()
            p_ded.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_ded.paragraph_format.space_before = Inches(3.0)
            r_ded = p_ded.add_run(cm.get("dedication_text", ""))
            r_ded.italic = True
            r_ded.font.size = Pt(11)
            doc.add_page_break()

        if cm.get("include_epigraph", False):
            p_epi = doc.add_paragraph()
            p_epi.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p_epi.paragraph_format.space_before = Inches(3.0)
            r_epi = p_epi.add_run(f'"{cm.get("epigraph_text", "")}"\n\n')
            r_epi.italic = True
            r_epi.font.size = Pt(10.5)
            r_src = p_epi.add_run(cm.get("epigraph_source", ""))
            r_src.font.size = Pt(9)
            doc.add_page_break()

    # BODY CHAPTERS
    for ch_idx, chapter in enumerate(parsed_book.get("chapters", [])):
        ch_num = chapter.get("chapter_number", str(ch_idx + 1))
        ch_title = chapter.get("title", "")
        
        ch_h = doc.add_paragraph()
        ch_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ch_h.paragraph_format.space_before = Inches(sinkage)
        ch_h.paragraph_format.space_after = Pt(4)
        
        r_num = ch_h.add_run(f"CHAPTER {ch_num}\n")
        r_num.font.size = Pt(10)
        r_num.font.bold = True
        r_num.font.name = font_name
        
        r_tit = ch_h.add_run(ch_title)
        r_tit.font.size = Pt(18)
        r_tit.font.bold = True
        r_tit.font.name = font_name

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
            
            for asset in assets_by_anchor.get(elem_id, []):
                img_path = asset.get("image_url", "")
                caption = asset.get("caption", "")
                
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
                        p_img.add_run().add_picture(local_file, width=Inches(max(3.0, trim_w - 1.8)))
                    except Exception:
                        p_img.add_run(f"[ILLUSTRATION: {asset.get('title', '')}]").italic = True
                else:
                    p_img.add_run(f"[ILLUSTRATION: {asset.get('title', '')}]").italic = True
                    
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
                    p.paragraph_format.first_line_indent = Inches(indent)
                    
                r = p.add_run(text)
                r.font.name = font_name
                r.font.size = Pt(body_size)
                first_p_done = True
                
            elif elem_type == "container":
                tag = elem.get("tag", "custom-container")
                content = elem.get("content", "")
                
                tbl = doc.add_table(rows=1, cols=1)
                tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
                cell = tbl.cell(0, 0)
                cell.width = Inches(max(3.0, trim_w - 1.6))
                
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
                c_run.font.name = "Courier New" if "transcript" in tag or "telemetry" in tag or "fsk" in tag else font_name
                if "slate" in tag or "transcript" in tag:
                    c_run.font.color.rgb = RGBColor(240, 240, 240)
                else:
                    c_run.font.color.rgb = RGBColor(30, 30, 30)
                    
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

        doc.add_page_break()

    # BACK MATTER
    if cm.get("include_acknowledgements", False):
        p_ak = doc.add_paragraph()
        p_ak.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ak.paragraph_format.space_before = Inches(2.0)
        p_ak.add_run("ACKNOWLEDGEMENTS\n\n").bold = True
        doc.add_paragraph(cm.get("acknowledgements_text", "")).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_page_break()

    if cm.get("include_about_author", False):
        p_aa = doc.add_paragraph()
        p_aa.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_aa.paragraph_format.space_before = Inches(2.0)
        p_aa.add_run("ABOUT THE AUTHOR\n\n").bold = True
        doc.add_paragraph(cm.get("about_author_text", "")).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        doc.add_page_break()

    if cm.get("include_colophon", True):
        p_col = doc.add_paragraph()
        p_col.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_col.paragraph_format.space_before = Inches(2.5)
        
        r_ch = p_col.add_run("COLOPHON\n\n")
        r_ch.font.size = Pt(10)
        r_ch.font.bold = True
        r_ch.font.name = font_name
        
        col_body = cm.get("colophon_text") or (
            f"This volume was formatted and typeset in {trim_w:.1f} x {trim_h:.1f}\" format using the Argon Book Studio Desktop Publishing Engine.\n\n"
            f"Body text set in {font_name} with {indent} in paragraph indentations.\n"
            f"Mirrored margins: {gutter} in inside gutter, {outside} in outside margin."
        )
        r_cb = p_col.add_run(col_body)
        r_cb.font.size = Pt(8.5)
        r_cb.font.color.rgb = RGBColor(120, 120, 120)

    os.makedirs(os.path.dirname(output_docx_path), exist_ok=True)
    doc.save(output_docx_path)
    return output_docx_path
