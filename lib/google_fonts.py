"""
Google Fonts downloader.

Downloads any font from Google Fonts by name, caches locally in assets/fonts/.
Uses the google/fonts GitHub repo for reliable TTF access.
"""

import json
import os
import re
import urllib.request

FONTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts")

# Google Fonts GitHub repo raw base URL
_GITHUB_RAW = "https://raw.githubusercontent.com/google/fonts/main"

# Font directory prefixes in the repo (tried in order)
_REPO_DIRS = ["ofl", "apache", "ufl"]

# Weight name to filename suffix mapping
_WEIGHT_SUFFIXES = {
    "Thin": "Thin",
    "ExtraLight": "ExtraLight",
    "Light": "Light",
    "Regular": "Regular",
    "Medium": "Medium",
    "SemiBold": "SemiBold",
    "Bold": "Bold",
    "ExtraBold": "ExtraBold",
    "Black": "Black",
}


def get_font(font_name, weight="Regular"):
    """
    Get a Google Font by name. Downloads if not cached.

    Args:
        font_name: Google Font family name, e.g. "Roboto", "Vibur", "Pacifico"
        weight: Font weight/style, e.g. "Regular", "Bold", "Italic"

    Returns:
        Absolute path to the .ttf file

    Examples:
        get_font("Roboto")           -> assets/fonts/Roboto-Regular.ttf
        get_font("Vibur")            -> assets/fonts/Vibur-Regular.ttf
        get_font("Roboto", "Bold")   -> assets/fonts/Roboto-Bold.ttf
    """
    os.makedirs(FONTS_DIR, exist_ok=True)

    # Normalize font name (remove spaces for filename)
    clean_name = font_name.replace(" ", "")
    suffix = _WEIGHT_SUFFIXES.get(weight, weight)
    filename = f"{clean_name}-{suffix}.ttf"
    local_path = os.path.join(FONTS_DIR, filename)

    # Return cached version
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        return local_path

    print(f"    Downloading font: {font_name} ({weight}) from Google Fonts...")

    # Strategy 1: Try GitHub repo with common path patterns
    repo_name = font_name.lower().replace(" ", "")
    file_variants = [
        f"{clean_name}-{suffix}.ttf",
        f"{clean_name}[wdth,wght].ttf",       # Variable font
        f"{clean_name}[wght].ttf",             # Variable font (weight only)
        f"{clean_name}-Static-{suffix}.ttf",   # Static variant
    ]

    downloaded = False
    for repo_dir in _REPO_DIRS:
        if downloaded:
            break
        for variant in file_variants:
            url = f"{_GITHUB_RAW}/{repo_dir}/{repo_name}/{variant}"
            try:
                urllib.request.urlretrieve(url, local_path)
                if os.path.getsize(local_path) > 1000:  # Valid font file
                    downloaded = True
                    break
                else:
                    os.remove(local_path)
            except Exception:
                if os.path.exists(local_path):
                    os.remove(local_path)
                continue

    # Strategy 2: Try static subfolder in GitHub repo
    if not downloaded:
        for repo_dir in _REPO_DIRS:
            url = f"{_GITHUB_RAW}/{repo_dir}/{repo_name}/static/{clean_name}-{suffix}.ttf"
            try:
                urllib.request.urlretrieve(url, local_path)
                if os.path.getsize(local_path) > 1000:
                    downloaded = True
                    break
                else:
                    os.remove(local_path)
            except Exception:
                if os.path.exists(local_path):
                    os.remove(local_path)
                continue

    # Strategy 3: Try GitHub API to list files in the font directory
    if not downloaded:
        downloaded = _try_github_api(font_name, repo_name, suffix, local_path)

    if not downloaded:
        raise RuntimeError(
            f"Could not download font '{font_name}' ({weight}). "
            f"Check the name at https://fonts.google.com"
        )

    size_kb = os.path.getsize(local_path) / 1024
    print(f"    Font cached: {filename} ({size_kb:.0f}KB)")
    return local_path


def _try_github_api(font_name, repo_name, suffix, local_path):
    """Last resort: use GitHub API to find the font file."""
    for repo_dir in _REPO_DIRS:
        api_url = f"https://api.github.com/repos/google/fonts/contents/{repo_dir}/{repo_name}"
        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "ghostwriter"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                files = json.loads(resp.read().decode())

            # Find any .ttf file matching our weight
            clean_name = font_name.replace(" ", "")
            for f in files:
                name = f.get("name", "")
                if name.endswith(".ttf") and suffix.lower() in name.lower():
                    urllib.request.urlretrieve(f["download_url"], local_path)
                    if os.path.getsize(local_path) > 1000:
                        return True

            # If no weight match, check static/ subfolder
            for f in files:
                if f.get("name") == "static" and f.get("type") == "dir":
                    static_url = f"{api_url}/static"
                    req2 = urllib.request.Request(static_url, headers={"User-Agent": "ghostwriter"})
                    with urllib.request.urlopen(req2, timeout=10) as resp2:
                        static_files = json.loads(resp2.read().decode())
                    for sf in static_files:
                        sname = sf.get("name", "")
                        if sname.endswith(".ttf") and suffix.lower() in sname.lower():
                            urllib.request.urlretrieve(sf["download_url"], local_path)
                            if os.path.getsize(local_path) > 1000:
                                return True

            # Fallback: grab any .ttf file from the directory
            for f in files:
                name = f.get("name", "")
                if name.endswith(".ttf"):
                    urllib.request.urlretrieve(f["download_url"], local_path)
                    if os.path.getsize(local_path) > 1000:
                        return True

        except Exception:
            continue

    return False


def resolve_font(font_spec):
    """
    Resolve a font specification to a local .ttf file path.

    Accepts:
        - Google Font name: "Roboto", "Vibur", "Pacifico"
        - Google Font with weight: "Roboto:Bold"
        - Local .ttf path: "assets/fonts/MyFont.ttf"
        - System font name: "AmericanTypewriter" (passed through as-is)

    Returns:
        Path to .ttf file, or the font name for system fonts.
    """
    # If it's already a path to an existing .ttf file, use it
    if font_spec.endswith(".ttf") and os.path.exists(font_spec):
        return font_spec

    # If it contains a colon, split into name:weight
    if ":" in font_spec:
        name, weight = font_spec.split(":", 1)
        return get_font(name.strip(), weight.strip())

    # Try as a Google Font name (if it looks like a proper name - capitalized)
    if font_spec[0].isupper() and "/" not in font_spec and "\\" not in font_spec:
        try:
            return get_font(font_spec)
        except RuntimeError:
            # Fall back to treating it as a system font name
            return font_spec

    return font_spec
