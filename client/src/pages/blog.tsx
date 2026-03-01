import { MarketingLayout } from "@/components/marketing/MarketingLayout";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Clock, Calendar } from "lucide-react";

const blogPosts = [
  {
    id: 1,
    title: "How to Calculate Your True Runway",
    excerpt: "Most founders overestimate their runway by 30-40%. Learn the Monte Carlo approach to calculating probabilistic runway with P10, P50, and P90 confidence intervals.",
    date: "Jul 12, 2025",
    category: "Financial Planning",
    readTime: "8 min read",
    gradient: "from-primary/20 to-primary/5",
  },
  {
    id: 2,
    title: "Monte Carlo Simulations: A Founder's Guide",
    excerpt: "Stop relying on single-point forecasts. Discover how running thousands of scenarios can reveal the true range of outcomes for your startup's finances.",
    date: "Jul 8, 2025",
    category: "Financial Planning",
    readTime: "12 min read",
    gradient: "from-chart-3/20 to-chart-3/5",
  },
  {
    id: 3,
    title: "5 Cap Table Mistakes That Cost Founders Millions",
    excerpt: "From uncapped SAFEs to misunderstanding pro-rata rights, these common cap table errors can silently erode your ownership. Here's how to avoid them.",
    date: "Jul 3, 2025",
    category: "Fundraising",
    readTime: "10 min read",
    gradient: "from-chart-2/20 to-chart-2/5",
  },
  {
    id: 4,
    title: "Why Your Board Deck Isn't Working (And How to Fix It)",
    excerpt: "Investors want forward-looking intelligence, not backward-looking reports. Learn how to transform your board deck from a status update into a strategic tool.",
    date: "Jun 28, 2025",
    category: "Fundraising",
    readTime: "7 min read",
    gradient: "from-chart-4/20 to-chart-4/5",
  },
  {
    id: 5,
    title: "Introducing Truth Scan: AI-Powered Data Validation",
    excerpt: "We built Truth Scan to solve the #1 problem in startup finance — bad data leading to bad decisions. Here's how our anomaly detection pipeline works under the hood.",
    date: "Jun 22, 2025",
    category: "Product Updates",
    readTime: "6 min read",
    gradient: "from-chart-5/20 to-chart-5/5",
  },
  {
    id: 6,
    title: "From Seed to Series A: One Founder's Data-Driven Journey",
    excerpt: "How the founder of a health-tech startup used scenario modeling and sensitivity analysis to negotiate a 40% better valuation in their Series A round.",
    date: "Jun 15, 2025",
    category: "Founder Stories",
    readTime: "9 min read",
    gradient: "from-primary/20 to-chart-2/5",
  },
];

const categoryColors: Record<string, "default" | "secondary" | "outline"> = {
  "Financial Planning": "secondary",
  "Fundraising": "outline",
  "Product Updates": "default",
  "Founder Stories": "secondary",
};

export default function BlogPage() {
  return (
    <MarketingLayout>
      <section className="py-16 md:py-24" data-testid="section-blog-hero">
        <div className="max-w-4xl mx-auto px-4 text-center">
          <h1 className="text-4xl md:text-5xl font-bold tracking-tight mb-4" data-testid="text-blog-title">
            Insights for Founders
          </h1>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto" data-testid="text-blog-subtitle">
            Practical guides on financial planning, fundraising strategy, and building with data.
            Written by founders and operators who have been in your shoes.
          </p>
        </div>
      </section>

      <section className="pb-16 md:pb-24" data-testid="section-blog-grid">
        <div className="max-w-6xl mx-auto px-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {blogPosts.map((post) => (
              <Card key={post.id} className="overflow-visible" data-testid={`card-blog-${post.id}`}>
                <div className={`h-40 rounded-t-xl bg-gradient-to-br ${post.gradient} flex items-center justify-center`}>
                  <Badge variant="outline" className="bg-background/80 backdrop-blur-sm" data-testid={`badge-coming-soon-${post.id}`}>
                    Coming Soon
                  </Badge>
                </div>
                <CardContent className="p-5 pt-5">
                  <div className="flex items-center gap-2 flex-wrap mb-3">
                    <Badge variant={categoryColors[post.category] || "secondary"} data-testid={`badge-category-${post.id}`}>
                      {post.category}
                    </Badge>
                  </div>
                  <h2 className="text-lg font-semibold mb-2 line-clamp-2" data-testid={`text-blog-title-${post.id}`}>
                    {post.title}
                  </h2>
                  <p className="text-sm text-muted-foreground line-clamp-2 mb-4" data-testid={`text-blog-excerpt-${post.id}`}>
                    {post.excerpt}
                  </p>
                  <div className="flex items-center gap-4 text-xs text-muted-foreground flex-wrap">
                    <span className="flex items-center gap-1" data-testid={`text-blog-date-${post.id}`}>
                      <Calendar className="w-3 h-3" />
                      {post.date}
                    </span>
                    <span className="flex items-center gap-1" data-testid={`text-blog-readtime-${post.id}`}>
                      <Clock className="w-3 h-3" />
                      {post.readTime}
                    </span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>
    </MarketingLayout>
  );
}
