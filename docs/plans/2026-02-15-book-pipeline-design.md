# Book Generation & Publishing Pipeline Design

**Date**: 2026-02-15
**Status**: Approved

## Overview

Two-script pipeline for automated KDP notebook/coloring book production:
1. **Generator** (`generate_books.py`) - Creates covers, interiors, and metadata from Python config files
2. **Publisher** (`publish_books.py`) - Automates full KDP publishing flow using Selenium with saved browser session

The scripts are decoupled. The only contract between them is the folder structure and `metadata.json` format.

## Architecture

```
books/                          # Book config files (Python dicts)
  cat_notebook.py

assets/                         # Shared resources
  images/                       # Cover images (kotek.png, etc.)
  fonts/                        # Custom fonts (optional)

books_to_publish/               # Generator output -> Publisher input
  cat-notebook-sage-green/
    cover.pdf
    interior.pdf
    metadata.json

books_published/                # Completed books archive

generate_books.py               # Script 1: The Generator
publish_books.py                # Script 2: The Publisher

lib/                            # Shared modules
  cover_generator.py            # Cover creation (from notebok_cover.py)
  interior_generator.py         # Interior creation (lines, images, etc.)
  kdp_browser.py                # Selenium helpers, KDP page interactions
  formats.py                    # Page format presets (6x9, 8.5x11, etc.)

chrome_profile/                 # Saved browser session (gitignored)
.env                            # Credentials (gitignored)
```

## Book Config Format

Each book template is a Python file in `books/` with a `BOOK` dict:

```python
# books/cat_notebook.py

BOOK = {
    "slug": "cat-notebook",
    "title": "Notebook: Things I'd like to tell my cat when I'm at work",
    "subtitle_template": "version: pages with lines, color: {color_name} PUSZEK EDITION",
    "author_first": "Michal",
    "author_last": "Lipinski",
    "description": """<h2>The Purrrfect Notebook...</h2>...""",
    "keywords": [
        "funny cat lover gifts for women men mom dad",
        "sarcastic coworker leaving gag gift for office",
        "work from home desk accessories essentials wfh",
        "novelty blank lined notebook journal diary pad",
        "crazy cat lady merchandise birthday christmas",
        "cute animal pet owner appreciation present",
    ],
    "categories": [
        "Crafts, Hobbies & Home>Crafts & Hobbies>Activity Books",
        "Self-Help>Journal Writing",
        "Humor & Entertainment>Humor>Cats, Dogs & Animals",
    ],
    "is_low_content": True,
    "is_adult": False,
    "price_usd": 7.99,

    # Cover settings
    "cover": {
        "image": "assets/images/kotek.png",
        "font": "AmericanTypewriter",
        "title_text": "THINGS I'D LIKE TO TELL MY CAT WHEN I'M AT WORK",
    },

    # Interior settings
    "interior": {
        "type": "lines",           # "lines" | "existing_pdf" | "images_folder"
        "format": "6x9",           # "6x9" | "8.5x11" | (w_mm, h_mm) custom
        "pages": 110,
        "line_spacing": 10,        # mm, for "lines" type
        "numbering": False,
    },

    # Color variants - each becomes a separate KDP listing
    "colors": [
        ["#B2AC88", "Sage Green"],
        ["#0047AB", "Cobalt Blue"],
        ["#E2725B", "Terracotta"],
    ],
}
```

### Key config rules:
- Each color variant = separate book on Amazon
- `{color_name}` in `subtitle_template` is replaced per variant
- Everything else is shared across all color variants
- `slug` + color name slug = folder name (e.g., `cat-notebook-sage-green`)

## metadata.json Contract

The generator writes this per book. The publisher reads ONLY this file:

```json
{
    "slug": "cat-notebook-sage-green",
    "title": "Notebook: Things I'd like to tell my cat when I'm at work",
    "subtitle": "version: pages with lines, color: Sage Green PUSZEK EDITION",
    "author_first": "Michal",
    "author_last": "Lipinski",
    "description": "<h2>The Purrrfect Notebook...</h2>...",
    "keywords": ["funny cat lover gifts..."],
    "categories": ["Crafts, Hobbies & Home>Crafts & Hobbies>Activity Books"],
    "is_low_content": true,
    "is_adult": false,
    "price_usd": 7.99,
    "cover_file": "cover.pdf",
    "interior_file": "interior.pdf",
    "generated_at": "2026-02-15T14:30:00",
    "source_config": "books/cat_notebook.py",
    "color_hex": "#B2AC88",
    "color_name": "Sage Green"
}
```

