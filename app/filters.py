"""
Argon Book Studio - Image Filter & Print Texture Pipeline.
Implements Python Pillow filter presets for all 5 Book Theme Profiles:
1. Cyanotype / 19th-Century Silver-Plate Etching
2. Charcoal & Hebridean Lithograph Wash
3. High-Contrast Oscilloscope & Architectural Blueprint Halftone
4. 1928 Sepia & Bioluminescent Amber Botanical Plate
5. Desert Ochre & UV-Fluorescence Archaeometric Micro-Grain

Supports live parameter tuning (grain, contrast, vignette, brightness),
base64 data URI generation for split Before/After comparison sliders,
300/600 DPI print resampling, and precision vector callouts.
"""

import base64
import io
import math
import os
import random
from typing import List, Dict, Any, Tuple, Optional
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance, ImageChops

PRINT_DPI = 300

# Dimensions at 300 DPI for standard book placements
DIMENSIONS_300DPI = {
    "Full-Page Recto Plate": (1800, 2700),
    "Half-Page Top": (1600, 1050),
    "Inline Archival Insert": (1400, 950),
    "Chapter Opener Vignette": (1600, 750),
    "Chapter End Tailpiece": (1200, 600)
}


def add_noise(image: Image.Image, intensity: float = 0.08) -> Image.Image:
    """Adds fine film grain / micro-stippling noise with custom intensity."""
    if intensity <= 0:
        return image
        
    img_rgba = image.convert("RGBA")
    width, height = img_rgba.size
    pixels = img_rgba.load()
    
    step = 2
    for y in range(0, height, step):
        for x in range(0, width, step):
            noise = int((random.random() - 0.5) * intensity * 255 * 1.5)
            r, g, b, a = pixels[x, y]
            nr = max(0, min(255, r + noise))
            ng = max(0, min(255, g + noise))
            nb = max(0, min(255, b + noise))
            pixels[x, y] = (nr, ng, nb, a)
            if x + 1 < width:
                pixels[x + 1, y] = (nr, ng, nb, a)
            if y + 1 < height:
                pixels[x, y + 1] = (nr, ng, nb, a)
    return img_rgba.convert("RGB")


def apply_vignette(image: Image.Image, strength: float = 0.38) -> Image.Image:
    """Applies a smooth edge vignette with adjustable strength."""
    if strength <= 0.01:
        return image
        
    width, height = image.size
    vignette = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(vignette)
    
    max_radius = math.hypot(width / 2, height / 2)
    center_x, center_y = width / 2, height / 2
    
    steps = 35
    for i in range(steps):
        factor = (i / steps)
        radius_x = (width / 2) * (1.15 - 0.5 * factor)
        radius_y = (height / 2) * (1.15 - 0.5 * factor)
        alpha = int(255 * (1 - strength * (1 - factor)))
        draw.ellipse(
            [center_x - radius_x, center_y - radius_y, center_x + radius_x, center_y + radius_y],
            outline=alpha,
            width=int(max_radius / steps) + 2
        )
    
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=max(2, width // 28)))
    
    r, g, b = image.split()
    r = ImageChops.multiply(r, vignette)
    g = ImageChops.multiply(g, vignette)
    b = ImageChops.multiply(b, vignette)
    return Image.merge("RGB", (r, g, b))


def filter_cyanotype_silver_plate(
    image: Image.Image,
    contrast: float = 1.35,
    grain: float = 0.08,
    vignette: float = 0.35,
    brightness: float = 1.0
) -> Image.Image:
    """Profile 01: Cyanotype / 19th-Century Silver-Plate Etching."""
    gray = ImageOps.grayscale(image)
    if brightness != 1.0:
        gray = ImageEnhance.Brightness(gray).enhance(brightness)
    contrasted = ImageEnhance.Contrast(gray).enhance(contrast)
    
    # Silver halide edge line enhancement
    edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1))
    edges = ImageOps.invert(edges)
    edges = ImageEnhance.Contrast(edges).enhance(1.2)
    
    colorized = ImageOps.colorize(
        contrasted,
        black=(12, 30, 48),
        mid=(38, 76, 118),
        white=(240, 246, 250),
        midpoint=122
    )
    
    colorized = Image.blend(colorized, edges.convert("RGB"), 0.12)
    final = add_noise(colorized, intensity=grain)
    final = apply_vignette(final, strength=vignette)
    return final


