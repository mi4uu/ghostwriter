from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageColor
import os
import textwrap

# --- 1. HELPER FUNCTIONS ---

def create_dummy_cat_image(filename="cat.png"):
    if not os.path.exists(filename):
        img = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([(100, 100), (400, 400)], fill=(80, 80, 80, 255))
        draw.ellipse([(230, 250), (270, 280)], fill=(180, 180, 180, 255))
        draw.polygon([(100, 150), (50, 50), (150, 100)], fill=(80, 80, 80, 255))
        draw.polygon([(350, 100), (450, 50), (400, 150)], fill=(80, 80, 80, 255))
        img.save(filename)
        print(f"-> Created dummy image: {filename}")

def get_tint(hex_color, factor=0.9):
    r, g, b = ImageColor.getrgb(hex_color)
    new_r = int(r + (255 - r) * factor)
    new_g = int(g + (255 - g) * factor)
    new_b = int(b + (255 - b) * factor)
    return (new_r, new_g, new_b)

def get_shade(hex_color, factor=0.4):
    r, g, b = ImageColor.getrgb(hex_color)
    new_r = int(r * (1 - factor))
    new_g = int(g * (1 - factor))
    new_b = int(b * (1 - factor))
    return (new_r, new_g, new_b)

def get_luminance(hex_color):
    r, g, b = ImageColor.getrgb(hex_color)
    return (0.299 * r + 0.587 * g + 0.114 * b)

def process_image_seamless(image_path, ink_color, paper_color):
    """
    FIXED: Instead of using transparency (which creates dirty borders),
    we create an OPAQUE image where the background matches the paper_color exactly.
    This makes the 'square' invisible.
    """
    # 1. Load Image
    src_img = Image.open(image_path).convert("RGBA")

    # 2. Flatten onto WHITE first (standardizes line art)
    # This ensures that transparent parts become White, and Black lines stay Black.
    flat_img = Image.new("RGB", src_img.size, (255, 255, 255))
    flat_img.paste(src_img, mask=src_img.getchannel('A'))

    # 3. Convert to Grayscale
    gray_img = flat_img.convert('L')

    # 4. NORMALIZE: Push light grays to pure white (background threshold)
    # This ensures the gray background area becomes pure white,
    # which will then map perfectly to paper_color during colorization
    # Using PIL's point() for pixel-wise threshold operation
    threshold = 200
    gray_img = gray_img.point(lambda x: 255 if x > threshold else x)

    # 5. Colorize (The Magic Step)
    # Map Black Pixels -> Ink Color (Text Color)
    # Map White Pixels -> Paper Color (Background Color)
    # This creates a solid square, but the 'background' parts are now
    # identical to the notebook cover, hiding the seam.
    final_img = ImageOps.colorize(gray_img, black=ink_color, white=paper_color)

    return final_img

def draw_wrapped_text(draw, text, font, max_width, start_y, center_x, color):
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
            if current_line: lines.append(' '.join(current_line))
            current_line = [word]
    if current_line: lines.append(' '.join(current_line))

    current_y = start_y
    try:
        line_height = font.size * 1.2
    except AttributeError:
        line_height = 40

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        draw.text((center_x - line_width / 2, current_y), line, font=font, fill=color)
        current_y += line_height
    return current_y

# --- 2. MAIN GENERATOR ---

