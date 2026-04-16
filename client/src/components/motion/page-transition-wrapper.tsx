import { motion, AnimatePresence } from "framer-motion";
import { type ReactNode } from "react";

/** Wraps page content with a smooth fade+slide transition */
export function PageTransition({
  children,
  className,
  pageKey,
}: {
  children: ReactNode;
  className?: string;
  pageKey: string;
}) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={pageKey}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -8 }}
        transition={{ duration: 0.3, ease: [0.25, 0.46, 0.45, 0.94] }}
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}

/** Animated tab content — smooth crossfade between tab panels */
export function AnimatedTabContent({
  children,
  tabKey,
  className,
}: {
  children: ReactNode;
  tabKey: string;
  className?: string;
}) {
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={tabKey}
        initial={{ opacity: 0, x: 10 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: -10 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className={className}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
}
