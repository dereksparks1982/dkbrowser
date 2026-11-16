#!/usr/bin/env python3
"""Prepare approved DK Browser artwork for Linux packaging (requires Pillow)."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    ("en", ROOT / "assets/images/DK Browser Imperial Icon.png"),
    ("ru", ROOT / "assets/images/DK Browser Russian Imperial Icon.png"),
)
SIZES = (16, 24, 32, 48, 64, 128, 256)


def main():
    try:
        from PIL import Image
    except ImportError:
        print("Install Pillow (python3-pil) to generate icons.", file=sys.stderr)
        return 1
    for language, source in SOURCES:
        if not source.is_file():
            print(f"Missing source artwork: {source}", file=sys.stderr)
            return 1
        with Image.open(source) as opened:
            rgba = opened.convert("RGBA")
            for size in SIZES:
                resized = rgba.resize((size, size), Image.Resampling.LANCZOS)
                # English is the default system launcher icon. Keep Russian
                # as a separate resource for localized desktop packaging.
                suffix = "" if language == "en" else "_ru"
                dst = ROOT / "chrome/app/theme/chromium/linux" / f"product_logo_{size}{suffix}.png"
                dst.parent.mkdir(parents=True, exist_ok=True)
                resized.save(dst, format="PNG", optimize=True)
                if language == "en":
                    # Both theme trees contain upstream product logo resources.
                    dst = ROOT / "chrome/app/theme/chromium" / f"product_logo_{size}.png"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    resized.save(dst, format="PNG", optimize=True)
                    if size in (16, 32):
                        dst = (ROOT / "chrome/app/theme/default_100_percent/chromium"
                               / f"product_logo_{size}.png")
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        resized.save(dst, format="PNG", optimize=True)
                print(f"{language} {size}px")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
