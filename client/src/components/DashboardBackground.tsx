import { useReducedMotion } from 'framer-motion';

export function DashboardBackground() {
  const prefersReducedMotion = useReducedMotion();

  return (
    <div className="fixed inset-0 z-0 pointer-events-none overflow-hidden" aria-hidden="true">
      <div
        className={cn(
          "absolute -top-[30%] -right-[20%] w-[50vw] h-[50vw] rounded-full opacity-[0.03]",
          "bg-gradient-to-br from-primary via-primary/50 to-transparent blur-[120px]",
          !prefersReducedMotion && "fc-drift1"
        )}
      />
      <div
        className={cn(
          "absolute -bottom-[20%] -left-[15%] w-[40vw] h-[40vw] rounded-full opacity-[0.025]",
          "bg-gradient-to-tr from-violet-500 via-violet-500/40 to-transparent blur-[100px]",
          !prefersReducedMotion && "fc-drift2"
        )}
      />
      <div
        className={cn(
          "absolute top-[40%] left-[50%] w-[30vw] h-[30vw] rounded-full opacity-[0.02]",
          "bg-gradient-to-bl from-emerald-500 via-emerald-500/30 to-transparent blur-[100px]",
          !prefersReducedMotion && "fc-drift3"
        )}
      />
    </div>
  );
}

function cn(...classes: (string | false | undefined)[]) {
  return classes.filter(Boolean).join(' ');
}
