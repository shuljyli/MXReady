from __future__ import annotations

import html

from mxready.models import ScanReport, calculate_badge_status

COLORS = {
    "static-passed": "#2e7d32",
    "warnings": "#b26a00",
    "blocked": "#b3261e",
    "verified": "#1565c0",
    "verification-stale": "#6b5e00",
    "scan-failed": "#5f6368",
}


def render_badge(report: ScanReport) -> str:
    status = calculate_badge_status(report).value
    label = "MXReady"
    escaped_label = html.escape(label, quote=True)
    escaped_status = html.escape(status, quote=True)
    escaped_accessible_name = html.escape(f"{label}: {status}", quote=True)
    color = COLORS[status]

    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="220" height="20" '
        f'role="img" aria-label="{escaped_accessible_name}">'
        f"<title>{escaped_accessible_name}</title>"
        '<clipPath id="mxready-badge"><rect width="220" height="20" rx="3"/></clipPath>'
        '<g clip-path="url(#mxready-badge)">'
        '<rect width="78" height="20" fill="#424242"/>'
        f'<rect x="78" width="142" height="20" fill="{color}"/>'
        "</g>"
        '<g fill="#fff" text-anchor="middle" '
        'font-family="Verdana,DejaVu Sans,sans-serif" font-size="11">'
        f'<text x="39" y="14">{escaped_label}</text>'
        f'<text x="149" y="14">{escaped_status}</text>'
        "</g>"
        "</svg>"
    )
