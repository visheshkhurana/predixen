import { cn } from "@/lib/utils";

export function SimSkeleton({ className, lines = 3 }: { className?: string; lines?: number }) {
  return (
    <div className={cn("space-y-2.5", className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={cn("h-3 rounded fc-animate-shimmer", i === lines - 1 ? "w-2/3" : "w-full")}
        />
      ))}
    </div>
  );
}
