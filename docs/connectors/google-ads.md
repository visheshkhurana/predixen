# Google Ads connector

Founders click **Connect with Google** on Integrations, approve Google Ads access, and the
connector pulls monthly spend for every non-manager account that login can see. Spend joins
Meta's in `marketing_spend` on the Profit screen (CM3, MER). Google's conversion value is
shown as platform-reported, never as revenue.

The card says **Coming Soon** until the server has these environment variables:

| Variable | Where it comes from |
| --- | --- |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Google Ads **manager** account → Admin → API Center. A new token starts at "Test account" access; apply for **Basic access** to read real accounts. |
| `GOOGLE_ADS_CLIENT_ID` / `GOOGLE_ADS_CLIENT_SECRET` | Google Cloud → APIs & Services → Credentials → OAuth client (Web). Falls back to `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` (the sign-in client) if unset. |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | Optional. Manager account id (digits only) when accounts are reached through a manager. |

In the same Google Cloud project:

1. Enable the **Google Ads API**.
2. Add `https://founderconsole.ai/api/connectors/google-ads/oauth/callback` as an authorised
   redirect URI on the OAuth client.
3. Add the scope `https://www.googleapis.com/auth/adwords` to the OAuth consent screen. It is a
   sensitive scope: until Google verifies the app, only test users listed on the consent screen
   can connect.

Code: `server/connectors/google_ads.py`, `server/api/google_ads_oauth.py`,
tests in `server/tests/test_google_ads_connector.py`.
