import { Link, useRoute } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { Clock, ArrowLeft, ArrowRight, ChevronRight } from "lucide-react";

const posts = [
  {
    slug: "calculate-true-runway",
    title: "How to Calculate Your True Runway",
    excerpt: "A single forecast is a trap. Learn how to build defensible runway scenarios using confidence intervals instead of gut feel, and why P10/P50/P90 bands matter.",
    category: "Financial Planning",
    date: "Feb 24, 2026",
    readTime: "8 min",
    author: "Nikita Kapoor",
    authorRole: "CEO & Co-Founder",
    content: [
      "Most founders calculate runway with a simple formula: cash in bank divided by monthly burn. That number feels precise. It's also dangerously wrong.",
      "The problem isn't the math — it's the assumption that your burn rate stays constant. In reality, burn fluctuates month to month. Revenue is lumpy. That big contract might close in Q2, or it might slip to Q4. A single-point forecast gives you a single answer that's almost certainly inaccurate.",
      "## Why Confidence Intervals Matter",
      "Instead of asking \"how many months of runway do we have?\" you should ask \"what's the probability we survive 18 months?\" This reframing changes everything. When you run a Monte Carlo simulation with 1,000+ iterations, you get a distribution of outcomes — not a single number.",
      "Your P10 runway is the pessimistic case: only 10% of simulations ended with less runway than this. Your P50 is the median — half of outcomes were better, half worse. Your P90 is the optimistic case. Together, these three numbers give you a confidence band that's vastly more useful than a single forecast.",
      "## The FounderConsole Approach",
      "When you connect your financial data to FounderConsole, we automatically calculate your baseline runway distribution. But the real power comes from scenario modeling. What happens to your runway if you cut marketing spend by 20%? What if your largest customer churns? What if you raise prices 15%?",
      "Each scenario generates its own distribution, and you can compare them side by side. The result is a decision framework, not just a number. You can tell your board: \"Our median runway is 14.2 months, but if we execute the cost optimization plan, it extends to 19.8 months with 80% confidence.\"",
      "## Getting Started",
      "Connect your accounting software (QuickBooks, Xero, or Stripe), run your first simulation, and you'll have a defensible runway forecast in under five minutes. No spreadsheets required.",
    ],
  },
  {
    slug: "monte-carlo-founders-guide",
    title: "Monte Carlo Simulations: A Founder's Guide",
    excerpt: "A plain-English explanation that turns Monte Carlo from intimidating to practical. No PhD required — just founders making better decisions under uncertainty.",
    category: "Product Updates",
    date: "Feb 18, 2026",
    readTime: "5 min",
    author: "Arjun Rao",
    authorRole: "CTO & Co-Founder",
    content: [
      "Monte Carlo simulation sounds like something from a physics textbook. In practice, it's one of the most practical tools a startup founder can use. Here's the plain-English version.",
      "## What It Actually Does",
      "Imagine you have a financial model with five inputs: revenue growth rate, churn rate, burn rate, hiring plan, and pricing. Each of these inputs has uncertainty — you don't know exactly what next quarter's growth rate will be. A Monte Carlo simulation runs your model thousands of times, each time picking slightly different values for each input based on realistic ranges.",
      "After 1,000 runs, you don't get one answer. You get a distribution of 1,000 answers. Some runs show you running out of cash in 8 months. Others show profitability by month 14. The spread between these outcomes IS the information — it tells you how much risk you're carrying.",
      "## Why Founders Should Care",
      "Investors increasingly expect probabilistic thinking. When you walk into a board meeting and say \"our runway is 12 months,\" the natural follow-up is \"how confident are you?\" With Monte Carlo, you can answer: \"We have a 75% probability of reaching 12 months, and a 90% probability of reaching 9 months.\"",
      "This isn't just impressive — it's actionable. If your P10 runway (worst 10% of outcomes) drops below 6 months, that's a clear signal to cut costs or accelerate fundraising. If your P90 runway exceeds 24 months, you might have room to invest more aggressively in growth.",
      "## How FounderConsole Makes It Easy",
      "You don't need to build Monte Carlo models from scratch. Connect your financial data, set your scenario parameters, and FounderConsole runs the simulation for you. Results come back in seconds with clear P10/P50/P90 bands, sensitivity analysis showing which variables matter most, and AI-generated narratives explaining the results in plain English.",
    ],
  },
  {
    slug: "cap-table-mistakes",
    title: "5 Cap Table Mistakes That Cost Founders Millions",
    excerpt: "From uncapped SAFEs to missing pro-rata rights — the most common equity mistakes early-stage founders make and how to avoid them before it's too late.",
    category: "Fundraising",
    date: "Feb 10, 2026",
    readTime: "9 min",
    author: "Priya Sharma",
    authorRole: "Head of Product",
    content: [
      "Your cap table is the single most consequential document in your startup. Get it wrong early, and the compounding effects can cost you millions in dilution, legal fees, and lost leverage. Here are the five mistakes we see most often.",
      "## 1. Uncapped SAFEs Without Modeling the Dilution",
      "SAFEs are founder-friendly — until they're not. An uncapped SAFE with no valuation cap means the investor converts at whatever your Series A price is. If you raise at a high valuation, great. But if you've stacked multiple uncapped SAFEs, the dilution at conversion can be staggering. Always model the conversion scenarios before signing.",
      "## 2. Ignoring the Option Pool Shuffle",
      "Investors typically require a 10-20% option pool before their investment. This pool comes out of the pre-money valuation, which means it dilutes existing shareholders (you), not the new investor. If you don't negotiate the pool size carefully, you could be giving away 5-10% more equity than you realize.",
      "## 3. Missing Pro-Rata Rights Documentation",
      "Pro-rata rights let existing investors maintain their ownership percentage in future rounds. If you don't document who has pro-rata rights and how they're calculated, you'll face painful negotiations (and potential lawsuits) at your next raise. Keep a clean record from day one.",
      "## 4. Vesting Schedule Gaps",
      "Every founder should be on a four-year vesting schedule with a one-year cliff. Without it, a co-founder who leaves after three months could walk away with 25-50% of the company. This isn't just good practice — most investors will require it before writing a check.",
      "## 5. Not Using Software to Track Changes",
      "Spreadsheet cap tables break. They have version control problems, formula errors, and they can't model complex scenarios like SAFE conversions or anti-dilution provisions. Use purpose-built cap table software that can model dilution scenarios, track all share classes, and generate investor-ready reports.",
      "## The Fix",
      "FounderConsole's Fundraising OS includes cap table management with real-time dilution modeling. You can model SAFE conversions, option pool expansions, and fundraising scenarios before making any commitments — and share investor-ready reports directly from the platform.",
    ],
  },
  {
    slug: "timing-series-a",
    title: "When to Raise: Timing Your Series A",
    excerpt: "How confidence intervals help you avoid raising too early or too late. A data-driven approach to the most consequential timing decision founders face.",
    category: "Fundraising",
    date: "Jan 29, 2026",
    readTime: "6 min",
    author: "Nikita Kapoor",
    authorRole: "CEO & Co-Founder",
    content: [
      "Timing your fundraise is one of the highest-stakes decisions a founder makes. Raise too early and you dilute excessively at a low valuation. Raise too late and you negotiate from a position of weakness — or worse, you run out of cash.",
      "## The Traditional Approach Is Broken",
      "Most founders use rules of thumb: \"raise when you have 6-8 months of runway left\" or \"raise when you hit $1M ARR.\" These heuristics ignore the most important variable: uncertainty. Your runway isn't a fixed number — it's a distribution of possible outcomes.",
      "## A Probabilistic Framework",
      "Instead of asking \"when should I raise?\" ask \"at what point does the probability of running out of cash before closing a round exceed my risk tolerance?\" This requires two inputs: your runway distribution (from Monte Carlo simulation) and a realistic estimate of how long fundraising takes.",
      "For most Series A raises, assume 4-6 months from first meeting to money in the bank. If your P10 runway (pessimistic case) is 10 months, that means you should start fundraising now — because in the worst 10% of scenarios, you'll have only 4-6 months left by the time you close.",
      "## Using FounderConsole for Timing",
      "Run a baseline simulation to see your current runway distribution. Then model a fundraising scenario: what happens to survival probability if you add $3M at month 6? What about $5M at month 9? The scenario comparison shows you the optimal timing window — the range of months where raising maximizes survival probability while minimizing dilution.",
      "The AI copilot can also factor in market conditions, pulling real-time data on comparable fundraising rounds, median time-to-close, and sector-specific benchmarks to refine the recommendation.",
    ],
  },
  {
    slug: "data-driven-culture",
    title: "Building a Data-Driven Culture",
    excerpt: "The best founders don't just track metrics — they build systems where every team member understands the numbers that matter and acts on them weekly.",
    category: "Founder Stories",
    date: "Jan 15, 2026",
    readTime: "7 min",
    author: "Dev Mehta",
    authorRole: "Lead Engineer",
    content: [
      "Every startup says they're \"data-driven.\" Few actually are. The gap between tracking metrics and building a culture where data informs every decision is enormous — and it's usually the founder's fault.",
      "## Metrics Without Context Are Noise",
      "Dashboards full of charts feel productive. But if your team can't answer \"what should we do differently based on this data?\", then the dashboard is decoration, not a tool. Every metric needs three things: a clear owner, a target, and a decision framework for what to do when the metric moves.",
      "## The Weekly Metrics Review",
      "The single highest-leverage meeting at a startup is the weekly metrics review. Not a status update — a review where the team looks at the numbers, identifies surprises, and decides on actions. Keep it to 30 minutes. Focus on 5-7 key metrics. Ask three questions for each: What happened? Why? What are we doing about it?",
      "## Making Data Accessible",
      "Most startup data lives in silos: revenue in Stripe, expenses in QuickBooks, pipeline in HubSpot, product metrics in Mixpanel. When data is fragmented, nobody has the full picture. The first step to a data-driven culture is connecting your sources so everyone sees the same numbers.",
      "## Probabilistic Thinking",
      "Data-driven doesn't mean deterministic. The best founders teach their teams to think in ranges and probabilities. Instead of \"we'll hit $100K MRR by June,\" try \"we have a 70% probability of hitting $100K MRR by June, and here's what we need to do to push that above 85%.\" This kind of thinking transforms how teams plan and prioritize.",
      "## Getting Started",
      "Start with three metrics the whole company can rally around. Connect your data sources so those metrics update automatically. Schedule a weekly 30-minute review. Within a month, you'll notice the shift: conversations move from opinions to evidence, and decisions get faster.",
    ],
  },
  {
    slug: "unit-economics-guide",
    title: "The Founder's Guide to Unit Economics",
    excerpt: "LTV, CAC, payback period, and contribution margin explained with real startup examples. The metrics investors actually care about and how to improve them.",
    category: "Financial Planning",
    date: "Jan 6, 2026",
    readTime: "6 min",
    author: "Priya Sharma",
    authorRole: "Head of Product",
    content: [
      "Unit economics tell you whether your business model actually works. Revenue growth can mask a broken model for a while, but eventually, investors and reality catch up. Here's what you need to know.",
      "## Customer Acquisition Cost (CAC)",
      "CAC is the total cost of acquiring one new customer: marketing spend plus sales salaries plus tools, divided by new customers acquired. A healthy SaaS startup should see CAC trending down over time as brand awareness grows and referral loops kick in. If your CAC is increasing quarter over quarter, something is wrong with your go-to-market strategy.",
      "## Lifetime Value (LTV)",
      "LTV is the total revenue you expect from a customer over their entire relationship with you. The simplest formula: Average Revenue Per Account (ARPA) multiplied by average customer lifetime (1 / monthly churn rate). For a $500/month product with 3% monthly churn, LTV = $500 × (1/0.03) = $16,667.",
      "## The LTV:CAC Ratio",
      "Investors want to see LTV:CAC of at least 3:1. Below 3:1, you're spending too much to acquire customers relative to what they're worth. Above 5:1, you might be under-investing in growth. The sweet spot is 3-5x, which tells investors you have an efficient, scalable model.",
      "## CAC Payback Period",
      "How many months until a customer's cumulative gross profit covers their acquisition cost? For most SaaS businesses, investors expect payback within 12-18 months. If your payback is 24+ months, you need significant capital to fund growth — and your Series A story needs to explain why payback will improve.",
      "## Contribution Margin",
      "Contribution margin is revenue minus variable costs (hosting, support, payment processing) per customer. This tells you how much each additional customer actually contributes to covering your fixed costs. A healthy SaaS contribution margin is 70-85%.",
      "## Tracking Unit Economics in FounderConsole",
      "Connect your data sources and FounderConsole automatically calculates CAC, LTV, LTV:CAC ratio, payback period, and contribution margin. You can model scenarios to see how pricing changes or churn improvements affect your unit economics over 24 months — with confidence intervals, not single-point guesses.",
    ],
  },
];

