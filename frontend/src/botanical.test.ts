import { describe, it, expect } from "vitest";
import { botanicalGeometry } from "./botanical_geometry";
import { swipeDirection } from "./page_swipe";
import { spendingSeries } from "./finance";
import { areaFor } from "./navigation";
describe("botanical experience", () => {
  it("keeps curved tissues and veins finite within a bounded lightweight scene", () => {
    for (const low of [true, false]) {
      const g = botanicalGeometry(low);
      let triangles = 0;
      for (const shape of Object.values(g)) {
        expect(
          Array.from(shape.getAttribute("position").array).every(
            Number.isFinite,
          ),
        ).toBe(true);
        shape.computeBoundingBox();
        expect(shape.boundingBox!.max.y).toBeLessThan(1.3);
        expect(shape.boundingBox!.min.y).toBeGreaterThan(-1.7);
        triangles += shape.index!.count / 3;
        shape.dispose();
      }
      expect(triangles).toBeLessThan(low ? 4000 : 11000);
    }
  });
  it("turns only deliberate horizontal gestures and preserves reading scroll/long press", () => {
    expect(swipeDirection(-90, 12, 250)).toBe("next");
    expect(swipeDirection(110, -8, 200)).toBe("previous");
    expect(swipeDirection(30, 5, 200)).toBeNull();
    expect(swipeDirection(-85, 120, 250)).toBeNull();
    expect(swipeDirection(-90, 3, 1200)).toBeNull();
  });
  it("charts actual expenses across the year boundary, excluding wishes and cancelled items", () => {
    const series = spendingSeries(
      [
        { status: "purchased", purchased_on: "2025-12-31", total_cents: 4590 },
        { status: "delivered", purchased_on: "2026-01-01", total_cents: 1200 },
        { status: "wishlist", purchased_on: "2026-01-01", total_cents: 99999 },
        { status: "cancelled", purchased_on: "2026-01-02", total_cents: 99999 },
      ],
      "2026-01",
    );
    expect(series.at(-2)?.month).toBe("2025-12");
    expect(series.at(-2)?.cents).toBe(4590);
    expect(series.at(-1)?.cents).toBe(1200);
    expect(series[0].cents).toBe(0);
  });
  it("groups preserved deep routes into coherent areas without exposing diagnostics as primary", () => {
    expect(areaFor("/knowledge/abc/read")).toBe("knowledge");
    expect(areaFor("/memory")).toBe("knowledge");
    expect(areaFor("/library")).toBe("knowledge");
    expect(areaFor("/alarms")).toBe("routine");
    expect(areaFor("/studio")).toBe("media");
    expect(areaFor("/laboratory")).toBe("advanced");
    expect(areaFor("/advanced/media")).toBe("advanced");
  });
});
