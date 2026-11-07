"""Build the phone mock: the page template filled with the book's text, fonts, paper and the desk."""

import base64
import json
import math
import sys
from pathlib import Path

web = Path(sys.argv[1])
here = Path(__file__).parent


def b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def load(name: str):
    return json.loads((web / "public" / name).read_text(encoding="utf-8"))


intro = load("introduction.json")
chapters = load("chapters.json")["chapters"]
finding = next(f for f in load("findings.json")["findings"] if f["key"] == "autumn-advance")
headline = next(h for h in load("headline.json")["headlines"] if h["key"] == "autumn-advance")

# --- The plate: the same basemap, resampling and Mercator band as `book/plate.ts`. ---------------
TOP_LAT, BOTTOM_LAT, SAMPLES, MIN_AREA = 80, -58, 56, 1.5


def mercator(lat: float) -> float:
    return math.log(math.tan(math.pi / 4 + lat * math.pi / 360))


TOP, BOTTOM = mercator(TOP_LAT), mercator(BOTTOM_LAT)


def resample(ring):
    spans = [0.0]
    for a, b in zip(ring, ring[1:]):
        spans.append(spans[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    total = spans[-1] or 1
    out, i = [], 1
    for step in range(SAMPLES):
        target = step / SAMPLES * total
        while i < len(spans) - 1 and spans[i] < target:
            i += 1
        f, t = spans[i - 1], spans[i]
        along = (target - f) / (t - f) if t > f else 0
        a, b = ring[i - 1], ring[i]
        out.append((a[0] + (b[0] - a[0]) * along, a[1] + (b[1] - a[1]) * along))
    return out


def area(points):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]))) / 2


def project(lon, lat):
    lat = max(BOTTOM_LAT, min(TOP_LAT, lat))
    return round((lon + 180) / 360, 4), round((TOP - mercator(lat)) / (TOP - BOTTOM), 4)


rings = []
for feature in load("basemap/land.geojson")["features"]:
    geometry = feature["geometry"]
    parts = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
    for polygon in parts:
        for ring in polygon:
            if len(ring) < 4:
                continue
            points = resample(ring)
            a = area(points)
            if a >= MIN_AREA:
                rings.append((a, [project(x, y) for x, y in points]))
rings.sort(key=lambda r: -r[0])

TABS = [
    ("how-to-read", "Start here", "An animal's year"),
    ("what-changed", "Earlier?", "The calendar moved"),
    ("why-it-changed", "Why?", "Whose hand is on the clock"),
    ("what-did-not", "Elsewhere?", "But the map stayed put"),
    ("no-average-animal", "Who decides?", "There is no average animal"),
    ("can-be-predicted", "Next year?", "What about next year?"),
    ("cannot-see", "Blind spots", "What we cannot see"),
    ("the-world", "The globe", "The world"),
]

# The audit's reader words, as `web/src/lib/ledger.ts` prints them.
DOMAINS = {
    "geographic": "Where it was measured",
    "temporal": "When, and for how long",
    "taxonomic": "Which animals",
    "environmental": "Which habitats",
    "detectability": "Whether it could be seen",
    "phenological": "Which part of the year",
}
STATUSES = {"addressed": "tested, and held", "bounded": "limited, and said so", "open": "still open"}

data = {
    "intro": intro,
    "calendar": {"title": "The calendar moved", **chapters["what-changed"]},
    "finding": {
        **{k: finding[k] for k in (
            "plain", "matters", "plain_how", "plain_caveat", "value", "scope", "claim", "caveat", "supporting",
        )},
        "bias": [
            {"domain": DOMAINS[b["domain"]], "status": b["status"], "verdict": STATUSES[b["status"]], "text": b["finding"]}
            for b in finding["bias"]
        ],
        "chart": {
            "title": headline["title"],
            "reading": headline["reading"],
            "label": headline["chart"]["series"][0]["label"],
            "points": headline["chart"]["series"][0]["points"],
            "trend": headline["chart"]["series"][0]["trend"],
        },
        "plate": {
            "rings": [points for _, points in rings],
            "center": project(-96, 42),
            # `story.ts` VIEWS["autumn-advance"].because, and the legend `Plate.svelte` prints.
            "caption": "The band the claim is made in: the middle of the United States, between 37 and 50 "
            "degrees north, where the radar stations sit.",
            "legend": ["The ground this claim is about", "Coastlines", "Grid lines, every 30 degrees"],
            "elsewhere": "The records themselves are drawn on the globe, in the last chapter.",
            "aspect": round(2 * math.pi / (TOP - BOTTOM), 4),
            "meridians": [round((lon + 180) / 360, 4) for lon in range(-150, 180, 30)],
            "parallels": [project(0, lat)[1] for lat in (60, 30, 0, -30)],
        },
    },
    "openers": [
        {"tab": i, "title": title, "question": chapters[slug]["question"], "paragraph": chapters[slug]["paragraphs"][0]}
        for i, (slug, _, title) in enumerate(TABS)
        if slug in chapters and slug != "what-changed"
    ],
    "chapters": [
        {"tab": tab, "title": title, "question": chapters[slug]["question"] if slug in chapters else title}
        for slug, tab, title in TABS
    ],
}

html = (here / "page.html").read_text(encoding="utf-8")
html = html.replace("{{VIRGIL}}", b64(web / "src/assets/fonts/Virgil.woff2"))
html = html.replace("{{EXCALIFONT}}", b64(web / "src/assets/fonts/Excalifont.woff2"))
html = html.replace("{{OPENDYSLEXIC}}", b64(web / "src/assets/fonts/OpenDyslexic.woff2"))
html = html.replace("{{FIBRE}}", b64(web / "src/assets/paper/fibre.webp"))
html = html.replace("{{ROUGH}}", b64(web / "src/assets/paper/rough.webp"))
desk_assets = here / "assets"
deskjs = (desk_assets / "desk.js").read_text(encoding="utf-8")
assert "</script" not in deskjs.lower()
html = html.replace("{{DESKJS}}", deskjs)
html = html.replace("{{DESKFILES}}", json.dumps({name: b64(desk_assets / name) for name in (
    "brass_candleholders.glb", "seadogs_compass.glb", "magnifying_glass_01.glb", "wood_diff.webp", "wood_nor.webp")}))
html = html.replace("{{DATA}}", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
with open(here / "assets" / "phone-desk.html", "w", encoding="utf-8", newline="\n") as out:
    out.write(html)
with open(here / "assets" / "phone-desk-local.html", "w", encoding="utf-8", newline="\n") as out:
    out.write('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" '
              'content="width=device-width,initial-scale=1,viewport-fit=cover"></head><body>')
    out.write(html)
    out.write("</body></html>")
print(f"phone-desk.html written, {len(html) // 1024} KB, {len(rings)} coast rings")
