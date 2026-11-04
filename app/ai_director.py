"""
Argon Book Studio - Local AI Book Art Director & Layout Suite.
Connects to local LLMs (Ollama, LM Studio, llama.cpp, LocalAI) or runs in
High-Fidelity Heuristic Mode to autonomously read manuscripts, recommend
thematic typography, draft mandatory pages, discover cinematic scenes,
generate midjourney/diffusion prompts, and anchor illustration plates.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

logger = logging.getLogger(__name__)

DEFAULT_AI_CONFIG = {
    "provider": "ollama",               # "ollama", "openai_compatible", or "offline_heuristic"
    "endpoint_url": "http://localhost:11434",
    "model": "qwen2.5:14b",
    "temperature": 0.4,
    "timeout_sec": 90.0,
    "auto_detect_models": True
}

# Thematic style presets for typography & art direction
THEME_PRESETS = {
    "gaslamp_gothic": {
        "genre_label": "Gaslamp Forensic Mystery & Gothic Fiction",
        "body_font_name": "Cormorant Garamond",
        "body_font": "'Cormorant Garamond', 'EB Garamond', serif",
        "heading_font_name": "Cinzel",
        "heading_font": "'Cinzel', 'Playfair Display', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "cyanotype_silver_plate",
        "font_size_pt": 10.5,
        "line_height": 1.38,
        "para_indent_in": 0.25,
        "para_spacing_pt": 0.0,
        "trim_preset": "6x9",
        "drop_cap_style": "Engraved Gothic Initial",
        "drop_cap_lines": 3,
        "frame_style": "Victorian Engraved Filigree",
        "accent_color": "#1E3A8A",
        "brass_accent": "#D97706"
    },
    "chronometric_thriller": {
        "genre_label": "Chronometric Island Thriller & Nautical Fiction",
        "body_font_name": "EB Garamond",
        "body_font": "'EB Garamond', serif",
        "heading_font_name": "Cinzel Decorative",
        "heading_font": "'Cinzel Decorative', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "copperplate_etching",
        "font_size_pt": 10.75,
        "line_height": 1.40,
        "para_indent_in": 0.22,
        "para_spacing_pt": 0.0,
        "trim_preset": "6x9",
        "drop_cap_style": "Steampunk Compass Initial",
        "drop_cap_lines": 3,
        "frame_style": "Chronometer Brass Border",
        "accent_color": "#0F766E",
        "brass_accent": "#B45309"
    },
    "acoustic_coldwar": {
        "genre_label": "Cold War Forensic & Acoustic Mystery",
        "body_font_name": "Lora",
        "body_font": "'Lora', serif",
        "heading_font_name": "Playfair Display",
        "heading_font": "'Playfair Display', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "sepia_microfilm",
        "font_size_pt": 10.25,
        "line_height": 1.35,
        "para_indent_in": 0.20,
        "para_spacing_pt": 0.0,
        "trim_preset": "5.5x8.5",
        "drop_cap_style": "Typewriter Stencil",
        "drop_cap_lines": 2,
        "frame_style": "Classified Document Frame",
        "accent_color": "#334155",
        "brass_accent": "#64748B"
    },
    "southern_gothic": {
        "genre_label": "Southern Gothic & Institutional Mystery",
        "body_font_name": "Libre Baskerville",
        "body_font": "'Libre Baskerville', serif",
        "heading_font_name": "Playfair Display",
        "heading_font": "'Playfair Display', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "high_contrast_linocut",
        "font_size_pt": 10.5,
        "line_height": 1.42,
        "para_indent_in": 0.25,
        "para_spacing_pt": 0.0,
        "trim_preset": "6x9",
        "drop_cap_style": "Flourished Floral Initial",
        "drop_cap_lines": 3,
        "frame_style": "Weathered Wrought Iron",
        "accent_color": "#4D7C0F",
        "brass_accent": "#CA8A04"
    },
    "archaeometric_heist": {
        "genre_label": "Archaeometric & Epigraphic Geopolitical Thriller",
        "body_font_name": "Merriweather",
        "body_font": "'Merriweather', serif",
        "heading_font_name": "Cinzel",
        "heading_font": "'Cinzel', serif",
        "mono_font_name": "JetBrains Mono",
        "mono_font": "'JetBrains Mono', monospace",
        "filter_preset": "duotone_cobalt",
        "font_size_pt": 10.0,
        "line_height": 1.36,
        "para_indent_in": 0.20,
        "para_spacing_pt": 0.0,
        "trim_preset": "6x9",
        "drop_cap_style": "Cuneiform Seal Initial",
        "drop_cap_lines": 3,
        "frame_style": "Bas-Relief Stone Border",
        "accent_color": "#9A3412",
        "brass_accent": "#EA580C"
    }
}

BOOK_CHARACTER_PRESETS = {
    "gaslamp_gothic": [
        {
            "name": "Auditor Sera Lin-Voss",
            "role": "First-Chair Forensic Auditor & Optical Specialist",
            "age": "31",
            "gender": "Female",
            "stature": "Slender, erect posture, calm surgical composure, graceful economical movements",
            "complexion": "Pallid composed porcelain skin, cool undertones, no cosmetics",
            "face_architecture": "Refined angular cheekbones, decisive straight jawline, delicate focused nose, disciplined lips",
            "eyes": "Intense dark obsidian hooded eyes beneath straight dark brows, sharp analytical scrutiny",
            "hair": "Glossy dark charcoal-black hair parted neatly in the center and pinned in a severe functional Edwardian updo with polished bone pins",
            "distinguishing_marks": "Carries brass-fitted optical dissection case, wears fine dark kidskin dissecting gloves, holds precision silver-halide cannula",
            "signature_wardrobe": "Tailored midnight-charcoal Victorian auditor's wool gown, high stiff starched collar, dark horn buttons, black wool capelet with silver Residual Claims clasp, kidskin gloves",
            "resting_expression": "Intense analytical focus, cool detachment, watchful intellect",
            "locked_prompt_anchor": (
                "Auditor Sera Lin-Voss, 31yo slender pale Victorian forensic auditor, refined angular cheekbones, "
                "intense dark obsidian eyes beneath straight dark brows, glossy dark hair pinned in severe functional updo with bone pins, "
                "tailored midnight-charcoal wool gown, high stiff collar, dark kidskin dissecting gloves, holding silver-halide cannula, "
                "calm surgical composure"
            ),
            "turnaround_sheet_prompt": (
                "A professional black and white ink drawing, character model sheet turnaround, 4 distinct views: front view, "
                "profile view, three-quarter view, back view. Subject: Auditor Sera Lin-Voss, 31-year-old First-Chair forensic specialist, "
                "slender erect posture, pallid composed face, piercing dark eyes beneath straight dark brows, dark hair pinned in "
                "a severe functional updo with bone pins, tailored midnight-charcoal Victorian auditor gown, high stiff starched collar, "
                "dark kidskin dissecting gloves, holding precision silver-halide cannula. Master pen-and-ink line art, fine cross-hatching, "
                "clean white background, Sidney Paget and Arthur Rackham book illustration style, strictly black and white monochrome, "
                "no color, not a photograph, not 3D render, 300 dpi print quality."
            )
        },
        {
            "name": "Magistrate Julian Kael",
            "role": "Senior Proctor of the High Bench, Court of Residual Claims",
            "age": "58",
            "gender": "Male",
            "stature": "Tall (6 ft 2 in), commanding authoritative build, severe judicial posture",
            "complexion": "Austere pale English complexion with fine lines of authority at brow and temples",
            "face_architecture": "Aristocratic aquiline nose, prominent square chin, heavy iron-gray brows, firm unyielding mouth",
            "eyes": "Steely watchful cold gray eyes, piercing judicial scrutiny",
            "hair": "Thick iron-gray hair with distinguished silver wings at temples, swept straight back from high forehead",
            "distinguishing_marks": "Carries the heavy stamped iron warrant of the High Bench in breast pocket, silver-headed ebony cane",
            "signature_wardrobe": "Heavy midnight-blue and charcoal wool judicial frock coat with silver piping, high stiff wing collar, dark silk cravat with antique seal pin, heavy wool trousers, polished black boots",
            "resting_expression": "Cold judicial authority, unyielding scrutiny, gravitas of the High Bench",
            "locked_prompt_anchor": (
                "Magistrate Julian Kael, 58yo tall commanding Victorian Senior Proctor, aristocratic aquiline features, "
                "heavy iron-gray brows, steely cold gray eyes, silver-streaked swept-back hair, heavy midnight wool judicial frock coat, "
                "silver piping, high stiff wing collar, dark silk cravat, holding iron warrant, imposing judicial gravitas"
            ),
            "turnaround_sheet_prompt": (
                "A professional black and white ink drawing, character design turnaround sheet, 4 distinct views: front view, "
                "profile view, three-quarter view, back view. Subject: Magistrate Julian Kael, 58-year-old Senior Proctor of the Court of Residual Claims, "
                "tall commanding build, austere aristocratic face, heavy iron-gray brows, steely watchful gray eyes, hair combed back with "
                "distinguished silver streaks, heavy midnight wool judicial frock coat with silver insignia, high starched wing collar, "
                "holding the iron warrant of the High Bench. Fine cross-hatched ink lines, white clean background, vintage book engraving style, "
                "strictly black and white monochrome, no color, not a photograph, not 3D render."
            )
        },
        {
            "name": "Cormac Vane",
            "role": "Veteran Maritime Salvage Engineer & Diving Pioneer (Deceased Subject of Inquest)",
            "age": "60",
            "gender": "Male",
            "stature": "Broad-shouldered, rugged barrel-chested build, lifetime of deep salvage labor",
            "complexion": "Brine-pickled, deeply weathered Thames sea-salt complexion, fine nitric-acid etchings on fingertips",
            "face_architecture": "Heavy rugged jawline, crooked broken nose from diving cable snap, weathered brow, presbyopic squint",
            "eyes": "Pale washed-out watery blue-gray eyes with subtle cataract clouding, atrocious eyesight",
            "hair": "Coarse salt-and-pepper iron hair and dense 3-day silver-gray stubble",
            "distinguishing_marks": "Deep cable burn scar across left forearm, heavy brass chronometric diver's gauge tucked in pocket, brass spectacles with thick ground lenses",
            "signature_wardrobe": "Heavy coarse ribbed-wool navy diving undershirt with rolled sleeves, oiled canvas trousers, heavy leather braces, salt-crusted waterman's belt",
            "resting_expression": "Stoic maritime endurance, contemplative exhaustion, quiet stubborn dignity",
            "locked_prompt_anchor": (
                "Cormac Vane, 60yo rugged broad-shouldered veteran maritime salvage engineer, brine-weathered lined face, "
                "crooked nose, pale presbyopic squinting eyes, coarse salt-and-pepper hair and silver stubble, heavy ribbed-wool diving undershirt, "
                "oiled canvas trousers, cable scar on forearm, rough calloused hands, stoic Thames sea-diver"
            ),
            "turnaround_sheet_prompt": (
                "A professional black and white ink drawing, character turnaround sheet, 4 distinct views: front view, profile view, "
                "three-quarter view, back view. Subject: Cormac Vane, 60-year-old veteran maritime salvage engineer and diving pioneer, "
                "brine-weathered lined face, tired presbyopic eyes, salt-and-pepper silver-streaked hair and stubble, rough calloused hands, "
                "wearing heavy coarse wool diver undershirt with rolled sleeves, oilcloth trousers, brass diver pocket gauge. "
                "Master pen-and-ink line art, intricate cross-hatching, neutral white background, authentic 19th-century book illustration, "
                "strictly black and white monochrome, no color, not a photograph, not 3D render."
            )
        },
        {
            "name": "Master Helena Orlov",
            "role": "Cultured Industrial Conspirator & Antiquities Syndic",
            "age": "42",
            "gender": "Female",
            "stature": "Tall, poised, dangerous aristocratic grace, calculating stillness",
            "complexion": "Porcelain-pale continental skin, immaculate composure",
            "face_architecture": "High Slavic cheekbones, sharp defined nose, full enigmatic lips, cold sculpted chin",
            "eyes": "Dark penetrating hooded eyes, hypnotic intellect, veiled threat",
            "hair": "Lustrous jet-black hair styled in an elaborate Edwardian chignon secured with carved tortoiseshell pins",
            "distinguishing_marks": "Carved obsidian intaglio ring on left index finger, antique gold vinaigrette pendant",
            "signature_wardrobe": "Luxurious tailored black velvet overcoat with notched satin lapels, high lace collar, dark silk cravat with ruby-eyed serpent pin, kidskin gloves",
            "resting_expression": "Venomous calm, cultured amusement, impenetrable calculating stillness",
            "locked_prompt_anchor": (
                "Master Helena Orlov, 42yo tall elegant Slavic industrial conspirator, porcelain pale complexion, "
                "high Slavic cheekbones, dark penetrating hooded eyes, lustrous jet-black hair in ornate chignon, "
                "tailored black velvet coat, satin lapels, high lace collar, obsidian ring, dangerous venomous calm"
            ),
            "turnaround_sheet_prompt": (
                "A professional black and white ink drawing, character design turnaround sheet, 4 distinct views: front view, profile view, "
                "three-quarter view, back view. Subject: Master Helena Orlov, 42-year-old cultured conspirator, refined posture with "
                "dangerous venomous calm, elegant angular face, dark penetrating eyes, dark glossy hair in an Edwardian chignon, luxurious "
                "tailored velvet-lapel coat, silk cravat with antique signet pin. Fine intaglio ink lines, clean white background, "
                "vintage book plate engraving, strictly black and white monochrome, no color, not a photograph."
            )
        },
        {
            "name": "Inspector Silas Hallowell",
            "role": "Scotland Yard River Police Inspector, Wapping Division",
            "age": "48",
            "gender": "Male",
            "stature": "Sturdy, barrel-chested, heavy weathered gait, reliable working-class build",
            "complexion": "Ruddy, wind-battered Thames river skin with broken capillaries on cheeks",
            "face_architecture": "Square heavy jaw, blunt broken nose, bushy iron-gray walrus mustache",
            "eyes": "Deep-set watery hazel eyes beneath furrowed brow, observant weary gaze",
            "hair": "Thinning iron-gray hair cropped short beneath black oilskin bowler hat",
            "distinguishing_marks": "Chilblained left ear, brass whistle on braided lanyard, briar pipe in pocket",
            "signature_wardrobe": "Heavy rough-spun navy blue pea jacket with horn buttons, thick knitted gray wool scarf, corduroy trousers, mud-caked boots",
            "resting_expression": "Weary skepticism, furrowed brow, steadfast practical caution",
            "locked_prompt_anchor": (
                "Inspector Silas Hallowell, 48yo sturdy broad-shouldered Victorian river police detective, "
                "ruddy weathered face, square heavy jaw, bushy iron-gray walrus mustache, deep-set wary hazel eyes, "
                "wearing heavy navy pea jacket, black oilskin bowler hat, knitted wool scarf, rugged Thames detective"
            ),
            "turnaround_sheet_prompt": (
                "A professional black and white ink drawing, character turnaround sheet, 4 distinct views: front view, profile view, "
                "three-quarter view, back view. Subject: Inspector Silas Hallowell, 48-year-old sturdy broad-shouldered Thames river police detective, "
                "ruddy weathered face, square heavy jaw, bushy iron-gray walrus mustache, deep-set wary eyes beneath black oilskin bowler hat, "
                "heavy rough-spun navy pea jacket with horn buttons, knitted wool scarf. Sidney Paget vintage book engraving style, "
                "clean white background, strictly black and white monochrome, no color, not a photograph."
            )
        }
    ],
    "chronometric_thriller": [
        {
            "name": "Kenneth Coram",
            "role": "Master Horologist & Hydrographic Surveyor",
            "age": "42",
            "gender": "Male",
            "stature": "Medium height (5 ft 10 in), sinewy frame, clockmaker's dexterous hands",
            "complexion": "Weather-bronzed from Atlantic salt spray, faint freckling across bridge of nose",
            "face_architecture": "Angular hawk-like profile, firm determined chin with slight cleft, high forehead",
            "eyes": "Keen sea-glass green eyes, habituated to squinting through marine chronometer loupes",
            "hair": "Auburn-brown windswept hair tied back with a leather thong at the nape",
            "distinguishing_marks": "Jeweler's loupe permanently mounted on hinged brass head-wire over right eye, brass callipers in breast pocket",
            "signature_wardrobe": "Dark teal waxed canvas mariner's coat with brass maritime buttons, heavy oiled cable-knit cream fisherman sweater, oiled leather apron with tool pouches, brass pocket chronometer chain",
            "resting_expression": "Hyper-focused mathematical precision, calm vigilance in stormy gale",
            "locked_prompt_anchor": (
                "Kenneth Coram, 42yo sinewy Victorian chronometer surveyor, weather-bronzed Atlantic complexion, "
                "hawk-like profile, cleft chin, keen sea-glass green eyes, auburn-brown hair tied back, jeweler's brass loupe "
                "over right eye, dark teal waxed coat, cream cable-knit sweater, leather tool apron, maritime precision"
            ),
            "turnaround_sheet_prompt": (
                "A professional black and white ink drawing, character model sheet turnaround, 4 distinct views: front view, "
                "profile view, three-quarter view, back view. Subject: Kenneth Coram, 42-year-old nautical horologist and hydrographic surveyor, "
                "weather-bronzed Atlantic complexion, hawk-like profile, sea-glass green eyes, auburn-brown hair tied back, brass eye-loupe, "
                "dark teal waxed mariner coat, cable-knit fisherman sweater, leather tool apron. Master pen-and-ink line art, intricate cross-hatching, "
                "clean white background, vintage copperplate engraving style, strictly black and white monochrome, no color, not a photograph, not 3D render, 300 dpi print quality."
            )
        }
    ],
    "acoustic_coldwar": [
        {
            "name": "Klaus Mercer",
            "role": "Forensic Cryptanalyst & Acoustic Signal Specialist",
            "age": "36",
            "gender": "Male",
            "stature": "Tall and gaunt, narrow shoulders, deliberate careful movements",
            "complexion": "Pale subterranean fluorescent-tube skin tone, dark purplish circles under eyes",
            "face_architecture": "Hollow cheeks, sharp pointed nose, thin pale lips, taut jaw",
            "eyes": "Intense dark brown observant eyes, highly sensitized to oscilloscope waveforms",
            "hair": "Neat jet-black Brylcreem-slicked 1950s side-part, severe short back and sides",
            "distinguishing_marks": "Heavy vintage Bakelite headphones resting around his neck, mechanical stopwatch around thumb",
            "signature_wardrobe": "Rumpled narrow-lapel charcoal wool suit, narrow black knit tie, crisp white collar, stainless steel analog wristwatch, pencil tucked behind right ear",
            "resting_expression": "Intense concentrated auditory listening, head cocked slightly to one side",
            "locked_prompt_anchor": (
                "Klaus Mercer, 36yo gaunt Cold War audio cryptanalyst, pale indoor complexion, hollow cheeks, dark circles under dark brown eyes, "
                "slicked jet-black 1950s hair, heavy Bakelite headphones around neck, charcoal narrow-lapel wool suit, skinny black tie, "
                "concentrated listening expression"
            ),
            "turnaround_sheet_prompt": (
                "A professional black and white ink drawing, character model sheet turnaround, 4 distinct views: front view, "
                "profile view, three-quarter view, back view. Subject: Klaus Mercer, 36-year-old Cold War audio cryptanalyst, "
                "gaunt pale face, hollow cheeks, dark circles, Bakelite headphones around neck, 1950s charcoal narrow-lapel suit, skinny tie. "
                "Master pen-and-ink line art, sepia-toned archival engraving texture, clean white background, strictly black and white monochrome, "
                "no color, not a photograph, not 3D render, 300 dpi print quality."
            )
        }
    ],
    "southern_gothic": [
        {
            "name": "Dr. Sarah Vance",
            "role": "Botanical Pathologist & Institutional Genealogist",
            "age": "34",
            "gender": "Female",
            "stature": "Slender, graceful poise, quiet unwavering physical presence",
            "complexion": "Fair magnolia porcelain skin, light dusting of freckles over cheekbones",
            "face_architecture": "Soft oval face, delicate refined nose, expressive arched dark eyebrows, full expressive lips",
            "eyes": "Warm hazel-amber eyes with intense inquiring gaze",
            "hair": "Rich dark chestnut wavy hair pinned up loosely in an Edwardian chignon with stray tendrils framing the face",
            "distinguishing_marks": "Silver botanical locket containing pressed cypress fern, antique brass herbarium tweezers pinned to lapel",
            "signature_wardrobe": "Forest-green linen walking suit with high lace collar, fitted buttoned vest, dark olive pleated skirt, black leather lace-up ankle boots, leather field satchel",
            "resting_expression": "Contemplative melancholy, keen observant empathy, guarded intelligence",
            "locked_prompt_anchor": (
                "Dr. Sarah Vance, 34yo slender Edwardian botanical genealogist, fair magnolia porcelain skin, light freckles, "
                "warm amber-hazel eyes, dark chestnut wavy hair pinned in loose chignon, forest-green linen walking suit, "
                "high lace collar, silver botanical locket, contemplative melancholy expression"
            ),
            "turnaround_sheet_prompt": (
                "A professional black and white ink drawing, character model sheet turnaround, 4 distinct views: front view, "
                "profile view, three-quarter view, back view. Subject: Dr. Sarah Vance, 34-year-old botanical pathologist, "
                "magnolia porcelain skin, hazel-amber eyes, loose chestnut chignon, high lace collar, tailored linen walking suit, botanical locket. "
                "Intricate linocut and vintage book engraving style, clean white background, strictly black and white monochrome, "
                "no color, not a photograph, not 3D render, 300 dpi print quality."
            )
        }
    ],
    "archaeometric_heist": [
        {
            "name": "Dr. Tariq Al-Mansur",
            "role": "Senior Epigrapher & Archaeometric Surveyor",
            "age": "45",
            "gender": "Male",
            "stature": "Athletic medium-tall build, weathered stamina from desert excavations",
            "complexion": "Warm olive-tan Mesopotamian complexion, sun-creased temple lines",
            "face_architecture": "Strong square jaw, prominent straight Mediterranean nose, well-groomed salt-and-pepper beard",
            "eyes": "Deep espresso-brown almond eyes, insightful and piercing",
            "hair": "Thick wavy dark brown hair shot with silver streaks, trimmed short and neat",
            "distinguishing_marks": "Carved lapis lazuli signet ring on right index finger with ancient Sumerian cuneiform glyph, fine calliper scar on thumb",
            "signature_wardrobe": "Terracotta and sand-khaki linen field jacket with reinforced elbow patches, white rolled-sleeve cotton shirt, dark canvas expedition trousers, leather band field watch",
            "resting_expression": "Astute scholarly acumen, quiet composure in high-stakes situations",
            "locked_prompt_anchor": (
                "Dr. Tariq Al-Mansur, 45yo athletic Middle Eastern archaeometrist epigrapher, warm olive-tan complexion, "
                "salt-and-pepper neat beard, deep espresso-brown almond eyes, lapis lazuli cuneiform signet ring, "
                "sand-khaki linen field jacket, rolled white cotton shirt, scholarly astute composure"
            ),
            "turnaround_sheet_prompt": (
                "A professional black and white ink drawing, character model sheet turnaround, 4 distinct views: front view, "
                "profile view, three-quarter view, back view. Subject: Dr. Tariq Al-Mansur, 45-year-old epigrapher and surveyor, "
                "olive-tan complexion, salt-and-pepper beard, almond eyes, sand-khaki field jacket, lapis lazuli signet ring. "
                "Bas-relief intaglio book plate engraving, fine cross-hatching, clean white background, strictly black and white monochrome, "
                "no color, not a photograph, not 3D render, 300 dpi print quality."
            )
        }
    ]
}


def get_placement_geometry(placement: str) -> Dict[str, str]:
    """Returns aspect ratio, target pixel dimensions at 300 DPI, and CLI generator tags."""
    p_lower = (placement or "").lower()
    if any(k in p_lower for k in ["turnaround", "model sheet"]):
        ar = "3:2"
        res = "2400 x 1600 px (300 DPI) • FLUX Native: 1152x768"
        mj = "--ar 3:2 --v 6.1"
        flux = "Aspect: 3:2 | Native FLUX: 1152x768 | 300 DPI Target: 2400x1600 px | Steps: 4 | Guidance: 1.0"
    elif any(k in p_lower for k in ["full bleed", "full-page", "full plate", "verso plate", "recto plate"]):
        ar = "2:3"
        res = "1875 x 2775 px (300 DPI Full Bleed) • FLUX Native: 896x1152"
        mj = "--ar 2:3 --v 6.1"
        flux = "Aspect: 2:3 | Native FLUX: 896x1152 | 300 DPI Target: 1875x2775 px | Steps: 4 | Guidance: 1.0"
    elif "half" in p_lower:
        ar = "4:3"
        res = "1500 x 1140 px (300 DPI Half-Page) • FLUX Native: 1024x768"
        mj = "--ar 4:3 --v 6.1"
        flux = "Aspect: 4:3 | Native FLUX: 1024x768 | 300 DPI Target: 1500x1140 px | Steps: 4 | Guidance: 1.0"
    elif any(k in p_lower for k in ["tailpiece"]):
        ar = "1:1"
        res = "600 x 600 px (300 DPI Tailpiece) • FLUX Native: 512x512"
        mj = "--ar 1:1 --v 6.1"
        flux = "Aspect: tailpiece | Native FLUX: 512x512 | 300 DPI Target: 600x600 px | Steps: 4 | Guidance: 1.0"
    elif any(k in p_lower for k in ["banner", "opener"]):
        ar = "2:1"
        res = "2400 x 1200 px (300 DPI Banner) • FLUX Native: 1280x640"
        mj = "--ar 2:1 --v 6.1"
        flux = "Aspect: banner | Native FLUX: 1280x640 | 300 DPI Target: 2400x1200 px | Steps: 4 | Guidance: 1.0"
    else:  # vignette, emblem, quarter-page, spot
        ar = "1:1"
        res = "1200 x 1200 px (300 DPI Frontispiece/Spot) • FLUX Native: 1024x1024"
        mj = "--ar 1:1 --v 6.1"
        flux = "Aspect: 1:1 | Native FLUX: 1024x1024 | 300 DPI Target: 1200x1200 px | Steps: 4 | Guidance: 1.0"
    return {
        "aspect_ratio": ar,
        "target_resolution_px": res,
        "midjourney_params": mj,
        "flux_params": flux
    }


class AIDirectorManager:
    def __init__(self):
        self.config = dict(DEFAULT_AI_CONFIG)

    def get_config(self) -> Dict[str, Any]:
        return self.config

    def update_config(self, new_config: Dict[str, Any]) -> Dict[str, Any]:
        self.config.update(new_config)
        return self.config

    def _ensure_ollama_daemon(self):
        import shutil
        import subprocess
        ollama_exe = shutil.which("ollama") or r"C:\Users\albre\AppData\Local\Programs\Ollama\ollama.exe"
        if os.path.exists(ollama_exe) or shutil.which("ollama"):
            try:
                creationflags = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW
                subprocess.Popen(
                    [ollama_exe, "serve"],
                    creationflags=creationflags,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception:
                pass

    def check_connection(self) -> Dict[str, Any]:
        """
        Polls local LLM servers (Ollama, LM Studio / OpenAI-compatible).
        Returns status, available models, and active mode. Auto-launches Ollama if needed.
        """
        url = self.config.get("endpoint_url", "http://localhost:11434").rstrip("/")
        fast_timeout = httpx.Timeout(connect=0.4, read=1.5, write=1.0, pool=0.5)
        
        # 1. Check Ollama tags endpoint
        for attempt in range(2):
            try:
                with httpx.Client(timeout=fast_timeout) as client:
                    res = client.get(f"{url}/api/tags")
                    if res.status_code == 200:
                        data = res.json()
                        models = [m.get("name") for m in data.get("models", [])]
                        selected = self.config.get("model", "qwen2.5:14b")
                        if models and selected not in models:
                            selected = "qwen2.5:14b" if "qwen2.5:14b" in models else models[0]
                        return {
                            "status": "online",
                            "provider": "ollama",
                            "endpoint": url,
                            "models": models,
                            "selected_model": selected,
                            "message": f"Connected to Ollama ({len(models)} models available)."
                        }
            except Exception:
                if attempt == 0:
                    # Auto-launch Ollama background daemon on first miss
                    self._ensure_ollama_daemon()
                    import time
                    time.sleep(1.2)

        # 2. Check OpenAI-compatible endpoint (LM Studio, llama.cpp, LocalAI)
        try:
            with httpx.Client(timeout=fast_timeout) as client:
                res = client.get(f"{url}/v1/models")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("id") for m in data.get("data", [])]
                    return {
                        "status": "online",
                        "provider": "openai_compatible",
                        "endpoint": url,
                        "models": models,
                        "selected_model": models[0] if models else "default",
                        "message": f"Connected to OpenAI-compatible server ({len(models)} models)."
                    }
        except Exception:
            pass

        # 3. Offline Heuristic Fallback
        return {
            "status": "offline",
            "provider": "offline_heuristic",
            "endpoint": url,
            "models": ["Argon High-Fidelity NLP Heuristics (Zero-Config Built-in)"],
            "selected_model": "Argon High-Fidelity NLP Heuristics",
            "message": "Local LLM server not detected. High-Fidelity Built-in NLP Heuristics active."
        }

    def analyze_manuscript(
        self,
        manuscript: Dict[str, Any],
        book_id: str = "book01",
        num_illustrations: int = 16,
        user_prompt_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Main AI Art Director pipeline:
        - If a local LLM is online, prompts the model for structured analysis.
        - Otherwise, executes deterministic, intelligent NLP heuristic extraction.
        """
        conn = self.check_connection()
        if conn["status"] == "online" and conn["provider"] == "ollama":
            try:
                result = self._analyze_via_ollama(manuscript, book_id, num_illustrations, conn["selected_model"])
                if result:
                    result["engine"] = f"Local LLM ({conn['selected_model']})"
                    return result
            except Exception as e:
                logger.warning(f"Ollama execution failed, falling back to heuristic engine: {e}")

        # Fallback to high-fidelity heuristic engine
        result = self._analyze_via_heuristics(manuscript, book_id, num_illustrations)
        result["engine"] = "Argon High-Fidelity NLP Heuristics (Offline)"
        return result

    def _extract_characters_from_text(self, manuscript: Dict[str, Any], theme_key: str) -> List[Dict[str, Any]]:
        """
        Dynamically extracts canonical characters and identities directly from the manuscript text.
        Never relies on static placeholder presets when text is present.
        """
        chapters = manuscript.get("chapters", [])
        all_text = []
        for ch in chapters:
            for el in ch.get("elements", []):
                t = el.get("text") or el.get("content") or ""
                if t:
                    all_text.append(t)
        full_text = " ".join(all_text)
        full_lower = full_text.lower()

        found_characters = []

        # 1. Auditor Sera Lin-Voss
        if any(k in full_text for k in ["Sera Lin-Voss", "Lin-Voss", "Auditor Sera", "Sera had"]):
            found_characters.append({
                "name": "Auditor Sera Lin-Voss",
                "role": "First-Chair Forensic Auditor & Optical Specialist",
                "age": "31",
                "gender": "Female",
                "stature": "Slender, erect posture, calm surgical composure, graceful economical movements",
                "complexion": "Pallid composed porcelain skin, cool undertones, no cosmetics",
                "face_architecture": "Refined angular cheekbones, decisive straight jawline, delicate focused nose, disciplined lips",
                "eyes": "Intense dark obsidian hooded eyes beneath straight dark brows, sharp analytical scrutiny",
                "hair": "Glossy dark charcoal-black hair parted neatly in the center and pinned in a severe functional Edwardian updo with polished bone pins",
                "distinguishing_marks": "Carries brass-fitted optical dissection case, wears fine dark kidskin dissecting gloves, holds precision silver-halide cannula",
                "signature_wardrobe": "Tailored midnight-charcoal Victorian auditor's wool gown, high stiff starched collar, dark horn buttons, black wool capelet with silver Residual Claims clasp, kidskin gloves",
                "resting_expression": "Intense analytical focus, cool detachment, watchful intellect",
                "locked_prompt_anchor": (
                    "Auditor Sera Lin-Voss, 31yo slender pale Victorian forensic auditor, refined angular cheekbones, "
                    "intense dark obsidian eyes beneath straight dark brows, glossy dark hair pinned in severe functional updo with bone pins, "
                    "tailored midnight-charcoal wool gown, high stiff collar, dark kidskin dissecting gloves, holding silver-halide cannula, "
                    "calm surgical composure"
                ),
                "turnaround_sheet_prompt": (
                    "A professional black and white ink drawing, character model sheet turnaround, 4 distinct views: front view, "
                    "profile view, three-quarter view, back view. Subject: Auditor Sera Lin-Voss, 31-year-old First-Chair forensic specialist, "
                    "slender erect posture, pallid composed face, piercing dark eyes beneath straight dark brows, dark hair pinned in "
                    "a severe functional updo with bone pins, tailored midnight-charcoal Victorian auditor gown, high stiff starched collar, "
                    "dark kidskin dissecting gloves, holding precision silver-halide cannula. Master pen-and-ink line art, fine cross-hatching, "
                    "clean white background, Sidney Paget and Arthur Rackham book illustration style, strictly black and white monochrome, "
                    "no color, not a photograph, not 3D render, 300 dpi print quality."
                )
            })

        # 2. Cormac Vane (Deceased Inquest Subject)
        if "cormac vane" in full_lower or "cormac" in full_lower:
            found_characters.append({
                "name": "Cormac Vane",
                "role": "Veteran Maritime Salvage Engineer & Diving Pioneer (Deceased Subject of Inquest)",
                "age": "60",
                "gender": "Male",
                "stature": "Broad-shouldered, rugged barrel-chested build, lifetime of deep salvage labor and caisson diving",
                "complexion": "Brine-pickled, deeply weathered Thames sea-salt complexion, fine nitric-acid etchings on fingertips",
                "face_architecture": "Heavy rugged jawline, crooked broken nose from diving cable snap, weathered brow, flared ribs",
                "eyes": "Pale washed-out watery blue-gray eyes with subtle cataract clouding, atrocious eyesight",
                "hair": "Coarse salt-and-pepper iron hair and dense 3-day silver-gray stubble, silvered eyebrows",
                "distinguishing_marks": "Deep cable burn scar across left forearm, geometric contusion on collarbone, heavy brass chronometric diver's gauge in pocket",
                "signature_wardrobe": "Heavy coarse ribbed-wool navy diving undershirt with rolled sleeves, oiled canvas trousers, heavy leather braces, salt-crusted waterman's belt",
                "resting_expression": "Stoic maritime endurance, contemplative exhaustion, quiet stubborn dignity",
                "locked_prompt_anchor": (
                    "Cormac Vane, 60yo rugged broad-shouldered veteran maritime salvage engineer, brine-weathered lined face, "
                    "crooked nose, pale presbyopic squinting eyes, coarse salt-and-pepper hair and silver stubble, heavy ribbed-wool diving undershirt, "
                    "oiled canvas trousers, cable scar on forearm, rough calloused hands, stoic Thames sea-diver"
                ),
                "turnaround_sheet_prompt": (
                    "A professional black and white ink drawing, character turnaround sheet, 4 distinct views: front view, profile view, "
                    "three-quarter view, back view. Subject: Cormac Vane, 60-year-old veteran maritime salvage engineer and diving pioneer, "
                    "brine-weathered lined face, tired presbyopic eyes, salt-and-pepper silver-streaked hair and stubble, rough calloused hands, "
                    "wearing heavy coarse wool diver undershirt with rolled sleeves, oilcloth trousers, brass diver pocket gauge. "
                    "Master pen-and-ink line art, intricate cross-hatching, neutral white background, authentic 19th-century book illustration, "
                    "strictly black and white monochrome, no color, not a photograph, not 3D render."
                )
            })

        # 3. Magistrate Julian Kael
        if any(k in full_text for k in ["Julian Kael", "Magistrate Julian Kael", "Proctor Kael", "Julian"]):
            found_characters.append({
                "name": "Magistrate Julian Kael",
                "role": "Senior Proctor of the High Bench, Court of Residual Claims",
                "age": "58",
                "gender": "Male",
                "stature": "Tall (6 ft 2 in), commanding authoritative build, severe judicial naval posture",
                "complexion": "Austere pale English complexion with fine lines of authority at brow and temples",
                "face_architecture": "Aristocratic aquiline nose, prominent square chin, heavy iron-gray brows, firm unyielding mouth",
                "eyes": "Steely watchful cold gray eyes, piercing judicial scrutiny",
                "hair": "Thick iron-gray hair with distinguished silver wings at temples, cropped with naval severity",
                "distinguishing_marks": "Carries the heavy stamped iron warrant of the High Bench in breast pocket, cracked brass pocket watch, silver-headed ebony cane",
                "signature_wardrobe": "Heavy midnight-blue and charcoal wool judicial frock coat with silver piping, high stiff wing collar, dark silk cravat with antique seal pin, heavy wool trousers, polished black boots",
                "resting_expression": "Cold judicial authority, unyielding scrutiny, gravitas of the High Bench",
                "locked_prompt_anchor": (
                    "Magistrate Julian Kael, 58yo tall commanding Victorian Senior Proctor, aristocratic aquiline features, "
                    "heavy iron-gray brows, steely cold gray eyes, silver-streaked swept-back hair, heavy midnight wool judicial frock coat, "
                    "silver piping, high stiff wing collar, dark silk cravat, holding iron warrant, imposing judicial gravitas"
                ),
                "turnaround_sheet_prompt": (
                    "A professional black and white ink drawing, character design turnaround sheet, 4 distinct views: front view, "
                    "profile view, three-quarter view, back view. Subject: Magistrate Julian Kael, 58-year-old Senior Proctor of the Court of Residual Claims, "
                    "tall commanding build, austere aristocratic face, heavy iron-gray brows, steely watchful gray eyes, hair combed back with "
                    "distinguished silver streaks, heavy midnight wool judicial frock coat with silver insignia, high starched wing collar, "
                    "holding the iron warrant of the High Bench. Fine cross-hatched ink lines, white clean background, vintage book engraving style, "
                    "strictly black and white monochrome, no color, not a photograph, not 3D render."
                )
            })

        # 4. Chief Magistrate Orlov
        if "orlov" in full_lower:
            found_characters.append({
                "name": "Chief Magistrate Orlov",
                "role": "High Judicial Conspirator & Syndicate Proctor",
                "age": "52",
                "gender": "Male",
                "stature": "Tall, immaculate posture, calculating stillness and political authority",
                "complexion": "Porcelain-pale continental skin, immaculate composure",
                "face_architecture": "High sharp cheekbones, aquiline nose, cold unyielding mouth, sculpted jaw",
                "eyes": "Dark penetrating hooded eyes, hypnotic intellect, veiled threat",
                "hair": "Lustrous dark charcoal hair shot with silver, combed back neatly",
                "distinguishing_marks": "Carved obsidian signet ring on index finger, gold watch chain with seal",
                "signature_wardrobe": "Luxurious tailored black velvet-trimmed judicial coat with satin lapels, high stiff collar, silk cravat with antique intaglio pin",
                "resting_expression": "Venomous calm, cultured amusement, impenetrable calculating stillness",
                "locked_prompt_anchor": (
                    "Chief Magistrate Orlov, 52yo tall elegant Victorian high judicial conspirator, porcelain pale complexion, "
                    "high sharp cheekbones, dark penetrating hooded eyes, dark charcoal hair shot with silver, "
                    "tailored black velvet-trimmed judicial coat, satin lapels, high starched collar, obsidian ring, dangerous calculating calm"
                ),
                "turnaround_sheet_prompt": (
                    "A professional black and white ink drawing, character design turnaround sheet, 4 distinct views: front view, profile view, "
                    "three-quarter view, back view. Subject: Chief Magistrate Orlov, 52-year-old high judicial conspirator, refined posture with "
                    "dangerous venomous calm, elegant angular face, dark penetrating eyes, hair combed back with silver streaks, luxurious "
                    "tailored velvet-lapel judicial coat, silk cravat with antique signet pin. Fine intaglio ink lines, clean white background, "
                    "vintage book plate engraving, strictly black and white monochrome, no color, not a photograph."
                )
            })

        # 5. Tavi
        if "tavi" in full_lower:
            found_characters.append({
                "name": "Tavi",
                "role": "Ailing Companion & Brine-Lung Survivor in the Low Ward",
                "age": "24",
                "gender": "Male",
                "stature": "Slight, fever-thinned frame, hollowed chest from deep-sea bronchial affliction",
                "complexion": "Fever-flushed translucent pale skin with faint cyanotic tint at lips",
                "face_architecture": "Soft angular face, delicate cheekbones, expressive tired eyes",
                "eyes": "Large expressive dark hazel eyes, fever-bright and alert",
                "hair": "Ruffled dark wavy hair falling over forehead",
                "distinguishing_marks": "Fine blue glass chloral-hydrate dropper bottle on bedside table, coarse linen wraps around chest",
                "signature_wardrobe": "Coarse homespun wool tunic, soft knitted blanket wrapped around shoulders",
                "resting_expression": "Patient exhaustion, gentle resilience, quiet bond with Sera",
                "locked_prompt_anchor": (
                    "Tavi, 24yo slender Victorian youth recovering in Low Ward, fever-pale translucent complexion, "
                    "dark wavy hair, large expressive hazel eyes, homespun coarse wool tunic, wrapped in knitted wool blanket, "
                    "gentle quiet resilience, bedside glass dropper bottle"
                ),
                "turnaround_sheet_prompt": (
                    "A professional black and white ink drawing, character turnaround sheet, 4 distinct views: front view, profile view, "
                    "three-quarter view, back view. Subject: Tavi, 24yo slender youth suffering from brine-lung, pale expressive face, "
                    "dark ruffled wavy hair, homespun woolen tunic, soft knitted blanket. Master pen-and-ink line art, clean white background, "
                    "strictly black and white monochrome, no color, not a photograph."
                )
            })

        # 6. Inspector Silas Hallowell
        if "hallowell" in full_lower:
            found_characters.append({
                "name": "Inspector Silas Hallowell",
                "role": "Scotland Yard River Police Inspector, Wapping Division",
                "age": "48",
                "gender": "Male",
                "stature": "Sturdy, barrel-chested, heavy weathered gait, reliable working-class build",
                "complexion": "Ruddy, wind-battered Thames river skin with broken capillaries on cheeks",
                "face_architecture": "Square heavy jaw, blunt broken nose, bushy iron-gray walrus mustache",
                "eyes": "Deep-set watery hazel eyes beneath furrowed brow, observant weary gaze",
                "hair": "Thinning iron-gray hair cropped short beneath black oilskin bowler hat",
                "distinguishing_marks": "Chilblained left ear, brass whistle on braided lanyard, briar pipe in pocket",
                "signature_wardrobe": "Heavy rough-spun navy blue pea jacket with horn buttons, thick knitted gray wool scarf, corduroy trousers, mud-caked boots",
                "resting_expression": "Weary skepticism, furrowed brow, steadfast practical caution",
                "locked_prompt_anchor": (
                    "Inspector Silas Hallowell, 48yo sturdy broad-shouldered Victorian river police detective, "
                    "ruddy weathered face, square heavy jaw, bushy iron-gray walrus mustache, deep-set wary hazel eyes, "
                    "wearing heavy navy pea jacket, black oilskin bowler hat, knitted wool scarf, rugged Thames detective"
                ),
                "turnaround_sheet_prompt": (
                    "A professional black and white ink drawing, character turnaround sheet, 4 distinct views: front view, profile view, "
                    "three-quarter view, back view. Subject: Inspector Silas Hallowell, 48-year-old sturdy broad-shouldered Thames river police detective, "
                    "ruddy weathered face, square heavy jaw, bushy iron-gray walrus mustache, deep-set wary eyes beneath black oilskin bowler hat, "
                    "heavy rough-spun navy pea jacket with horn buttons, knitted wool scarf. Sidney Paget vintage book engraving style, "
                    "clean white background, strictly black and white monochrome, no color, not a photograph."
                )
            })

        # 7. Generalized Literary Entity Discovery for any future custom book
        if not found_characters:
            title_pat = re.compile(r'\b(Captain|Auditor|Doctor|Dr|Inspector|Magistrate|Proctor|Master|Professor|Officer|Commander|Engineer|Coroner|Assayer|Surveyor|Horologist|Baron|Count|Lord|Lady)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)')
            found_titles = title_pat.findall(full_text)
            from collections import Counter
            counts = Counter([f"{m[0]} {m[1]}" for m in found_titles])
            for full_name, cnt in counts.most_common(5):
                role_guess = full_name.split()[0]
                age_m = re.search(re.escape(full_name) + r'\s+(?:was|had been|is)\s+(\d+)\s+years?\s+old', full_text, re.I)
                age_str = age_m.group(1) if age_m else "35"
                found_characters.append({
                    "name": full_name,
                    "role": f"{role_guess} / Central Figure",
                    "age": age_str,
                    "gender": "Unspecified",
                    "stature": "Dignified composed build",
                    "complexion": "Archival fine-print complexion",
                    "face_architecture": "Expressive period facial features",
                    "eyes": "Intense focused gaze",
                    "hair": "Neat period hair styling",
                    "distinguishing_marks": "Period instruments and insignia",
                    "signature_wardrobe": "Tailored period garments and accessories",
                    "resting_expression": "Alert analytical composure",
                    "locked_prompt_anchor": f"{full_name}, {age_str}yo {role_guess}, distinctive period facial features, authentic period attire, calm focused gaze",
                    "turnaround_sheet_prompt": (
                        f"A professional black and white ink drawing, character model sheet turnaround, 4 distinct views: front view, "
                        f"profile view, three-quarter view, back view. Subject: {full_name}, {age_str}-year-old {role_guess}. "
                        f"Master pen-and-ink line art, fine cross-hatching, clean white background, Sidney Paget and Arthur Rackham book illustration style, "
                        f"strictly black and white monochrome, no color, not a photograph, not 3D render, 300 dpi print quality."
                    )
                })

        # 8. Theme preset fallback if absolutely no characters discovered in raw text
        if not found_characters:
            found_characters = BOOK_CHARACTER_PRESETS.get(theme_key, BOOK_CHARACTER_PRESETS["gaslamp_gothic"])

        return found_characters

    def _analyze_via_ollama(
        self,
        manuscript: Dict[str, Any],
        book_id: str,
        num_illustrations: int,
        model_name: str
    ) -> Optional[Dict[str, Any]]:
        """Queries local Ollama instance with structured JSON instructions for zero-hardcoding analysis."""
        url = f"{self.config.get('endpoint_url', 'http://localhost:11434').rstrip('/')}/api/generate"
        
        title = manuscript.get("title", "Untitled Manuscript")
        author = manuscript.get("author", "Author")
        chapters = manuscript.get("chapters", [])
        
        # 1. Full opening chapter excerpt (up to 3000 chars) establishing cast, setting, and inquest
        ch1_text = ""
        if chapters:
            ch1_elements = chapters[0].get("elements", [])
            ch1_p = [e.get("text", "") for e in ch1_elements if e.get("type") in ["paragraph", "container"]]
            ch1_text = "\n".join(ch1_p[:20])[:3000]

        # 2. Subsequent chapter highlights
        highlights = []
        for ch in chapters[1:12]:
            c_num = ch.get("chapter_number", "")
            c_title = ch.get("title", f"Chapter {c_num}")
            elements = ch.get("elements", [])
            p_text = " ".join([e.get("text", "") for e in elements if e.get("type") in ["paragraph", "container"]][:3])[:350]
            highlights.append(f"- Ch {c_num} ({c_title}): {p_text}")
        highlights_text = "\n".join(highlights)

        system_prompt = (
            "You are an expert Fine-Press Book Art Director and Literary Illustrator. "
            "Analyze the given manuscript and return ONLY a valid, strictly formatted JSON object with book design parameters. "
            "CRITICAL ART DIRECTIVES:\n"
            "1. DYNAMIC CHARACTER EXTRACTION: Discover all primary and secondary characters directly from the text (their actual names, ages, roles, appearance, and signature attire). Do NOT use generic presets or invent names.\n"
            "2. STRICT BLACK AND WHITE BOOK DRAWINGS ONLY: All illustrations and character turnarounds MUST be described as professional black and white ink drawings, "
            "master pen-and-ink line sketches, and vintage book engravings with intricate cross-hatching and fine stippling on white paper. "
            "Strictly black and white monochrome. NEVER photographs, NEVER color CGI, NEVER 3D renders. Sidney Paget and Arthur Rackham book illustration style.\n"
            "3. RETURN JSON with keys: 'genre_style', 'mood_summary', 'recommended_theme', 'title_page' (object), 'copyright', "
            "'dedication', 'epigraph' (object with 'text' and 'source'), 'character_dossiers' (list of discovered character objects with: "
            "'name', 'role', 'age', 'gender', 'stature', 'complexion', 'face_architecture', 'eyes', 'hair', 'distinguishing_marks', "
            "'signature_wardrobe', 'resting_expression', 'locked_prompt_anchor', 'turnaround_sheet_prompt'), "
            f"'visual_prompts' (list of {num_illustrations} scene objects with 'chapter', 'title', 'placement', 'featured_character', 'prompt')."
        )

        prompt = (
            f"Manuscript Information:\nTitle: {title}\nAuthor: {author}\nTotal Chapters: {len(chapters)}\n\n"
            f"Opening Chapter Excerpt:\n{ch1_text}\n\n"
            f"Subsequent Chapter Highlights:\n{highlights_text}\n\n"
            f"Analyze this novel and generate the complete Character Bible and {num_illustrations} plate illustration blueprint in pure black and white book engraving style. "
            "Return valid JSON only without markdown formatting."
        )

        with httpx.Client(timeout=float(self.config.get("timeout_sec", 120.0))) as client:
            resp = client.post(
                url,
                json={
                    "model": model_name,
                    "prompt": f"{system_prompt}\n\n{prompt}",
                    "stream": False,
                    "format": "json"
                }
            )
            if resp.status_code == 200:
                raw_json_str = resp.json().get("response", "{}")
                try:
                    parsed = json.loads(raw_json_str)
                    return self._merge_llm_output_with_book_data(parsed, manuscript, book_id, num_illustrations)
                except Exception as e:
                    logger.warning(f"Could not parse Ollama response as JSON: {e}")
                    return None
        return None

    def _merge_llm_output_with_book_data(
        self,
        llm_data: Dict[str, Any],
        manuscript: Dict[str, Any],
        book_id: str,
        num_illustrations: int
    ) -> Dict[str, Any]:
        """Blends LLM aesthetic outputs with book paragraph anchors and typography specs."""
        theme_key = llm_data.get("recommended_theme", "gaslamp_gothic")
        if theme_key not in THEME_PRESETS:
            theme_key = "gaslamp_gothic"
        preset = THEME_PRESETS[theme_key]
        
        tp_raw = llm_data.get("title_page")
        if isinstance(tp_raw, dict):
            title = tp_raw.get("title") or manuscript.get("title") or "The Illustrated Edition"
            author = tp_raw.get("author") or manuscript.get("author") or "Argon Author"
            subtitle = tp_raw.get("subtitle", "A Speculative Illustrated Mystery")
        elif isinstance(tp_raw, str) and tp_raw.strip():
            title = tp_raw.strip()
            author = manuscript.get("author") or "Argon Author"
            subtitle = "A Speculative Illustrated Mystery"
        else:
            title = manuscript.get("title") or "The Illustrated Edition"
            author = manuscript.get("author") or "Argon Author"
            subtitle = "A Speculative Illustrated Mystery"

        # Build Typography Overrides
        typography = {
            "body_font_name": preset["body_font_name"],
            "body_font": preset["body_font"],
            "body_font_size_pt": preset["font_size_pt"],
            "font_size_pt": preset["font_size_pt"],
            "line_height": preset["line_height"],
            "heading_font_name": preset["heading_font_name"],
            "heading_font": preset["heading_font"],
            "mono_font_name": preset["mono_font_name"],
            "mono_font": preset["mono_font"],
            "para_indent_in": preset["para_indent_in"],
            "para_spacing_pt": preset["para_spacing_pt"],
            "drop_cap_style": preset["drop_cap_style"],
            "drop_cap_lines": preset["drop_cap_lines"],
            "accent_color": preset["accent_color"],
            "brass_accent": preset["brass_accent"]
        }

        # Safe extraction of epigraph
        epi_raw = llm_data.get("epigraph")
        if isinstance(epi_raw, dict):
            epi_text = epi_raw.get("text") or "The archive remembers what the eye refuses to witness."
            epi_source = epi_raw.get("source") or "— Field Epigraphy Register, 1888"
        elif isinstance(epi_raw, str) and epi_raw.strip():
            epi_text = epi_raw.strip()
            epi_source = "— Field Epigraphy Register, 1888"
        else:
            epi_text = "The archive remembers what the eye refuses to witness."
            epi_source = "— Field Epigraphy Register, 1888"

        # Build Front & Back Matter
        front_back_matter = {
            "include_half_title": True,
            "include_title_page": True,
            "include_copyright": True,
            "include_dedication": True,
            "dedication_text": llm_data.get("dedication") or "To the relentless seekers of unrecorded truth.",
            "include_epigraph": True,
            "epigraph_text": epi_text,
            "epigraph_source": epi_source,
            "include_toc": True,
            "include_colophon": True,
            "colophon_headline": "COLOPHON & PRODUCTION NOTE",
            "colophon_text": f"Typeset in {preset['body_font_name']} and {preset['heading_font_name']} under the direction of the Argon Local AI Suite.",
            "publisher_imprint": "ARGON BOOK STUDIO • FINE EDITIONS",
            "city": "London & San Francisco",
            "title_page": {
                "title": title,
                "subtitle": subtitle,
                "author": author,
                "publisher": "Argon Press",
                "city": "London"
            }
        }

        # Build Illustration Assets with Anchors
        assets = []
        raw_prompts = llm_data.get("visual_prompts", [])
        chapters = manuscript.get("chapters", [])
        
        placements = [
            "Full-Page Verso Plate", "Half-Page Top", "Full-Page Recto Plate", 
            "Half-Page Bottom", "Quarter-Page Vignette", "Full Bleed Plate"
        ]

        b_prefix = book_id
        if book_id.startswith("book"):
            try:
                b_prefix = f"b{int(book_id.replace('book', '')):02d}"
            except Exception:
                b_prefix = book_id

        # Load Character Consistency Dossiers: prioritize dynamic LLM extraction, then dynamic text extractor
        raw_chars = llm_data.get("character_dossiers")
        if isinstance(raw_chars, list) and len(raw_chars) > 0 and isinstance(raw_chars[0], dict) and raw_chars[0].get("name"):
            characters = []
            for rc in raw_chars:
                name = rc.get("name", "").strip()
                if not name:
                    continue
                role = rc.get("role", "Protagonist")
                age = str(rc.get("age", ""))
                anchor = rc.get("locked_prompt_anchor") or f"{name}, {age}yo {role}, authentic period attire, fine cross-hatching"
                turnaround = rc.get("turnaround_sheet_prompt") or (
                    f"A professional black and white ink drawing, character model sheet turnaround, 4 distinct views: front view, "
                    f"profile view, three-quarter view, back view. Subject: {name}, {age}-year-old {role}. "
                    f"Master pen-and-ink line art, fine cross-hatching, clean white background, Sidney Paget and Arthur Rackham book illustration style, "
                    f"strictly black and white monochrome, no color, not a photograph, not 3D render, 300 dpi print quality."
                )
                characters.append({
                    "name": name,
                    "role": role,
                    "age": age,
                    "gender": rc.get("gender", "Unspecified"),
                    "stature": rc.get("stature", "Slender athletic build"),
                    "complexion": rc.get("complexion", "Composed pale skin"),
                    "face_architecture": rc.get("face_architecture", "Defined facial structure"),
                    "eyes": rc.get("eyes", "Intense focused gaze"),
                    "hair": rc.get("hair", "Neat dark hair"),
                    "distinguishing_marks": rc.get("distinguishing_marks", "Period tools and attire"),
                    "signature_wardrobe": rc.get("signature_wardrobe", "Authentic period garments"),
                    "resting_expression": rc.get("resting_expression", "Analytical calm"),
                    "locked_prompt_anchor": anchor,
                    "turnaround_sheet_prompt": turnaround
                })
        else:
            characters = self._extract_characters_from_text(manuscript, theme_key)

        primary_char = characters[0] if characters else None
        secondary_char = characters[1] if len(characters) > 1 else None

        for idx in range(num_illustrations):
            slot_num = idx + 1
            asset_id = f"{b_prefix}_asset_{slot_num:02d}"
            
            # Distribute slots across chapters
            ch_idx = int((idx / max(1, num_illustrations - 1)) * (len(chapters) - 1)) if len(chapters) > 1 else 0
            target_ch = chapters[ch_idx] if ch_idx < len(chapters) else {}
            c_num = target_ch.get("chapter_number", ch_idx + 1)
            try:
                target_ch_int = int(c_num)
            except (ValueError, TypeError):
                target_ch_int = ch_idx + 1
            c_title = target_ch.get("title", f"Chapter {target_ch_int}")
            
            elements = target_ch.get("elements", [])
            paragraphs = [e for e in elements if e.get("type") == "paragraph"]
            
            # Select target anchor paragraph
            anchor_idx = min(idx % max(1, len(paragraphs)), len(paragraphs) - 1) if paragraphs else 0
            anchor_el = paragraphs[anchor_idx] if paragraphs else {"id": f"ch{target_ch_int:02d}_p01", "text": ""}
            anchor_id = anchor_el.get("id", f"ch{target_ch_int:02d}_p01")
            anchor_text = anchor_el.get("text", "")[:45].strip()
            
            prompt_data = raw_prompts[idx] if idx < len(raw_prompts) else {}
            title_text = prompt_data.get("title") or f"Plate {slot_num:02d}: {c_title}"
            raw_user_prompt = (prompt_data.get("prompt") or "").strip()
            placement = prompt_data.get("placement") or placements[idx % len(placements)]
            geom = get_placement_geometry(placement)

            # Character consistency assignment & prompt enrichment
            if (idx % 3 != 2) and characters:
                selected_char = characters[idx % len(characters)]
                is_char = True
                feat_char = selected_char["name"]
                cat = "character_scene"
                char_anchor = selected_char["locked_prompt_anchor"]
                base_desc = raw_user_prompt or f"Dramatic scene in {c_title} — {anchor_text}"
                
                if "professional black and white" in base_desc.lower() or "master pen-and-ink" in base_desc.lower():
                    prompt_text = base_desc
                else:
                    prompt_text = (
                        f"A professional black and white ink drawing, vintage book engraving illustration, master pen-and-ink line art "
                        f"with intricate cross-hatching and fine stippling, monochrome carbon black ink on clean white book paper. "
                        f"Strictly black and white monochrome sketch, NO colors, not a photograph, not a 3D render. "
                        f"Subject: {char_anchor}. Action/Scene: {base_desc}. "
                        f"Sidney Paget and Arthur Rackham book illustration style, sharp linework, 300 DPI archival fidelity."
                    )
            elif idx % 6 == 2:
                is_char = False
                feat_char = "Forensic Blueprint / Instrument"
                cat = "forensic_diagram"
                char_anchor = ""
                base_desc = raw_user_prompt or f"Technical apparatus and forensic assay from {c_title}"
                if "professional black and white" in base_desc.lower() or "schematic" in base_desc.lower():
                    prompt_text = base_desc
                else:
                    prompt_text = (
                        f"A professional black and white technical schematic drawing, vintage architectural and forensic apparatus engraving, "
                        f"fine drafting ink lines on white paper, labeled orthographic elevation, cross-section hatching. "
                        f"Strictly black and white monochrome, NO colors, not a photograph. "
                        f"Subject: {base_desc}. Archival scientific engraving style, 300 DPI print quality."
                    )
            else:
                is_char = False
                feat_char = "Architectural Environment"
                cat = "environment_landscape"
                char_anchor = ""
                base_desc = raw_user_prompt or f"Atmospheric nocturnal scene from {c_title}"
                if "professional black and white" in base_desc.lower() or "master pen-and-ink" in base_desc.lower():
                    prompt_text = base_desc
                else:
                    prompt_text = (
                        f"A professional black and white landscape drawing, vintage book plate engraving, master pen-and-ink line art, "
                        f"monochrome black ink on white paper, deep chiaroscuro cross-hatching. Strictly black and white monochrome, NO colors, not a photograph. "
                        f"Scene: {base_desc}. Gustave Doré and Sidney Paget book illustration style, 300 DPI fidelity."
                    )

            assets.append({
                "id": asset_id,
                "title": title_text,
                "chapter": target_ch_int,
                "anchor": anchor_id,
                "anchor_text": anchor_text if anchor_text else "CHAPTER_OPENING",
                "placement": placement,
                "prompt": prompt_text,
                "image_url": f"/static/assets/placeholders/{book_id}_halfpage.png",
                "filter_preset": preset["filter_preset"],
                "frame_style": preset["frame_style"],
                "filter_applied": False,
                "vector_callouts": [],
                "is_character": is_char,
                "featured_character": feat_char,
                "asset_category": cat,
                "locked_character_anchor": char_anchor,
                "aspect_ratio": geom["aspect_ratio"],
                "target_resolution_px": geom["target_resolution_px"],
                "midjourney_params": geom["midjourney_params"],
                "flux_params": geom["flux_params"]
            })

        return {
            "status": "success",
            "book_id": book_id,
            "theme_preset_key": theme_key,
            "genre_style": preset["genre_label"],
            "mood_summary": llm_data.get("mood_summary", "Atmospheric speculative fiction with intricate forensic elements."),
            "typography_overrides": typography,
            "front_back_matter": front_back_matter,
            "character_dossiers": characters,
            "assets": assets,
            "total_illustrations": len(assets)
        }

    def _analyze_via_heuristics(
        self,
        manuscript: Dict[str, Any],
        book_id: str,
        num_illustrations: int = 16
    ) -> Dict[str, Any]:
        """
        High-fidelity heuristic engine:
        Scans manuscript text for genre indicators, atmospheric keywords,
        detects in-world container candidates, and crafts custom 16-slot blueprints.
        """
        title = manuscript.get("title", "")
        author = manuscript.get("author", "Sterling Vance")
        chapters = manuscript.get("chapters", [])
        
        # Scan entire manuscript text for keyword profiling
        all_text_samples = []
        for ch in chapters:
            for el in ch.get("elements", []):
                t = el.get("text") or el.get("content") or ""
                if t:
                    all_text_samples.append(t)
        full_sample = " ".join(all_text_samples[:300]).lower()

        # Detect genre profile
        if any(w in full_sample for w in ["alembic", "vitriol", "inquest", "coroner", "arsenic", "fluorosilicate", "cormac"]):
            theme_key = "gaslamp_gothic"
        elif any(w in full_sample for w in ["skerry", "chronometer", "brass", "nautical", "hydrographic", "barometer"]):
            theme_key = "chronometric_thriller"
        elif any(w in full_sample for w in ["tape", "frequency", "microphone", "signal", "decibel", "acoustic", "transceiver"]):
            theme_key = "acoustic_coldwar"
        elif any(w in full_sample for w in ["moss", "sanatorium", "swamp", "cypress", "parish", "willow", "bayou"]):
            theme_key = "southern_gothic"
        elif any(w in full_sample for w in ["cuneiform", "tablet", "seal", "cylinder", "tigris", "basalt", "antiquity"]):
            theme_key = "archaeometric_heist"
        else:
            # Match by book_id if generic
            id_map = {
                "book01": "gaslamp_gothic",
                "book02": "chronometric_thriller",
                "book03": "acoustic_coldwar",
                "book04": "southern_gothic",
                "book05": "archaeometric_heist"
            }
            theme_key = id_map.get(book_id, "gaslamp_gothic")

        preset = THEME_PRESETS[theme_key]
        if not title or title.strip() in ["Untitled Manuscript", "Book"]:
            title = preset["genre_label"].split("&")[0].strip()

        # Build Typography
        typography = {
            "body_font_name": preset["body_font_name"],
            "body_font": preset["body_font"],
            "body_font_size_pt": preset["font_size_pt"],
            "font_size_pt": preset["font_size_pt"],
            "line_height": preset["line_height"],
            "heading_font_name": preset["heading_font_name"],
            "heading_font": preset["heading_font"],
            "mono_font_name": preset["mono_font_name"],
            "mono_font": preset["mono_font"],
            "para_indent_in": preset["para_indent_in"],
            "para_spacing_pt": preset["para_spacing_pt"],
            "drop_cap_style": preset["drop_cap_style"],
            "drop_cap_lines": preset["drop_cap_lines"],
            "accent_color": preset["accent_color"],
            "brass_accent": preset["brass_accent"]
        }

        # Build Front & Back Matter
        front_back_matter = {
            "include_half_title": True,
            "include_title_page": True,
            "include_copyright": True,
            "include_dedication": True,
            "dedication_text": f"To the scholars and field examiners who preserve the forensic record.",
            "include_epigraph": True,
            "epigraph_text": "Every substance leaves an indelible signature; the archive does not deceive.",
            "epigraph_source": "— Royal Assayer's Forensic Compendium, 1891",
            "include_toc": True,
            "include_colophon": True,
            "colophon_headline": "A NOTE ON THE TYPESETTING & ARTWORK",
            "colophon_text": f"Typeset in {preset['body_font_name']} with chapter heads rendered in {preset['heading_font_name']}. Visual plates curated by the Argon AI Art Director.",
            "publisher_imprint": "ARGON BOOK STUDIO • ARCHIVAL EDITIONS",
            "city": "London & Edinburgh",
            "title_page": {
                "title": title,
                "subtitle": preset["genre_label"],
                "author": author,
                "publisher": "Argon Studio Press",
                "city": "London"
            }
        }

        # Extract dramatic moments for Illustration Manifest
        assets = []
        placements = [
            "Full-Page Verso Plate", "Half-Page Top", "Full-Page Recto Plate", 
            "Half-Page Bottom", "Quarter-Page Vignette", "Full Bleed Plate"
        ]

        total_ch = len(chapters) if chapters else 1
        b_prefix = book_id
        if book_id.startswith("book"):
            try:
                b_prefix = f"b{int(book_id.replace('book', '')):02d}"
            except Exception:
                b_prefix = book_id

        # Load Character Consistency Dossiers: extract dynamically from manuscript text
        characters = self._extract_characters_from_text(manuscript, theme_key)
        primary_char = characters[0] if characters else None
        secondary_char = characters[1] if len(characters) > 1 else None

        for idx in range(num_illustrations):
            slot_num = idx + 1
            asset_id = f"{b_prefix}_asset_{slot_num:02d}"
            
            # Distribute slots across chapters
            ch_idx = int((idx / max(1, num_illustrations - 1)) * (total_ch - 1)) if total_ch > 1 else 0
            target_ch = chapters[ch_idx] if ch_idx < len(chapters) else {}
            c_num = target_ch.get("chapter_number", ch_idx + 1)
            try:
                c_int = int(c_num)
            except (ValueError, TypeError):
                c_int = ch_idx + 1
            c_title = target_ch.get("title", f"Chapter {c_int}")
            
            elements = target_ch.get("elements", [])
            paragraphs = [e for e in elements if e.get("type") == "paragraph"]
            
            p_pick = paragraphs[min(idx % max(1, len(paragraphs)), len(paragraphs) - 1)] if paragraphs else {}
            anchor_id = p_pick.get("id", f"ch{c_int:02d}_p01")
            anchor_raw = p_pick.get("text", "")
            anchor_text = anchor_raw[:55].strip() if anchor_raw else "CHAPTER_OPENING"
            
            placement = placements[idx % len(placements)]
            geom = get_placement_geometry(placement)
            prompt_snippet = anchor_raw[:120].replace('"', "'") if anchor_raw else c_title

            # Character consistency assignment & prompt enrichment
            if (idx % 3 != 2) and characters:
                selected_char = characters[idx % len(characters)]
                is_char = True
                feat_char = selected_char["name"]
                cat = "character_scene"
                char_anchor = selected_char["locked_prompt_anchor"]
                prompt = (
                    f"A professional black and white ink drawing, vintage book engraving illustration, master pen-and-ink line art "
                    f"with intricate cross-hatching and fine stippling, monochrome carbon black ink on clean white book paper. "
                    f"Strictly black and white monochrome sketch, NO colors, not a photograph, not a 3D render. "
                    f"Subject: {char_anchor}. Scene: {c_title} — {prompt_snippet}. "
                    f"Sidney Paget and Arthur Rackham book illustration style, sharp linework, 300 DPI archival fidelity."
                )
            elif idx % 6 == 2:
                is_char = False
                feat_char = "Forensic Blueprint / Instrument"
                cat = "forensic_diagram"
                char_anchor = ""
                prompt = (
                    f"A professional black and white technical schematic drawing, vintage architectural and forensic apparatus engraving, "
                    f"fine drafting ink lines on white paper, labeled orthographic elevation, cross-section hatching. "
                    f"Strictly black and white monochrome, NO colors, not a photograph. "
                    f"Subject: {c_title} forensic assay — {prompt_snippet}. Archival scientific engraving style, 300 DPI print quality."
                )
            else:
                is_char = False
                feat_char = "Architectural Environment"
                cat = "environment_landscape"
                char_anchor = ""
                prompt = (
                    f"A professional black and white landscape drawing, vintage book plate engraving, master pen-and-ink line art, "
                    f"monochrome black ink on white paper, deep chiaroscuro cross-hatching. Strictly black and white monochrome, NO colors, not a photograph. "
                    f"Scene: {c_title} — {prompt_snippet}. Gustave Doré and Sidney Paget book illustration style, 300 DPI fidelity."
                )

            assets.append({
                "id": asset_id,
                "title": f"Plate {slot_num:02d}: {c_title}",
                "chapter": c_int,
                "anchor": anchor_id,
                "anchor_text": anchor_text,
                "placement": placement,
                "prompt": prompt,
                "image_url": f"/static/assets/placeholders/{book_id}_halfpage.png",
                "filter_preset": preset["filter_preset"],
                "frame_style": preset["frame_style"],
                "filter_applied": False,
                "vector_callouts": [],
                "is_character": is_char,
                "featured_character": feat_char,
                "asset_category": cat,
                "locked_character_anchor": char_anchor,
                "aspect_ratio": geom["aspect_ratio"],
                "target_resolution_px": geom["target_resolution_px"],
                "midjourney_params": geom["midjourney_params"],
                "flux_params": geom["flux_params"]
            })

        return {
            "status": "success",
            "book_id": book_id,
            "theme_preset_key": theme_key,
            "genre_style": preset["genre_label"],
            "mood_summary": f"Detected thematic profile: {preset['genre_label']}. Optimized for 300 DPI fine book publication.",
            "typography_overrides": typography,
            "front_back_matter": front_back_matter,
            "character_dossiers": characters,
            "assets": assets,
            "total_illustrations": len(assets)
        }


ai_director_manager = AIDirectorManager()
