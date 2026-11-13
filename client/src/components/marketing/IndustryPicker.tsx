import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation } from "wouter";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import {
  ArrowRight,
  Briefcase,
  Cloud,
  Landmark,
  Rocket,
  ShoppingBag,
  Sparkles,
  Store,
  X,
  type LucideIcon,
} from "lucide-react";
import {
  INDUSTRY_PAGES,
  INDUSTRY_SKIPPED,
  getIndustryPage,
  industryPath,
  type IndustryIconName,
} from "@/data/industry-pages";
import {
  analyticsDeclined,
  industryParam,
  markDismissedThisSession,
  readDismissedThisSession,
  readStoredIndustry,
  shouldShowIndustryPicker,
  storeIndustry,
  type IndustrySource,
} from "@/lib/industryPicker";
import { trackFunnel } from "@/lib/funnel";

export const INDUSTRY_ICONS: Record<IndustryIconName, LucideIcon> = {
  ShoppingBag,
  Cloud,
  Store,
  Briefcase,
  Landmark,
  Rocket,
};

/** `industry_selected` with {industry, source}. Skipped when analytics was declined. */
export function trackIndustrySelected(industry: string, source: IndustrySource) {
  if (analyticsDeclined()) return;
  trackFunnel("industry_selected", { industry, source });
}

/**
 * The path of the document the visitor first loaded in this tab. A visitor who
 * entered on a deep link (/pricing, /blog/..., /for/saas) and later clicked the
 * logo should not be interrupted on `/`. The navigation timing entry is the one
 * record of the entry URL that survives client-side routing.
 */
function entryPathname(): string {
  try {
    const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
    if (nav?.name) return new URL(nav.name).pathname;
  } catch {
    // fall through
  }
  return window.location.pathname;
}

/* --------------------------------- dialog --------------------------------- */

