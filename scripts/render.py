# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow==12.0.0"]
# ///
"""Render every published asset from the logo in source/ and the fonts in fonts/.

    uv run scripts/render.py           write every asset
    uv run scripts/render.py --check   fail if a committed asset is out of date

The output paths are a contract: other repositories link to them from
`main`, so a path is never renamed or removed. Change what is drawn freely.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont, ImageStat

ROOT = Path(__file__).resolve().parent.parent
SOURCE_LOGO = ROOT / "source" / "pi-logo.png"
WORDMARK_FONT = ROOT / "fonts" / "AbrilFatface-Regular.ttf"
TAGLINE_FONT = ROOT / "fonts" / "IBMPlexMono-SemiBold.ttf"

# The palette is sampled from the logo itself.
INK = (0x0E, 0x0C, 0x0B, 255)
CREAM = (0xFB, 0xE3, 0xC0, 255)
TEAL = (0x14, 0x7C, 0x6C, 255)
# Graph paper: a cool off-white with a faint green-grey grid. It sets Pi apart
# from Jaws's warm paper, and the eye's ink outline keeps the cream sclera clear.
PAPER = (0xE9, 0xEF, 0xEC, 255)
GRID = (0xC3, 0xD3, 0xD0, 255)
# The grid's square, in final pixels.
GRID_STEP = 20

WORDMARK = "Pi"
TAGLINE = "IRRATIONALLY GOOD AT MATH"

# Everything is drawn at SCALE times its final size and scaled down once,
# which anti-aliases the card's outlines.
SCALE = 4


def trimmed_logo() -> Image.Image:
    """The logo cropped to its visible pixels."""
    logo = Image.open(SOURCE_LOGO).convert("RGBA")
    alpha = logo.getchannel("A").point(lambda v: 255 if v > 16 else 0)
    return logo.crop(alpha.getbbox())


def fit(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale an image to fit inside width x height, keeping its aspect ratio."""
    ratio = min(width / image.width, height / image.height)
    size = (round(image.width * ratio), round(image.height * ratio))
    return image.resize(size, Image.Resampling.LANCZOS)


def paste_centered(canvas: Image.Image, image: Image.Image) -> None:
    left = (canvas.width - image.width) // 2
    top = (canvas.height - image.height) // 2
    canvas.alpha_composite(image, (left, top))


