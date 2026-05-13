"""
OG image card renderer for the Startup Survival Simulator.
Generates a 1200x630 PNG suitable for Twitter/LinkedIn/OG previews.
"""
import io
import json
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Response
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy import text

from server.core.db import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/survival-sim", tags=["Survival Simulator"])

CARD_W, CARD_H = 1200, 630
BG = (10, 14, 25)
PANEL = (15, 23, 42)
PANEL_BORDER = (30, 41, 59)
TEXT = (255, 255, 255)
MUTED = (148, 163, 184)
ACCENT = (16, 185, 129)
GRADE_COLORS = {
    "A": (16, 185, 129),
    "B": (234, 179, 8),
    "C": (249, 115, 22),
    "D": (239, 68, 68),
}

FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/nix/store/.fonts/DejaVuSans-Bold.ttf",
    "/run/current-system/sw/share/fonts/truetype/DejaVuSans-Bold.ttf",
]
FONT_PATHS_REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/nix/store/.fonts/DejaVuSans.ttf",
    "/run/current-system/sw/share/fonts/truetype/DejaVuSans.ttf",
]


def _font(size: int, bold: bool = True) -> ImageFont.ImageFont:
    paths = FONT_PATHS if bold else FONT_PATHS_REGULAR
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, txt: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), txt, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _load_sim(sim_id: str) -> Optional[dict]:
    try:
        with SessionLocal() as db:
            row = db.execute(
                text("SELECT results_json FROM survival_simulations WHERE sim_id = :sid"),
                {"sid": sim_id},
            ).fetchone()
            if not row:
                return None
            data = row[0]
            if isinstance(data, str):
                return json.loads(data)
            return data
    except Exception as e:
        logger.warning(f"og-card: failed to load sim {sim_id}: {e}")
        return None


def _render_card(sim: dict) -> bytes:
    img = Image.new("RGB", (CARD_W, CARD_H), BG)
    draw = ImageDraw.Draw(img)

    runway_p50 = sim.get("runway", {}).get("p50", 0)
    survival_12m = sim.get("survival", {}).get("12m", 0)
    grade_letter = sim.get("grade", {}).get("letter", "C")
    grade_label = sim.get("grade", {}).get("label", "Moderate")
    grade_rgb = GRADE_COLORS.get(grade_letter, GRADE_COLORS["C"])

    # Top bar — brand
    f_brand = _font(28, bold=True)
    f_eyebrow = _font(22, bold=False)
    draw.text((60, 50), "FOUNDERCONSOLE", font=f_brand, fill=TEXT)
    draw.text((60, 92), "Startup Survival Simulator", font=f_eyebrow, fill=MUTED)

    # Big runway number (left)
    f_huge = _font(190, bold=True)
    f_label = _font(34, bold=True)
    f_sub = _font(26, bold=False)

    runway_str = f"{int(runway_p50)}" if isinstance(runway_p50, (int, float)) else "—"
    runway_unit = "months"
    draw.text((60, 175), runway_str, font=f_huge, fill=TEXT)
    rw_w, _ = _text_size(draw, runway_str, f_huge)
    draw.text((70 + rw_w, 305), runway_unit, font=f_label, fill=MUTED)

    draw.text((60, 400), "MEDIAN RUNWAY (P50)", font=_font(20, bold=True), fill=ACCENT)

    # Survival probability row
    surv_pct = f"{int(survival_12m)}%"
    draw.text((60, 460), surv_pct, font=_font(72, bold=True), fill=TEXT)
    sp_w, _ = _text_size(draw, surv_pct, _font(72, bold=True))
    draw.text((70 + sp_w, 488), "chance of surviving 12 months", font=f_sub, fill=MUTED)

    # Grade badge (right side circle)
    cx, cy, r = 1000, 290, 150
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PANEL, outline=grade_rgb, width=8)
    f_grade = _font(180, bold=True)
    gw, gh = _text_size(draw, grade_letter, f_grade)
    draw.text((cx - gw / 2, cy - gh / 2 - 18), grade_letter, font=f_grade, fill=grade_rgb)
    f_glabel = _font(28, bold=True)
    gl_w, _ = _text_size(draw, grade_label.upper(), f_glabel)
    draw.text((cx - gl_w / 2, cy + r + 14), grade_label.upper(), font=f_glabel, fill=grade_rgb)

    # Footer
    f_foot = _font(22, bold=False)
    draw.text((60, CARD_H - 60), "Run yours free at founderconsole.ai/survival-simulator", font=f_foot, fill=MUTED)

    # Accent bar
    draw.rectangle((0, 0, CARD_W, 6), fill=ACCENT)

    out = io.BytesIO()
    img.save(out, format="PNG", optimize=True)
    return out.getvalue()


@router.get("/og-image/{sim_id}.png")
def og_image(sim_id: str):
    sim = _load_sim(sim_id)
    if not sim:
        # Fallback generic card so social previews still render something
        sim = {
            "runway": {"p50": 0},
            "survival": {"12m": 0},
            "grade": {"letter": "C", "label": "Run yours"},
        }
    png = _render_card(sim)
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Cache-Control": "public, max-age=86400, s-maxage=604800",
            "Content-Disposition": f'inline; filename="founderconsole-survival-{sim_id}.png"',
        },
    )


@router.get("/share-card/{sim_id}.png")
def share_card_download(sim_id: str):
    sim = _load_sim(sim_id)
    if not sim:
        raise HTTPException(status_code=404, detail="Simulation not found")
    png = _render_card(sim)
    return Response(
        content=png,
        media_type="image/png",
        headers={
            "Content-Disposition": f'attachment; filename="founderconsole-survival-{sim_id}.png"',
        },
    )
