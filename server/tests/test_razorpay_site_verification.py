"""Razorpay website verification: the CI half of server/tests/legal-pages-ssr.test.ts.

Razorpay's reviewer checks for Terms, Privacy, a Refund & Cancellation policy,
a Contact page naming the legal business, and visible product pricing. The
TypeScript test renders the prerender and asserts behaviour, but pr-checks.yml
lists TS tests by hand and is hold-listed, so it does not run in CI. The pytest
job does. What this file can honestly cover is source invariants:

  1. ONE PRICE. shared/pricing.json is the only place the Razorpay prices are
     written. plans.py (what checkout charges) loads it, and the public pages
     import it rather than retyping a number.
  2. NO PLACEHOLDER RENDERS. client/src/data/legal.ts holds the owner-to-fill
     constants. Nothing outside that file reads them raw; every renderer goes
     through legalValue()/registeredAddress()/grievanceOfficer(), which drop a
     "TODO" value.
  3. THE PAGE IS REACHABLE. /refund-policy is a client route, a known route
     (else it 404s), in the sitemap, in the footer's Legal group next to Terms,
     and /cancellation-policy and /refunds redirect to it.
  4. THE GATE. /pricing shows the paid plan only when billing is live, using the
     same rule as razorpay_enabled().
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from server.core import plans

ROOT = Path(__file__).resolve().parents[2]
PRICING_JSON = ROOT / "shared" / "pricing.json"
LEGAL = ROOT / "client" / "src" / "data" / "legal.ts"
PUBLIC_PRICING = ROOT / "client" / "src" / "data" / "public-pricing.ts"
PRERENDER = ROOT / "server" / "seo-prerender.ts"
PRICING_PAGE = ROOT / "client" / "src" / "pages" / "pricing.tsx"
REFUND_PAGE = ROOT / "client" / "src" / "pages" / "refund-policy.tsx"
TERMS_PAGE = ROOT / "client" / "src" / "pages" / "terms.tsx"
LAYOUT = ROOT / "client" / "src" / "components" / "marketing" / "MarketingLayout.tsx"
BILLING_GATE = ROOT / "server" / "billing-gate.ts"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_comments(ts: str) -> str:
    ts = re.sub(r"/\*[\s\S]*?\*/", "", ts)
    return re.sub(r"(?m)^[ \t]*//.*$", "", ts)


# 1. One price ---------------------------------------------------------------

def test_plans_py_charges_the_shared_prices():
    data = json.loads(read(PRICING_JSON))
    starter = data["regional_monthly_prices"]["starter"]
    assert starter == {"INR": 3000, "USD": 39, "AED": 149}
    assert data["annual_multiplier"] == 10
    for currency, monthly in starter.items():
        assert plans.get_regional_price("starter", currency, "monthly")["amount"] == monthly
        assert plans.get_regional_price("starter", currency, "annual")["amount"] == monthly * 10
    assert plans.ANNUAL_LABEL == data["annual_label"] == "2 months free"


def test_public_pages_import_the_price_rather_than_retype_it():
    src = read(PUBLIC_PRICING)
    assert "shared/pricing.json" in src
    code = strip_comments(src)
    for literal in ("3000", "3,000", "30000", "149", "1490", "390"):
        assert literal not in code, f"public-pricing.ts retypes a price: {literal}"
    assert re.search(r"\b39\b", code) is None
    # The prerender and the React pages take the price from that module.
    for path in (PRERENDER, PRICING_PAGE, REFUND_PAGE):
        text = read(path)
        assert "data/public-pricing" in text, path
        assert "₹3,000" not in strip_comments(text), f"{path}: hardcoded INR price"


# 2. No placeholder renders ------------------------------------------------

OWNER_CONSTANTS = ("LEGAL_ENTITY_ADDRESS", "GRIEVANCE_OFFICER_NAME", "GRIEVANCE_OFFICER_EMAIL")


def test_owner_constants_are_declared_once_and_never_read_raw():
    legal = read(LEGAL)
    for name in OWNER_CONSTANTS:
        assert re.search(rf"export const {name} = \"[^\"]*\";", legal), name
    for path in list((ROOT / "client" / "src").rglob("*.ts*")) + [PRERENDER]:
        if path == LEGAL:
            continue
        text = read(path)
        for name in OWNER_CONSTANTS:
            assert name not in text, f"{path} reads {name} raw; use legalValue()/registeredAddress()/grievanceOfficer()"


def test_legal_value_drops_the_todo_prefix():
    legal = read(LEGAL)
    body = legal[legal.index("export function legalValue"):]
    body = body[: body.index("\n}\n")]
    assert "LEGAL_PLACEHOLDER_PREFIX" in body and "return null" in body
    assert 'export const LEGAL_PLACEHOLDER_PREFIX = "TODO";' in legal
    assert "registeredAddress()" in read(PRERENDER)
    assert "grievanceOfficer()" in read(PRERENDER)


def test_refund_window_is_an_owner_decision_constant():
    legal = read(LEGAL)
    m = re.search(r"OWNER DECISION[\s\S]{0,600}?export const FIRST_PAYMENT_REFUND_WINDOW_DAYS = (\d+);", legal)
    assert m, "FIRST_PAYMENT_REFUND_WINDOW_DAYS must carry its OWNER DECISION comment"
    assert m.group(1) == "7"
    # Terms must not keep a second, contradicting window.
    terms = read(TERMS_PAGE)
    assert "within 14 days" not in terms
    assert "FIRST_PAYMENT_REFUND_WINDOW_DAYS" in terms
    assert "processed securely by Stripe" not in terms
    assert "processed securely by Stripe" not in read(PRERENDER)


def test_entity_name_is_the_registered_company():
    legal = read(LEGAL)
    assert 'export const LEGAL_ENTITY_NAME = "ULTRASAFE AI INDIA PRIVATE LIMITED";' in legal
    for page in ("terms.tsx", "privacy.tsx", "contact.tsx", "refund-policy.tsx"):
        text = read(ROOT / "client" / "src" / "pages" / page)
        assert "LegalEntityNotice" in text or "PRODUCT_OF_LINE" in text, page
    for page in ("privacy.tsx", "contact.tsx"):
        assert "GrievanceOfficerText" in read(ROOT / "client" / "src" / "pages" / page), page


# 3. The page is reachable ---------------------------------------------------

def test_refund_policy_is_routed_known_and_in_the_sitemap():
    assert '<Route path="/refund-policy" component={RefundPolicyPage} />' in read(ROOT / "client/src/App.tsx")
    assert '"/refund-policy",' in read(ROOT / "server/known-routes.ts")
    assert "<loc>https://founderconsole.ai/refund-policy</loc>" in read(ROOT / "client/public/sitemap.xml")
    assert 'path: "/refund-policy"' in read(ROOT / "scripts/generate-sitemap.ts")
    redirects = read(ROOT / "server/middleware/legacyRedirects.ts")
    for alias in ("/cancellation-policy", "/refunds"):
        assert f'"{alias}": "/refund-policy"' in redirects, alias
    assert 'if (path === "/refund-policy")' in read(PRERENDER)
    assert 'title: "Refund & Cancellation Policy | FounderConsole"' in read(PRERENDER)


def test_footer_legal_group_lists_the_refund_policy_next_to_terms():
    layout = read(LAYOUT)
    block = layout[layout.index("const footerLegal = ["):]
    block = block[: block.index("];")]
    hrefs = re.findall(r'href: "([^"]+)"', block)
    assert hrefs[:3] == ["/privacy", "/terms", "/refund-policy"], hrefs
    assert "PRODUCT_OF_LINE" in layout


# 4. The gate ----------------------------------------------------------------

def test_pricing_gate_matches_razorpay_enabled():
    gate = strip_comments(read(BILLING_GATE))
    for name in ("BILLING_PROVIDER", "RAZORPAY_KEY_ID", "RAZORPAY_KEY_SECRET", "RAZORPAY_WEBHOOK_SECRET"):
        assert name in gate, name
    assert '=== "razorpay"' in gate
    prerender = read(PRERENDER)
    pricing_block = prerender[prerender.index('if (path === "/pricing")'):]
    pricing_block = pricing_block[: pricing_block.index('if (path === "/refund-policy")')]
    assert "razorpayBillingEnabled()" in pricing_block
    assert 'title: "Pricing | FounderConsole"' in pricing_block  # HAG-471 launch gate
    page = read(PRICING_PAGE)
    assert 'plansData?.payments_enabled && plansData?.provider === "razorpay"' in page
    assert "paidEnabled ? paidTiers : tiers" in page
