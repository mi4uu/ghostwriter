#!/usr/bin/env python3
"""
Book Publisher - Script 2 of the KDP Pipeline.

Scans books_to_publish/ for book folders, automates full KDP publishing,
and moves published books to books_published/.

Usage:
    python publish_books.py
    python publish_books.py --dry-run
    python publish_books.py --book cat-notebook-sage-green
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime

from lib.kdp_browser import (
    setup_driver,
    ensure_logged_in,
    fill_book_details,
    fill_content_page,
    fill_pricing_page,
)


INPUT_DIR = "books_to_publish"
OUTPUT_DIR = "books_published"
LOG_FILE = "automation_log.txt"


def find_books(input_dir, book_filter=None):
    """Find all book folders with valid metadata.json."""
    books = []

    if not os.path.isdir(input_dir):
        print(f"No '{input_dir}' directory found. Generate books first.")
        return books

    for folder_name in sorted(os.listdir(input_dir)):
        folder_path = os.path.join(input_dir, folder_name)

        if not os.path.isdir(folder_path):
            continue

        if book_filter and folder_name != book_filter:
            continue

        metadata_path = os.path.join(folder_path, "metadata.json")
        if not os.path.exists(metadata_path):
            print(f"  Skipping {folder_name} (no metadata.json)")
            continue

        # Check required files exist
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        cover_path = os.path.join(folder_path, metadata.get("cover_file", "cover.pdf"))
        interior_path = os.path.join(folder_path, metadata.get("interior_file", "interior.pdf"))

        if not os.path.exists(cover_path):
            print(f"  Skipping {folder_name} (missing cover: {metadata.get('cover_file')})")
            continue
        if not os.path.exists(interior_path):
            print(f"  Skipping {folder_name} (missing interior: {metadata.get('interior_file')})")
            continue

        books.append((folder_name, folder_path, metadata))

    return books


def move_to_published(book_dir, folder_name, metadata):
    """Move a published book folder to books_published/ and update metadata."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    dest = os.path.join(OUTPUT_DIR, folder_name)

    # If destination already exists (re-publish), remove it
    if os.path.exists(dest):
        shutil.rmtree(dest)

    # Update metadata with publish timestamp
    metadata["published_at"] = datetime.now().isoformat()
    metadata_path = os.path.join(book_dir, "metadata.json")
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    shutil.move(book_dir, dest)
    print(f"  Moved to {dest}")


def log_result(folder_name, success, error=None):
    """Append a result line to the automation log."""
    timestamp = datetime.now().isoformat()
    status = "SUCCESS" if success else "FAILED"
    error_msg = f" - {error}" if error else ""
    line = f"[{timestamp}] {status}: {folder_name}{error_msg}\n"

    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def publish_book(driver, folder_name, book_dir, metadata, dry_run=False):
    """Publish a single book through the full KDP flow."""
    print(f"\nPublishing: {folder_name}")
    print(f"  Title: {metadata['title']}")
    print(f"  Subtitle: {metadata['subtitle']}")
    print(f"  Color: {metadata['color_name']} ({metadata['color_hex']})")

    if dry_run:
        print("  [DRY RUN] Would publish this book. Skipping.")
        return True

    try:
        # Page 1: Book Details
        fill_book_details(driver, metadata)

        # Page 2: Content (uploads + preview)
        fill_content_page(driver, metadata, book_dir)

        # Page 3: Pricing + Publish
        success = fill_pricing_page(driver, metadata)

        if success:
            move_to_published(book_dir, folder_name, metadata)
            log_result(folder_name, True)
            return True
        else:
            log_result(folder_name, False, "Publish button failed")
            return False

    except Exception as e:
        error_msg = str(e)
        print(f"  ERROR: {error_msg}")
        log_result(folder_name, False, error_msg)

        # Take debug screenshot
        try:
            screenshot_path = os.path.join(book_dir, "error_screenshot.png")
            driver.save_screenshot(screenshot_path)
            print(f"  Debug screenshot saved: {screenshot_path}")
        except Exception:
            pass

        return False


def main():
    parser = argparse.ArgumentParser(
        description="Publish books from books_to_publish/ to Amazon KDP."
    )
    parser.add_argument(
        "--book",
        help="Publish only a specific book folder name",
        default=None,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List books that would be published, without actually publishing",
    )
    parser.add_argument(
        "--profile",
        help="Chrome profile directory (default: ./chrome_profile)",
        default="./chrome_profile",
    )
    args = parser.parse_args()

    # Find books to publish
    books = find_books(INPUT_DIR, args.book)

    if not books:
        print("No books ready to publish.")
        sys.exit(0)

    print(f"Found {len(books)} book(s) to publish:")
    for name, _, meta in books:
        print(f"  - {name} ({meta['color_name']})")

    if args.dry_run:
        print("\n[DRY RUN MODE]")

    # Set up browser
    driver = None
    try:
        if not args.dry_run:
            print("\nStarting browser...")
            driver = setup_driver(profile_dir=args.profile)
            ensure_logged_in(driver)

        # Publish each book
        published = 0
        failed = 0

        for folder_name, book_dir, metadata in books:
            success = publish_book(
                driver, folder_name, book_dir, metadata, dry_run=args.dry_run
            )
            if success:
                published += 1
            else:
                failed += 1

        # Summary
        print(f"\n{'=' * 50}")
        print(f"Publishing complete!")
        print(f"  Published: {published}")
        print(f"  Failed: {failed}")
        print(f"  Total: {len(books)}")
        if failed > 0:
            print(f"  Failed books remain in '{INPUT_DIR}/' for retry.")

    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)

    finally:
        if driver:
            print("\nBrowser session kept open for 30 seconds...")
            print("Press Ctrl+C to close immediately, or wait.")
            try:
                import time
                time.sleep(30)
            except KeyboardInterrupt:
                pass
            driver.quit()


if __name__ == "__main__":
    main()
