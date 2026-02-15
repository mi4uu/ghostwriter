"""
Cover generator for KDP books.

Generates full wrap-around covers (back + spine + front) as PDF.
Migrated and cleaned up from notebok_cover.py.
"""

from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageColor
import os

from lib.formats import COVER_DPI
from lib.google_fonts import resolve_font


# --- Color Helpers ---

def get_tint(hex_color, factor=0.9):
    """Lighten a color toward white by factor (0=original, 1=white)."""
    r, g, b = ImageColor.getrgb(hex_color)
    return (
        int(r + (255 - r) * factor),
        int(g + (255 - g) * factor),
        int(b + (255 - b) * factor),
    )


def get_shade(hex_color, factor=0.4):
    """Darken a color toward black by factor (0=original, 1=black)."""
    r, g, b = ImageColor.getrgb(hex_color)
    return (
        int(r * (1 - factor)),
        int(g * (1 - factor)),
        int(b * (1 - factor)),
    )


def get_luminance(hex_color):
    """Get perceived luminance of a color (0=dark, 255=bright)."""
    r, g, b = ImageColor.getrgb(hex_color)
    return 0.299 * r + 0.587 * g + 0.114 * b


def process_image_seamless(image_path, ink_color, paper_color):
    """
    Process a line-art image so it blends seamlessly with the cover background.

    Creates an opaque image where:
    - Dark pixels (lines) become ink_color
    - Light pixels (background) become paper_color

    This eliminates dirty borders from transparency.
    """
    src_img = Image.open(image_path).convert("RGBA")

    # Flatten onto white to standardize
    flat_img = Image.new("RGB", src_img.size, (255, 255, 255))
    flat_img.paste(src_img, mask=src_img.getchannel('A'))

    # Grayscale + normalize light grays to pure white
    gray_img = flat_img.convert('L')
    threshold = 200
    gray_img = gray_img.point(lambda x: 255 if x > threshold else x)

    # Colorize: black pixels -> ink, white pixels -> paper
    return ImageOps.colorize(gray_img, black=ink_color, white=paper_color)


def draw_wrapped_text(draw, text, font, max_width, start_y, center_x, color):
    """Draw text centered and word-wrapped. Returns the Y position after last line."""
    lines = []
    words = text.split()
    current_line = []

    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        line_width = bbox[2] - bbox[0]
        if line_width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))

    current_y = start_y
    try:
        line_height = font.size * 1.2
    except AttributeError:
        line_height = 40

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        draw.text(
            (center_x - line_width / 2, current_y),
            line, font=font, fill=color
        )
        current_y += line_height

    return current_y


def generate_cover(
    title_text,
    color_hex,
    image_path,
    output_path,
    font_name="AmericanTypewriter",
    page_format="6x9",
):
    """
    Generate a full KDP wrap-around cover (back + spine + front).

    Args:
        title_text: The title displayed on the front cover
        color_hex: Main color hex code (e.g., "#B2AC88")
        image_path: Path to the line-art image for the cover
        output_path: Path to save the output PDF
        font_name: Font name to use for the title
        page_format: Page format string or tuple (used for page dimensions)
    """
    from lib.formats import format_to_pixels

    DPI = COVER_DPI
    PAGE_WIDTH, PAGE_HEIGHT = format_to_pixels(page_format, DPI)
    BLEED = int(0.125 * DPI)
    SPINE_WIDTH = int(0.25 * DPI)
    TOTAL_WIDTH = int((PAGE_WIDTH * 2) + SPINE_WIDTH + (BLEED * 2))
    TOTAL_HEIGHT = int(PAGE_HEIGHT + (BLEED * 2))

    # Resolve image path - fallback to dummy
    if not os.path.exists(image_path):
        print(f"  Warning: Image '{image_path}' not found, using dummy")
        image_path = _create_dummy_image()

    # Color logic
    bg_rgb = get_tint(color_hex, 0.90)
    lum = get_luminance(color_hex)
    if lum > 180:
        text_color_rgb = get_shade(color_hex, 0.55)
        border_rgb = get_shade(color_hex, 0.3)
    else:
        text_color_rgb = ImageColor.getrgb(color_hex)
        border_rgb = get_tint(color_hex, 0.4)

    # Create canvas
    cover = Image.new("RGB", (TOTAL_WIDTH, TOTAL_HEIGHT), bg_rgb)
    draw = ImageDraw.Draw(cover)

    # Layout
    front_start_x = int(BLEED + PAGE_WIDTH + SPINE_WIDTH)
    spine_x1 = int(BLEED + PAGE_WIDTH)

    # Spine
    draw.rectangle(
        [spine_x1, 0, spine_x1 + SPINE_WIDTH, TOTAL_HEIGHT],
        fill=border_rgb
    )

    # Front accent strip
    strip_width = int(0.8 * DPI)
    draw.rectangle(
        [front_start_x, 0, front_start_x + strip_width, TOTAL_HEIGHT],
        fill=border_rgb
    )

    # Font
    font = _load_font(font_name, size=100)

    # Title text
    text_area_width = PAGE_WIDTH - strip_width - (0.5 * DPI)
    text_center_x = front_start_x + strip_width + (text_area_width / 2)
    text_start_y = 1.5 * DPI

    text_end_y = draw_wrapped_text(
        draw, title_text, font, text_area_width,
        text_start_y, text_center_x, text_color_rgb
    )

    # Image
    try:
        cat_img = process_image_seamless(image_path, text_color_rgb, bg_rgb)

        target_img_width = 4 * DPI
        ratio = target_img_width / cat_img.width
        target_img_height = int(cat_img.height * ratio)

        cat_img = cat_img.resize(
            (int(target_img_width), target_img_height),
            Image.Resampling.LANCZOS
        )

        img_x = int(text_center_x - (target_img_width / 2))
        img_y = int(text_end_y + (0.5 * DPI))

        cover.paste(cat_img, (img_x, img_y))
    except Exception as e:
        print(f"  Error processing image: {e}")

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    cover.save(output_path, "PDF", resolution=DPI)
    print(f"  Cover saved: {output_path}")


def _load_font(font_name, size=100):
    """
    Load a font by name. Supports:
    - Google Font names: "Roboto", "Vibur", "Pacifico"
    - Google Font with weight: "Roboto:Bold"
    - Local .ttf paths: "assets/fonts/MyFont.ttf"
    - System font names: "AmericanTypewriter"
    """
    # Resolve Google Fonts / paths
    resolved = resolve_font(font_name)
    try:
        return ImageFont.truetype(resolved, size)
    except IOError:
        pass
    # Fallback to system font name directly
    try:
        return ImageFont.truetype(font_name, size)
    except IOError:
        pass
    try:
        return ImageFont.truetype("arial.ttf", size)
    except IOError:
        pass
    return ImageFont.load_default()


def _create_dummy_image(path="/tmp/ghostwriter_dummy_cat.png"):
    """Create a simple dummy cat silhouette image."""
    if not os.path.exists(path):
        img = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([(100, 100), (400, 400)], fill=(80, 80, 80, 255))
        draw.ellipse([(230, 250), (270, 280)], fill=(180, 180, 180, 255))
        draw.polygon([(100, 150), (50, 50), (150, 100)], fill=(80, 80, 80, 255))
        draw.polygon([(350, 100), (450, 50), (400, 150)], fill=(80, 80, 80, 255))
        img.save(path)
    return path
