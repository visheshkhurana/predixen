import { useEffect, useState } from "react";
import { Link, useLocation, useParams } from "wouter";
import {
  ArrowRight,
  BookOpen,
  Calculator,
  Check,
  ChevronDown,
  Plug,
  Zap,
} from "lucide-react";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import { trackFunnel } from "@/lib/funnel";
import NotFound from "@/pages/not-found";
import {
  INDUSTRY_PAGES,
  METRIC_SOURCE_LABEL,
  getIndustryPage,
  industryJsonLd,
  industryPath,
  industrySignupHref,
  type IndustryPage,
  type MetricSource,
} from "@/data/industry-pages";
import {
  INDUSTRY_ICONS,
  IndustryPickerDialog,
  IndustryPill,
  trackIndustrySelected,
} from "@/components/marketing/IndustryPicker";
import { markDismissedThisSession, storeIndustry } from "@/lib/industryPicker";

/**
 * `/for/:slug` — one industry homepage, rendered entirely from
 * client/src/data/industry-pages.ts. The server prerender renders the same
 * config (server/seo-prerender.ts, `buildIndustryLandingBodyContent`), so the
 * copy a crawler reads and the copy a visitor reads cannot drift.
 */

const SOURCE_TONE: Record<MetricSource, string> = {
  "built-in": "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  "free-tool": "bg-primary/10 text-primary",
  custom: "bg-muted text-muted-foreground",
};

function Hero({ page, onChangeIndustry }: { page: IndustryPage; onChangeIndustry: () => void }) {
  const Icon = INDUSTRY_ICONS[page.icon];
  const firstTool = page.links.find((l) => l.kind === "tool");
  return (
    <section className="relative overflow-hidden">
      <div className="aurora-hero" aria-hidden />
      <div className="grid-floor" aria-hidden />
      <div className="relative mx-auto max-w-5xl px-4 pb-16 pt-8 text-center md:pb-24 md:pt-10">
        <div className="flex justify-center">
          <IndustryPill slug={page.slug} mode="page" onChange={onChangeIndustry} />
        </div>
        <Badge variant="secondary" className="mt-10 text-xs font-medium" data-testid="badge-industry-eyebrow">
          <Icon className="mr-1.5 h-3 w-3" aria-hidden />
          {page.eyebrow}
        </Badge>
        <h1
          className="mx-auto mt-5 max-w-4xl text-4xl font-bold leading-[1.08] tracking-tight text-foreground md:text-6xl"
          data-testid="text-industry-headline"
        >
          {page.headline}
        </h1>
        <p
          className="mx-auto mt-6 max-w-2xl text-lg leading-relaxed text-muted-foreground md:text-xl"
          data-testid="text-industry-subhead"
        >
          {page.subhead}
        </p>
        <div className="mt-9 flex flex-wrap justify-center gap-3">
          <Button
            size="lg"
            className="h-12 px-8 text-base shadow-lg shadow-primary/25 transition-shadow hover:shadow-xl hover:shadow-primary/40"
            asChild
            data-testid="button-industry-start-free"
          >
            <Link
              href={industrySignupHref(page.slug)}
              onClick={() => trackFunnel("cta_click", { location: "industry-hero", industry: page.slug })}
            >
              Start free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
          {firstTool && (
            <Button size="lg" variant="outline" className="h-12 px-6 text-base backdrop-blur" asChild>
              <Link
                href={firstTool.href}
                onClick={() => trackFunnel("cta_click", { location: "industry-hero-tool", industry: page.slug })}
                data-testid="button-industry-free-tool"
              >
                <Calculator className="mr-2 h-4 w-4" />
                Try a free tool first
              </Link>
            </Button>
          )}
        </div>
        <p className="mt-5 text-xs text-muted-foreground">Free during public beta · No credit card required</p>
      </div>
    </section>
  );
}

