"""Convert the design screenshots under ``docs/design`` from PNG to WebP.

PNG is a poor fit for continuous-tone art: the two generated concept images are
1.2-1.3 MB each as PNG while the same pixels take ~85 KB as lossy WebP. Real page
screenshots are the opposite case -- flat fills and sharp glyph edges -- so they
are encoded losslessly, which is still ~65% smaller than PNG and bit-exact
(PSNR inf, max channel difference 0).

The encoding is therefore chosen per file rather than globally:

* ``implemented-*``  real screenshots  -> lossless WebP
* everything else    generated art     -> lossy WebP at quality 92 (PSNR >= 44 dB)

Pixel dimensions are left untouched: these images carry readable UI text, and
downsampling them would be an irreversible loss while WebP already recovers most
of the weight. Run ``--check`` in CI or before a release to prove the tree holds
no PNGs any more.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image

DESIGN_DIR = Path(__file__).resolve().parent.parent / "docs" / "design"
LOSSLESS_PREFIX = "implemented-"
LOSSY_QUALITY = 92


def encoding_for(path: Path) -> dict[str, object]:
    """Lossless for flat UI screenshots, high-quality lossy for rendered art."""
    if path.name.startswith(LOSSLESS_PREFIX):
        return {"lossless": True, "quality": 100, "method": 6}
    return {"quality": LOSSY_QUALITY, "method": 6}


def convert(path: Path) -> tuple[int, int]:
    """Write the WebP sibling and return ``(source bytes, result bytes)``."""
    target = path.with_suffix(".webp")
    with Image.open(path) as image:
        image.load()
        # Every source here is opaque RGB; forcing the mode keeps the encoder
        # from promoting paletted inputs into a needlessly large RGBA output.
        image.convert("RGB").save(target, "WEBP", **encoding_for(path))
    return path.stat().st_size, target.stat().st_size


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="report PNGs still present instead of converting them",
    )
    parser.add_argument(
        "--keep-png",
        action="store_true",
        help="leave the source PNG on disk for manual review",
    )
    args = parser.parse_args(argv)

    pngs = sorted(DESIGN_DIR.rglob("*.png"))
    if not pngs:
        print(f"no PNG under {DESIGN_DIR.relative_to(DESIGN_DIR.parent.parent)}")
        return 0

    if args.check:
        for path in pngs:
            print(f"unconverted: {path.relative_to(DESIGN_DIR.parent.parent)}")
        return 1

    print(f"{'file':34s} {'png':>10s} {'webp':>10s} {'change':>8s}")
    before_total = after_total = 0
    for path in pngs:
        before, after = convert(path)
        before_total += before
        after_total += after
        print(
            f"{path.name:34s} {before / 1024:9.1f}K {after / 1024:9.1f}K "
            f"{(after - before) / before * 100:+7.1f}%"
        )
        if not args.keep_png:
            path.unlink()

    change = (after_total - before_total) / before_total * 100
    print(f"{'total':34s} {before_total / 1024:9.1f}K {after_total / 1024:9.1f}K {change:+7.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
