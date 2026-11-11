"""Generate original, reproducible PNG app icons without external assets."""

import math
import struct
import zlib
from pathlib import Path

folder = Path(__file__).resolve().parents[1] / "frontend/public/icons"
folder.mkdir(parents=True, exist_ok=True)
for size in (192, 512):
    pixels = bytearray()
    for y in range(size):
        pixels.append(0)
        for x in range(size):
            px, py = (x - size / 2) / (size / 2), (y - size / 2) / (size / 2)
            radius = math.hypot(px, py)
            angle = math.atan2(py, px)
            edge = 0.53 + 0.04 * math.sin(angle * 3) + 0.025 * math.cos(angle * 5)
            glow = math.exp(-(((radius - edge) / 0.035) ** 2))
            inner = (
                max(0, 1 - radius / edge) * (0.5 + 0.5 * math.sin(px * 9 + py * 3))
                if radius < edge
                else 0
            )
            pixels.extend(
                (
                    min(255, int(7 + glow * 100 + inner * 20)),
                    min(255, int(17 + glow * 212 + inner * 110)),
                    min(255, int(22 + glow * 190 + inner * 100)),
                )
            )

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    output = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(pixels)))
        + chunk(b"IEND", b"")
    )
    (folder / f"saly-{size}.png").write_bytes(output)
