# Google OAuth verification pack (FounderConsole)

Everything needed to move the `founderconsole-ads` Google Cloud project's
consent screen from **Testing** to **In production**. Nothing here is secret.

Console: https://console.cloud.google.com/auth/overview?project=founderconsole-ads

## 0. Before you start (checklist)

- [ ] Privacy policy live with the "Google User Data" section and the Limited Use
      sentence: https://www.founderconsole.ai/privacy#google-user-data
- [ ] Homepage (https://www.founderconsole.ai) shows the app name "FounderConsole",
      says what it does, and links to the privacy policy in the footer.
- [ ] Domain `founderconsole.ai` verified in Google Search Console by an owner or
      editor of the Cloud project (vysheshk@gmail.com):
      https://search.google.com/search-console -> Add property -> Domain ->
      `founderconsole.ai` -> add the TXT record at the DNS provider.
- [ ] Demo video uploaded to YouTube as **Unlisted** (script in section 4).
- [ ] Support email on the consent screen is one you read.

## 1. Branding page (Google Auth Platform -> Branding)

| Field | Value |
|---|---|
| App name | FounderConsole |
| User support email | vysheshk@gmail.com (or a founderconsole.ai address) |
| App logo | `client/public/app-icon-1024.png` resized to 120x120 PNG |
| Application home page | https://www.founderconsole.ai |
| Privacy policy link | https://www.founderconsole.ai/privacy |
| Terms of service link | https://www.founderconsole.ai/terms |
| Authorized domains | founderconsole.ai |
| Developer contact email | vysheshk@gmail.com |

Changing the logo or name triggers brand verification (2-3 business days). Do it
in the same submission as the scopes.

## 2. Data access page (scopes)

Scopes to list (Sign in with Google uses a different OAuth client, `GOOGLE_CLIENT_ID`, so its scopes aren't part of this project):

| Scope | Type | Used by |
|---|---|---|
| `https://www.googleapis.com/auth/adwords` | Sensitive | Google Ads connector |
| `https://www.googleapis.com/auth/analytics.readonly` | Sensitive | GA4 connector, **only if** the GA4 OAuth client (`GOOGLE_ANALYTICS_CLIENT_ID`) lives in this same project. If it's in another project, that project needs its own submission with the GA4 text below. |

### Justification: `adwords`

> FounderConsole is a financial planning dashboard for startup founders. When a
> founder clicks "Connect with Google" on the Integrations page, we use the
> adwords scope to call the Google Ads API (customers:listAccessibleCustomers and
> googleAds:search) and read, for each ad account the founder can access, the
> account name, ID and currency and monthly totals of cost, impressions, clicks,
> conversions and conversion value. We show this as the founder's monthly
> marketing spend and use it to calculate contribution margin after marketing
> (CM3) and marketing efficiency ratio (MER) on the founder's own dashboard and
> forecasts. We never create, modify, pause or spend on campaigns. Google Ads
> does not offer a narrower read-only scope, so adwords is the minimum scope that
> lets us read this reporting data. Data is visible only to the founder's own
> workspace, the refresh token is encrypted at rest, and Disconnect deletes the
> token and all imported figures.

### Justification: `analytics.readonly` (if in this project)

> FounderConsole reads monthly sessions, users and conversion totals from the
> single GA4 property the founder chooses, using the Analytics Data API, to show
> traffic and conversion trends next to revenue and marketing spend on the
> founder's own dashboard. Read-only; we never change Analytics settings. It is
> the narrowest scope that allows reading GA4 reports.

### "How will the scopes be used?" (short field)

> Read-only reporting: monthly ad spend and performance per Google Ads account
> (and monthly GA4 traffic totals) shown on the founder's own financial
> dashboard. No writes.

## 3. Audience page

- User type: **External**
- Click **Publish app** -> confirm. Status becomes "In production", verification
  "Needs verification" -> **Prepare for verification** walks through sections 1,
  2 and 4.
- Until approved, users see the "Google hasn't verified this app" screen and the
  app is capped at 100 users. Existing test users keep working.

## 4. Demo video (YouTube, Unlisted, 2-4 minutes, English, no music needed)

Record the screen with the browser address bar visible the whole time. Google
checks that the URL, app name and client ID match what's in the console.

1. **Homepage** (10 s): open https://www.founderconsole.ai, scroll to the footer,
   click Privacy, scroll to "Google User Data". Say: "FounderConsole is a
   financial dashboard for founders. This is our privacy policy and Limited Use
   disclosure."
2. **Sign in** (10 s): log in to FounderConsole.
3. **Start the connection** (20 s): go to Integrations, find the Google Ads card,
   click **Connect with Google**.
4. **Consent screen** (30 s), the most important part:
   - pick the Google account;
   - pause on the consent screen so the app name **FounderConsole** and the
     Google Ads permission are readable;
   - **click the address bar and slowly scroll through the URL** so the
     `client_id=` value is visible (it must match the client in the console);
   - click Continue / Allow.
5. **Back in the app** (20 s): the "Google Ads connected" message and the card
   showing Connected and records imported.
6. **Show the data in use** (40 s): open the Profit screen and point at the
   marketing spend, CM3 and MER figures that came from Google Ads. Say: "We only
   read monthly spend, impressions, clicks and conversions to calculate marketing
   efficiency. We never change campaigns."
7. **Disconnect** (15 s): back on Integrations, click Disconnect and show the card
   returns to "Connect with Google". Say: "Disconnecting deletes the token and the
   imported data."
8. If GA4 is in the same project, repeat steps 3-6 for the Google Analytics card.

Tips: 1080p, cursor visible, no other tabs with personal data open, no
notifications. Upload as Unlisted and paste the link in the verification form.

## 5. After submitting

- Google emails the developer contact, usually within 3-5 business days, often
  with follow-up questions. Reply in the same thread.
- Sensitive scopes (adwords, analytics.readonly) do **not** need the paid CASA
  security assessment; that's only for restricted scopes (Gmail, Drive full).
- Once approved, the unverified-app screen and the 100-user cap disappear.