def generate_kdp_cover(title, main_color_hex, image_filename, output_filename):
    if not os.path.exists(image_filename):
        if os.path.exists("cat.png"): image_filename = "cat.png"
        else: create_dummy_cat_image("cat.png"); image_filename = "cat.png"

    # --- CONFIG ---
    DPI = 300
    PAGE_WIDTH = 6 * DPI
    PAGE_HEIGHT = 9 * DPI
    BLEED = int(0.125 * DPI)
    SPINE_WIDTH = int(0.25 * DPI)
    TOTAL_WIDTH = int((PAGE_WIDTH * 2) + SPINE_WIDTH + (BLEED * 2))
    TOTAL_HEIGHT = int(PAGE_HEIGHT + (BLEED * 2))

    # --- COLOR LOGIC ---
    bg_rgb = get_tint(main_color_hex, 0.90)
    lum = get_luminance(main_color_hex)
    if lum > 180:
        text_color_rgb = get_shade(main_color_hex, 0.55)
        border_rgb = get_shade(main_color_hex, 0.3)
    else:
        text_color_rgb = ImageColor.getrgb(main_color_hex)
        border_rgb = get_tint(main_color_hex, 0.4)

    # --- SETUP CANVAS ---
    cover = Image.new("RGB", (TOTAL_WIDTH, TOTAL_HEIGHT), bg_rgb)
    draw = ImageDraw.Draw(cover)

    front_start_x = int(BLEED + PAGE_WIDTH + SPINE_WIDTH)
    spine_x1 = int(BLEED + PAGE_WIDTH)

    draw.rectangle([spine_x1, 0, spine_x1 + SPINE_WIDTH, TOTAL_HEIGHT], fill=border_rgb)
    strip_width = int(0.8 * DPI)
    draw.rectangle([front_start_x, 0, front_start_x + strip_width, TOTAL_HEIGHT], fill=border_rgb)

    try: font = ImageFont.truetype("AmericanTypewriter", 100)
    except IOError:
        try: font = ImageFont.truetype("arial.ttf", 100)
        except IOError: font = ImageFont.load_default()

    text_area_width = PAGE_WIDTH - strip_width - (0.5 * DPI)
    text_center_x = front_start_x + strip_width + (text_area_width / 2)
    text_start_y = 1.5 * DPI

    text_end_y = draw_wrapped_text(
        draw, title, font, text_area_width, text_start_y, text_center_x, text_color_rgb
    )

    # --- IMAGE PROCESSING (SEAMLESS) ---
    try:
        # We pass both the TEXT color (for the lines) and the BACKGROUND color (for the fill)
        cat_img = process_image_seamless(image_filename, text_color_rgb, bg_rgb)

        target_img_width = 4 * DPI
        ratio = target_img_width / cat_img.width
        target_img_height = int(cat_img.height * ratio)

        # Resize opaque image (No transparency issues!)
        cat_img = cat_img.resize((int(target_img_width), target_img_height), Image.Resampling.LANCZOS)

        img_x = int(text_center_x - (target_img_width / 2))
        img_y = int(text_end_y + (0.5 * DPI))

        cover.paste(cat_img, (img_x, img_y)) # No mask needed, it blends perfectly

    except Exception as e:
        print(f"   Error processing image: {e}")

    cover.save(output_filename, "PDF", resolution=DPI)

# --- 3. EXECUTION ---

if not os.path.exists("out"): os.makedirs("out")

MY_TITLE = "THINGS I’D LIKE TO TELL MY CAT WHEN I’M AT WORK"

COLORS = [
    # Best Sellers
    ["#B2AC88", "Sage Green"], ["#E2725B", "Terracotta"], ["#E6E6FA", "Lavender Mist"],
    ["#FAD0C9", "Dusty Pink"], ["#000080", "Navy Blue"],
    # Pastels
    ["#A0C4FF", "Periwinkle"], ["#98FF98", "Mint Green"], ["#FFD1DC", "Ballet Slipper"],
    ["#FFFACD", "Lemon Chiffon"], ["#E0B0FF", "Mauve"], ["#87CEEB", "Sky Blue"],
    # Earth
    ["#C2B280", "Sand Beige"], ["#808000", "Olive Green"], ["#964B00", "Brown Sugar"],
    ["#D2B48C", "Tan"], ["#CC7722", "Ochre"], ["#708090", "Slate Gray"],
    # Pop
    ["#FF007F", "Hot Pink"], ["#00FFFF", "Electric Cyan"], ["#FF5733", "Sunset Orange"],
    ["#DFFF00", "Chartreuse"], ["#BF00FF", "Electric Purple"],
    # Dark
    ["#36454F", "Charcoal"], ["#013220", "Forest Green"], ["#800020", "Burgundy"],
    ["#301934", "Dark Plum"], ["#0047AB", "Cobalt Blue"], ["#4B0082", "Indigo"]
]

create_dummy_cat_image("cat.png")

print(f"Starting batch of {len(COLORS)} covers...")

for i, [hex_code, color_name] in enumerate(COLORS):
    safe_name = color_name.replace(" ", "-")
    filename = f"out/cat_notebook_cover_{safe_name}.pdf"
    print(f"Processing {i+1}/{len(COLORS)}: {color_name}...")

    generate_kdp_cover(
        title=MY_TITLE,
        main_color_hex=hex_code,
        image_filename="kotek.png",
        output_filename=filename
    )

print("Batch processing complete!")