def filter_charcoal_lithograph(
    image: Image.Image,
    contrast: float = 1.4,
    grain: float = 0.09,
    vignette: float = 0.45,
    brightness: float = 0.95
) -> Image.Image:
    """Profile 02: Charcoal & Hebridean Lithograph Wash."""
    gray = ImageOps.grayscale(image)
    if brightness != 1.0:
        gray = ImageEnhance.Brightness(gray).enhance(brightness)
    contrasted = ImageEnhance.Contrast(gray).enhance(contrast)
    
    diffuse = gray.filter(ImageFilter.GaussianBlur(2))
    chalk = Image.blend(contrasted, diffuse, 0.22)
    
    colorized = ImageOps.colorize(
        chalk,
        black=(16, 20, 26),
        mid=(74, 88, 106),
        white=(235, 240, 245),
        midpoint=115
    )
    
    final = add_noise(colorized, intensity=grain)
    final = apply_vignette(final, strength=vignette)
    return final


def filter_blueprint_halftone(
    image: Image.Image,
    contrast: float = 1.5,
    grain: float = 0.06,
    vignette: float = 0.25,
    brightness: float = 1.0
) -> Image.Image:
    """Profile 03: High-Contrast Oscilloscope & Architectural Blueprint Halftone."""
    gray = ImageOps.grayscale(image)
    if brightness != 1.0:
        gray = ImageEnhance.Brightness(gray).enhance(brightness)
    contrasted = ImageEnhance.Contrast(gray).enhance(contrast)
    
    colorized = ImageOps.colorize(
        contrasted,
        black=(7, 18, 36),
        mid=(2, 132, 199),
        white=(224, 242, 254),
        midpoint=135
    )
    
    # Raster blueprint grid
    w, h = colorized.size
    grid_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grid_draw = ImageDraw.Draw(grid_img)
    step = 40
    for x in range(0, w, step):
        grid_draw.line([(x, 0), (x, h)], fill=(56, 189, 248, 22), width=1)
    for y in range(0, h, step):
        grid_draw.line([(0, y), (w, y)], fill=(56, 189, 248, 22), width=1)
        
    colorized_rgba = colorized.convert("RGBA")
    colorized_rgba.alpha_composite(grid_img)
    final = colorized_rgba.convert("RGB")
    final = add_noise(final, intensity=grain)
    final = apply_vignette(final, strength=vignette)
    return final


def filter_sepia_bioluminescent_amber(
    image: Image.Image,
    contrast: float = 1.25,
    grain: float = 0.08,
    vignette: float = 0.38,
    brightness: float = 1.0
) -> Image.Image:
    """Profile 04: 1928 Sepia & Bioluminescent Amber Botanical Plate."""
    gray = ImageOps.grayscale(image)
    if brightness != 1.0:
        gray = ImageEnhance.Brightness(gray).enhance(brightness)
    contrasted = ImageEnhance.Contrast(gray).enhance(contrast)
    
    colorized = ImageOps.colorize(
        contrasted,
        black=(31, 21, 13),
        mid=(184, 110, 22),
        white=(250, 244, 228),
        midpoint=120
    )
    
    final = add_noise(colorized, intensity=grain)
    final = apply_vignette(final, strength=vignette)
    return final


def filter_desert_ochre_uv(
    image: Image.Image,
    contrast: float = 1.3,
    grain: float = 0.09,
    vignette: float = 0.32,
    brightness: float = 1.0
) -> Image.Image:
    """Profile 05: Desert Ochre & UV-Fluorescence Archaeometric Micro-Grain."""
    gray = ImageOps.grayscale(image)
    if brightness != 1.0:
        gray = ImageEnhance.Brightness(gray).enhance(brightness)
    contrasted = ImageEnhance.Contrast(gray).enhance(contrast)
    
    colorized = ImageOps.colorize(
        contrasted,
        black=(59, 27, 16),
        mid=(156, 81, 42),
        white=(247, 234, 208),
        midpoint=125
    )
    
    edges = gray.filter(ImageFilter.FIND_EDGES)
    enh_edges = ImageEnhance.Contrast(edges).enhance(1.5)
    uv_accent = ImageOps.colorize(
        enh_edges,
        black=(0, 0, 0),
        white=(218, 165, 32)
    )
    blended = Image.blend(colorized, uv_accent, 0.15)
    
    final = add_noise(blended, intensity=grain)
    final = apply_vignette(final, strength=vignette)
    return final


FILTER_MAP = {
    "cyanotype_silver_plate": filter_cyanotype_silver_plate,
    "charcoal_lithograph": filter_charcoal_lithograph,
    "blueprint_halftone": filter_blueprint_halftone,
    "sepia_bioluminescent_amber": filter_sepia_bioluminescent_amber,
    "desert_ochre_uv": filter_desert_ochre_uv
}


