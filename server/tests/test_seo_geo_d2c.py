"""SEO / GEO guards for the D2C content and crawler files.

Python on purpose: pytest collects everything under server/tests, while each
TypeScript test has to be listed by hand in pr-checks.yml. The behavioural half
(prerendered HTML, app-shell noindex, the calculator's maths) lives in
server/tests/d2c-margin.test.ts and server/tests/seo-geo.test.ts.

What is guarded:
  1. robots.txt lets AI search and answer engines crawl the marketing site and
     keeps /api out, for every user-agent group.
  2. The D2C worked example quoted in llms.txt is the one the calculator
     computes (client/src/lib/tools/d2cMargin.ts, pinned by d2c-margin.test.ts).
     If the maths changes, this fails before a published figure goes stale.
  3. Every D2C blog post links to the D2C calculator and to signup, and the
     calculator page is in the sitemap and the tools hub.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ROBOTS = ROOT / "client" / "public" / "robots.txt"
LLMS = ROOT / "client" / "public" / "llms.txt"
SITEMAP = ROOT / "client" / "public" / "sitemap.xml"
POSTS = ROOT / "client" / "src" / "data" / "blog-posts.ts"
MATHS = ROOT / "client" / "src" / "lib" / "tools" / "d2cMargin.ts"
TOOLS_INDEX = ROOT / "client" / "src" / "pages" / "tools-index.tsx"

AI_BOTS = (
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "Claude-SearchBot",
    "PerplexityBot",
    "Google-Extended",
)
D2C_TOOL = "/tools/d2c-contribution-margin"


def robots_groups() -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    current: list[str] = []
    for line in ROBOTS.read_text().splitlines():
        line = line.strip()
        if line.lower().startswith("user-agent:"):
            agent = line.split(":", 1)[1].strip()
            current = groups.setdefault(agent, [])
        elif line and not line.startswith("#") and current is not None:
            current.append(line)
    return groups


def test_robots_invites_ai_crawlers_and_blocks_the_api():
    groups = robots_groups()
    for bot in (*AI_BOTS, "*"):
        assert bot in groups, f"robots.txt has no group for {bot}"
        rules = groups[bot]
        assert "Allow: /" in rules, f"{bot} is not allowed on the marketing site"
        assert "Disallow: /" not in rules, f"{bot} is blocked from the whole site"
        assert "Disallow: /api/" in rules, f"{bot} may crawl /api/"
    assert "Sitemap: https://founderconsole.ai/sitemap.xml" in ROBOTS.read_text()


def test_llms_txt_worked_example_matches_the_calculator_defaults():
    maths = MATHS.read_text()
    block = maths[maths.index("D2C_WORKED_EXAMPLE: D2cMarginInputs = {"):]
    block = block[: block.index("};")]
    defaults = dict(re.findall(r"(\w+):\s*([\d.]+)", block))
    assert defaults == {
        "aov": "1200",
        "orders": "2000",
        "rtoPct": "18",
        "returnPct": "5",
        "codPct": "55",
        "cogsPerOrder": "420",
        "packagingPerOrder": "30",
        "forwardShipping": "70",
        "reverseShipping": "70",
        "gatewayPct": "2",
        "codFee": "40",
        "marketing": "600000",
    }, "the calculator's worked example changed; update llms.txt, the blog posts and d2c-margin.test.ts"

    text = " ".join(LLMS.read_text().split())
    for fact in (
        "CM1 (contribution margin 1) = net revenue - COGS",
        "Break-even MER = 1 / CM2 margin",
        "Net revenue Rs 18.70 lakh",
        "CM3 Rs 3.27 lakh (17.5%)",
        "MER 3.12x vs break-even MER 2.02x",
        "At 30% RTO, CM3 falls to Rs 1.38 lakh",
        D2C_TOOL,
    ):
        assert fact in text, f"llms.txt lost: {fact!r}"
    # The published-facts guard still holds alongside the new section.
    assert "34 read-only data connectors" in text
    assert "every feature is free during the public beta" in text.lower()


def d2c_post_blocks() -> dict[str, str]:
    src = POSTS.read_text(encoding="utf-8")
    out: dict[str, str] = {}
    for chunk in re.split(r"\n  \{\n", src)[1:]:
        slug = re.search(r'slug:\s*"([^"]+)"', chunk)
        category = re.search(r'category:\s*"([^"]+)"', chunk)
        if slug and category and category.group(1) == "D2C Finance":
            out[slug.group(1)] = chunk
    return out


def test_d2c_posts_link_the_calculator_and_signup():
    blocks = d2c_post_blocks()
    assert len(blocks) >= 6, f"expected the six D2C posts, found {sorted(blocks)}"
    for slug, chunk in blocks.items():
        assert f"]({D2C_TOOL})" in chunk, f"{slug} does not link the D2C calculator"
        assert "](/signup)" in chunk, f"{slug} has no in-body signup link"
        # No fabricated proof: these posts must not claim customers or testimonials.
        assert not re.search(r"\b\d[\d,]* (brands|customers|founders) (use|trust)", chunk), slug


def test_calculator_page_is_in_the_sitemap_and_the_hub():
    assert f"<loc>https://founderconsole.ai{D2C_TOOL}</loc>" in SITEMAP.read_text()
    for slug in d2c_post_blocks():
        assert f"<loc>https://founderconsole.ai/blog/{slug}</loc>" in SITEMAP.read_text(), slug
    assert f'href: "{D2C_TOOL}"' in TOOLS_INDEX.read_text()
