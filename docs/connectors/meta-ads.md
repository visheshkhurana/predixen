# Meta Ads connector

Brings monthly Facebook and Instagram ad spend into the Profit screen
(`/profit`), where it becomes `marketing_spend` for CM3 and MER.

Code: `server/connectors/meta_ads.py` (connector), `server/services/d2c_months.py`
(storage and precedence), `server/models/d2c_month.py` (`D2CAdSpend`).

## What it reads

For each ad account the founder lists, over the last 3 complete calendar
months (`lookback_months` setting, 1 to 24):

| Field | Graph API source |
|---|---|
| Spend | `insights.spend`, in the ad account's currency |
| Impressions, clicks | `insights.impressions`, `insights.clicks` |
| Purchases | `insights.actions`, first present of `omni_purchase`, `purchase`, `offsite_conversion.fb_pixel_purchase` |
| Purchase value | `insights.action_values`, same order |

Call: `GET /{GRAPH_API_VERSION}/act_<id>/insights?level=account&time_increment=monthly&time_range={"since":...,"until":...}`.
The three purchase action types overlap (`omni_purchase` already includes
pixel purchases), so the connector uses the first one present and never adds
them up. A month with no insights row is stored as zero spend.

The Graph API version is one constant, `GRAPH_API_VERSION` in
`meta_ads.py` (currently `v24.0`). Meta supports each version for about two
years; bump the constant when Meta announces the deprecation date.

### Platform-reported purchases are not revenue

Purchase value is what Meta's attribution claims its ads caused. It overlaps
with Google, email, organic and every other channel's claims. FounderConsole
shows it only as **Meta ROAS (platform-reported)**. MER always divides the
store's net revenue (after discounts, RTO and returns, from Shopify / manual
entry) by total marketing spend.

## How spend becomes `marketing_spend`

- One `d2c_ad_spend` row per month x ad platform (`source`) x ad account, in
  the account's own currency.
- A sync replaces only its own platform's rows for each month, so re-syncing
  never double counts, and a removed ad account disappears from the total.
- `d2c_months.marketing_spend` = sum of `spend_company` over all platforms and
  accounts for the month, and its source is recorded (e.g. `meta_ads`, or
  `google_ads+meta_ads` once a second platform exists).
- A manual entry always wins. Clearing the manual value hands the field back
  to the platforms' total. Disconnecting Meta Ads removes its rows and
  recomputes the affected months.
- Currency: if the ad account currency equals the company currency,
  `spend_company = spend`. If it differs, the connector converts only with a
  stored market rate (`exchange_rates`, not the `static_fallback` source) dated
  in that month or up to 7 days after it. Without one, the native amount is
  kept, the month's total is left empty (CM3 and MER show as missing rather
  than mixing currencies), and the Profit screen names the account and its
  currency.

Adding Google Ads later: write a connector that returns the same
`metadata["ad_spend"]` shape (`{"source": "google_ads", "months": [{"period", "accounts": [...]}]}`).
`server/api/connectors.py` already stores it, and the sum picks it up.

## Errors

| Graph error | Behaviour |
|---|---|
| 190 / 102 (token expired, revoked, invalid) | Sync fails; the connector is marked `needs_reauth`; the Integrations card shows **Reconnect** |
| 10, 200-299 (permission) | Clear message naming the ad account and `ads_read` |
| 4, 17, 32, 613, 80000-80014, HTTP 429, 5xx | Retried up to 4 times with exponential backoff, waiting as long as `X-Business-Use-Case-Usage.estimated_time_to_regain_access` says (capped at 60 s per wait); then fails with "try again later" |

Pagination follows `paging.next`, and only to `https://graph.facebook.com`.

## Meta app setup (owner, one time)

1. **Create the app.** developers.facebook.com > My Apps > Create app >
   use case "Other" > app type **Business**. Attach it to FounderConsole's
   Business portfolio.
2. **Add the Marketing API product.**
3. **Permissions.**
   - `ads_read`: required. Reads insights for ad accounts the token can access.
   - `business_management`: only needed if FounderConsole later lists a
     business's ad accounts for the founder or creates system users on their
     behalf. The token-entry flow below does not need it.
4. **Access level / App Review.**
   - With *Standard Access*, `ads_read` works only for ad accounts owned by
     people with a role on the app (admins, developers, testers). Enough to
     test with your own accounts.
   - To read founders' ad accounts you need **Advanced Access for `ads_read`**,
     which requires Business Verification of FounderConsole's business
     portfolio and App Review: a screencast of a founder connecting and the
     Profit screen showing spend, a description of how ad data is used
     (read-only, used to compute marketing efficiency for the account owner,
     never shared), the privacy policy URL and a data deletion URL or
     instructions.
   - Marketing API access tier: apps start on the development tier with low
     rate limits; Meta raises it to standard once the app has made enough
     successful calls and has Advanced Access.
5. **App settings.** Add the privacy policy URL, terms URL, data deletion
   instructions URL and app domain (founderconsole.ai).
6. **Redirect URI** (only needed for the Facebook Login for Business flow,
   see below): `https://founderconsole.ai/api/connectors/meta_ads/oauth/callback`,
   added under Facebook Login for Business > Settings > Valid OAuth Redirect URIs.

### Environment variables

| Variable | Needed for | Notes |
|---|---|---|
| `META_APP_SECRET` | Recommended now | When set, every call sends `appsecret_proof` (HMAC-SHA256 of the token). Enable "Require app secret" in the app's Advanced settings once it is set in production. |
| `META_APP_ID` | Facebook Login for Business flow (future) | Not read by the token-entry flow. |
| `META_LOGIN_CONFIG_ID` | Facebook Login for Business flow (future) | The configuration that requests `ads_read`. |

Credentials a founder enters are stored encrypted (Fernet, `server/core/encryption.py`)
in the company's connector metadata, like every other connector.

### Why token entry and not OAuth (yet)

FounderConsole's connectors have no OAuth redirect flow today (QuickBooks,
Xero and others take tokens too); the only OAuth flow in the app is Google
sign-in. This connector follows the existing pattern. A Facebook Login for
Business flow (redirect to Meta, exchange the code for a token, store it
through the same `/connect` endpoint) can be added without changing the
connector: it only needs `access_token` and `ad_account_ids`.

## How a founder connects

1. In Meta Business Settings > Users > **System users**, create a system user
   (role Employee is enough), click **Add assets** and give it the ad
   account(s) with "View performance".
2. **Generate new token** for the system user: pick the FounderConsole app,
   tick `ads_read`, and choose "Never" expiry. (A long-lived personal token
   from Graph API Explorer also works but expires in about 60 days; the card
   will then ask to reconnect.)
3. Copy the ad account id(s) from Ads Manager (the number next to the account
   name, or `act_<number>`).
4. In FounderConsole: Integrations > **Meta Ads** > Connect, paste the token
   and the account ids (comma separated), Connect, then **Sync Now**.
5. Open `/profit`: the last three months show spend by account, MER from
   store revenue, Meta's platform-reported ROAS and break-even MER.

If the ad account is billed in a different currency than the company
currency, the Profit screen says so. Either keep a stored exchange rate for
that month, set the company currency to match, or type the month's total
marketing spend in the company currency.