function BlogList() {
  useSEO({
    title: "Blog | FounderConsole",
    description:
      "Insights for startup founders: runway planning, Monte Carlo simulations, cap table management, fundraising timing, unit economics, and data-driven decision making.",
  });

  return (
    <MarketingLayout>
      <section>
        <div className="mx-auto max-w-6xl px-4 py-16 md:py-20">
          <h1 className="text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-blog-title">
            Insights for Founders
          </h1>
          <p className="mt-3 max-w-2xl text-lg text-muted-foreground" data-testid="text-blog-subtitle">
            Practical decision science for founders. Runway, fundraising, hiring, and strategy — through the lens of probability.
          </p>
        </div>
      </section>

      <section className="border-t">
        <div className="mx-auto max-w-6xl px-4 py-10">
          <div className="grid gap-6 grid-cols-1 md:grid-cols-2">
            {posts.map((post, index) => (
              <Link
                key={post.slug}
                href={`/blog/${post.slug}`}
                className="group"
                data-testid={`card-blog-${index}`}
              >
                <article className="rounded-xl border bg-card overflow-hidden transition-colors group-hover:border-primary/40">
                  <div className="relative h-40 bg-gradient-to-br from-primary/20 to-primary/5 flex items-end p-4">
                    <Badge
                      variant="secondary"
                      className="absolute top-3 right-3"
                      data-testid={`badge-category-${index}`}
                    >
                      {post.category}
                    </Badge>
                    <h2 className="text-lg font-semibold text-foreground leading-snug group-hover:text-primary transition-colors" data-testid={`text-blog-post-title-${index}`}>
                      {post.title}
                    </h2>
                  </div>
                  <div className="p-5">
                    <p className="text-sm text-muted-foreground line-clamp-2" data-testid={`text-blog-excerpt-${index}`}>
                      {post.excerpt}
                    </p>
                    <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground">
                      <div className="flex items-center gap-3">
                        <span data-testid={`text-blog-date-${index}`}>{post.date}</span>
                        <span className="text-border">·</span>
                        <span className="flex items-center gap-1" data-testid={`text-blog-readtime-${index}`}>
                          <Clock className="h-3 w-3" />
                          {post.readTime}
                        </span>
                      </div>
                      <span className="flex items-center gap-1 text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                        Read <ChevronRight className="h-3 w-3" />
                      </span>
                    </div>
                  </div>
                </article>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}

function BlogPost({ slug }: { slug: string }) {
  const post = posts.find((p) => p.slug === slug);

  useSEO({
    title: post ? `${post.title} | FounderConsole Blog` : "Blog | FounderConsole",
    description: post?.excerpt || "",
  });

  if (!post) {
    return (
      <MarketingLayout>
        <div className="mx-auto max-w-3xl px-4 py-16 text-center">
          <h1 className="text-2xl font-bold text-foreground">Article not found</h1>
          <p className="mt-2 text-muted-foreground">The article you're looking for doesn't exist.</p>
          <Button asChild className="mt-6" data-testid="button-back-to-blog">
            <Link href="/blog">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Blog
            </Link>
          </Button>
        </div>
      </MarketingLayout>
    );
  }

  return (
    <MarketingLayout>
      <article className="mx-auto max-w-3xl px-4 py-12 md:py-16" data-testid="blog-article">
        <Link href="/blog" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors mb-8" data-testid="link-back-to-blog">
          <ArrowLeft className="h-4 w-4" />
          Back to Blog
        </Link>

        <header className="mb-8">
          <Badge variant="secondary" data-testid="badge-article-category">{post.category}</Badge>
          <h1 className="mt-3 text-3xl font-bold tracking-tight text-foreground md:text-4xl" data-testid="text-article-title">
            {post.title}
          </h1>
          <div className="mt-4 flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
                <span className="text-xs font-semibold text-muted-foreground">
                  {post.author.split(" ").map((n) => n[0]).join("")}
                </span>
              </div>
              <div>
                <p className="font-medium text-foreground" data-testid="text-article-author">{post.author}</p>
                <p className="text-xs" data-testid="text-article-author-role">{post.authorRole}</p>
              </div>
            </div>
            <span className="text-border">·</span>
            <span data-testid="text-article-date">{post.date}</span>
            <span className="text-border">·</span>
            <span className="flex items-center gap-1" data-testid="text-article-readtime">
              <Clock className="h-3 w-3" />
              {post.readTime}
            </span>
          </div>
        </header>

        <div className="prose prose-sm dark:prose-invert max-w-none" data-testid="article-content">
          {post.content.map((paragraph, i) => {
            if (paragraph.startsWith("## ")) {
              return (
                <h2 key={i} className="mt-8 mb-3 text-xl font-semibold text-foreground">
                  {paragraph.replace("## ", "")}
                </h2>
              );
            }
            return (
              <p key={i} className="mb-4 text-muted-foreground leading-relaxed">
                {paragraph}
              </p>
            );
          })}
        </div>

        <div className="mt-12 border-t pt-8">
          <div className="rounded-xl border bg-card/50 p-6 text-center">
            <h3 className="text-lg font-semibold text-foreground" data-testid="text-article-cta">
              Ready to try this yourself?
            </h3>
            <p className="mt-2 text-sm text-muted-foreground">
              All features are free during beta. Connect your data and get your first forecast in under 5 minutes.
            </p>
            <div className="mt-4">
              <Button asChild data-testid="button-article-get-started">
                <Link href="/auth">
                  Get Started Free
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </article>
    </MarketingLayout>
  );
}

export default function BlogPage() {
  const [, params] = useRoute("/blog/:slug");

  if (params?.slug) {
    return <BlogPost slug={params.slug} />;
  }

  return <BlogList />;
}