export function IndustryPickerDialog({
  open,
  onOpenChange,
  onChoose,
  onSkip,
  current,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onChoose: (slug: string) => void;
  onSkip: () => void;
  current?: string | null;
}) {
  const optionRefs = useRef<Array<HTMLButtonElement | null>>([]);

  // Arrow keys move between options (wrapping); Home/End jump to the ends.
  // Tab still moves through them in order, so nothing is reachable only by arrows.
  const onGridKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const keys = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"];
    if (!keys.includes(e.key)) return;
    const items = optionRefs.current.filter(Boolean) as HTMLButtonElement[];
    const index = items.indexOf(document.activeElement as HTMLButtonElement);
    if (index === -1) return;
    e.preventDefault();
    let next = index;
    if (e.key === "ArrowRight" || e.key === "ArrowDown") next = (index + 1) % items.length;
    if (e.key === "ArrowLeft" || e.key === "ArrowUp") next = (index - 1 + items.length) % items.length;
    if (e.key === "Home") next = 0;
    if (e.key === "End") next = items.length - 1;
    items[next]?.focus();
  };

  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        {/* The marketing header sits at z-[9999]; the picker has to clear it. */}
        <DialogPrimitive.Overlay className="fixed inset-0 z-[10000] bg-background/70 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 motion-reduce:animate-none" />
        <DialogPrimitive.Content
          data-testid="industry-picker"
          onOpenAutoFocus={(e) => {
            e.preventDefault();
            const currentIndex = INDUSTRY_PAGES.findIndex((p) => p.slug === current);
            optionRefs.current[Math.max(0, currentIndex)]?.focus();
          }}
          className="fixed z-[10001] inset-x-0 bottom-0 max-h-[92dvh] overflow-y-auto rounded-t-3xl border bg-background shadow-2xl sm:inset-x-auto sm:bottom-auto sm:left-1/2 sm:top-1/2 sm:w-[calc(100%-2rem)] sm:max-w-2xl sm:-translate-x-1/2 sm:-translate-y-1/2 sm:rounded-3xl data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:slide-in-from-bottom-8 sm:data-[state=open]:slide-in-from-bottom-2 sm:data-[state=open]:zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 motion-reduce:animate-none"
        >
          <div className="relative px-5 pb-5 pt-6 sm:px-8 sm:pb-7 sm:pt-8">
            <div className="mx-auto mb-4 h-1.5 w-10 rounded-full bg-muted sm:hidden" aria-hidden />
            <DialogPrimitive.Close
              className="absolute right-4 top-4 rounded-full p-2 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              aria-label="Close"
              data-testid="industry-picker-close"
            >
              <X className="h-4 w-4" />
            </DialogPrimitive.Close>

            <div className="pr-8">
              <p className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wider text-primary">
                <Sparkles className="h-3 w-3" aria-hidden />
                Personalise FounderConsole
              </p>
              <DialogPrimitive.Title className="mt-3 text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
                What kind of business do you run?
              </DialogPrimitive.Title>
              <DialogPrimitive.Description className="mt-2 text-sm text-muted-foreground sm:text-base">
                We'll show you the numbers, tools and guides that matter for your business. You can change this any time.
              </DialogPrimitive.Description>
            </div>

            <div
              className="mt-6 grid grid-cols-2 gap-2.5 sm:grid-cols-3 sm:gap-3"
              role="group"
              aria-label="Business type"
              onKeyDown={onGridKeyDown}
            >
              {INDUSTRY_PAGES.map((page, i) => {
                const Icon = INDUSTRY_ICONS[page.icon];
                const selected = page.slug === current;
                return (
                  <button
                    key={page.slug}
                    ref={(el) => {
                      optionRefs.current[i] = el;
                    }}
                    type="button"
                    onClick={() => onChoose(page.slug)}
                    aria-pressed={selected}
                    data-testid={`industry-option-${page.slug}`}
                    className={`group flex min-h-[7.5rem] flex-col items-start gap-2 rounded-2xl border p-3.5 text-left transition-all duration-150 hover:-translate-y-0.5 hover:border-primary/50 hover:bg-primary/[0.04] hover:shadow-md focus:outline-none focus-visible:border-primary focus-visible:ring-2 focus-visible:ring-primary/40 motion-reduce:transition-none motion-reduce:hover:translate-y-0 sm:p-4 ${
                      selected ? "border-primary bg-primary/[0.06] ring-1 ring-primary/30" : "bg-card"
                    }`}
                  >
                    <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary/10 text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                      <Icon className="h-[18px] w-[18px]" aria-hidden />
                    </span>
                    <span className="text-sm font-semibold leading-snug text-foreground">{page.label}</span>
                    <span className="text-xs leading-snug text-muted-foreground">{page.pickerHint}</span>
                  </button>
                );
              })}
            </div>

            <div className="mt-5 flex flex-col-reverse items-center justify-between gap-3 border-t pt-4 sm:flex-row">
              <p className="text-xs text-muted-foreground">Free during public beta · No credit card required</p>
              <button
                type="button"
                onClick={onSkip}
                data-testid="industry-picker-skip"
                className="inline-flex items-center gap-1 rounded-full px-3 py-1.5 text-sm font-medium text-muted-foreground underline-offset-4 transition-colors hover:text-foreground hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Skip, just show me everything
                <ArrowRight className="h-3.5 w-3.5" aria-hidden />
              </button>
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

/* ---------------------------------- pill ---------------------------------- */

