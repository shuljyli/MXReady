"""Keep exported SVG glyphs on the same cell grid as the live terminal."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from rich.cells import cell_len

_SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", _SVG)


def align_svg_cells(svg: str, *, columns: int) -> str:
    """Normalize Rich's generated SVG; never patch its terminal width calculations.

    Rich positions runs in terminal cells but sets their textLength using len(text).
    CJK therefore gets compressed into one column in SVG viewers. Explicit glyph
    positions also prevent fallback fonts from shifting mixed Latin/CJK runs.
    """
    if columns < 1:
        raise ValueError("Screenshot columns must be positive")
    root = ET.fromstring(svg)
    # The exported line clip rectangles span the full terminal width. Derive the
    # cell advance from this geometry instead of assuming a font or pixel size.
    cell_width = None
    for clip in root.iter(f"{{{_SVG}}}clipPath"):
        if "-line-" in clip.get("id", ""):
            rect = clip.find(f"{{{_SVG}}}rect")
            if rect is not None:
                cell_width = float(rect.attrib["width"]) / columns
                break
    if cell_width is None:
        raise ValueError("Screenshot SVG has no terminal cell geometry")
    for node in root.iter(f"{{{_SVG}}}text"):
        if "textLength" not in node.attrib or len(node):
            continue  # Leave the window title and already-positioned spans alone.
        text = node.text or ""
        x = float(node.attrib["x"])
        node.attrib.pop("textLength")
        node.text = None
        glyphs: list[str] = []
        for character in text:
            if glyphs and (cell_len(character) == 0 or glyphs[-1].endswith("\u200d")):
                glyphs[-1] += character
            else:
                glyphs.append(character)
        for glyph in glyphs:
            advance = cell_width * cell_len(glyph)
            attributes = {"x": f"{x:.6f}"}
            if advance:
                attributes.update(textLength=f"{advance:.6f}", lengthAdjust="spacingAndGlyphs")
            ET.SubElement(node, f"{{{_SVG}}}tspan", attributes).text = glyph
            x += advance
    return ET.tostring(root, encoding="unicode")
