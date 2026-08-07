import { blogPosts, blogPostContent } from "./seo-data";

const SITE_URL = "https://founderconsole.ai";
const OG_IMAGE = `${SITE_URL}/og-image.png`;

interface PageMeta {
  title: string;
  description: string;
  canonical: string;
  ogType?: string;
  ogImage?: string;
  robots?: string;
  jsonLd?: object[];
  bodyContent?: string;
}

const landingFaqs = [
  { q: "What is FounderConsole?", a: "FounderConsole is an AI-powered financial intelligence platform for startups. It connects your financial data, builds a digital twin of your company, runs Monte Carlo simulations, and provides AI-powered strategic recommendations." },
  { q: "Is FounderConsole free?", a: "Yes. All features are free during the public beta, including Monte Carlo simulations, AI copilot, cap table management, 37 data connectors, and board deck generation. No credit card is required." },
  { q: "How does FounderConsole help with fundraising?", a: "FounderConsole includes a Fundraising OS with cap table management, dilution modeling, investor CRM, SAFE conversion modeling, and exit waterfall analysis." },
  { q: "What data sources can I connect?", a: "FounderConsole supports 37 data connectors including Stripe, QuickBooks, Xero, Mercury, Brex, Plaid, Gusto, HubSpot, Shopify, Salesforce, and more." },
  { q: "What is a Monte Carlo simulation?", a: "Monte Carlo simulation runs your financial model thousands of times with slightly different inputs each time, producing a probability distribution instead of a single forecast." },
  { q: "How is this different from a spreadsheet?", a: "Spreadsheets give you one forecast. FounderConsole runs thousands of scenarios, accounts for uncertainty, connects to live data, and uses AI to generate insights." },
  { q: "What is a startup digital twin?", a: "A digital twin is a continuously updated virtual representation of your company that reflects your current financial reality without manual updates." },
  { q: "How long does setup take?", a: "Most founders are up and running in under five minutes. Connect your primary data source and FounderConsole automatically builds your digital twin." },
];

function buildLandingBodyContent(): string {
  const faqHtml = landingFaqs.map((f) =>
    `<section><h3>${escapeHtml(f.q)}</h3><p>${escapeHtml(f.a)}</p></section>`
  ).join("");

  return `<article>
<h1>FounderConsole — The Flight Simulator for Founders</h1>
<p>FounderConsole is the AI-powered decision simulator for startup founders. Connect your company data, simulate the future, and get AI-powered decisions. Run your startup like a simulation.</p>
<h2>How it works</h2>
<ol>
<li><strong>Connect your data</strong> — Link Stripe, QuickBooks, or upload a CSV. Your financial data flows in automatically.</li>
<li><strong>Your company becomes a Digital Twin</strong> — We build a live model of your startup, validated, structured, and ready for simulation.</li>
<li><strong>Run simulations</strong> — Test hiring plans, pricing changes, fundraising timing, and growth strategies before committing.</li>
<li><strong>AI recommends decisions</strong> — Get ranked recommendations backed by data, with narratives you can defend to your board.</li>
</ol>
<h2>Core capabilities</h2>
<ul>
<li><strong>Digital Twin</strong> — Your company modeled in real time. Every financial metric, team member, and data source unified into a living digital representation.</li>
<li><strong>Monte Carlo Simulator</strong> — Test decisions before making them. Run thousands of scenarios to see P10/P50/P90 outcomes.</li>
<li><strong>AI Founder Copilot</strong> — Ask strategic questions in plain English. Get recommendations from parallel AI agents specialized in finance, strategy, and market analysis.</li>
<li><strong>Decision Engine</strong> — Track every decision with full context. Learn from outcomes, compare scenarios, and build institutional memory.</li>
</ul>
<h2>Frequently Asked Questions</h2>
${faqHtml}
</article>`;
}

function buildBlogListBodyContent(): string {
  const postsHtml = blogPosts.map((p) =>
    `<article><h2><a href="/blog/${escapeHtml(p.slug)}">${escapeHtml(p.title)}</a></h2><p>${escapeHtml(p.excerpt)}</p><span>${escapeHtml(p.date)} — ${escapeHtml(p.author)}</span></article>`
  ).join("");
  return `<section><h1>Insights for Founders</h1><p>Practical decision science for founders. Runway, fundraising, hiring, and strategy — through the lens of probability.</p>${postsHtml}</section>`;
}

