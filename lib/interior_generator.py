"""
Interior page generator for KDP books.

Supports three modes:
- "lines": Generate lined notebook pages
- "existing_pdf": Copy a pre-made PDF
- "images_folder": Build from a folder of images (coloring books)
"""

import os
import shutil
import glob

from fpdf import FPDF

from lib.formats import resolve_format


class LinedPDF(FPDF):
    """PDF with lined pages for notebooks/journals."""

    def __init__(self, width_mm, height_mm, line_spacing_mm=10, numbering=False):
        super().__init__(orientation='P', unit='mm', format=(width_mm, height_mm))
        self.page_width_mm = width_mm
        self.page_height_mm = height_mm
        self.line_spacing_mm = line_spacing_mm
        self.numbering = numbering
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        pass

    def footer(self):
        if self.numbering:
            self.set_y(-15)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(180)
            self.cell(0, 10, str(self.page_no()), 0, 0, 'C')

    def draw_lines(self):
        self.set_draw_color(200, 200, 200)
        top_margin = 25
        bottom_margin = 25
        left_margin = 15
        right_edge = self.page_width_mm - 15

        y = top_margin
        while y < (self.page_height_mm - bottom_margin):
            self.line(left_margin, y, right_edge, y)
            y += self.line_spacing_mm


class ImagePDF(FPDF):
    """PDF built from a folder of images (for coloring books, etc.)."""

    def __init__(self, width_mm, height_mm, numbering=False):
        super().__init__(orientation='P', unit='mm', format=(width_mm, height_mm))
        self.page_width_mm = width_mm
        self.page_height_mm = height_mm
        self.numbering = numbering
        self.set_auto_page_break(auto=False)

    def header(self):
        pass

    def footer(self):
        if self.numbering:
            self.set_y(-12)
            self.set_font('Arial', 'I', 8)
            self.set_text_color(180)
            self.cell(0, 10, str(self.page_no()), 0, 0, 'C')


def generate_interior(interior_config, output_path):
    """
    Generate or copy an interior PDF based on config.

    Args:
        interior_config: Dict with interior settings from book config
        output_path: Where to save the resulting PDF

    Interior config types:
        {"type": "lines", "format": "6x9", "pages": 110, "line_spacing": 10, "numbering": False}
        {"type": "existing_pdf", "path": "assets/Notes_content_6x9.pdf"}
        {"type": "images_folder", "format": "8.5x11", "folder": "assets/pages/",
         "blank_alternating": True, "numbering": True}
    """
    interior_type = interior_config.get("type", "lines")

    if interior_type == "existing_pdf":
        _generate_existing(interior_config, output_path)
    elif interior_type == "lines":
        _generate_lines(interior_config, output_path)
    elif interior_type == "images_folder":
        _generate_from_images(interior_config, output_path)
    else:
        raise ValueError(f"Unknown interior type: '{interior_type}'. Use 'lines', 'existing_pdf', or 'images_folder'.")

    print(f"  Interior saved: {output_path}")


def _generate_existing(config, output_path):
    """Copy an existing PDF to the output path."""
    source = config.get("path")
    if not source:
        raise ValueError("Interior type 'existing_pdf' requires a 'path' field.")
    if not os.path.exists(source):
        raise FileNotFoundError(f"Interior PDF not found: {source}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    shutil.copy2(source, output_path)


def _generate_lines(config, output_path):
    """Generate a lined notebook interior."""
    fmt = config.get("format", "6x9")
    w_mm, h_mm = resolve_format(fmt)
    pages = config.get("pages", 110)
    line_spacing = config.get("line_spacing", 10)
    numbering = config.get("numbering", False)

    pdf = LinedPDF(w_mm, h_mm, line_spacing_mm=line_spacing, numbering=numbering)

    for _ in range(pages):
        pdf.add_page()
        pdf.draw_lines()

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    pdf.output(output_path)


def _generate_from_images(config, output_path):
    """Generate interior from a folder of images (coloring books)."""
    fmt = config.get("format", "8.5x11")
    w_mm, h_mm = resolve_format(fmt)
    folder = config.get("folder")
    blank_alternating = config.get("blank_alternating", False)
    numbering = config.get("numbering", False)

    if not folder:
        raise ValueError("Interior type 'images_folder' requires a 'folder' field.")
    if not os.path.isdir(folder):
        raise FileNotFoundError(f"Images folder not found: {folder}")

    # Collect image files, sorted alphabetically
    image_extensions = ("*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff", "*.webp")
    image_files = []
    for ext in image_extensions:
        image_files.extend(glob.glob(os.path.join(folder, ext)))
    image_files.sort()

    if not image_files:
        raise ValueError(f"No images found in '{folder}'")

    pdf = ImagePDF(w_mm, h_mm, numbering=numbering)

    # Margins for images
    margin = 10  # mm
    usable_w = w_mm - (2 * margin)
    usable_h = h_mm - (2 * margin) - (10 if numbering else 0)  # extra space for page number

    for img_path in image_files:
        # Add image page
        pdf.add_page()
        _place_image_centered(pdf, img_path, margin, usable_w, usable_h)

        # Add blank page after image if requested
        if blank_alternating:
            pdf.add_page()  # blank page

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    pdf.output(output_path)

    print(f"  Built interior from {len(image_files)} images")


def _place_image_centered(pdf, img_path, margin, usable_w, usable_h):
    """Place an image centered on the page, maintaining aspect ratio."""
    from PIL import Image as PILImage

    with PILImage.open(img_path) as img:
        img_w, img_h = img.size

    aspect = img_w / img_h
    usable_aspect = usable_w / usable_h

    if aspect > usable_aspect:
        # Image is wider - fit to width
        display_w = usable_w
        display_h = usable_w / aspect
    else:
        # Image is taller - fit to height
        display_h = usable_h
        display_w = usable_h * aspect

    x = margin + (usable_w - display_w) / 2
    y = margin + (usable_h - display_h) / 2

    pdf.image(img_path, x=x, y=y, w=display_w, h=display_h)
