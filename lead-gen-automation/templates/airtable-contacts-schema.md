# Airtable `Contacts` table — setup

Create a new Airtable base named **FounderConsole CRM** with one table named **Contacts**.

## Fields (in order)

| # | Field name | Type | Options / Notes |
|---|---|---|---|
| 1 | `email` | Email | **Primary field** — drag this to position 1 |
| 2 | `first_name` | Single line text | |
| 3 | `last_name` | Single line text | |
| 4 | `company_name` | Single line text | |
| 5 | `signup_source` | Single select | Options: `web`, `scraper`, `manual`, `demo_request` |
| 6 | `signed_up_at` | Date | Include time: yes |
| 7 | `has_simulated` | Checkbox | |
| 8 | `trial_status` | Single select | Options: `free`, `pro`, `team`, `churned`, `trial` |
| 9 | `last_email_at` | Date | Include time: yes |
| 10 | `reply_category` | Single select | Options: `pricing`, `question`, `use_case`, `onboarding`, `meeting`, `misc`, `noop` |
| 11 | `linkedin_url` | URL | |
| 12 | `stage` | Single select | Options: `pre-seed`, `seed`, `series-a`, `series-b`, `later`, `bootstrapped`, `unknown` |
| 13 | `notes` | Long text | |
| 14 | `demo_booked_at` | Date | Include time: yes |
| 15 | `p50_survival` | Number | Precision: 0, or leave blank if they haven't run a sim |
| 16 | `last_activity_at` | Last modified time | Auto-populated |

## Views to create

1. **All contacts** — default grid view
2. **Active signups** — filter where `trial_status != churned` AND `signed_up_at` is within last 30 days
3. **Hot leads** — filter where `reply_category` is `meeting` or `use_case`, sorted by `last_email_at` desc
4. **Need follow-up** — filter where `last_email_at` is >3 days ago AND `replied_at` is empty
5. **Converted** — filter where `trial_status` is `pro` or `team`

## API access

1. Go to [airtable.com/create/tokens](https://airtable.com/create/tokens)
2. Create a Personal Access Token named `n8n-founderconsole`
3. Grant scopes: `data.records:read`, `data.records:write`
4. Access: add the **FounderConsole CRM** base
5. Copy the token and paste it as an Airtable credential in n8n

## Base ID

After creating the base, grab the base ID from the URL:
- URL: `https://airtable.com/appXXXXXXXXXXXXXX/tbl...`
- The part starting with `app` is your base ID
- Paste it into every Airtable node in the n8n workflow (or set `AIRTABLE_BASE_ID` as an n8n env var and reference it)
