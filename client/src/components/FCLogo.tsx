import { BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";

interface FCLogoProps {
  size?: "sm" | "md" | "lg";
  className?: string;
}

const sizeMap = {
  sm: { container: "h-7 w-7", icon: "h-4 w-4" },
  md: { container: "h-9 w-9", icon: "h-5 w-5" },
  lg: { container: "h-10 w-10", icon: "h-5.5 w-5.5" },
};

export function FCLogo({ size = "md", className }: FCLogoProps) {
  const s = sizeMap[size];
  return (
    <div
      className={cn(
        s.container,
        "rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shrink-0",
        className
      )}
    >
      <BarChart3 className={cn(s.icon, "text-white")} />
    </div>
  );
}