function MetricsStrip({ page }: { page: IndustryPage }) {
  return (
    <section className="border-t bg-card/30" aria-labelledby="industry-metrics-heading">
      <div className="mx-auto max-w-6xl px-4 py-12 md:py-14">
        <h2
          id="industry-metrics-heading"
          className="text-center text-xs font-semibold uppercase tracking-wider text-muted-foreground"
        >
          The numbers that matter for {page.label.toLowerCase()}
        </h2>
        <ul className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4" data-testid="industry-metrics">
          {page.metrics.map((m) => (
            <li key={m.label} className="rounded-xl border bg-background/70 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-semibold text-foreground">{m.label}</span>
                <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${SOURCE_TONE[m.source]}`}>
                  {METRIC_SOURCE_LABEL[m.source]}
                </span>
              </div>
              <p className="mt-1.5 text-xs leading-relaxed text-muted-foreground">{m.hint}</p>
            </li>
          ))}
        </ul>
        <p className="mt-4 text-center text-xs text-muted-foreground">
          Built in: computed for you. Free calculator: no account needed. Custom metric: add it on the KPI board and track it alongside the rest.
        </p>
      </div>
    </section>
  );
}

function PainFeatures({ page }: { page: IndustryPage }) {
  return (
    <section className="border-t" aria-labelledby="industry-pains-heading">
      <div className="mx-auto max-w-6xl px-4 py-20 md:py-24">
        <div className="mb-12 text-center">
          <h2 id="industry-pains-heading" className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">
            What gets in the way, and what helps
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-muted-foreground">
            Real problems, matched to features that exist in FounderConsole today.
          </p>
        </div>
        <div className="grid gap-5 md:grid-cols-2">
          {page.pains.map((p, i) => (
            <article
              key={p.pain}
              className="flex flex-col rounded-2xl border bg-card/60 p-6 transition-shadow duration-300 hover:shadow-lg"
              data-testid={`industry-pain-${i}`}
            >
              <p className="text-base font-semibold leading-snug text-foreground">“{p.pain}”</p>
              <div className="mt-4 flex items-start gap-3 rounded-xl bg-primary/[0.05] p-4">
                <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" aria-hidden />
                <div>
                  <h3 className="text-sm font-semibold text-primary">{p.feature}</h3>
                  <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{p.detail}</p>
                  {p.href && (
                    <Link
                      href={p.href}
                      className="mt-2 inline-flex items-center gap-1 text-sm font-medium text-primary underline-offset-4 hover:underline"
                    >
                      Try it free <ArrowRight className="h-3.5 w-3.5" />
                    </Link>
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}

function ConnectorsAndLinks({ page }: { page: IndustryPage }) {
  const tools = page.links.filter((l) => l.kind !== "post");
  const posts = page.links.filter((l) => l.kind === "post");
  return (
    <section className="border-t bg-card/20">
      <div className="mx-auto grid max-w-6xl gap-10 px-4 py-20 md:grid-cols-3 md:py-24">
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground">
            <Plug className="h-4 w-4 text-primary" aria-hidden />
            Connect what you already use
          </h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Among the 36 read-only data connectors. CSV upload and manual entry work too.
          </p>
          <ul className="mt-4 flex flex-wrap gap-2" data-testid="industry-connectors">
            {page.connectors.map((c) => (
              <li key={c}>
                <Badge variant="secondary" className="px-3 py-1 font-normal text-muted-foreground">
                  {c}
                </Badge>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground">
            <Calculator className="h-4 w-4 text-primary" aria-hidden />
            Free tools, no account
          </h2>
          <ul className="mt-4 space-y-2.5">
            {tools.map((l) => (
              <li key={l.href}>
                <Link
                  href={l.href}
                  className="group inline-flex items-start gap-2 text-sm text-foreground underline-offset-4 hover:text-primary hover:underline"
                >
                  <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary transition-transform group-hover:translate-x-0.5" />
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
        {posts.length > 0 && (
          <div>
            <h2 className="flex items-center gap-2 text-lg font-semibold text-foreground">
              <BookOpen className="h-4 w-4 text-primary" aria-hidden />
              Guides worth reading
            </h2>
            <ul className="mt-4 space-y-2.5">
              {posts.map((l) => (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    className="group inline-flex items-start gap-2 text-sm text-foreground underline-offset-4 hover:text-primary hover:underline"
                  >
                    <ArrowRight className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary transition-transform group-hover:translate-x-0.5" />
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function Faq({ page }: { page: IndustryPage }) {
  const [openIndex, setOpenIndex] = useState<number | null>(0);
  return (
    <section className="border-t" aria-labelledby="industry-faq-heading">
      <div className="mx-auto max-w-3xl px-4 py-20 md:py-24">
        <h2 id="industry-faq-heading" className="mb-10 text-center text-3xl font-bold tracking-tight text-foreground md:text-4xl">
          Questions {page.label.split(/[ /&]/)[0]} founders ask
        </h2>
        <div className="space-y-3">
          {page.faqs.map((f, i) => {
            const open = openIndex === i;
            const id = `industry-faq-${i}`;
            return (
              <div key={f.q} className="overflow-hidden rounded-xl border bg-card/50">
                <button
                  className="flex w-full items-center justify-between gap-4 p-5 text-left"
                  onClick={() => setOpenIndex(open ? null : i)}
                  aria-expanded={open}
                  aria-controls={id}
                  data-testid={`industry-faq-button-${i}`}
                >
                  <span className="text-sm font-medium text-foreground">{f.q}</span>
                  <ChevronDown
                    className={`h-4 w-4 shrink-0 text-muted-foreground transition-transform ${open ? "rotate-180" : ""}`}
                    aria-hidden
                  />
                </button>
                <div id={id} hidden={!open} className="px-5 pb-5 text-sm leading-relaxed text-muted-foreground">
                  {f.a}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function FinalCta({ page }: { page: IndustryPage }) {
  const others = INDUSTRY_PAGES.filter((p) => p.slug !== page.slug);
  return (
    <section className="relative overflow-hidden border-t">
      <div className="aurora-hero" style={{ opacity: 0.3 }} aria-hidden />
      <div className="relative mx-auto max-w-6xl px-4 py-20 text-center md:py-24">
        <Zap className="mx-auto mb-4 h-8 w-8 text-primary" aria-hidden />
        <h2 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl">Start free in a few minutes</h2>
        <p className="mx-auto mt-3 max-w-lg text-muted-foreground">
          Connect a data source or type in your numbers. Every feature is free during the public beta.
        </p>
        <div className="mt-8 flex justify-center">
          <Button size="lg" className="h-12 px-8 text-base shadow-lg shadow-primary/25" asChild data-testid="button-industry-bottom-cta">
            <Link
              href={industrySignupHref(page.slug)}
              onClick={() => trackFunnel("cta_click", { location: "industry-footer", industry: page.slug })}
            >
              Start free
              <ArrowRight className="ml-2 h-4 w-4" />
            </Link>
          </Button>
        </div>
        <p className="mt-4 text-xs text-muted-foreground">No credit card required.</p>
        <nav className="mt-14" aria-label="Other business types">
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Not quite you?</p>
          <ul className="mt-3 flex flex-wrap justify-center gap-2">
            {others.map((p) => (
              <li key={p.slug}>
                <Link
                  href={industryPath(p.slug)}
                  className="inline-flex rounded-full border bg-background/70 px-3 py-1.5 text-xs text-foreground transition-colors hover:border-primary/50 hover:text-primary"
                >
                  {p.label}
                </Link>
              </li>
            ))}
            <li>
              <Link
                href="/"
                className="inline-flex rounded-full border bg-background/70 px-3 py-1.5 text-xs text-foreground transition-colors hover:border-primary/50 hover:text-primary"
              >
                Everything FounderConsole does
              </Link>
            </li>
          </ul>
        </nav>
      </div>
    </section>
  );
}

function IndustryLanding({ page }: { page: IndustryPage }) {
  const [, navigate] = useLocation();
  const [pickerOpen, setPickerOpen] = useState(false);

  useSEO({
    title: page.title,
    description: page.description,
    path: industryPath(page.slug),
    jsonLd: industryJsonLd(page),
  });

  // Arriving here counts as having chosen a context: the homepage picker should
  // not interrupt this visitor later in the session if they click the logo.
  useEffect(() => {
    markDismissedThisSession();
  }, []);

  return (
    <MarketingLayout>
      <div data-testid={`industry-landing-${page.slug}`}>
        <Hero page={page} onChangeIndustry={() => setPickerOpen(true)} />
        <MetricsStrip page={page} />
        <PainFeatures page={page} />
        <ConnectorsAndLinks page={page} />
        <Faq page={page} />
        <FinalCta page={page} />
      </div>
      <IndustryPickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        current={page.slug}
        onChoose={(slug) => {
          storeIndustry(slug);
          trackIndustrySelected(slug, "pill");
          setPickerOpen(false);
          if (slug !== page.slug) navigate(industryPath(slug));
        }}
        onSkip={() => {
          storeIndustry("all");
          setPickerOpen(false);
          navigate("/");
        }}
      />
    </MarketingLayout>
  );
}

export default function IndustryLandingPage() {
  const params = useParams<{ slug: string }>();
  const page = getIndustryPage(params.slug);
  if (!page) return <NotFound />;
  // keyed so switching industries resets FAQ state and scroll
  return <IndustryLanding key={page.slug} page={page} />;
}