def apply_frame_style(image: Image.Image, frame_style: str = "none", profile_id: str = "book01") -> Image.Image:
    """Applies authentic book frame styling around illustration."""
    if not frame_style or frame_style == "none":
        return image
        
    img = image.convert("RGB")
    w, h = img.size
    draw = ImageDraw.Draw(img)
    
    if frame_style == "thin_ink_border":
        draw.rectangle([8, 8, w - 8, h - 8], outline=(30, 30, 30), width=2)
    elif frame_style == "double_brass_frame":
        draw.rectangle([10, 10, w - 10, h - 10], outline=(27, 40, 56), width=3)
        draw.rectangle([16, 16, w - 16, h - 16], outline=(184, 134, 11), width=1)
    elif frame_style == "blueprint_grid_frame":
        draw.rectangle([12, 12, w - 12, h - 12], outline=(15, 23, 42), width=2)
        for cx, cy in [(12, 12), (w - 12, 12), (12, h - 12), (w - 12, h - 12)]:
            draw.line([(cx - 10, cy), (cx + 10, cy)], fill=(56, 189, 248), width=2)
            draw.line([(cx, cy - 10), (cx, cy + 10)], fill=(56, 189, 248), width=2)
    elif frame_style == "rounded_slate":
        draw.rounded_rectangle([10, 10, w - 10, h - 10], radius=14, outline=(40, 48, 60), width=3)
        
    return img