metadata.json is **self-contained**. You can also manually create a book folder with cover.pdf, interior.pdf, and metadata.json - the publisher will handle it without needing a config.

## Interior Generation

Three modes, all respecting configurable page formats:

### Format Presets

| Preset     | Size (mm)        | Use case                    |
|------------|------------------|-----------------------------|
| `"6x9"`    | 152.4 x 228.6   | Notebooks, journals         |
| `"8.5x11"` | 215.9 x 279.4  | Coloring books, activity    |
| `(w, h)`   | Custom tuple     | Anything else               |

### Type 1: `"lines"` - Lined notebook pages
```python
"interior": {
    "type": "lines",
    "format": "6x9",
    "pages": 110,
    "line_spacing": 10,
    "numbering": False,
}
```

### Type 2: `"existing_pdf"` - Pre-made file
```python
"interior": {
    "type": "existing_pdf",
    "path": "assets/Notes_content_6x9.pdf",
}
```
Generator copies the file into the book folder. No processing.

### Type 3: `"images_folder"` - From images (coloring books)
```python
"interior": {
    "type": "images_folder",
    "format": "8.5x11",
    "folder": "assets/cat_coloring_pages/",
    "blank_alternating": True,
    "numbering": True,
}
```
- Images sorted alphabetically, each becomes a full page
- `blank_alternating: true` inserts blank page after each image (prevents bleed-through)
- `numbering: true` adds page numbers at the bottom
- Images auto-scaled to fit format with margins

## Publisher: Full KDP Flow

### Browser setup
- Selenium + Chrome with `--user-data-dir=./chrome_profile`
- User logs in once manually, session persists across runs
- Credentials in `.env` as fallback (never hardcoded)

### Page 1 - Book Details
1. Navigate to `https://kdp.amazon.com/en_US/title-setup/paperback/new/details?type=PRIMARY`
2. Fill: title, subtitle, author first name, author last name
3. Set: not public domain, not adult content
4. Check low content checkbox (if applicable)
5. Fill up to 7 keywords
6. Fill HTML description via CKEditor
7. Open categories modal, select categories
8. Click "Save and Continue"

### Page 2 - Content
1. Set print options (black & white, no bleed, matte)
2. Upload interior PDF via hidden file input
3. Select "Upload a cover you already have"
4. Upload cover PDF via hidden file input
5. Mark "Not AI-generated"
6. Click "Save and Continue"
7. Wait for preview generation (30-60s)
8. Launch previewer, wait for load, close it
9. Click "Approve" preview
10. Click "Save and Continue"

### Page 3 - Pricing
1. Select all territories
2. Set USD price from metadata
3. Click "Publish Your Paperback Book"

### Post-publish
- Move book folder from `books_to_publish/` to `books_published/`
- Add `published_at` timestamp to metadata.json
- Log result to `automation_log.txt`

### Error handling
- If any step fails for a book, skip it
- Log the error with details
- Leave folder in `books_to_publish/` for retry on next run

## Usage

```bash
# 1. Define your book config
#    Edit books/cat_notebook.py

# 2. Generate all color variants
python generate_books.py books/cat_notebook.py

# 3. Publish everything waiting in books_to_publish/
python publish_books.py

# Optional: generate + publish in one go
python generate_books.py books/cat_notebook.py --publish
```

## Security

- Credentials stored in `.env` (gitignored)
- `chrome_profile/` directory gitignored
- No hardcoded passwords in source code

## Migration from current code

- `notebok_cover.py` logic -> `lib/cover_generator.py`
- `notebook_lines.py` logic -> `lib/interior_generator.py`
- `add_notebook.py` variables -> `books/cat_notebook.py` BOOK dict
- `kdp_automation.py` Selenium logic -> `lib/kdp_browser.py` + `publish_books.py`
- Existing covers in `out/` can remain as-is (legacy)
