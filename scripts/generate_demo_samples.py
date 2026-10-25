"""Generate deterministic, clearly synthetic OrbitalPulse demo image pairs.

Uses only Python's standard library. These are illustrative computer-generated
scenes, not satellite observations and not suitable for geospatial inference.
"""

from __future__ import annotations

import json
import math
import random
import struct
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1] / "data" / "samples"
WIDTH, HEIGHT = 640, 448


def base_scene() -> list[bytearray]:
    rng = random.Random(481516)
    rows = []
    for y in range(HEIGHT):
        row = bytearray(WIDTH * 3)
        for x in range(WIDTH):
            ridges = math.sin((x + y * 0.65) / 39) * 6 + math.sin((x - y * 0.4) / 83) * 8
            noise = rng.randrange(-5, 6)
            value = int(151 + ridges + noise - y * 0.028)
            index = x * 3
            row[index:index + 3] = bytes((value + 12, value + 2, value - 18))
        rows.append(row)
    return rows


def clone(rows: list[bytearray]) -> list[bytearray]:
    return [bytearray(row) for row in rows]


def fill_ellipse(rows: list[bytearray], cx: int, cy: int, rx: int, ry: int, rgb: tuple[int, int, int]) -> None:
    for y in range(max(0, cy - ry), min(HEIGHT, cy + ry + 1)):
        ratio = 1 - ((y - cy) / ry) ** 2
        if ratio <= 0:
            continue
        dx = int(rx * math.sqrt(ratio))
        for x in range(max(0, cx - dx), min(WIDTH, cx + dx + 1)):
            index = x * 3
            rows[y][index:index + 3] = bytes(rgb)


def fill_polygon(rows: list[bytearray], points: list[tuple[int, int]], rgb: tuple[int, int, int]) -> None:
    min_y = max(0, min(y for _, y in points))
    max_y = min(HEIGHT - 1, max(y for _, y in points))
    for y in range(min_y, max_y + 1):
        intersections = []
        for index, (x1, y1) in enumerate(points):
            x2, y2 = points[(index + 1) % len(points)]
            if (y1 <= y < y2) or (y2 <= y < y1):
                intersections.append(int(x1 + (y - y1) * (x2 - x1) / (y2 - y1)))
        intersections.sort()
        for left, right in zip(intersections[0::2], intersections[1::2]):
            for x in range(max(0, left), min(WIDTH, right + 1)):
                offset = x * 3
                rows[y][offset:offset + 3] = bytes(rgb)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def save_png(path: Path, rows: list[bytearray]) -> None:
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack(">IIBBBBB", WIDTH, HEIGHT, 8, 2, 0, 0, 0)
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", header) + png_chunk(b"IDAT", zlib.compress(raw, 9)) + png_chunk(b"IEND", b""))


def make_scenarios() -> list[dict[str, str]]:
    scenarios = []

    # Vegetation loss: healthy scrub is replaced by exposed dry soil in a broad clearing.
    before = base_scene()
    for cx, cy, rx, ry in [(160, 155, 80, 55), (278, 169, 77, 58), (205, 247, 67, 44), (394, 127, 52, 36)]:
        fill_ellipse(before, cx, cy, rx, ry, (64, 119, 74))
        fill_ellipse(before, cx - 8, cy - 6, rx // 2, ry // 2, (76, 133, 83))
    after = clone(before)
    fill_polygon(after, [(89, 122), (278, 103), (343, 170), (305, 254), (153, 280), (87, 215)], (174, 113, 76))
    fill_polygon(after, [(112, 150), (257, 128), (301, 173), (273, 224), (161, 247), (112, 207)], (191, 130, 88))
    scenarios.append({"id": "vegetation-loss", "title": "Vegetation loss", "category": "VEGETATION LOSS", "description": "Synthetic scrubland with a broad cleared patch exposing dry soil.", "expected_change": "Large connected clearing with a strong vegetation-to-soil pixel delta."})
    write_pair(scenarios[-1], before, after)

    # New construction: a building pad and access road appear on previously undisturbed ground.
    before = base_scene()
    after = clone(before)
    fill_polygon(after, [(352, 100), (535, 100), (535, 238), (352, 238)], (193, 174, 141))
    fill_polygon(after, [(373, 119), (508, 119), (508, 220), (373, 220)], (75, 85, 92))
    for x in (390, 438, 486):
        fill_polygon(after, [(x, 134), (x + 28, 134), (x + 28, 204), (x, 204)], (164, 168, 159))
    fill_polygon(after, [(376, 237), (403, 237), (315, 382), (285, 382)], (102, 98, 88))
    fill_polygon(after, [(385, 236), (391, 236), (307, 382), (300, 382)], (219, 205, 163))
    scenarios.append({"id": "new-construction", "title": "New construction & land disturbance", "category": "CONSTRUCTION", "description": "Synthetic undeveloped terrain with a new building pad, structures, and graded access road.", "expected_change": "Several connected construction surfaces and a linear access-road disturbance."})
    write_pair(scenarios[-1], before, after)

    # Flood-like expansion: a dark water body advances over synthetic dry terrain.
    before = base_scene()
    fill_polygon(before, [(0, 315), (65, 302), (128, 313), (184, 298), (247, 315), (315, 302), (376, 323), (445, 306), (505, 319), (570, 302), (640, 318), (640, 448), (0, 448)], (104, 123, 125))
    after = clone(before)
    fill_polygon(after, [(0, 254), (68, 266), (132, 245), (196, 263), (257, 248), (321, 271), (385, 251), (448, 270), (510, 249), (574, 264), (640, 245), (640, 448), (0, 448)], (48, 101, 129))
    fill_polygon(after, [(0, 331), (110, 324), (192, 338), (284, 326), (389, 343), (484, 329), (571, 340), (640, 327), (640, 448), (0, 448)], (39, 87, 112))
    scenarios.append({"id": "flood-expansion", "title": "Flood-like water expansion", "category": "WATER EXPANSION", "description": "Synthetic dry channel and floodplain with a wider, deeper blue water footprint in the later frame.", "expected_change": "A broad connected water expansion across the lower image area."})
    write_pair(scenarios[-1], before, after)

    return scenarios


def write_pair(metadata: dict[str, str], before: list[bytearray], after: list[bytearray]) -> None:
    folder = ROOT / metadata["id"]
    folder.mkdir(parents=True, exist_ok=True)
    save_png(folder / "before.png", before)
    save_png(folder / "after.png", after)
    (folder / "scenario.json").write_text(json.dumps({**metadata, "synthetic": True}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    for scenario in make_scenarios():
        print(f"Generated synthetic scenario: {scenario['title']} ({scenario['id']})")