def render_vector_callouts(image: Image.Image, callouts: List[Dict[str, Any]], profile_id: str = "book01") -> Image.Image:
    """
    Renders high-resolution vector text callout labels, boxes, crosshairs, and pointers
    over maps and diagrams without AI distortion.
    """
    if not callouts:
        return image

    img_copy = image.copy().convert("RGBA")
    overlay = Image.new("RGBA", img_copy.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    w, h = img_copy.size
    
    theme_colors = {
        "book01": {"bg": (27, 54, 93, 235), "border": (184, 134, 11, 255), "text": (255, 255, 255, 255)},
        "book02": {"bg": (30, 34, 41, 240), "border": (0, 168, 150, 255), "text": (255, 255, 255, 255)},
        "book03": {"bg": (15, 23, 42, 245), "border": (56, 189, 248, 255), "text": (224, 242, 254, 255)},
        "book04": {"bg": (44, 64, 46, 240), "border": (217, 119, 6, 255), "text": (255, 253, 245, 255)},
        "book05": {"bg": (90, 42, 24, 240), "border": (201, 138, 44, 255), "text": (250, 246, 238, 255)},
    }
    tc = theme_colors.get(profile_id, theme_colors["book01"])
    
    font_size = max(13, int(w * 0.016))
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    for c in callouts:
        raw_x = c.get("x_pct")
        if raw_x is None:
            raw_x = c.get("x")
        if raw_x is None:
            raw_x = 50
        x_pct = float(raw_x)

        raw_y = c.get("y_pct")
        if raw_y is None:
            raw_y = c.get("y")
        if raw_y is None:
            raw_y = 50
        y_pct = float(raw_y)
        
        has_target = (c.get("target_x_pct") is not None or c.get("target_x") is not None)
        raw_tx = c.get("target_x_pct")
        if raw_tx is None:
            raw_tx = c.get("target_x")
        if raw_tx is None:
            raw_tx = x_pct
        tx_pct = float(raw_tx)

        raw_ty = c.get("target_y_pct")
        if raw_ty is None:
            raw_ty = c.get("target_y")
        if raw_ty is None:
            raw_ty = y_pct
        ty_pct = float(raw_ty)
        
        label = str(c.get("text", c.get("label", ""))).strip().upper()
        c_type = str(c.get("style", c.get("type", "badge"))).lower()
        if not label:
            continue
            
        px = int((x_pct / 100.0) * w)
        py = int((y_pct / 100.0) * h)
        tpx = int((tx_pct / 100.0) * w)
        tpy = int((ty_pct / 100.0) * h)
        
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad_x = 12
        pad_y = 6
        
        box_w = text_w + pad_x * 2
        box_h = text_h + pad_y * 2
        
        x0 = max(10, min(w - box_w - 10, px - box_w // 2))
        y0 = max(10, min(h - box_h - 10, py - box_h // 2))
        x1 = x0 + box_w
        y1 = y0 + box_h
        
        # If target point is separated from label, draw pointer leader line
        if has_target and (abs(tpx - px) > 15 or abs(tpy - py) > 15):
            # Find closest edge point on label box
            mid_x = (x0 + x1) // 2
            mid_y = (y0 + y1) // 2
            edge_x = x0 if tpx < mid_x else x1
            edge_y = y0 if tpy < mid_y else y1
            
            # Draw leader line
            draw.line([(edge_x, mid_y), (tpx, tpy)], fill=tc["border"], width=2)
            # Draw target indicator at (tpx, tpy)
            draw.circle((tpx, tpy), radius=4, fill=tc["border"])
            draw.ellipse([tpx - 8, tpy - 8, tpx + 8, tpy + 8], outline=tc["border"], width=1)

        if "crosshair" in c_type:
            # Target crosshair at (tpx, tpy)
            cr = 14
            draw.ellipse([tpx - cr, tpy - cr, tpx + cr, tpy + cr], outline=tc["border"], width=2)
            draw.line([(tpx - cr - 6, tpy), (tpx + cr + 6, tpy)], fill=tc["border"], width=2)
            draw.line([(tpx, tpy - cr - 6), (tpx, tpy + cr + 6)], fill=tc["border"], width=2)
            draw.circle((tpx, tpy), radius=3, fill=tc["border"])
            draw.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=tc["bg"], outline=tc["border"], width=1)
            draw.text((x0 + pad_x, y0 + pad_y - 2), label, font=font, fill=tc["text"])
        elif "box" in c_type:
            draw.rectangle([x0, y0, x1, y1], fill=tc["bg"], outline=tc["border"], width=2)
            draw.line([x0 - 4, y0, x0 + 4, y0], fill=tc["border"], width=1)
            draw.line([x0, y0 - 4, x0, y0 + 4], fill=tc["border"], width=1)
            draw.text((x0 + pad_x, y0 + pad_y - 2), label, font=font, fill=tc["text"])
        elif "badge" in c_type:
            draw.rounded_rectangle([x0, y0, x1, y1], radius=6, fill=tc["bg"], outline=tc["border"], width=2)
            if not has_target:
                draw.circle((px, py + box_h // 2 + 10), radius=4, fill=tc["border"])
                draw.line([(px, py + box_h // 2), (px, py + box_h // 2 + 10)], fill=tc["border"], width=2)
            draw.text((x0 + pad_x, y0 + pad_y - 2), label, font=font, fill=tc["text"])
        elif "arrow" in c_type:
            draw.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=tc["bg"], outline=tc["border"], width=2)
            if not has_target:
                target_y = y1 + 16 if "down" in c_type or "up" not in c_type else y0 - 16
                draw.line([(px, y1), (px, target_y)], fill=tc["border"], width=2)
                draw.polygon([(px - 4, target_y), (px + 4, target_y), (px, target_y + 6)], fill=tc["border"])
            draw.text((x0 + pad_x, y0 + pad_y - 2), label, font=font, fill=tc["text"])
        else: # callout_pointer or default
            draw.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=tc["bg"], outline=tc["border"], width=2)
            draw.text((x0 + pad_x, y0 + pad_y - 2), label, font=font, fill=tc["text"])
            
    img_copy.alpha_composite(overlay)
    return img_copy.convert("RGB")


def process_image(
    input_image_path: str,
    output_image_path: str,
    filter_preset: str,
    placement_type: str = "Half-Page Top",
    callouts: List[Dict[str, Any]] = None,
    profile_id: str = "book01",
    target_dpi: int = PRINT_DPI,
    contrast: float = 1.35,
    grain: float = 0.08,
    vignette: float = 0.38,
    brightness: float = 1.0,
    frame_style: str = "none"
) -> str:
    """Applies filter, custom adjustments, callouts, framing, and resamples to target DPI."""
    img = Image.open(input_image_path).convert("RGB")
    
    scale_factor = 2 if target_dpi >= 600 else 1
    base_size = DIMENSIONS_300DPI.get(placement_type, (1600, 1050))
    target_size = (base_size[0] * scale_factor, base_size[1] * scale_factor)
    
    img = ImageOps.fit(img, target_size, method=Image.Resampling.LANCZOS)
    
    filter_func = FILTER_MAP.get(filter_preset, filter_cyanotype_silver_plate)
    filtered = filter_func(
        img,
        contrast=contrast,
        grain=grain,
        vignette=vignette,
        brightness=brightness
    )
    
    if frame_style and frame_style != "none":
        filtered = apply_frame_style(filtered, frame_style, profile_id)
        
    if callouts:
        filtered = render_vector_callouts(filtered, callouts, profile_id)
        
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    filtered.save(output_image_path, "PNG", dpi=(target_dpi, target_dpi))
    return output_image_path


def generate_preview_base64(
    image_path: str,
    filter_preset: str,
    contrast: float = 1.35,
    grain: float = 0.08,
    vignette: float = 0.38,
    brightness: float = 1.0,
    callouts: List[Dict[str, Any]] = None,
    profile_id: str = "book01",
    frame_style: str = "none"
) -> str:
    """Generates a fast base64 preview for the interactive split comparison slider."""
    if not os.path.exists(image_path):
        return ""
    img = Image.open(image_path).convert("RGB")
    # Resize to modest preview dimensions (max 900px)
    img.thumbnail((900, 600), Image.Resampling.LANCZOS)
    
    filter_func = FILTER_MAP.get(filter_preset, filter_cyanotype_silver_plate)
    filtered = filter_func(
        img,
        contrast=contrast,
        grain=grain,
        vignette=vignette,
        brightness=brightness
    )
    if frame_style and frame_style != "none":
        filtered = apply_frame_style(filtered, frame_style, profile_id)
    if callouts:
        filtered = render_vector_callouts(filtered, callouts, profile_id)
        
    buf = io.BytesIO()
    filtered.save(buf, format="JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_procedural_placeholder(
    output_path: str,
    title: str,
    prompt: str,
    placement_type: str,
    filter_preset: str,
    profile_id: str,
    callouts: List[Dict[str, Any]] = None,
    contrast: float = 1.35,
    grain: float = 0.08,
    vignette: float = 0.38,
    frame_style: str = "none"
) -> str:
    """Generates an authentic procedural etching/engraving plate with custom parameters."""
    size = DIMENSIONS_300DPI.get(placement_type, (1600, 1050))
    w, h = size
    
    base = Image.new("RGB", (w, h), (245, 242, 235))
    draw = ImageDraw.Draw(base)
    
    margin = int(w * 0.05)
    draw.rectangle([margin, margin, w - margin, h - margin], outline=(40, 40, 40), width=3)
    draw.rectangle([margin + 12, margin + 12, w - margin - 12, h - margin - 12], outline=(90, 90, 90), width=1)
    
    hatch_spacing = 18
    for i in range(margin + 20, w - margin - 20, hatch_spacing):
        y_top = margin + 20
        y_bot = h - margin - 20
        curve_pts = []
        for y in range(y_top, y_bot, 20):
            x_offset = int(math.sin(y / 45.0 + i / 100.0) * 8)
            curve_pts.append((i + x_offset, y))
        if len(curve_pts) > 1:
            draw.line(curve_pts, fill=(180, 175, 165), width=1)
            
    cx, cy = w // 2, h // 2
    r = min(w, h) // 4
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(50, 50, 50), width=3)
    draw.ellipse([cx - r + 15, cy - r + 15, cx + r - 15, cy + r - 15], outline=(100, 100, 100), width=1)
    
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x_outer = cx + int((r - 20) * math.cos(rad))
        y_outer = cy + int((r - 20) * math.sin(rad))
        x_inner = cx + int((r // 3) * math.cos(rad))
        y_inner = cy + int((r // 3) * math.sin(rad))
        draw.line([(x_inner, y_inner), (x_outer, y_outer)], fill=(60, 60, 60), width=2)
        
    draw.circle((cx, cy), radius=16, fill=(40, 40, 40))
    
    plaque_w = int(w * 0.7)
    plaque_h = int(h * 0.12)
    px0 = (w - plaque_w) // 2
    py0 = h - margin - plaque_h - 20
    draw.rectangle([px0, py0, px0 + plaque_w, py0 + plaque_h], fill=(255, 255, 255), outline=(30, 30, 30), width=2)
    
    try:
        font_large = ImageFont.truetype("arialbd.ttf", int(plaque_h * 0.35))
        font_small = ImageFont.truetype("arial.ttf", int(plaque_h * 0.22))
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        
    draw.text((px0 + 20, py0 + 12), title[:45].upper(), font=font_large, fill=(20, 20, 20))
    draw.text((px0 + 20, py0 + 16 + int(plaque_h * 0.4)), f"ARGON STUDIO SPECIFICATION // {placement_type.upper()}", font=font_small, fill=(90, 90, 90))
    
    filter_func = FILTER_MAP.get(filter_preset, filter_cyanotype_silver_plate)
    filtered = filter_func(base, contrast=contrast, grain=grain, vignette=vignette)
    
    if frame_style and frame_style != "none":
        filtered = apply_frame_style(filtered, frame_style, profile_id)
        
    if callouts:
        filtered = render_vector_callouts(filtered, callouts, profile_id)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    filtered.save(output_path, "PNG", dpi=(PRINT_DPI, PRINT_DPI))
    return output_path
