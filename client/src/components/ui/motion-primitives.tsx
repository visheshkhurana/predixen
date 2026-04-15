import type React from "react";
import { motion, type HTMLMotionProps, AnimatePresence, useInView, useReducedMotion } from "framer-motion";
import { forwardRef, useRef, useEffect, type ReactNode } from "react";
import { cn } from "@/lib/utils";

const springTransition = { type: "spring", stiffness: 300, damping: 30 };
const smoothTransition = { duration: 0.5, ease: [0.16, 1, 0.3, 1] };

export function FadeIn({
  children,
  className,
  delay = 0,
  duration = 0.5,
  direction = "up",
  ...props
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  duration?: number;
  direction?: "up" | "down" | "left" | "right" | "none";
} & Omit<HTMLMotionProps<"div">, "children">) {
  const prefersReducedMotion = useReducedMotion();
  const directionMap = {
    up: { y: 24 },
    down: { y: -24 },
    left: { x: 24 },
    right: { x: -24 },
    none: {},
  };

  if (prefersReducedMotion) {
    const { initial, animate, exit, transition, whileHover, whileTap, whileFocus, whileInView, whileDrag, layout, layoutId, onAnimationStart, onAnimationComplete, ...htmlProps } = props;
    return <div className={className} {...htmlProps as React.HTMLAttributes<HTMLDivElement>}>{children}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, ...directionMap[direction] }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function ScaleIn({
  children,
  className,
  delay = 0,
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
}) {
  const prefersReducedMotion = useReducedMotion();
  if (prefersReducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerChildren({
  children,
  className,
  staggerDelay = 0.06,
  initialDelay = 0,
}: {
  children: ReactNode;
  className?: string;
  staggerDelay?: number;
  initialDelay?: number;
}) {
  const prefersReducedMotion = useReducedMotion();
  if (prefersReducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={{
        hidden: {},
        visible: {
          transition: {
            staggerChildren: staggerDelay,
            delayChildren: initialDelay,
          },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0, y: 16, scale: 0.98 },
        visible: {
          opacity: 1,
          y: 0,
          scale: 1,
          transition: { duration: 0.45, ease: [0.16, 1, 0.3, 1] },
        },
      }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function ScrollReveal({
  children,
  className,
  delay = 0,
  direction = "up",
}: {
  children: ReactNode;
  className?: string;
  delay?: number;
  direction?: "up" | "down" | "left" | "right";
}) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-80px" });
  const prefersReducedMotion = useReducedMotion();

  const dirMap = {
    up: { y: 40 },
    down: { y: -40 },
    left: { x: 40 },
    right: { x: -40 },
  };

  if (prefersReducedMotion) {
    return <div ref={ref} className={className}>{children}</div>;
  }

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, ...dirMap[direction] }}
      animate={isInView ? { opacity: 1, x: 0, y: 0 } : { opacity: 0, ...dirMap[direction] }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function HoverLift({
  children,
  className,
  liftAmount = -4,
}: {
  children: ReactNode;
  className?: string;
  liftAmount?: number;
}) {
  const prefersReducedMotion = useReducedMotion();

  return (
    <motion.div
      whileHover={prefersReducedMotion ? {} : { y: liftAmount, transition: springTransition }}
      whileTap={prefersReducedMotion ? {} : { scale: 0.98, transition: springTransition }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function PressScale({
  children,
  className,
  as = "div",
}: {
  children: ReactNode;
  className?: string;
  as?: "div" | "button";
}) {
  const Comp = as === "button" ? motion.button : motion.div;
  const prefersReducedMotion = useReducedMotion();

  return (
    <Comp
      whileTap={prefersReducedMotion ? {} : { scale: 0.97 }}
      transition={springTransition}
      className={className}
    >
      {children}
    </Comp>
  );
}

export function PageTransition({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

export function NumberTicker({
  value,
  prefix = "",
  suffix = "",
  decimals = 0,
  className,
  duration = 1.2,
}: {
  value: number;
  prefix?: string;
  suffix?: string;
  decimals?: number;
  className?: string;
  duration?: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const isInView = useInView(ref, { once: true, margin: "-40px" });
  const prefersReducedMotion = useReducedMotion();

  if (prefersReducedMotion) {
    return <span className={className}>{`${prefix}${value.toFixed(decimals)}${suffix}`}</span>;
  }

  return (
    <motion.span
      ref={ref}
      className={className}
      initial={{ opacity: 0 }}
      animate={isInView ? { opacity: 1 } : { opacity: 0 }}
      transition={{ duration: 0.3 }}
    >
      {isInView ? (
        <CountUp target={value} prefix={prefix} suffix={suffix} decimals={decimals} duration={duration} />
      ) : (
        `${prefix}${value.toFixed(decimals)}${suffix}`
      )}
    </motion.span>
  );
}

function CountUp({
  target,
  prefix,
  suffix,
  decimals,
  duration,
}: {
  target: number;
  prefix: string;
  suffix: string;
  decimals: number;
  duration: number;
}) {
  const ref = useRef<HTMLSpanElement>(null);
  const animRef = useRef<number>();

  useEffect(() => {
    const startTime = performance.now();
    const animate = () => {
      const elapsed = performance.now() - startTime;
      const progress = Math.min(elapsed / (duration * 1000), 1);
      const eased = 1 - Math.pow(1 - progress, 4);
      const current = eased * target;

      if (ref.current) {
        ref.current.textContent = `${prefix}${current.toFixed(decimals)}${suffix}`;
      }

      if (progress < 1) {
        animRef.current = requestAnimationFrame(animate);
      }
    };
    animRef.current = requestAnimationFrame(animate);
    return () => {
      if (animRef.current) cancelAnimationFrame(animRef.current);
    };
  }, [target, prefix, suffix, decimals, duration]);

  return <span ref={ref}>{`${prefix}0${suffix}`}</span>;
}

export function GlowEffect({
  children,
  className,
  color = "primary",
}: {
  children: ReactNode;
  className?: string;
  color?: "primary" | "violet" | "emerald" | "amber";
}) {
  const colorMap = {
    primary: "shadow-[0_0_30px_-5px_hsl(217_91%_60%/0.3)]",
    violet: "shadow-[0_0_30px_-5px_hsl(271_81%_56%/0.3)]",
    emerald: "shadow-[0_0_30px_-5px_hsl(142_76%_36%/0.3)]",
    amber: "shadow-[0_0_30px_-5px_hsl(24_95%_53%/0.3)]",
  };

  return (
    <div className={cn(colorMap[color], className)}>
      {children}
    </div>
  );
}

export { AnimatePresence, motion, springTransition, smoothTransition };
