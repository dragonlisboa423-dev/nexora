"""Reproducible botanical app icons from original vector geometry; no remote assets."""

import math
from pathlib import Path

from PIL import Image, ImageDraw

folder = Path(__file__).resolve().parents[1] / "frontend/public/icons"
folder.mkdir(parents=True, exist_ok=True)
for size in (192, 512):
    scale = 3
    image = Image.new("RGB", (size * scale, size * scale), "#0c1510")
    draw = ImageDraw.Draw(image)

    def pixel(point, unit=size * scale / 2):
        return ((point[0] + 1) * unit, (point[1] + 1) * unit)

    for angle, height, color in (
        (-0.38, 0.9, "#344c2d"),
        (0.38, 0.94, "#3d5930"),
        (-0.04, 1.0, "#52733c"),
    ):

        def leaf(t, s, tilt=angle, stretch=height):
            x = s * 0.28 * math.sin(math.pi * t) ** 0.8 + 0.05 * math.sin(t * 4)
            y = -1.08 * t * stretch
            return (
                x * math.cos(tilt) - y * math.sin(tilt),
                0.46 + x * math.sin(tilt) + y * math.cos(tilt),
            )

        boundary = [pixel(leaf(i / 60, -1)) for i in range(61)] + [
            pixel(leaf(i / 60, 1)) for i in range(60, -1, -1)
        ]
        draw.polygon(boundary, fill=color)
        draw.line(
            boundary + [boundary[0]], fill="#6c8b47", width=max(1, round(size * scale * 0.003))
        )
        draw.line(
            [pixel(leaf(i / 40, 0)) for i in range(40)],
            fill="#a8bf74",
            width=max(1, round(size * scale * 0.005)),
        )
        for t in (0.25, 0.43, 0.61, 0.77):
            for side in (-1, 1):
                draw.line(
                    [pixel(leaf(t + 0.12 * i / 12, side * 0.85 * i / 12)) for i in range(13)],
                    fill="#829e55",
                    width=max(1, round(size * scale * 0.003)),
                )
    for dx in (-0.18, -0.06, 0.07, 0.2):
        points = [pixel((dx * t * t, 0.44 + 0.31 * t)) for t in (0, 0.2, 0.4, 0.6, 0.8, 1)]
        draw.line(points, fill="#829d52", width=max(1, round(size * scale * 0.004)))
    image.resize((size, size), Image.Resampling.LANCZOS).save(folder / f"saly-{size}.png")
