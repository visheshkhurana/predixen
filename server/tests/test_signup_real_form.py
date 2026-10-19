"""HAG-238: `/signup` is a URL that can actually create an account.

Why this file is Python: `pr-checks.yml` names every TypeScript test file by hand
as its own step and that workflow is on the hold list, so a new `.test.ts` would
never run in CI. `pytest.ini` sets `testpaths = server/tests`, so this file is
collected automatically with no workflow change.

What was wrong. `/signup` was a marketing article whose only real control was a
button to `/auth?tab=register`, so the page could not do the one thing its name
promises. PR #80 repointed the footer's "Get started" away from it for that
reason, leaving a canonical signup URL that almost nothing linked to. There were
two honest fixes: make the URL work, or delete it. Making it work is the smaller
total change and the one that keeps every existing pin true, so this file pins
that all four of them really are still true rather than being edited to match:

  * `residual-dead-routes.test.ts` `live` list — `path="/signup"` must exist;
  * `residual-dead-routes.test.ts` `assertAlias("/apply", "/signup")`;
  * `residual-dead-routes.test.ts` `assertAlias("/referral", "/signup")`;
  * `signup-ssr.test.ts` — the prerendered `/signup` body, which lives in
    `server/seo-prerender.ts` and is deliberately NOT touched here.

The last one is the one worth being explicit about. That body is the view a
crawler and a no-JS visitor get, and every link in it is still a real
destination, so it is left alone rather than rewritten to describe the new page.
This file checks the hrefs it requires still exist in the builder, so
`signup-ssr.test.ts` keeps passing for the right reason.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SIGNUP_PAGE = REPO_ROOT / "client/src/pages/signup.tsx"
AUTH_PAGE = REPO_ROOT / "client/src/pages/auth.tsx"
APP = REPO_ROOT / "client/src/App.tsx"
PRERENDER = REPO_ROOT / "server/seo-prerender.ts"
RESIDUAL = REPO_ROOT / "server/tests/residual-dead-routes.test.ts"
SIGNUP_SSR = REPO_ROOT / "server/tests/signup-ssr.test.ts"
SITEMAP_XML = REPO_ROOT / "client/public/sitemap.xml"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_signup_renders_the_real_register_form():
    src = read(SIGNUP_PAGE)
    assert '<AuthPage initialTab="register" />' in src, "/signup does not render the auth page"
    # The real component, lazily, the same way App.tsx loads it for /auth.
    assert 'lazy(() => import("@/pages/auth"))' in src
    # No longer a marketing article: the page is the form.
    assert "MarketingLayout" not in src, "/signup is still the marketing wrapper"


def test_the_register_form_is_the_one_hag166_measured():
    # The real register controls. The card named them "register-email" and
    # "register-password"; read at main the testids are input-register-email,
    # input-register-password and button-register, with the Google button
    # relabelled for the register tab ("Sign up with Google", not "Continue
    # with"). Asserted as they are, not as the card remembered them.
    src = read(AUTH_PAGE)
    assert 'data-testid="input-register-email"' in src
    assert 'data-testid="input-register-password"' in src
    assert 'data-testid="button-register"' in src
    assert 'data-testid="button-google-login"' in src
    assert "Sign up with Google" in src


def test_auth_still_defaults_to_the_login_tab():
    # /signup passes register explicitly; /auth must be untouched by that, and
    # /auth?tab=register must keep working through AuthPage's own effect.
    src = read(AUTH_PAGE)
    assert "initialTab = 'login'," in src, "AuthPage default is no longer login"
    assert "useState(initialTab)" in src
    assert "const [activeTab, setActiveTab] = useState('login');" not in src
    assert "if (tab === 'register' || tab === 'signup' || params.get('mode') === 'signup')" in src
    assert "setActiveTab('register');" in src


def test_pin_one_signup_is_still_a_registered_live_destination():
    app = read(APP)
    assert '<Route path="/signup">' in app, "the /signup route is gone"
    assert 'lazy(() => import("@/pages/signup"))' in app
    # And the pinned list in residual-dead-routes.test.ts still names it.
    residual = read(RESIDUAL)
    assert 'const live = ["/settings", "/signup", "/data", "/integrations"];' in residual
    # The loop that turns that list into `path="<each>"` assertions is intact, so
    # /signup really is still a required live destination and not just a name in
    # an unused array.
    assert "for (const path of live) {" in residual
    assert "must be registered as a live destination" in residual


def test_pin_two_and_three_apply_and_referral_still_land_on_signup():
    # Both assertAlias pins, quoted from the test file itself so this fails if
    # either is ever quietly repointed.
    residual = read(RESIDUAL)
    assert 'assertAlias("/apply", "/signup");' in residual
    assert 'assertAlias("/referral", "/signup");' in residual
    # And App.tsx really does redirect them there.
    app = read(APP)
    assert 'path="/apply"' in app and 'Redirect to="/signup"' in app
    assert 'path="/referral"' in app
    assert "assertAlias" in residual and "must redirect to" in residual


def test_pin_four_the_prerendered_body_still_serves_the_register_funnel():
    # signup-ssr.test.ts asserts these hrefs against injectSEO(SHELL, "/signup"),
    # which builds its body from buildSignupBodyContent(). That builder is not
    # touched by this change, and this checks it still carries every link the
    # other test requires — so that test passes for the right reason.
    prerender = read(PRERENDER)
    body = prerender[prerender.index("function buildSignupBodyContent") :]
    body = body[: body.index("function buildSecurityBodyContent")]
    for href in (
        "/signup",
        "/product",
        "/features",
        "/pricing",
        "/tools/runway-calculator",
        "/survival-simulator",
        "/default-alive",
    ):
        assert f'href="{href}"' in body, f"the /signup body lost {href}"
    for phrase in ("free — all features", "no credit card", "Create a free account"):
        assert phrase.lower() in body.lower(), f"the /signup body lost {phrase!r}"


def test_the_prerender_coverage_pins_for_signup_are_untouched():
    # prerender-coverage.test.ts groups /signup with the pages that already
    # work. Nothing here changes that, so the file must not have been edited.
    assert "/signup" in read(REPO_ROOT / "server/tests/prerender-coverage.test.ts")


def test_signup_keeps_its_own_canonical_and_title():
    # /signup is a real page with its own metadata; it must not fall back to the
    # untouched shell, which carries the homepage canonical.
    src = read(PRERENDER)
    assert 'canonical: SITE_URL + "/signup"' in src
    assert 'title: "Get Started — Create a Free FounderConsole Account"' in src
    assert 'path: "/signup",' in read(SIGNUP_PAGE)


def test_signup_is_still_in_the_sitemap():
    assert "<loc>https://founderconsole.ai/signup</loc>" in read(SITEMAP_XML)


def test_the_signup_view_and_start_events_still_fire():
    # The form on /signup must be the instrumented one, or moving the page
    # would silently lose the funnel steps GA4 and PostHog read.
    src = read(AUTH_PAGE)
    assert "trackFunnel('signup_view', {})" in src
    assert "trackFunnel('signup_start', {})" in src
    assert "trackFunnel('signup_completed'" in src
