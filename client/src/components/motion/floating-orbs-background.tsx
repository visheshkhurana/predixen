import { motion } from "framer-motion";

/** Floating gradient orbs — subtle 3D-like ambient background for dashboard sections */
export function FloatingOrbsBackground({ className }: { className?: string }) {
  return (
    <div className={`pointer-events-none absolute inset-0 overflow-hidden ${className ?? ""}`}>
      {/* Primary orb — slow drift top-right */}
      <motion.div
        className="absolute -top-32 -right-32 h-96 w-96 rounded-full bg-primary/5 blur-3xl"
        animate={{
          x: [0, 30, -20, 0],
          y: [0, -20, 15, 0],
          scale: [1, 1.1, 0.95, 1],
        }}
        transition={{ duration: 20, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* Secondary orb — drift bottom-left */}
      <motion.div
        className="absolute -bottom-24 -left-24 h-72 w-72 rounded-full bg-indigo-500/5 blur-3xl"
        animate={{
          x: [0, -25, 15, 0],
          y: [0, 20, -10, 0],
          scale: [1, 0.9, 1.05, 1],
        }}
        transition={{ duration: 25, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* Accent orb — center drift */}
      <motion.div
        className="absolute top-1/2 left-1/2 h-48 w-48 -translate-x-1/2 -translate-y-1/2 rounded-full bg-emerald-500/3 blur-3xl"
        animate={{
          x: [0, 40, -30, 0],
          y: [0, -30, 25, 0],
          opacity: [0.3, 0.6, 0.3],
        }}
        transition={{ duration: 30, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

/** Glow card wrapper — adds a subtle animated glow border effect */
export function GlowCard({
  children,
  className,
  glowColor = "primary",
}: {
  children: React.ReactNode;
  className?: string;
  glowColor?: "primary" | "emerald" | "amber" | "red";
}) {
  const colors = {
    primary: "from-primary/20 via-primary/5 to-transparent",
    emerald: "from-emerald-500/20 via-emerald-500/5 to-transparent",
    amber: "from-amber-500/20 via-amber-500/5 to-transparent",
    red: "from-red-500/20 via-red-500/5 to-transparent",
  };

  return (
    <motion.div
      className={`relative group ${className ?? ""}`}
      whileHover={{ scale: 1.01 }}
      transition={{ duration: 0.2 }}
    >
      {/* Glow border — visible on hover */}
      <div
        className={`absolute -inset-[1px] rounded-xl bg-gradient-to-r ${colors[glowColor]} opacity-0 group-hover:opacity-100 transition-opacity duration-500 blur-sm`}
      />
      <div className="relative">{children}</div>
    </motion.div>
  );
}

/** Dot grid pattern — subtle geometric background texture */
export function DotGridPattern({ className }: { className?: string }) {
  return (
    <div
      className={`pointer-events-none absolute inset-0 ${className ?? ""}`}
      style={{
        backgroundImage: `radial-gradient(circle, hsl(var(--muted-foreground) / 0.07) 1px, transparent 1px)`,
        backgroundSize: "24px 24px",
      }}
    />
  );
}
