#!/usr/bin/env python3
"""
Book Generator - Script 1 of the KDP Pipeline.

Reads book config files from books/ and generates all color variants
into books_to_publish/ with covers, interiors, and metadata.

Usage:
    python generate_books.py books/cat_notebook.py
    python generate_books.py books/cat_notebook.py --publish
    python generate_books.py books/cat_notebook.py --colors "Sage Green,Cobalt Blue"
"""

import argparse
import importlib.util
import json
import os
import sys
from datetime import datetime

from lib.cover_generator import generate_cover
from lib.interior_generator import generate_interior


OUTPUT_DIR = "books_to_publish"


def load_book_config(config_path):
    """Load a BOOK dict from a Python config file."""
    if not os.path.exists(config_path):
        print(f"Error: Config file not found: {config_path}")
        sys.exit(1)

    spec = importlib.util.spec_from_file_location("book_config", config_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "BOOK"):
        print(f"Error: Config file '{config_path}' must define a BOOK dict.")
        sys.exit(1)

    return module.BOOK


def slugify(text):
    """Convert text to a URL/folder-safe slug."""
    return (
        text.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace("&", "and")
        .replace(",", "")
    )


def generate_single_book(book_config, color_hex, color_name, config_path):
    """Generate a single book variant (cover + interior + metadata)."""
    slug = book_config["slug"]
    color_slug = slugify(color_name)
    book_slug = f"{slug}-{color_slug}"
    book_dir = os.path.join(OUTPUT_DIR, book_slug)

    # Skip if already generated
    metadata_path = os.path.join(book_dir, "metadata.json")
    if os.path.exists(metadata_path):
        print(f"  Skipping {book_slug} (already exists)")
        return book_dir

    os.makedirs(book_dir, exist_ok=True)

    cover_path = os.path.join(book_dir, "cover.pdf")
    interior_path = os.path.join(book_dir, "interior.pdf")

    # Generate cover
    cover_config = book_config.get("cover", {})
    image_path = cover_config.get("image", "assets/images/cat.png")
    font_name = cover_config.get("font", "AmericanTypewriter")
    title_text = cover_config.get("title_text", book_config["title"].upper())
    page_format = book_config.get("interior", {}).get("format", "6x9")

    print(f"  Generating cover...")
    generate_cover(
        title_text=title_text,
        color_hex=color_hex,
        image_path=image_path,
        output_path=cover_path,
        font_name=font_name,
        page_format=page_format,
    )

    # Generate interior
    interior_config = book_config.get("interior", {"type": "lines", "format": "6x9"})
    print(f"  Generating interior ({interior_config.get('type', 'lines')})...")
    generate_interior(interior_config, interior_path)

    # Build subtitle from template
    subtitle_template = book_config.get("subtitle_template", "color: {color_name}")
    subtitle = subtitle_template.replace("{color_name}", color_name)

    # Write metadata
    metadata = {
        "slug": book_slug,
        "title": book_config["title"],
        "subtitle": subtitle,
        "author_first": book_config["author_first"],
        "author_last": book_config["author_last"],
        "description": book_config["description"],
        "keywords": book_config.get("keywords", [])[:7],
        "categories": book_config.get("categories", []),
        "is_low_content": book_config.get("is_low_content", True),
        "is_adult": book_config.get("is_adult", False),
        "price_usd": book_config.get("price_usd", 7.99),
        "cover_file": "cover.pdf",
        "interior_file": "interior.pdf",
        "generated_at": datetime.now().isoformat(),
        "source_config": config_path,
        "color_hex": color_hex,
        "color_name": color_name,
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"  Metadata written: {metadata_path}")
    return book_dir


def main():
    parser = argparse.ArgumentParser(
        description="Generate KDP book variants from a config file."
    )
    parser.add_argument(
        "config",
        help="Path to book config file (e.g., books/cat_notebook.py)"
    )
    parser.add_argument(
        "--colors",
        help="Comma-separated list of color names to generate (default: all)",
        default=None,
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="After generating, run the publisher automatically",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Regenerate even if book folder already exists",
    )
    args = parser.parse_args()

    print(f"Loading config: {args.config}")
    book = load_book_config(args.config)

    colors = book.get("colors", [])
    if not colors:
        print("Error: No colors defined in BOOK config.")
        sys.exit(1)

    # Filter colors if specified
    if args.colors:
        requested = [c.strip().lower() for c in args.colors.split(",")]
        colors = [c for c in colors if c[1].lower() in requested]
        if not colors:
            print(f"Error: No matching colors found. Available: {[c[1] for c in book['colors']]}")
            sys.exit(1)

    print(f"Generating {len(colors)} book variants for '{book['slug']}'...\n")

    generated = []
    for i, (hex_code, color_name) in enumerate(colors):
        print(f"[{i + 1}/{len(colors)}] {color_name} ({hex_code})")

        # Remove existing if --force
        if args.force:
            book_dir = os.path.join(OUTPUT_DIR, f"{book['slug']}-{slugify(color_name)}")
            if os.path.exists(book_dir):
                import shutil
                shutil.rmtree(book_dir)

        try:
            book_dir = generate_single_book(book, hex_code, color_name, args.config)
            generated.append(book_dir)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue

        print()

    print(f"Done! Generated {len(generated)}/{len(colors)} books in '{OUTPUT_DIR}/'")

    if args.publish:
        print("\nStarting publisher...")
        os.system(f"{sys.executable} publish_books.py")


if __name__ == "__main__":
    main()
