#!/usr/bin/env python3
"""
Verification script to check if everything is ready for KDP automation.
Run this before starting the automation to catch any missing files or configuration issues.
"""
import os
from add_notebook import *

def check_file_exists(filepath, description):
    """Check if a file exists and report status."""
    exists = os.path.exists(filepath)
    status = "✓" if exists else "✗"
    print(f"{status} {description}: {filepath}")
    return exists

def main():
    print("=" * 60)
    print("KDP AUTOMATION PRE-FLIGHT CHECK")
    print("=" * 60)

    all_good = True

    # Check interior PDF
    print("\n1. CHECKING INTERIOR PDF:")
    if not check_file_exists(BOOK_CONTENT, "Interior PDF"):
        all_good = False

    # Check cover PDFs
    print("\n2. CHECKING COVER PDFs:")
    colors = [
        "Sage-Green", "Terracotta", "Lavender-Mist", "Dusty-Pink", "Navy-Blue",
        "Periwinkle", "Mint-Green", "Ballet-Slipper", "Lemon-Chiffon", "Mauve",
        "Sky-Blue", "Sand-Beige", "Olive-Green", "Brown-Sugar", "Tan", "Ochre",
        "Slate-Gray", "Hot-Pink", "Electric-Cyan", "Sunset-Orange", "Chartreuse",
        "Electric-Purple", "Charcoal", "Forest-Green", "Burgundy", "Dark-Plum",
        "Cobalt-Blue", "Indigo"
    ]

    missing_covers = []
    for color in colors:
        cover_file = f"out/cat_notebook_cover_{color}.pdf"
        if not check_file_exists(cover_file, f"Cover for {color}"):
            missing_covers.append(color)
            all_good = False

    # Check configuration
    print("\n3. CHECKING CONFIGURATION:")
    print(f"✓ Price: ${PRICE_IN_USD}")
    print(f"✓ Title: {BOOK_TITLE}")
    print(f"✓ Author: {AUTHOR_FIRST_NAME} {AUTHOR_LAST_NAME}")
    print(f"✓ Keywords: {len(KEYWORDS)} keywords")
    print(f"✓ Categories: {len(CATEGORIES)} categories")

    # Summary
    print("\n" + "=" * 60)
    if all_good:
        print("✅ ALL CHECKS PASSED - Ready to run automation!")
        print("\nRun: uv run kdp_automation.py")
    else:
        print("❌ ISSUES FOUND - Fix the following before running:")
        if not os.path.exists(BOOK_CONTENT):
            print(f"   - Missing interior PDF: {BOOK_CONTENT}")
        if missing_covers:
            print(f"   - Missing {len(missing_covers)} cover PDFs:")
            for color in missing_covers[:5]:  # Show first 5
                print(f"     • {color}")
            if len(missing_covers) > 5:
                print(f"     ... and {len(missing_covers) - 5} more")
            print("\n   Run: uv run notebok_cover.py")
    print("=" * 60)

    return all_good

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