def graph_paper(width: int, height: int, step: int, line: int) -> Image.Image:
    """A sheet of graph paper, with the grid centered so its margins match."""
    sheet = Image.new("RGBA", (width, height), PAPER)
    draw = ImageDraw.Draw(sheet)
    for x in range((width // 2) % step, width, step):
        draw.rectangle((x - line // 2, 0, x - line // 2 + line - 1, height - 1), fill=GRID)
    for y in range((height // 2) % step, height, step):
        draw.rectangle((0, y - line // 2, width - 1, y - line // 2 + line - 1), fill=GRID)
    return sheet


def logo(size: int = 1024, padding: float = 0.04) -> Image.Image:
    """The logo on a transparent square, for places that supply a background."""
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    inner = round(size * (1 - 2 * padding))
    paste_centered(canvas, fit(trimmed_logo(), inner, inner))
    return canvas


def avatar(size: int = 1024, padding: float = 0.06) -> Image.Image:
    """The logo on a graph-paper square, for avatars cropped to a circle.

    The eye is about twice as wide as it is tall and its corners are points
    on its horizontal midline, so it stays inside the circle at this width.
    The grid is coarser than the banner's so it still reads at avatar sizes.
    """
    canvas = graph_paper(size, size, step=size // 16, line=2)
    inner = round(size * (1 - 2 * padding))
    paste_centered(canvas, fit(trimmed_logo(), inner, inner))
    return canvas.convert("RGB")


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    """A font with the basic layout engine on every platform.

    Pillow uses Raqm for text layout where its build has it (Linux) and the
    basic engine where it does not (macOS), and the two place glyphs a little
    differently. Forcing the basic engine renders identically everywhere.
    """
    return ImageFont.truetype(str(path), size, layout_engine=ImageFont.Layout.BASIC)


def tracked_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple[int, int, int, int],
    tracking: float,
) -> float:
    """Draw text letter by letter with extra spacing; returns the end x."""
    x, y = xy
    for char in text:
        draw.text((x, y), char, font=font, fill=fill, anchor="ls")
        x += font.getlength(char) + tracking
    return x - tracking


def text_width(text: str, font: ImageFont.FreeTypeFont, tracking: float) -> float:
    return sum(font.getlength(char) for char in text) + tracking * (len(text) - 1)


def card(
    width: int,
    height: int,
    *,
    mark_box: tuple[int, int],
    wordmark_size: int,
    tagline_size: int,
    gap: int,
    rounded: bool,
) -> Image.Image:
    """A paper flash-sheet card: the eye on the left, the wordmark and tagline on the right.

    Sizes are in final pixels. The eye and the text block are centered on the
    card together, and vertically on its midline.
    """
    s = SCALE
    w, h = width * s, height * s
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0) if rounded else INK)
    draw = ImageDraw.Draw(canvas)

    # The card, with a heavy outer line and a fine inner one, like a flash sheet.
    radius = (28 if rounded else 0) * s
    draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=INK)
    border = 7 * s
    paper_box = (border, border, w - 1 - border, h - 1 - border)
    paper_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(paper_mask).rounded_rectangle(paper_box, radius=max(radius - border, 0), fill=255)
    canvas.paste(graph_paper(w, h, step=GRID_STEP * s, line=s), (0, 0), paper_mask)
    inset = 17 * s
    draw.rounded_rectangle(
        (inset, inset, w - 1 - inset, h - 1 - inset),
        radius=max(radius - inset + 4 * s, 0),
        outline=INK,
        width=2 * s,
    )

    mark = fit(trimmed_logo(), mark_box[0] * s, mark_box[1] * s)
    wordmark_font = font(WORDMARK_FONT, wordmark_size * s)
    tagline_font = font(TAGLINE_FONT, tagline_size * s)
    wordmark_tracking = 2 * s
    tagline_tracking = tagline_size * 0.09 * s
    shadow = max(round(wordmark_size * 0.022), 3) * s

    wordmark_w = text_width(WORDMARK, wordmark_font, wordmark_tracking) + shadow
    tagline_w = text_width(TAGLINE, tagline_font, tagline_tracking)
    text_w = max(wordmark_w, tagline_w)

    # Lay the text block out from its cap height down: wordmark, rule, tagline.
    ascent = wordmark_font.getbbox("P", anchor="ls")[1] * -1
    rule_gap = round(wordmark_size * 0.2) * s
    rule_h = max(round(tagline_size * 0.18), 3) * s
    tagline_cap = tagline_font.getbbox("I", anchor="ls")[1] * -1
    tagline_gap = round(tagline_size * 0.9) * s
    block_h = ascent + shadow + rule_gap + rule_h + tagline_gap + tagline_cap
    block_top = (h - block_h) // 2

    left = (w - (mark.width + gap * s + text_w)) // 2
    canvas.alpha_composite(mark, (int(left), (h - mark.height) // 2))
    text_left = left + mark.width + gap * s

    # The wordmark, with an offset teal shadow.
    baseline = block_top + ascent
    tracked_text(draw, (text_left + shadow, baseline + shadow), WORDMARK, wordmark_font, TEAL, wordmark_tracking)
    tracked_text(draw, (text_left, baseline), WORDMARK, wordmark_font, INK, wordmark_tracking)

    # A teal rule the width of the text block, then the tagline.
    rule_top = baseline + shadow + rule_gap
    draw.rectangle((text_left, rule_top, text_left + text_w, rule_top + rule_h), fill=TEAL)
    tagline_baseline = rule_top + rule_h + tagline_gap + tagline_cap
    tracked_text(draw, (text_left, tagline_baseline), TAGLINE, tagline_font, INK, tagline_tracking)

    return canvas.resize((width, height), Image.Resampling.LANCZOS)


def banner() -> Image.Image:
    """The README banner, 1280 x 320, with rounded corners on a transparent ground."""
    return card(1280, 320, mark_box=(430, 230), wordmark_size=150, tagline_size=30, gap=64, rounded=True)


def social_preview() -> Image.Image:
    """The repository social preview, 1280 x 640, square-cornered and opaque.

    Link cards crop to their own shape, so the card fills the whole image.
    """
    image = card(1280, 640, mark_box=(500, 380), wordmark_size=220, tagline_size=32, gap=64, rounded=False)
    return image.convert("RGB")


ASSETS = {
    "assets/logo/pi-logo.png": logo,
    "assets/avatar/pi-avatar.png": avatar,
    "assets/banner/pi-readme-banner.png": banner,
    "assets/social/pi-social-preview.png": social_preview,
}


# The largest mean difference per channel, out of 255, that still counts as
# the same image. It absorbs anti-aliasing differences between platforms and
# catches any real change to what is drawn.
TOLERANCE = 1.0


def differs(committed: Path, rendered: Image.Image) -> float | None:
    """The mean per-channel difference, or None when the sizes differ."""
    with Image.open(committed) as image:
        current = image.convert("RGBA")
    rendered = rendered.convert("RGBA")
    if current.size != rendered.size:
        return None
    return max(ImageStat.Stat(ImageChops.difference(current, rendered)).mean)


def main(argv: list[str]) -> int:
    check = argv == ["--check"]
    stale = []
    for relative, render in ASSETS.items():
        path = ROOT / relative
        image = render()
        if check:
            difference = differs(path, image) if path.is_file() else None
            if difference is None or difference > TOLERANCE:
                stale.append(relative)
                print(f"  STALE  {relative}  (difference: {difference})")
            else:
                print(f"  ok     {relative}  (difference: {difference:.3f})")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        image.save(path, optimize=True)
        print(f"{relative}  {image.width}x{image.height}  {path.stat().st_size // 1024} KiB")
    if stale:
        print("Run `uv run scripts/render.py` and commit the assets it writes.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
