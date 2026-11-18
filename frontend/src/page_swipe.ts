import { useRef } from "react";
export function swipeDirection(
  dx: number,
  dy: number,
  duration: number,
): "next" | "previous" | null {
  if (duration > 1000 || Math.abs(dx) < 60 || Math.abs(dx) < Math.abs(dy) * 1.4)
    return null;
  return dx < 0 ? "next" : "previous";
}
export function usePageSwipe({
  disabled = false,
  next,
  previous,
}: {
  disabled?: boolean;
  next: () => void;
  previous: () => void;
}) {
  const start = useRef<{
    x: number;
    y: number;
    time: number;
    id: number;
  } | null>(null);
  return {
    onPointerDown: (event: React.PointerEvent<HTMLElement>) => {
      if (
        disabled ||
        event.pointerType === "mouse" ||
        !event.isPrimary ||
        (event.target as Element).closest(
          "button,input,textarea,select,a,[contenteditable],[role=button],[role=slider],.science-block",
        )
      )
        return;
      start.current = {
        x: event.clientX,
        y: event.clientY,
        time: performance.now(),
        id: event.pointerId,
      };
    },
    onPointerUp: (event: React.PointerEvent<HTMLElement>) => {
      const began = start.current;
      start.current = null;
      if (
        disabled ||
        !began ||
        began.id !== event.pointerId ||
        document.getSelection()?.toString()
      )
        return;
      const direction = swipeDirection(
        event.clientX - began.x,
        event.clientY - began.y,
        performance.now() - began.time,
      );
      if (direction === "next") next();
      if (direction === "previous") previous();
    },
    onPointerCancel: () => {
      start.current = null;
    },
  };
}
