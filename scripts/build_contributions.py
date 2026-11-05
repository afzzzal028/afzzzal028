"""Build an orange contribution heatmap SVG from real GitHub contribution data.

Usage:  python scripts/build_contributions.py
Requires: authenticated `gh` CLI.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "contributions.svg"

QUERY = (
    "query { viewer { contributionsCollection { contributionCalendar { "
    "totalContributions weeks { contributionDays { date contributionCount weekday } } "
    "} } } }"
)

W, H = 1200, 230
LEFT, TOP = 86, 62
CELL, PITCH = 14, 19
BG = "#080B12"
BORDER = "#17304F"
EMPTY = "#10161F"
LEVELS = ["#10161F", "#3D1A08", "#7A2E08", "#C24A0A", "#FF6B1A"]
BLUE = "#4C9AFF"
MUTED = "#6B7280"
DIM = "#7C8CA3"

BAT = (
    "M0,18 C-6,18 -12,14 -22,15 C-34,16 -42,10 -52,9 C-47,15 -46,21 -38,25 "
    "C-46,27 -52,26 -58,29 C-47,32 -38,38 -28,36 C-20,35 -12,40 -6,47 "
    "C-4,40 -2,36 0,36 C2,36 4,40 6,47 C12,40 20,35 28,36 C38,38 47,32 58,29 "
    "C52,26 46,27 38,25 C46,21 47,15 52,9 C42,10 34,16 22,15 C12,14 6,18 0,18 Z"
)


def fetch_calendar() -> dict:
    gh = shutil.which("gh")
    if not gh:
        raise SystemExit("gh CLI not found on PATH")
    raw = subprocess.check_output(
        [gh, "api", "graphql", "-f", f"query={QUERY}"], text=True, encoding="utf-8"
    )
    payload = json.loads(raw)
    if "errors" in payload:
        raise SystemExit(payload["errors"])
    return payload["data"]["viewer"]["contributionsCollection"]["contributionCalendar"]


def level_for(count: int, cuts: tuple[int, int, int]) -> int:
    if count == 0:
        return 0
    if count <= cuts[0]:
        return 1
    if count <= cuts[1]:
        return 2
    if count <= cuts[2]:
        return 3
    return 4


def month_label(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%b").upper()


def main() -> None:
    calendar = fetch_calendar()
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]
    all_days = [d for w in weeks for d in w["contributionDays"]]
    counts = [d["contributionCount"] for d in all_days]
    nz = sorted(c for c in counts if c > 0)

    def pct(p: float) -> int:
        if not nz:
            return 1
        return nz[min(len(nz) - 1, int(len(nz) * p))]

    cuts = (max(1, pct(0.45)), max(2, pct(0.75)), max(3, pct(0.92)))

    graph_w = (len(weeks) - 1) * PITCH + CELL
    first = all_days[0]["date"]
    last = all_days[-1]["date"]
    span = f"{date.fromisoformat(first).strftime('%b %Y').upper()} – {date.fromisoformat(last).strftime('%b %Y').upper()}"

    parts: list[str] = []
    add = parts.append
    add(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
        f'role="img" aria-label="Orange contribution heatmap: {total} contributions from {span}">'
    )
    add(
        "<defs>"
        '<linearGradient id="edge" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0" stop-color="#2F81F7"/><stop offset="0.78" stop-color="#2F81F7"/>'
        '<stop offset="1" stop-color="#FF6B1A"/></linearGradient>'
        '<radialGradient id="heat" cx="0.5" cy="0.5" r="0.5">'
        '<stop offset="0" stop-color="#FF6B1A" stop-opacity="0.10"/>'
        '<stop offset="1" stop-color="#FF6B1A" stop-opacity="0"/></radialGradient>'
        "</defs>"
    )
    add(f'<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="14" fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>')
    add(f'<rect x="14" y="1" width="{W - 28}" height="2" rx="1" fill="url(#edge)" opacity="0.9"/>')
    add(f'<circle cx="1160" cy="0" r="200" fill="url(#heat)"/>')

    # header
    add(f'<g transform="translate(44,30) scale(0.14)"><path d="{BAT}" fill="{BLUE}" opacity="0.9"/></g>')
    add(
        f'<text x="62" y="39" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
        f'font-size="13" font-weight="600" letter-spacing="2" fill="{BLUE}">CONTRIBUTION GRID</text>'
    )
    add(
        f'<text x="1164" y="39" text-anchor="end" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
        f'font-size="10" letter-spacing="1.5" fill="{DIM}">{total} CONTRIBUTIONS · {span}</text>'
    )

    # month labels
    last_label_x = -100
    for i, week in enumerate(weeks):
        label = month_label(week["contributionDays"][0]["date"])
        if i == 0 or label != month_label(weeks[i - 1]["contributionDays"][0]["date"]):
            x = LEFT + i * PITCH
            if x - last_label_x >= 34:
                add(
                    f'<text x="{x}" y="{TOP - 10}" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
                    f'font-size="9" letter-spacing="0.6" fill="{MUTED}">{label}</text>'
                )
                last_label_x = x

    # weekday labels
    for row, name in ((1, "MON"), (3, "WED"), (5, "FRI")):
        add(
            f'<text x="{LEFT - 10}" y="{TOP + row * PITCH + CELL - 3}" text-anchor="end" '
            f'font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" font-size="9" '
            f'letter-spacing="0.4" fill="{MUTED}">{name}</text>'
        )

    # cells
    for i, week in enumerate(weeks):
        for day in week["contributionDays"]:
            x = LEFT + i * PITCH
            y = TOP + int(day["weekday"]) * PITCH
            fill = LEVELS[level_for(day["contributionCount"], cuts)]
            add(
                f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{fill}">'
                f'<title>{day["date"]}: {day["contributionCount"]} contribution(s)</title></rect>'
            )

    # legend
    add(
        f'<text x="1010" y="216" text-anchor="end" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
        f'font-size="9.5" fill="{MUTED}">Less</text>'
    )
    for i, fill in enumerate(LEVELS):
        add(f'<rect x="{1022 + i * 14}" y="206" width="10" height="10" rx="2" fill="{fill}"/>')
    add(
        f'<text x="1100" y="216" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
        f'font-size="9.5" fill="{MUTED}">More</text>'
    )

    # subtle footer note
    add(
        f'<text x="36" y="216" font-family="\'Segoe UI\', \'Helvetica Neue\', Arial, sans-serif" '
        f'font-size="9.5" letter-spacing="1.4" fill="{MUTED}">GOTHAM NEVER SLEEPS</text>'
    )

    add("</svg>")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"wrote {OUT} | {total} contributions | {len(weeks)} weeks | cuts={cuts} | graph_w={graph_w}")


if __name__ == "__main__":
    main()