export function IndustryPill({
  slug,
  mode,
  onChange,
}: {
  /** A known slug, or "all" for a visitor who skipped. */
  slug: string;
  /** "page": on /for/<slug>. "home": on the general homepage. */
  mode: "page" | "home";
  onChange: () => void;
}) {
  const page = getIndustryPage(slug);
  const base =
    "inline-flex max-w-full items-center gap-2 rounded-full border bg-background/80 px-3 py-1.5 text-xs shadow-sm backdrop-blur";

  if (!page) {
    return (
      <div className={base} data-testid="industry-pill">
        <Sparkles className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
        <button
          type="button"
          onClick={onChange}
          className="font-medium text-foreground underline-offset-4 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
          data-testid="industry-pill-change"
        >
          Tailor this page to your business
        </button>
      </div>
    );
  }

  const Icon = INDUSTRY_ICONS[page.icon];
  return (
    <div className={base} data-testid="industry-pill">
      <Icon className="h-3.5 w-3.5 shrink-0 text-primary" aria-hidden />
      {mode === "page" ? (
        <span className="truncate text-muted-foreground">
          Viewing for: <span className="font-medium text-foreground">{page.label}</span>
        </span>
      ) : (
        <Link
          href={industryPath(page.slug)}
          className="truncate font-medium text-foreground underline-offset-4 hover:underline"
          data-testid="industry-pill-open"
        >
          Your page: {page.label} →
        </Link>
      )}
      <span className="text-muted-foreground" aria-hidden>
        ·
      </span>
      <button
        type="button"
        onClick={onChange}
        className="shrink-0 font-medium text-primary underline-offset-4 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
        aria-label={`Change business type (currently ${page.label})`}
        data-testid="industry-pill-change"
      >
        change
      </button>
    </div>
  );
}

/* ------------------------------ homepage gate ------------------------------ */

/**
 * Mounted on `/`. Decides between: nothing (crawlers, deep links), the picker
 * (first visit), or the pill (returning visitor). Also honours `/?industry=x`
 * by remembering x and opening its page.
 *
 * Renders nothing on the server and nothing until mounted, so the prerendered
 * homepage body is untouched and a no-JS visitor keeps the full general page.
 */
export function HomeIndustryGate() {
  const [, navigate] = useLocation();
  const [mounted, setMounted] = useState(false);
  const [open, setOpen] = useState(false);
  const [stored, setStored] = useState<string | null>(null);
  const [source, setSource] = useState<IndustrySource>("modal");

  useEffect(() => {
    setMounted(true);
    const { pathname, search, hash } = window.location;
    const param = industryParam(search);
    if (param !== null) {
      // A shared or campaign link (`/?industry=saas`): never a modal.
      if (getIndustryPage(param)) {
        storeIndustry(param);
        trackIndustrySelected(param, "url");
        navigate(industryPath(param), { replace: true });
      }
      return;
    }
    const current = readStoredIndustry();
    setStored(current);
    const entry = entryPathname().replace(/\/+$/, "") || "/";
    const show =
      entry === "/" &&
      shouldShowIndustryPicker({
        userAgent: navigator.userAgent,
        pathname,
        search,
        hash,
        stored: current,
        dismissedThisSession: readDismissedThisSession(),
      });
    if (!show) return;
    // Let the hero paint first; the picker is an offer, not a gate.
    const t = window.setTimeout(() => {
      setSource("modal");
      setOpen(true);
    }, 450);
    return () => window.clearTimeout(t);
  }, [navigate]);

  const choose = useCallback(
    (slug: string) => {
      storeIndustry(slug);
      trackIndustrySelected(slug, source);
      setOpen(false);
      navigate(industryPath(slug));
    },
    [navigate, source],
  );

  const skip = useCallback(() => {
    storeIndustry(INDUSTRY_SKIPPED);
    setStored(INDUSTRY_SKIPPED);
    if (!analyticsDeclined()) trackFunnel("industry_picker_skipped", { source });
    setOpen(false);
  }, [source]);

  const onOpenChange = useCallback((next: boolean) => {
    if (!next) markDismissedThisSession(); // Esc, outside click or the X: ask again next visit
    setOpen(next);
  }, []);

  if (!mounted) return null;

  return (
    <>
      {stored && (
        <div className="pointer-events-none absolute inset-x-0 top-4 z-10 flex justify-center px-4">
          <div className="pointer-events-auto">
            <IndustryPill
              slug={stored}
              mode="home"
              onChange={() => {
                setSource("pill");
                setOpen(true);
              }}
            />
          </div>
        </div>
      )}
      <IndustryPickerDialog
        open={open}
        onOpenChange={onOpenChange}
        onChoose={choose}
        onSkip={skip}
        current={stored}
      />
    </>
  );
}
