import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Badge } from "@/components/ui/badge";
import { useSEO } from "@/lib/seo";
import { Clock } from "lucide-react";

const posts = [
  {
    title: "How to Calculate Your True Runway",
    excerpt: "A single forecast is a trap. Learn how to build defensible runway scenarios using confidence intervals instead of gut feel, and why P10/P50/P90 bands matter.",
    category: "Financial Planning",
    date: "Feb 2026",
    readTime: "8 min",
  },
  {
    title: "Monte Carlo Simulations: A Founder's Guide",
    excerpt: "A plain-English explanation that turns Monte Carlo from intimidating to practical. No PhD required — just founders making better decisions under uncertainty.",
    category: "Product Updates",
    date: "Feb 2026",
    readTime: "5 min",
  },
  {
    title: "5 Cap Table Mistakes That Cost Founders Millions",
    excerpt: "From uncapped SAFEs to missing pro-rata rights — the most common equity mistakes early-stage founders make and how to avoid them before it's too late.",
    category: "Fundraising",
    date: "Jan 2026",
    readTime: "9 min",
  },
  {
    title: "When to Raise: Timing Your Series A",
    excerpt: "How confidence intervals help you avoid raising too early or too late. A data-driven approach to the most consequential timing decision founders face.",
    category: "Fundraising",
    date: "Jan 2026",
    readTime: "6 min",
  },
  {
    title: "Building a Data-Driven Culture",
    excerpt: "The best founders don't just track metrics — they build systems where every team member understands the numbers that matter and acts on them weekly.",
    category: "Founder Stories",
    date: "Dec 2025",
    readTime: "7 min",
  },
  {
    title: "The Founder's Guide to Unit Economics",
    excerpt: "LTV, CAC, payback period, and contribution margin explained with real startup examples. The metrics investors actually care about and how to improve them.",
    category: "Financial Planning",
    date: "Dec 2025",
    readTime: "6 min",
  },
];

export default function BlogPage() {
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
              <article
                key={post.title}
                className="rounded-xl border bg-card overflow-hidden"
                data-testid={`card-blog-${index}`}
              >
                <div className="relative h-40 bg-gradient-to-br from-primary/20 to-purple-500/20">
                  <Badge
                    variant="secondary"
                    className="absolute top-3 right-3"
                    data-testid={`badge-coming-soon-${index}`}
                  >
                    Coming Soon
                  </Badge>
                </div>
                <div className="p-5">
                  <Badge variant="secondary" data-testid={`badge-category-${index}`}>
                    {post.category}
                  </Badge>
                  <h2 className="mt-3 font-semibold text-foreground" data-testid={`text-blog-post-title-${index}`}>
                    {post.title}
                  </h2>
                  <p className="mt-2 text-sm text-muted-foreground line-clamp-2" data-testid={`text-blog-excerpt-${index}`}>
                    {post.excerpt}
                  </p>
                  <div className="mt-4 flex items-center gap-3 flex-wrap text-xs text-muted-foreground">
                    <span data-testid={`text-blog-date-${index}`}>{post.date}</span>
                    <span>·</span>
                    <span className="flex items-center gap-1" data-testid={`text-blog-readtime-${index}`}>
                      <Clock className="h-3 w-3" />
                      {post.readTime}
                    </span>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