function buildBlogPostBodyContent(slug: string): string | null {
  const post = blogPosts.find((p) => p.slug === slug);
  const content = blogPostContent[slug];
  if (!post) return null;
  const paragraphs = content || [];
  const bodyParagraphs = paragraphs.map((p: string) => {
    if (p.startsWith("## ")) return `<h2>${escapeHtml(p.replace("## ", ""))}</h2>`;
    return `<p>${escapeHtml(p)}</p>`;
  }).join("");
  return `<article><h1>${escapeHtml(post.title)}</h1><p><em>By ${escapeHtml(post.author)} — ${escapeHtml(post.date)}</em></p>${bodyParagraphs}</article>`;
}

function buildRunwayCalculatorBodyContent(): string {
  return `<article>
<h1>Startup Runway Calculator</h1>
<p>Enter your financials to instantly see how many months of runway you have, when you'll run out of cash, and how growth affects your timeline.</p>
<h2>How to Calculate Startup Runway: The Complete Guide</h2>
<p>Startup runway is the number of months your company can continue operating before it runs out of cash, assuming no additional funding. It is one of the most important metrics for any early-stage founder because it determines how much time you have to achieve product-market fit, hit growth milestones, or close your next fundraising round.</p>
<p>The basic runway formula is simple: divide your current cash balance by your monthly net burn rate. Net burn is the difference between your monthly expenses and your monthly revenue. If you have $500,000 in the bank and you burn $40,000 per month net, your runway is 12.5 months.</p>
<h3>Why Simple Runway Calculations Are Dangerous</h3>
<p>The problem with the simple formula is that it assumes a constant burn rate. In reality, expenses increase as you hire, revenue fluctuates month-to-month, and unexpected costs arise. A single-point runway estimate gives you false confidence.</p>
<h3>Factors That Affect Your Runway</h3>
<p>Revenue growth rate is the single biggest lever. Customer churn works in the opposite direction. Hiring pace is usually the largest controllable expense. Payment terms and accounts receivable also matter.</p>
<h3>When to Start Fundraising Based on Runway</h3>
<p>Most venture capital firms recommend starting your fundraise when you have 9 to 12 months of runway remaining. This gives you enough time to run a proper process without the desperation that comes from having only 3 months of cash left.</p>
<p>FounderConsole connects to your actual financial data sources and runs Monte Carlo simulations to show you probabilistic runway projections with P10/P50/P90 confidence bands.</p>
</article>`;
}

