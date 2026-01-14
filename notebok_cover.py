from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageColor
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
        # Nose (Lighter Gray to show detail preservation)
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

def colorize_grayscale_image(image_path, target_color):
    """
    Preserves grayscale details (shading) but tints the image 
    towards the target color (Duotone effect).
    """
    # 1. Load and prepare
    src_img = Image.open(image_path).convert("RGBA")
    
    # Extract the Alpha channel to re-apply later
    alpha = src_img.getchannel('A')
    
    # 2. Convert to Grayscale (L) for the base structure
    gray_img = src_img.convert('L')
    
    # 3. Colorize (Map Black->Black, White->Target Color)
    # This keeps shadows dark and highlights colored, preserving detail.
    # You can swap black="black" to black=target_color if you want it lighter.
    colorized_rgb = ImageOps.colorize(gray_img, white="white", black=target_color)
    # colorized_rgb = ImageOps.colorize(gray_img, black="black", white=target_color)
    # colorized_rgb = ImageOps.colorize(gray_img, black=target_color, white=target_color)

    # 4. Re-apply transparency
    colorized_rgb.putalpha(alpha)
    
    return colorized_rgb

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
        # Get width of test line
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
    line_height = font.size * 1.2 # 1.2 is standard line spacing
    
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_width = bbox[2] - bbox[0]
        # Draw centered
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
    
    # --- 3. DRAW GEOMETRY (Spine & Border) ---
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
    
    # --- 4. DRAW TITLE (Wrapped) ---
    try:
        # AmericanTypewriter is standard on macOS, but might fail on Linux/Windows
        font_path = "AmericanTypewriter" 
        font_size = 100 # Slightly smaller to accommodate long titles
        font = ImageFont.truetype(font_path, font_size)
    except IOError:
        # Fallback to standard arial or default
        try:
            font = ImageFont.truetype("arial.ttf", 100)
        except IOError:
            font = ImageFont.load_default()
            print("Warning: Custom fonts not found. Using default.")

    # Define text area (Right of the strip, Left of the edge)
    text_area_width = PAGE_WIDTH - strip_width - (0.5 * DPI) # 0.5 inch padding
    text_center_x = front_start_x + strip_width + (text_area_width / 2)
    text_start_y = 1.5 * DPI
    
    # Draw text and get the Y position where it finished
    text_end_y = draw_wrapped_text(
        draw, title, font, 
        max_width=text_area_width, 
        start_y=text_start_y, 
        center_x=text_center_x, 
        color=main_rgb
    )

    # --- 5. DRAW IMAGE (Preserving Detail) ---
    try:
        # Use the new colorize function
        cat_img = colorize_grayscale_image(image_filename, main_rgb)
        
        # Resize Logic
        target_img_width = 4 * DPI
        ratio = target_img_width / cat_img.width
        target_img_height = int(cat_img.height * ratio)
        
        cat_img = cat_img.resize((int(target_img_width), target_img_height), Image.Resampling.LANCZOS)
        
        # Position Image (1 inch below the last line of text)
        img_x = int(text_center_x - (target_img_width / 2))
        img_y = int(text_end_y + (0.5 * DPI)) 
        
        # Paste with transparency
        cover.paste(cat_img, (img_x, img_y), cat_img)
        
    except FileNotFoundError:
        print(f"Error: Could not find {image_filename}")

    # --- 6. SAVE ---
    cover.save(output_filename, "PDF", resolution=DPI)
    print(f"Success! Cover generated: {output_filename}")

# --- EXECUTION ---

# 1. Setup
create_dummy_cat_image("cat.png")

# 2. Config
MY_MAIN_COLOR = "#0047AB" # Cobalt Blue
# MY_TITLE = "THINGS I WISH I COULD SAY TO MY CAT WHEN I'M AT WORK"
MY_TITLE = "Things I’d like to tell my cat when I’m at work".upper()

# 3. Run
# generate_kdp_cover(
#     title=MY_TITLE, 
#     main_color_hex=MY_MAIN_COLOR, 
#     image_filename="lines.png", 
#     output_filename="Cover_Smart_Wrapped.pdf"
# )
COLORS=[["#0047AB","Cobalt Blue"],
        ["#7b7b7b","Gray"],
        ["#7bc4c4","AQUA SKY"],
        ["#a07bc4","Amethyst"],
        ["#c47b7b","Old Rose"],
        ["#007b7b","Teal"],
        ["#a0c47b","Sage Green"],
        ["#0099cc","Bondi Blue"],
        ["#ffcc00","Tangerine Yellow"]
        ]
for [MY_MAIN_COLOR,COLOR_NAME] in COLORS:
    generate_kdp_cover(
        title=MY_TITLE, 
        main_color_hex=MY_MAIN_COLOR, 
        image_filename="lines.png", 
        output_filename="out/cat_notebook_cover_COLOR.pdf".replace("COLOR",COLOR_NAME.replace(" ","-"))
    )