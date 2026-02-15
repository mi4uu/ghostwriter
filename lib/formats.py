"""Page format presets for KDP books."""

# Format presets: (width_mm, height_mm)
PRESETS = {
    "5x8":     (127.0, 203.2),
    "5.25x8":  (133.35, 203.2),
    "5.5x8.5": (139.7, 215.9),
    "6x9":     (152.4, 228.6),
    "6.14x9.21": (155.956, 233.934),
    "6.69x9.61": (169.926, 244.094),
    "7x10":    (177.8, 254.0),
    "7.5x9.25": (190.5, 234.95),
    "8x10":    (203.2, 254.0),
    "8.25x6":  (209.55, 152.4),
    "8.25x8.25": (209.55, 209.55),
    "8.5x8.5": (215.9, 215.9),
    "8.5x11":  (215.9, 279.4),
}

# DPI for cover generation (print quality)
COVER_DPI = 300


def resolve_format(fmt):
    """
    Resolve a format specification to (width_mm, height_mm).

    Args:
        fmt: Either a preset string like "6x9" or a tuple (width_mm, height_mm)

    Returns:
        Tuple of (width_mm, height_mm)

    Raises:
        ValueError: If format string is not a known preset
    """
    if isinstance(fmt, (list, tuple)) and len(fmt) == 2:
        return (float(fmt[0]), float(fmt[1]))
    if isinstance(fmt, str):
        if fmt in PRESETS:
            return PRESETS[fmt]
        raise ValueError(
            f"Unknown format preset '{fmt}'. "
            f"Available: {', '.join(sorted(PRESETS.keys()))}. "
            f"Or pass a tuple: (width_mm, height_mm)"
        )
    raise ValueError(f"Invalid format: {fmt}. Use a preset string or (w_mm, h_mm) tuple.")


def format_to_inches(fmt):
    """Resolve format and return as (width_inches, height_inches)."""
    w_mm, h_mm = resolve_format(fmt)
    return (w_mm / 25.4, h_mm / 25.4)


def format_to_pixels(fmt, dpi=COVER_DPI):
    """Resolve format and return as (width_px, height_px) at given DPI."""
    w_in, h_in = format_to_inches(fmt)
    return (int(w_in * dpi), int(h_in * dpi))