function getPageMeta(path: string): PageMeta | null {
  if (path === "/" || path === "") {
    return {
      title: "FounderConsole — AI Decision Simulator for Founders",
      description: "FounderConsole is the AI-powered decision simulator for startup founders. Monte Carlo simulations, AI copilot, fundraising CRM, and 37 data connectors — replace spreadsheets with simulations.",
      canonical: SITE_URL + "/",
      bodyContent: buildLandingBodyContent(),
      jsonLd: [
        {
          "@context": "https://schema.org",
          "@type": "Organization",
          name: "FounderConsole",
          url: SITE_URL,
          logo: OG_IMAGE,
          description: "AI-powered financial intelligence platform for startups.",
          sameAs: ["https://twitter.com/founderconsole", "https://linkedin.com/company/founderconsole", "https://github.com/founderconsole"],
        },
        {
          "@context": "https://schema.org",
          "@type": "SoftwareApplication",
          name: "FounderConsole",
          applicationCategory: "BusinessApplication",
          operatingSystem: "Web",
          url: SITE_URL,
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
          featureList: "Monte Carlo Simulation, AI Copilot, Fundraising CRM, Cap Table Management, 37 Data Connectors, Digital Twin",
        },
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: landingFaqs.map((f) => ({
            "@type": "Question",
            name: f.q,
            acceptedAnswer: { "@type": "Answer", text: f.a },
          })),
        },
      ],
    };
  }

  if (path === "/features") {
    return {
      title: "Features — Simulation, AI Copilot, Fundraising CRM & More | FounderConsole",
      description: "Monte Carlo simulation engine, multi-LLM AI copilot, Truth Scan data validation, Fundraising OS with CRM, 37 data connectors, and AI strategic briefings.",
      canonical: SITE_URL + "/features",
    };
  }

  if (path === "/pricing") {
    return {
      title: "Pricing | FounderConsole",
      description: "FounderConsole pricing tiers with fast time-to-value. All features free during public beta — no credit card required.",
      canonical: SITE_URL + "/pricing",
    };
  }

  if (path === "/about") {
    return {
      title: "About | FounderConsole",
      description: "Learn about FounderConsole — the AI-powered financial intelligence platform built for startup founders.",
      canonical: SITE_URL + "/about",
    };
  }

  if (path === "/contact") {
    return {
      title: "Contact | FounderConsole",
      description: "Get in touch with the FounderConsole team.",
      canonical: SITE_URL + "/contact",
    };
  }

  if (path === "/faq") {
    return {
      title: "FAQ | FounderConsole",
      description: "FounderConsole FAQ: product, data, pricing, accuracy, and explainability.",
      canonical: SITE_URL + "/faq",
    };
  }

  if (path === "/demo") {
    return {
      title: "Demo | FounderConsole",
      description: "See FounderConsole in action with an interactive demo.",
      canonical: SITE_URL + "/demo",
    };
  }

  if (path === "/blog") {
    return {
      title: "Blog — Startup Finance, Runway Planning & AI Strategy | FounderConsole",
      description: "Insights for startup founders: runway planning, Monte Carlo simulations, SaaS benchmarks, cap table management, and AI-powered financial tools.",
      canonical: SITE_URL + "/blog",
      bodyContent: buildBlogListBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        name: "FounderConsole Blog",
        url: SITE_URL + "/blog",
      }],
    };
  }

  if (path === "/tools/runway-calculator") {
    return {
      title: "Free Startup Runway Calculator | FounderConsole",
      description: "Calculate your startup runway in seconds. Enter cash on hand, monthly revenue, expenses, and growth rate to see how many months until you need to raise.",
      canonical: SITE_URL + "/tools/runway-calculator",
      bodyContent: buildRunwayCalculatorBodyContent(),
      jsonLd: [{
        "@context": "https://schema.org",
        "@type": "WebApplication",
        name: "Startup Runway Calculator",
        url: SITE_URL + "/tools/runway-calculator",
        applicationCategory: "BusinessApplication",
        operatingSystem: "Web",
        offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
      }],
    };
  }

  const runwayIndustryMatch = path.match(/^\/runway\/([a-z0-9-]+)$/);
  if (runwayIndustryMatch) {
    const slug = runwayIndustryMatch[1];
    const known = ["saas","ecommerce","fintech","marketplace","ai","hardware","biotech","devtools"];
    if (known.includes(slug)) {
      const titleMap: Record<string,string> = {
        saas: "SaaS Startup Runway Calculator",
        ecommerce: "Ecommerce Startup Runway Calculator",
        fintech: "Fintech Startup Runway Calculator",
        marketplace: "Marketplace Startup Runway Calculator",
        ai: "AI Startup Runway Calculator",
        hardware: "Hardware Startup Runway Calculator",
        biotech: "Biotech Startup Runway Calculator",
        devtools: "Developer Tools Startup Runway Calculator",
      };
      const title = titleMap[slug];
      return {
        title: `${title} | FounderConsole`,
        description: `Free ${slug} startup runway calculator with industry benchmarks, Monte Carlo simulation, and AI-powered recommendations tuned for ${slug} economics.`,
        canonical: `${SITE_URL}/runway/${slug}`,
        jsonLd: [{
          "@context": "https://schema.org",
          "@type": "WebApplication",
          name: title,
          url: `${SITE_URL}/runway/${slug}`,
          applicationCategory: "BusinessApplication",
          operatingSystem: "Web",
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
        }],
      };
    }
  }

  if (path === "/embed/survival") {
    return {
      title: "Startup Runway Widget — FounderConsole",
      description: "Embeddable startup runway calculator widget powered by FounderConsole.",
      canonical: `${SITE_URL}/embed/survival`,
      robots: "noindex, follow",
    };
  }

  if (path === "/survival-simulator") {
    return {
      title: "Startup Survival Simulator | FounderConsole",
      description: "Free startup survival probability calculator. Enter your financials and get AI-powered survival analysis with Monte Carlo simulations.",
      canonical: SITE_URL + "/survival-simulator",
    };
  }

  if (path === "/default-alive") {
    return {
      title: "Default Alive or Default Dead? Free Calculator for Founders | FounderConsole",
      description: "Paul Graham's default alive test, as a calculator. Enter cash, revenue, expenses and growth rate to find out whether you reach profitability before the money runs out — and what it would take to flip the answer.",
      canonical: SITE_URL + "/default-alive",
      // Server-rendered body so the page is legible to crawlers and to the AI
      // assistants that increasingly answer "am I default alive" without
      // executing JavaScript. The interactive verdict is the client's job.
      bodyContent: `<article>
<h1>Default Alive or Default Dead?</h1>
<p>Paul Graham's test, in 30 seconds: at your current growth rate and current expenses, do you reach profitability before the money runs out?</p>
<h2>What default alive actually means</h2>
<p>Paul Graham coined the term in 2015. The question is simple: assuming your current expenses and current growth rate, would you make it to profitability on the money you already have?</p>
<p>If yes, you are default alive. Raising becomes a choice about going faster rather than a condition of survival, and that changes how you negotiate.</p>
<p>If no, you are default dead, and the important part is that most founders in that position do not know it. The number feels abstract until you watch the date land in a specific month.</p>
<h2>The caveat most calculators leave out</h2>
<p>The test assumes expenses stay flat while revenue compounds. Almost no growing company works that way — you hire, and costs climb with revenue. This calculator lets you switch expense growth on. If your verdict flips the moment you allow expenses to grow at all, the "alive" answer was fragile to begin with.</p>
<h2>The three levers</h2>
<p>If you come out default dead, there are only three things that change the answer: cut expenses, grow faster, or raise more. The calculator shows how far each one would have to move on your specific numbers — how large a cut, what growth rate, and how much cash.</p>
<h2>Why a single projection is not enough</h2>
<p>This calculator holds one growth rate steady. Real revenue is lumpy, and the month your biggest customer churns is not the average month. FounderConsole runs the same question thousands of times over your actual financials and returns the odds rather than one line.</p>
</article>`,
      jsonLd: [
        {
          "@context": "https://schema.org",
          "@type": "WebApplication",
          name: "Default Alive or Default Dead Calculator",
          url: SITE_URL + "/default-alive",
          applicationCategory: "BusinessApplication",
          operatingSystem: "Web",
          offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
          description: "Free calculator implementing Paul Graham's default alive test.",
          creator: { "@type": "Organization", name: "FounderConsole", url: SITE_URL },
        },
        {
          "@context": "https://schema.org",
          "@type": "FAQPage",
          mainEntity: [
            {
              "@type": "Question",
              name: "What does default alive mean?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "A startup is default alive if, at its current growth rate and current expenses, it would reach profitability on the money it already has — without raising again.",
              },
            },
            {
              "@type": "Question",
              name: "What does default dead mean?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "A startup is default dead if it runs out of cash before reaching profitability on its current trajectory. Survival then depends on raising more money, cutting expenses, or growing faster.",
              },
            },
            {
              "@type": "Question",
              name: "Who coined default alive or default dead?",
              acceptedAnswer: {
                "@type": "Answer",
                text: "Paul Graham, co-founder of Y Combinator, introduced the framing in a 2015 essay as a way for founders to know whether raising money is a choice or a necessity.",
              },
            },
          ],
        },
      ],
    };
  }

  const survivalShareMatch = path.match(/^\/survival\/([A-Za-z0-9_-]+)$/);
  if (survivalShareMatch) {
    const simId = survivalShareMatch[1];
    return {
      title: "My Startup Survival Score — FounderConsole",
      description: "I just simulated my startup's survival probability with FounderConsole. Run yours free in 60 seconds.",
      canonical: `${SITE_URL}/survival/${simId}`,
      ogType: "article",
      ogImage: `${SITE_URL}/api/survival-sim/og-image/${simId}.png`,
    };
  }

  if (path === "/privacy") {
    return {
      title: "Privacy Policy | FounderConsole",
      description: "FounderConsole privacy policy. How we handle your data.",
      canonical: SITE_URL + "/privacy",
    };
  }

  if (path === "/terms") {
    return {
      title: "Terms of Service | FounderConsole",
      description: "FounderConsole terms of service.",
      canonical: SITE_URL + "/terms",
    };
  }

  const blogMatch = path.match(/^\/blog\/(.+)$/);
  if (blogMatch) {
    const slug = blogMatch[1];
    const post = blogPosts.find((p) => p.slug === slug);
    if (post) {
      const isoDate = new Date(post.date).toISOString().split("T")[0];
      return {
        title: `${post.title} | FounderConsole`,
        description: post.excerpt,
        canonical: `${SITE_URL}/blog/${slug}`,
        ogType: "article",
        bodyContent: buildBlogPostBodyContent(slug) || undefined,
        jsonLd: [{
          "@context": "https://schema.org",
          "@type": "Article",
          headline: post.title,
          description: post.excerpt,
          datePublished: isoDate,
          author: { "@type": "Person", name: post.author },
          publisher: { "@type": "Organization", name: "FounderConsole", logo: { "@type": "ImageObject", url: OG_IMAGE } },
          image: OG_IMAGE,
          mainEntityOfPage: `${SITE_URL}/blog/${slug}`,
        }],
      };
    }
  }

  return null;
}

