import { cn } from "@/lib/utils";
import { ReactNode } from "react";

interface SimGlassCardProps {
  children: ReactNode;
  className?: string;
  variant?: "default" | "elevated" | "active" | "processing";
  hover?: boolean;
}

export function SimGlassCard({ children, className, variant = "default", hover = true }: SimGlassCardProps) {
  return (
    <div className={cn(
      "relative rounded-xl border backdrop-blur-md transition-all duration-300",
      variant === "default" && "bg-white/[0.03] border-white/[0.06]",
      variant === "elevated" && "bg-[#1e1e2a] border-white/10 shadow-lg shadow-black/20",
      variant === "active" && "bg-white/[0.03] border-blue-500/30 shadow-[0_0_20px_rgba(79,125,249,0.15)]",
      variant === "processing" && "bg-white/[0.03] border-amber-500/30 fc-animate-pulse-border",
      hover && "hover:border-white/20 hover:bg-white/[0.06]",
      className
    )}>
      {children}
    </div>
  );
}
