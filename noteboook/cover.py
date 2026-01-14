from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageColor, ImageChops
import colorsys
import os
import textwrap

def create_dummy_cat_image(filename="cat.png"):
    """Creates a temporary transparent PNG with a cat shape for testing."""
    if not os.path.exists(filename):
        img = Image.new("RGBA", (500, 500), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Draw a crude cat face with shading (grayscale)
        # Head (Dark Gray)
        draw.ellipse([(100, 100), (400, 400)], fill=(80, 80, 80, 255)) 
        # Nose (Lighter Gray)
        draw.ellipse([(230, 250), (270, 280)], fill=(180, 180, 180, 255)) 
        # Ears
        draw.polygon([(100, 150), (50, 50), (150, 100)], fill=(80, 80, 80, 255)) 
        draw.polygon([(350, 100), (450, 50), (400, 150)], fill=(80, 80, 80, 255)) 
        img.save(filename)
        print(f"Created dummy image: {filename}")

def adjust_lightness(hex_color, factor):
    """Adjusts the lightness of a HEX color."""
    rgb = ImageColor.getrgb(hex_color)
    h, l, s = colorsys.rgb_to_hls(rgb[0]/255, rgb[1]/255, rgb[2]/255)
    new_l = max(0, min(1, l * factor))
    new_rgb = colorsys.hls_to_rgb(h, new_l, s)
    return tuple(int(x * 255) for x in new_rgb)

def draw_wrapped_text(draw, text, font, max_width, start_y, center_x, color):
    """
    Splits text into lines that fit within max_width and draws them centered.
    Returns the Y coordinate where the text ended.
    """
    lines = []
    words = text.split()
    current_line = []
    
    # 1. Calculate lines
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
    
    # 2. Draw lines
    current_y = start_y
    line_height = font.size * 1.2 
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        draw.text((center_x - line_width / 2, current_y), line, font=font, fill=color)
        current_y += line_height
        
    return current_y

def generate_kdp_cover(title, main_color_hex, image_filename, output_filename):
    # --- 1. CONFIGURATION ---
    DPI = 300
    PAGE_WIDTH = 6 * DPI
    PAGE_HEIGHT = 9 * DPI
    BLEED = 0.125 * DPI
    SPINE_WIDTH = 0.25 * DPI 
    
    TOTAL_WIDTH = int((PAGE_WIDTH * 2) + SPINE_WIDTH + (BLEED * 2))
    TOTAL_HEIGHT = int(PAGE_HEIGHT + (BLEED * 2))
    
    main_rgb = ImageColor.getrgb(main_color_hex)
    bg_rgb = adjust_lightness(main_color_hex, 1.8) 
    border_rgb = adjust_lightness(main_color_hex, 1.3)

    # --- 2. CREATE BACKGROUND ---
    cover = Image.new("RGB", (TOTAL_WIDTH, TOTAL_HEIGHT), bg_rgb)
    draw = ImageDraw.Draw(cover)
    
    # Calculate Front Cover Start (Right side)
    front_start_x = int(BLEED + PAGE_WIDTH + SPINE_WIDTH)
    
    # --- 3. DRAW GEOMETRY ---
    # Spine
    spine_x1 = int(BLEED + PAGE_WIDTH)
    spine_x2 = int(spine_x1 + SPINE_WIDTH)
    draw.rectangle([spine_x1, 0, spine_x2, TOTAL_HEIGHT], fill=border_rgb)
    
    # Left Border on Front Cover
    strip_width = 0.8 * DPI
    draw.rectangle(
        [front_start_x, 0, front_start_x + strip_width, TOTAL_HEIGHT], 
        fill=border_rgb
    )
    
    # --- 4. DRAW TITLE ---
    try:
        font_path = "AmericanTypewriter" 
        font_size = 100 
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        try:
            font = ImageFont.truetype("arial.ttf", 100)
        except IOError:
            font = ImageFont.load_default()
            print("Warning: Custom fonts not found. Using default.")

    text_area_width = PAGE_WIDTH - strip_width - (0.5 * DPI)
    text_center_x = front_start_x + strip_width + (text_area_width / 2)
    text_start_y = 1.5 * DPI
    
    text_end_y = draw_wrapped_text(
        draw, title, font, 
        max_width=text_area_width, 
        start_y=text_start_y, 
        center_x=text_center_x, 
        color=main_rgb
    )

    # --- 5. PASTE IMAGE AS MULTIPLY ---
    try:
        # A. Load original
        cat_img = Image.open(image_filename).convert("RGBA")
        
        # B. Resize logic
        target_img_width = 4 * DPI
        ratio = target_img_width / cat_img.width
        target_img_height = int(cat_img.height * ratio)
        cat_img = cat_img.resize((int(target_img_width), target_img_height), Image.Resampling.LANCZOS)
        
        # C. Prepare coordinates
        img_x = int(text_center_x - (target_img_width / 2))
        img_y = int(text_end_y + (0.5 * DPI)) 
        box = (img_x, img_y, img_x + cat_img.width, img_y + cat_img.height)

        # D. PREPARE MULTIPLY EFFECT
        # 1. Extract Alpha mask to restore transparency edges later if needed
        alpha_mask = cat_img.split()[3]
        
        # 2. Flatten cat onto WHITE background. 
        # In 'Multiply' mode, White is transparent (1.0 * Background = Background).
        # This handles the transparency in your PNG cleanly.
        cat_on_white = Image.new("RGB", cat_img.size, (255, 255, 255))
        cat_on_white.paste(cat_img, mask=alpha_mask)
        
        # 3. Crop the existing background from the cover where the image will go
        bg_crop = cover.crop(box)
        
        # 4. Perform the Multiply Blend
        # Formula: (Source * Destination) / 255
        multiplied_img = ImageChops.multiply(bg_crop, cat_on_white)
        
        # 5. Paste the result back onto the cover
        # We can paste directly, or use alpha_mask if we want to be super strict about edges,
        # but since we multiplied with white, the "transparent" areas are already mathematically identical to the background.
        cover.paste(multiplied_img, box)
        
    except FileNotFoundError:
        print(f"Error: Could not find {image_filename}")

    # --- 6. SAVE ---
    if not os.path.exists("out"):
        os.makedirs("out")
    cover.save(output_filename, "PDF", resolution=DPI)
    print(f"Success! Cover generated: {output_filename}")

# --- EXECUTION ---

# 1. Setup
create_dummy_cat_image("cat.png")

# 2. Config
MY_MAIN_COLOR = "#0047AB" # Cobalt Blue
MY_TITLE = "Things I’d like to tell my cat when I’m at work".upper()

# 3. Run
generate_kdp_cover(
    title=MY_TITLE, 
    main_color_hex=MY_MAIN_COLOR, 
    image_filename="lines.png", 
    output_filename="out/Cover_Multiply.pdf"
)