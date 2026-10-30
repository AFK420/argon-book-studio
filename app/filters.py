"""
Argon Book Studio - Image Filter & Print Texture Pipeline.
Implements Python Pillow filter presets for all 5 Book Theme Profiles:
1. Cyanotype / 19th-Century Silver-Plate Etching
2. Charcoal & Hebridean Lithograph Wash
3. High-Contrast Oscilloscope & Architectural Blueprint Halftone
4. 1928 Sepia & Bioluminescent Amber Botanical Plate
5. Desert Ochre & UV-Fluorescence Archaeometric Micro-Grain

Also handles 300 DPI print resampling and vector callout overlay generation.
"""

import io
import math
import os
import random
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageEnhance

PRINT_DPI = 300

# Dimensions at 300 DPI for 6x9 book (margins respected or full bleed)
DIMENSIONS_300DPI = {
    "Full-Page Recto Plate": (1800, 2700),
    "Half-Page Top": (1600, 1050),
    "Inline Archival Insert": (1400, 950),
    "Chapter Opener Vignette": (1600, 750),
    "Chapter End Tailpiece": (1200, 600)
}


def add_noise(image: Image.Image, intensity: float = 0.08) -> Image.Image:
    """Adds fine film grain / micro-stippling noise."""
    img_rgba = image.convert("RGBA")
    width, height = img_rgba.size
    pixels = img_rgba.load()
    
    # We sample noise across pixels
    for y in range(0, height, 2):
        for x in range(0, width, 2):
            noise = int((random.random() - 0.5) * intensity * 255)
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


