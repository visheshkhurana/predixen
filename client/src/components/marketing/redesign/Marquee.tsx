import type { ReactNode } from "react";

/** Infinite CSS marquee. Content is duplicated for a seamless loop; pauses on hover. */
export function Marquee({ children, duration = 28 }: { children: ReactNode; duration?: number }) {
  return (
    <div className="marquee-mask relative overflow-hidden">
      <div className="marquee-track flex w-max gap-3" style={{ animationDuration: `${duration}s` }}>
        <div className="flex shrink-0 gap-3">{children}</div>
        <div className="flex shrink-0 gap-3" aria-hidden>
          {children}
        </div>
      </div>
    </div>
  );
}
