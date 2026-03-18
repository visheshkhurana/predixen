import { Link, useRoute } from "wouter";
import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useSEO } from "@/lib/seo";
import { Clock, ArrowLeft, ArrowRight, ChevronRight } from "lucide-react";
import { blogPosts } from "@/data/blog-posts";

function BlogList() {
  useSEO({
    title: "Blog — Startup Finance, Runway Planning & AI Strategy | FounderConsole",
    description:
      "Insights for startup founders: runway planning, Monte Carlo simulations, SaaS benchmarks, cap table management, fundraising timing, and AI-powered financial tools.",
    path: "/blog",
    jsonLd: {
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      name: "FounderConsole Blog",
      url: "https://founderconsole.ai/blog",
      description: "Insights for startup founders on runway planning, Monte Carlo simulations, SaaS benchmarks, and AI-powered financial decision-making.",
    },
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
            {blogPosts.map((post, index) => (
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

function dateToISO(dateStr: string): string {
  const d = new Date(dateStr);
  return isNaN(d.getTime()) ? "" : d.toISOString().split("T")[0];
}

function BlogPost({ slug }: { slug: string }) {
  const post = blogPosts.find((p) => p.slug === slug);
  const isoDate = post ? dateToISO(post.date) : "";

  useSEO({
    title: post ? `${post.title} | FounderConsole` : "Blog | FounderConsole",
    description: post?.excerpt || "",
    path: `/blog/${slug}`,
    ogType: post ? "article" : "website",
    articleMeta: post ? { publishedTime: isoDate, author: post.author } : undefined,
    jsonLd: post
      ? {
          "@context": "https://schema.org",
          "@type": "BlogPosting",
          headline: post.title,
          description: post.excerpt,
          datePublished: isoDate,
          author: { "@type": "Person", name: post.author },
          publisher: {
            "@type": "Organization",
            name: "FounderConsole",
            logo: { "@type": "ImageObject", url: "https://founderconsole.ai/og-image.png" },
          },
          image: "https://founderconsole.ai/og-image.png",
          mainEntityOfPage: `https://founderconsole.ai/blog/${slug}`,
        }
      : undefined,
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
