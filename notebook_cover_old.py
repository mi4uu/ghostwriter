from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageColor
import colorsys
import os

def create_dummy_cat_image(filename="cat.png"):
    """Creates a temporary transparent PNG with a cat shape for testing."""
    if not os.path.exists(filename):
        img = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Draw a crude cat face (grayscale)
        draw.ellipse([(100, 100), (400, 400)], fill=(50, 50, 50, 255)) # Head
        draw.polygon([(100, 150), (50, 50), (150, 100)], fill=(50, 50, 50, 255)) # Left Ear
        draw.polygon([(350, 100), (450, 50), (400, 150)], fill=(50, 50, 50, 255)) # Right Ear
        img.save(filename)
        print(f"Created dummy image: {filename}")

def adjust_lightness(hex_color, factor):
    """
    Adjusts the lightness of a HEX color.
    Factor > 1 makes it lighter, Factor < 1 makes it darker.
    """
    rgb = ImageColor.getrgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(rgb[0]/255, rgb[1]/255, rgb[2]/255)
    
    # Adjust lightness (clamp between 0 and 1)
    new_l = max(0, min(1, l * factor))
    
    new_rgb = colorsys.hls_to_rgb(h, new_l, s)
    return tuple(int(x * 255) for x in new_rgb)

def colorize_image_with_transparency(image_path, target_color):
    """
    Loads a PNG, keeps the transparency, but turns all visible pixels 
    into the target_color.
    """
    # 1. Load image and ensure RGBA (Alpha channel)
    src_img = Image.open(image_path).convert("RGBA")
    
    # 2. Create a solid color image of the same size
    solid_color = Image.new("RGBA", src_img.size, target_color)
    
    # 3. Composite: Use the source alpha channel as a mask for the solid color
    # This keeps the shape of the cat, but fills it with your Main Color
    output = Image.composite(solid_color, Image.new("RGBA", src_img.size, (0,0,0,0)), src_img)
    
    return output

def generate_kdp_cover(title, main_color_hex, image_filename, output_filename):
    # --- 1. KDP CONSTANTS (6x9 inch book, ~110 pages) ---
    DPI = 300
    PAGE_WIDTH = 6 * DPI
    PAGE_HEIGHT = 9 * DPI
    BLEED = 0.125 * DPI
    # Approx spine for 110 pages (0.25 inches)
    SPINE_WIDTH = 0.25 * DPI 
    
    # Total Canvas Size = Back + Spine + Front + Bleed area
    TOTAL_WIDTH = int((PAGE_WIDTH * 2) + SPINE_WIDTH + (BLEED * 2))
    TOTAL_HEIGHT = int(PAGE_HEIGHT + (BLEED * 2))
    
    # --- 2. PREPARE COLORS ---
    # Convert HEX to RGB tuple
    main_rgb = ImageColor.getrgb(main_color_hex)
    
    # Background: Main color but 60% lighter (Factor 1.6 approx)
    bg_rgb = adjust_lightness(main_color_hex, 1.8) 
    
    # Left Border/Spine: Main color but 30% lighter (Factor 1.3 approx)
    border_rgb = adjust_lightness(main_color_hex, 1.3)

    # --- 3. CREATE CANVAS ---
    cover = Image.new("RGB", (TOTAL_WIDTH, TOTAL_HEIGHT), bg_rgb)
    draw = ImageDraw.Draw(cover)
    
    # --- 4. DRAW LAYOUT ---
    
    # Coordinates for the Front Cover (Right side of the spread)
    # X start = Bleed + Back_Cover + Spine
    front_start_x = int(BLEED + PAGE_WIDTH + SPINE_WIDTH)
    
    # A. Draw The Spine (Center)
    spine_x1 = int(BLEED + PAGE_WIDTH)
    spine_x2 = int(spine_x1 + SPINE_WIDTH)
    draw.rectangle([spine_x1, 0, spine_x2, TOTAL_HEIGHT], fill=border_rgb)
    
    # B. Draw the "Left Border" on the Front Cover
    # (Visual strip on the left side of the front cover)
    strip_width = 0.8 * DPI # 0.8 inch strip
    draw.rectangle(
        [front_start_x, 0, front_start_x + strip_width, TOTAL_HEIGHT], 
        fill=border_rgb
    )
    
    # --- 5. ADD TEXT ---
    
    # Try to load a nice font, fallback to default if not found
    try:
        # Looking for Arial or standard font. Adjust path for Mac/Linux if needed.
        # For Windows: "arial.ttf", Linux: "/usr/share/fonts/...", Mac: "/Library/Fonts/..."
        font_path = "AmericanTypewriter" 
        font_size = 120
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        font = ImageFont.load_default()
        print("Standard font not found, using default pixel font.")

    # Calculate text position (Centered horizontally on Front Cover area)
    # We ignore the left border strip for centering to make it look balanced
    text_area_width = PAGE_WIDTH
    text_center_x = front_start_x + (text_area_width / 2)
    text_y = 1.5 * DPI # 1.5 inches from top
    
    # Draw Title (Main Color)
    # Anchor 'mm' aligns middle-middle (requires newer Pillow), else use standard math
    try:
        draw.text((text_center_x, text_y), title, fill=main_rgb, font=font, anchor="mm")
    except ValueError:
        # Fallback for older Pillow versions
        w, h = draw.textsize(title, font=font)
        draw.text((text_center_x - w/2, text_y - h/2), title, fill=main_rgb, font=font)

    # --- 6. PROCESS & PLACE IMAGE ---
    
    # Colorize the cat image
    try:
        cat_img = colorize_image_with_transparency(image_filename, main_rgb)
        
        # Resize logic (Keep aspect ratio, fit within 4 inches width)
        target_img_width = 4 * DPI
        ratio = target_img_width / cat_img.width
        target_img_height = int(cat_img.height * ratio)
        cat_img = cat_img.resize((int(target_img_width), target_img_height), Image.Resampling.LANCZOS)
        
        # Position below title
        img_x = int(text_center_x - (target_img_width / 2))
        img_y = int(text_y + (1 * DPI)) # 1 inch below title
        
        # Paste (Use cat_img as mask for transparency)
        cover.paste(cat_img, (img_x, img_y), cat_img)
        
    except FileNotFoundError:
        print(f"Error: Could not find {image_filename}")

    # --- 7. SAVE AS PDF ---
    cover.save(output_filename, "PDF", resolution=DPI)
    print(f"Cover generated: {output_filename}")

# --- EXECUTION ---

# 1. Create a dummy image if you don't have one
create_dummy_cat_image("cat.png")

# 2. Define your preferences
MY_MAIN_COLOR = "#0047AB" # Cobalt Blue
MY_TITLE = "THINGS I WISH I COULD SAY TO MY CAT WHEN I'M AT WORK"

# 3. Generate
generate_kdp_cover(
    title=MY_TITLE, 
    main_color_hex=MY_MAIN_COLOR, 
    image_filename="cat.png", 
    output_filename="Cover_Blue_Cat.pdf"
)