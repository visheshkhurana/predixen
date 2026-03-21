import { useEffect, useRef, useState } from "react";

interface SimAnimatedCounterProps {
  value: number;
  duration?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
  decimals?: number;
}

export function SimAnimatedCounter({ value, duration = 1200, prefix = "", suffix = "", className, decimals = 0 }: SimAnimatedCounterProps) {
  const [display, setDisplay] = useState(0);
  const prev = useRef(0);
  const start = useRef<number | null>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    prev.current = display;
    start.current = null;

    const tick = (ts: number) => {
      if (!start.current) start.current = ts;
      const p = Math.min((ts - start.current) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 4);
      setDisplay(prev.current + (value - prev.current) * eased);
      if (p < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current !== null) {
        cancelAnimationFrame(rafRef.current);
      }
    };
  }, [value, duration]);

  const formatted = decimals > 0 ? display.toFixed(decimals) : Math.round(display).toLocaleString();

  return <span className={className}>{prefix}{formatted}{suffix}</span>;
}
