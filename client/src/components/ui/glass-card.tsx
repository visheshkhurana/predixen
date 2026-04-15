import * as React from "react";
import { cn } from "@/lib/utils";
import { motion, type HTMLMotionProps, useReducedMotion } from "framer-motion";

type GlassCardProps = {
  intensity?: "subtle" | "medium" | "strong";
  glow?: boolean;
  animated?: boolean;
  delay?: number;
  children?: React.ReactNode;
  className?: string;
} & Omit<HTMLMotionProps<"div">, "children">;

const intensityClasses = {
  subtle: "glass-subtle",
  medium: "glass-medium",
  strong: "glass-strong",
};

const GlassCard = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, intensity = "medium", glow = false, animated = true, delay = 0, children, ...rest }, ref) => {
    const prefersReducedMotion = useReducedMotion();
    const classes = cn(
      "rounded-xl",
      intensityClasses[intensity],
      glow && "glass-glow",
      className
    );

    if (animated && !prefersReducedMotion) {
      return (
        <motion.div
          ref={ref}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay, ease: [0.16, 1, 0.3, 1] }}
          className={classes}
          {...rest}
        >
          {children}
        </motion.div>
      );
    }

    const { initial, animate, exit, transition, whileHover, whileTap, whileFocus, whileInView, whileDrag, layout, layoutId, onAnimationStart, onAnimationComplete, ...htmlProps } = rest;
    return (
      <div ref={ref} className={classes} {...htmlProps as React.HTMLAttributes<HTMLDivElement>}>
        {children}
      </div>
    );
  }
);
GlassCard.displayName = "GlassCard";

const GlassPanel = React.forwardRef<HTMLDivElement, Omit<GlassCardProps, "animated" | "delay">>(
  ({ className, intensity = "subtle", glow = false, children, initial, animate, exit, transition, whileHover, whileTap, whileFocus, whileInView, whileDrag, layout, layoutId, onAnimationStart, onAnimationComplete, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        "rounded-2xl p-6",
        intensityClasses[intensity],
        glow && "glass-glow",
        className
      )}
      {...props as React.HTMLAttributes<HTMLDivElement>}
    >
      {children}
    </div>
  )
);
GlassPanel.displayName = "GlassPanel";

const GlassModal = React.forwardRef<HTMLDivElement, GlassCardProps>(
  ({ className, intensity = "strong", glow = true, children, ...rest }, ref) => {
    const { initial, animate, exit, transition, whileHover, whileTap, whileFocus, whileInView, whileDrag, layout, layoutId, onAnimationStart, onAnimationComplete, ...htmlProps } = rest;
    return (
      <div
        ref={ref}
        className={cn(
          "rounded-2xl p-6 border border-white/10 shadow-2xl",
          intensityClasses[intensity],
          glow && "glass-glow",
          className
        )}
        {...htmlProps as React.HTMLAttributes<HTMLDivElement>}
      >
        {children}
      </div>
    );
  }
);
GlassModal.displayName = "GlassModal";

export { GlassCard, GlassPanel, GlassModal };