function escapeHtml(str: string): string {
  return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

export function injectSEO(html: string, path: string): string {
  const meta = getPageMeta(path);
  if (!meta) {
    return html;
  }

  const ogType = meta.ogType || "website";
  const robots = meta.robots || "index, follow";
  const safeTitle = escapeHtml(meta.title);
  const safeDesc = escapeHtml(meta.description);

  let result = html;

  result = result.replace(/<title>[^<]*<\/title>/, `<title>${safeTitle}</title>`);

  result = result.replace(
    /<meta\s+name="description"\s+content="[^"]*"\s*\/?>/,
    `<meta name="description" content="${safeDesc}" />`
  );

  result = result.replace(
    /<link\s+rel="canonical"\s+href="[^"]*"\s*\/?>/,
    `<link rel="canonical" href="${meta.canonical}" />`
  );

  result = result.replace(
    /<meta\s+name="robots"\s+content="[^"]*"\s*\/?>/,
    `<meta name="robots" content="${robots}" />`
  );

  result = result.replace(
    /<meta\s+property="og:title"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:title" content="${safeTitle}" />`
  );
  result = result.replace(
    /<meta\s+property="og:description"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:description" content="${safeDesc}" />`
  );
  result = result.replace(
    /<meta\s+property="og:url"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:url" content="${meta.canonical}" />`
  );
  result = result.replace(
    /<meta\s+property="og:type"\s+content="[^"]*"\s*\/?>/,
    `<meta property="og:type" content="${ogType}" />`
  );

  result = result.replace(
    /<meta\s+name="twitter:title"\s+content="[^"]*"\s*\/?>/,
    `<meta name="twitter:title" content="${safeTitle}" />`
  );
  result = result.replace(
    /<meta\s+name="twitter:description"\s+content="[^"]*"\s*\/?>/,
    `<meta name="twitter:description" content="${safeDesc}" />`
  );

  if (meta.ogImage) {
    const safeImg = escapeHtml(meta.ogImage);
    result = result.replace(
      /<meta\s+property="og:image"\s+content="[^"]*"\s*\/?>/,
      `<meta property="og:image" content="${safeImg}" />`
    );
    result = result.replace(
      /<meta\s+name="twitter:image"\s+content="[^"]*"\s*\/?>/,
      `<meta name="twitter:image" content="${safeImg}" />`
    );
  }

  if (meta.jsonLd && meta.jsonLd.length > 0) {
    const newLdScripts = meta.jsonLd.map((ld) => `<script type="application/ld+json">${JSON.stringify(ld)}</script>`).join("\n    ");
    let replaced = false;
    result = result.replace(/<script\s+type="application\/ld\+json">[\s\S]*?<\/script>/g, (match) => {
      if (!replaced) {
        replaced = true;
        return newLdScripts;
      }
      return "";
    });
  }

  if (meta.bodyContent) {
    result = result.replace(
      '<div id="root"></div>',
      `<div id="root"></div><div id="ssr-content" style="position:absolute;left:-9999px;top:-9999px;overflow:hidden;width:1px;height:1px">${meta.bodyContent}</div>`
    );
  }

  return result;
}
