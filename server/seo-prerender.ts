import { blogPosts } from "./seo-data";

const SITE_URL = "https://founderconsole.ai";
const OG_IMAGE = `${SITE_URL}/og-image.png`;

interface PageMeta {
  title: string;
  description: string;
  canonical: string;
  ogType?: string;
  robots?: string;
  jsonLd?: object[];
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

function getPageMeta(path: string): PageMeta | null {
  if (path === "/" || path === "") {
    return {
      title: "FounderConsole — AI Decision Simulator for Founders",
      description: "FounderConsole is the AI-powered decision simulator for startup founders. Monte Carlo simulations, AI copilot, fundraising CRM, and 37 data connectors — replace spreadsheets with simulations.",
      canonical: SITE_URL + "/",
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

  if (path === "/survival-simulator") {
    return {
      title: "Startup Survival Simulator | FounderConsole",
      description: "Free startup survival probability calculator. Enter your financials and get AI-powered survival analysis with Monte Carlo simulations.",
      canonical: SITE_URL + "/survival-simulator",
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

  result = result.replace(
    /<script\s+type="application\/ld\+json">[\s\S]*?<\/script>/,
    (meta.jsonLd || []).map((ld) => `<script type="application/ld+json">${JSON.stringify(ld)}</script>`).join("\n    ")
  );

  return result;
}