def apply_vignette(image: Image.Image, strength: float = 0.4) -> Image.Image:
    """Applies a smooth edge vignette."""
    width, height = image.size
    vignette = Image.new("L", (width, height), 255)
    draw = ImageDraw.Draw(vignette)
    
    max_radius = math.hypot(width / 2, height / 2)
    center_x, center_y = width / 2, height / 2
    
    steps = 40
    for i in range(steps):
        factor = (i / steps)
        radius_x = (width / 2) * (1.1 - 0.5 * factor)
        radius_y = (height / 2) * (1.1 - 0.5 * factor)
        alpha = int(255 * (1 - strength * (1 - factor)))
        draw.ellipse(
            [center_x - radius_x, center_y - radius_y, center_x + radius_x, center_y + radius_y],
            outline=alpha,
            width=int(max_radius / steps) + 2
        )
    
    vignette = vignette.filter(ImageFilter.GaussianBlur(radius=width // 25))
    
    # Apply vignette as shadow
    r, g, b = image.split()
    r = ImageMath_multiply(r, vignette)
    g = ImageMath_multiply(g, vignette)
    b = ImageMath_multiply(b, vignette)
    return Image.merge("RGB", (r, g, b))


def ImageMath_multiply(ch: Image.Image, mask: Image.Image) -> Image.Image:
    """Fast channel multiplication with mask."""
    return ImageChops_multiply(ch, mask)


def ImageChops_multiply(a: Image.Image, b: Image.Image) -> Image.Image:
    from PIL import ImageChops
    return ImageChops.multiply(a, b)


def filter_cyanotype_silver_plate(image: Image.Image) -> Image.Image:
    """
    Profile 01: Cyanotype / 19th-Century Silver-Plate Etching.
    Rich Prussian-cyan toning, silver halide grain, contrast-deepened midtones, fine etched edges.
    """
    gray = ImageOps.grayscale(image)
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(1.35)
    
    # Silver halide edge line enhancement
    edges = gray.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(1))
    edges = ImageOps.invert(edges)
    edges = ImageEnhance.Contrast(edges).enhance(1.2)
    
    # Colorize with Prussian Blue / Silver Tint:
    # Deep shadow: #0A1B2A (10, 27, 42)
    # Midtone: #1E3F66 (30, 63, 102)
    # Highlight: #EBF3F8 (235, 243, 248)
    colorized = ImageOps.colorize(
        contrasted,
        black=(12, 30, 48),
        mid=(38, 76, 118),
        white=(240, 246, 250),
        midpoint=122
    )
    
    # Blend with fine etching line detail
    colorized = Image.blend(colorized, edges.convert("RGB"), 0.12)
    
    # Add subtle silver-plate micro-noise & vignette
    final = add_noise(colorized, intensity=0.07)
    final = apply_vignette(final, strength=0.35)
    return final


def filter_charcoal_lithograph(image: Image.Image) -> Image.Image:
    """
    Profile 02: Charcoal & Hebridean Lithograph Wash.
    Desaturated slate-charcoal tones, wet wash diffusion, crushed basalt blacks, salt-spray grain.
    """
    gray = ImageOps.grayscale(image)
    
    # Deepen shadows for basalt cliffs
    contrasted = ImageEnhance.Contrast(gray).enhance(1.4)
    contrasted = ImageEnhance.Brightness(contrasted).enhance(0.92)
    
    # Charcoal blur-diffuse pass
    diffuse = gray.filter(ImageFilter.GaussianBlur(2))
    chalk = Image.blend(contrasted, diffuse, 0.25)
    
    # Colorize with dark basalt & stormy slate tones:
    # Black: #10141A (16, 20, 26)
    # Slate mid: #4A5568 (74, 85, 104)
    # White: #EDF2F7 (237, 242, 247)
    colorized = ImageOps.colorize(
        chalk,
        black=(16, 20, 26),
        mid=(74, 88, 106),
        white=(235, 240, 245),
        midpoint=115
    )
    
    # Add salt-spray lithograph wash grain
    final = add_noise(colorized, intensity=0.09)
    final = apply_vignette(final, strength=0.45)
    return final


def filter_blueprint_halftone(image: Image.Image) -> Image.Image:
    """
    Profile 03: High-Contrast Oscilloscope & Architectural Blueprint Halftone.
    Navy-cyan blueprint duotone with cathode grid structure and sharp line edges.
    """
    gray = ImageOps.grayscale(image)
    
    # Oscilloscope beam edge filter
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = ImageOps.invert(edges)
    
    contrasted = ImageEnhance.Contrast(gray).enhance(1.5)
    
    # Blueprint color scheme:
    # Deep Navy: #071224 (7, 18, 36)
    # Oscilloscope Cyan: #0284C7 (2, 132, 199)
    # Phosphor Beam Highlight: #E0F2FE (224, 242, 254)
    colorized = ImageOps.colorize(
        contrasted,
        black=(7, 18, 36),
        mid=(2, 132, 199),
        white=(224, 242, 254),
        midpoint=135
    )
    
    # Grid lines overlay (architectural blueprint raster)
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
    final = add_noise(final, intensity=0.05)
    return final


def filter_sepia_bioluminescent_amber(image: Image.Image) -> Image.Image:
    """
    Profile 04: 1928 Sepia & Bioluminescent Amber Botanical Plate.
    Archival warm sepia plate stippling with glowing warm amber bioluminescent highlights in shadows.
    """
    gray = ImageOps.grayscale(image)
    contrasted = ImageEnhance.Contrast(gray).enhance(1.25)
    
    # Sepia & amber colorization:
    # Shadow: #1F150D (31, 21, 13)
    # Amber Glow Mid: #C47414 (196, 116, 20)
    # Antique Paper: #FAF5E8 (250, 245, 232)
    colorized = ImageOps.colorize(
        contrasted,
        black=(31, 21, 13),
        mid=(184, 110, 22),
        white=(250, 244, 228),
        midpoint=120
    )
    
    final = add_noise(colorized, intensity=0.08)
    final = apply_vignette(final, strength=0.38)
    return final


def filter_desert_ochre_uv(image: Image.Image) -> Image.Image:
    """
    Profile 05: Desert Ochre & UV-Fluorescence Archaeometric Micro-Grain.
    Ochre terracotta tones with fluorescent ultraviolet highlights and museum micro-crack grain.
    """
    gray = ImageOps.grayscale(image)
    contrasted = ImageEnhance.Contrast(gray).enhance(1.3)
    
    # Ochre with UV trace:
    # Shadow: #3B1B10 (59, 27, 16)
    # Terracotta: #9C512A (156, 81, 42)
    # UV Sand Glow: #F7EAD0 (247, 234, 208)
    colorized = ImageOps.colorize(
        contrasted,
        black=(59, 27, 16),
        mid=(156, 81, 42),
        white=(247, 234, 208),
        midpoint=125
    )
    
    # Overlay fluorescent UV rim accents
    edges = gray.filter(ImageFilter.FIND_EDGES)
    enh_edges = ImageEnhance.Contrast(edges).enhance(1.5)
    uv_accent = ImageOps.colorize(
        enh_edges,
        black=(0, 0, 0),
        white=(218, 165, 32)
    )
    blended = Image.blend(colorized, uv_accent, 0.15)
    
    final = add_noise(blended, intensity=0.09)
    final = apply_vignette(final, strength=0.32)
    return final


FILTER_MAP = {
    "cyanotype_silver_plate": filter_cyanotype_silver_plate,
    "charcoal_lithograph": filter_charcoal_lithograph,
    "blueprint_halftone": filter_blueprint_halftone,
    "sepia_bioluminescent_amber": filter_sepia_bioluminescent_amber,
    "desert_ochre_uv": filter_desert_ochre_uv
}


def render_vector_callouts(image: Image.Image, callouts: List[Dict[str, Any]], profile_id: str = "book01") -> Image.Image:
    """
    Renders clean, high-resolution vector text callout labels, boxes, and pointer lines
    over maps and diagrams so text is completely crisp and readable without AI artifacts.
    """
    if not callouts:
        return image

    img_copy = image.copy().convert("RGBA")
    overlay = Image.new("RGBA", img_copy.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    w, h = img_copy.size
    
    # Palette per profile
    theme_colors = {
        "book01": {"bg": (27, 54, 93, 230), "border": (184, 134, 11, 255), "text": (255, 255, 255, 255)},
        "book02": {"bg": (30, 34, 41, 235), "border": (0, 168, 150, 255), "text": (255, 255, 255, 255)},
        "book03": {"bg": (15, 23, 42, 240), "border": (56, 189, 248, 255), "text": (224, 242, 254, 255)},
        "book04": {"bg": (44, 64, 46, 235), "border": (217, 119, 6, 255), "text": (255, 253, 245, 255)},
        "book05": {"bg": (90, 42, 24, 235), "border": (201, 138, 44, 255), "text": (250, 246, 238, 255)},
    }
    tc = theme_colors.get(profile_id, theme_colors["book01"])
    
    # Font sizing relative to image width
    font_size = max(14, int(w * 0.016))
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    for c in callouts:
        x_pct = float(c.get("x", 50))
        y_pct = float(c.get("y", 50))
        label = str(c.get("label", "")).strip().upper()
        c_type = c.get("type", "badge")
        if not label:
            continue
            
        px = int((x_pct / 100.0) * w)
        py = int((y_pct / 100.0) * h)
        
        # Calculate text bounding box
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        pad_x = 12
        pad_y = 6
        
        box_w = text_w + pad_x * 2
        box_h = text_h + pad_y * 2
        
        # Center box on (px, py)
        x0 = max(10, min(w - box_w - 10, px - box_w // 2))
        y0 = max(10, min(h - box_h - 10, py - box_h // 2))
        x1 = x0 + box_w
        y1 = y0 + box_h
        
        # Draw background and border
        if c_type == "box":
            draw.rectangle([x0, y0, x1, y1], fill=tc["bg"], outline=tc["border"], width=2)
            # Crosshair mark in corner
            draw.line([x0 - 4, y0, x0 + 4, y0], fill=tc["border"], width=1)
            draw.line([x0, y0 - 4, x0, y0 + 4], fill=tc["border"], width=1)
        elif c_type == "badge":
            draw.rounded_rectangle([x0, y0, x1, y1], radius=6, fill=tc["bg"], outline=tc["border"], width=2)
            # Dot anchor
            draw.circle((px, py + box_h // 2 + 10), radius=4, fill=tc["border"])
            draw.line([(px, py + box_h // 2), (px, py + box_h // 2 + 10)], fill=tc["border"], width=2)
        elif c_type.startswith("arrow"):
            draw.rounded_rectangle([x0, y0, x1, y1], radius=4, fill=tc["bg"], outline=tc["border"], width=2)
            # Pointer arrow
            target_y = y1 + 16 if "down" in c_type or "up" not in c_type else y0 - 16
            draw.line([(px, y1), (px, target_y)], fill=tc["border"], width=2)
            draw.polygon([(px - 4, target_y), (px + 4, target_y), (px, target_y + 6)], fill=tc["border"])
        else:
            draw.rectangle([x0, y0, x1, y1], fill=tc["bg"], outline=tc["border"], width=2)
            
        # Draw text inside box
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
    target_dpi: int = PRINT_DPI
) -> str:
    """
    Main processing entrypoint:
    1. Loads original image.
    2. Resizes / resamples for 300 DPI print placement.
    3. Applies Book Theme Profile Pillow filter.
    4. Renders sharp vector callouts over maps/diagrams.
    5. Saves with 300 DPI metadata.
    """
    img = Image.open(input_image_path).convert("RGB")
    
    # Resample to target print dimensions
    target_size = DIMENSIONS_300DPI.get(placement_type, (1600, 1050))
    img = ImageOps.fit(img, target_size, method=Image.Resampling.LANCZOS)
    
    # Apply filter preset
    filter_func = FILTER_MAP.get(filter_preset, filter_cyanotype_silver_plate)
    filtered = filter_func(img)
    
    # Render vector callouts
    if callouts:
        filtered = render_vector_callouts(filtered, callouts, profile_id)
        
    os.makedirs(os.path.dirname(output_image_path), exist_ok=True)
    filtered.save(output_image_path, "PNG", dpi=(target_dpi, target_dpi))
    return output_image_path


def generate_procedural_placeholder(
    output_path: str,
    title: str,
    prompt: str,
    placement_type: str,
    filter_preset: str,
    profile_id: str,
    callouts: List[Dict[str, Any]] = None
) -> str:
    """
    Generates an authentic procedural etching/engraving base plate when user has not yet uploaded
    custom art, ensuring the spread preview looks rich and production-ready immediately.
    """
    size = DIMENSIONS_300DPI.get(placement_type, (1600, 1050))
    w, h = size
    
    base = Image.new("RGB", (w, h), (245, 242, 235))
    draw = ImageDraw.Draw(base)
    
    # Architectural / technical framing lines
    margin = int(w * 0.05)
    draw.rectangle([margin, margin, w - margin, h - margin], outline=(40, 40, 40), width=3)
    draw.rectangle([margin + 12, margin + 12, w - margin - 12, h - margin - 12], outline=(90, 90, 90), width=1)
    
    # Shading / hatch lines to simulate an engraved plate
    hatch_spacing = 18
    for i in range(margin + 20, w - margin - 20, hatch_spacing):
        y_top = margin + 20
        y_bot = h - margin - 20
        # Curved wavy engraving lines
        curve_pts = []
        for y in range(y_top, y_bot, 20):
            x_offset = int(math.sin(y / 45.0 + i / 100.0) * 8)
            curve_pts.append((i + x_offset, y))
        if len(curve_pts) > 1:
            draw.line(curve_pts, fill=(180, 175, 165), width=1)
            
    # Technical geometry or focal emblem in center
    cx, cy = w // 2, h // 2
    r = min(w, h) // 4
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(50, 50, 50), width=3)
    draw.ellipse([cx - r + 15, cy - r + 15, cx + r - 15, cy + r - 15], outline=(100, 100, 100), width=1)
    
    # Radiating radial compass lines
    for angle in range(0, 360, 30):
        rad = math.radians(angle)
        x_outer = cx + int((r - 20) * math.cos(rad))
        y_outer = cy + int((r - 20) * math.sin(rad))
        x_inner = cx + int((r // 3) * math.cos(rad))
        y_inner = cy + int((r // 3) * math.sin(rad))
        draw.line([(x_inner, y_inner), (x_outer, y_outer)], fill=(60, 60, 60), width=2)
        
    draw.circle((cx, cy), radius=16, fill=(40, 40, 40))
    
    # Title plaque at bottom
    plaque_w = int(w * 0.7)
    plaque_h = int(h * 0.12)
    px0 = (w - plaque_w) // 2
    py0 = h - margin - plaque_h - 20
    draw.rectangle([px0, py0, px0 + plaque_w, py0 + plaque_h], fill=(255, 255, 255), outline=(30, 30, 30), width=2)
    
    # Draw title text
    try:
        font_large = ImageFont.truetype("arialbd.ttf", int(plaque_h * 0.35))
        font_small = ImageFont.truetype("arial.ttf", int(plaque_h * 0.22))
    except Exception:
        font_large = ImageFont.load_default()
        font_small = ImageFont.load_default()
        
    draw.text((px0 + 20, py0 + 12), title[:45].upper(), font=font_large, fill=(20, 20, 20))
    draw.text((px0 + 20, py0 + 16 + int(plaque_h * 0.4)), f"ARGON STUDIO SPECIFICATION // {placement_type.upper()}", font=font_small, fill=(90, 90, 90))
    
    # Apply theme filter
    filter_func = FILTER_MAP.get(filter_preset, filter_cyanotype_silver_plate)
    filtered = filter_func(base)
    
    # Render callouts if any
    if callouts:
        filtered = render_vector_callouts(filtered, callouts, profile_id)
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    filtered.save(output_path, "PNG", dpi=(PRINT_DPI, PRINT_DPI))
    return output_path
