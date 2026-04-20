#!/bin/bash
# FounderConsole n8n webhook test scripts
# Replace N8N_HOST with your actual n8n host before running.
# Usage: bash webhook-tests.sh [outbound|activation|all]

set -euo pipefail

N8N_HOST="${N8N_HOST:-https://your-n8n.example.com}"
TEST_EMAIL="${TEST_EMAIL:-vysheshk@gmail.com}"  # USE YOUR OWN EMAIL for first tests — do NOT hit real prospects

# ============================================================
# Test 1: Outbound cold-drip webhook
# Simulates a new lead being pushed into the drip engine.
# Wired in n8n to: Webhook → HighLevel → Merge → Basic LLM Chain7 → Hunter → ...
# ============================================================
test_outbound() {
  echo "→ Testing outbound drip webhook..."
  curl -sS -X POST "${N8N_HOST}/webhook/leadgen-outbound" \
    -H "Content-Type: application/json" \
    -d @- <<EOF
{
  "email": "${TEST_EMAIL}",
  "first_name": "Test",
  "last_name": "Founder",
  "company_name": "TestCo",
  "linkedin_url": "https://linkedin.com/in/testfounder",
  "website": "https://testco.example",
  "source": "webhook_test"
}
EOF
  echo ""
  echo "Expected: email #1 arrives at ${TEST_EMAIL} within ~30 seconds"
  echo "Check: n8n execution log + your inbox"
}

# ============================================================
# Test 2: Activation drip webhook (signup event)
# Wired in n8n to: Signup Webhook → Airtable Upsert → Welcome Email → ...
# ============================================================
test_activation() {
  echo "→ Testing activation drip webhook..."
  curl -sS -X POST "${N8N_HOST}/webhook/founderconsole-signup" \
    -H "Content-Type: application/json" \
    -d @- <<EOF
{
  "email": "${TEST_EMAIL}",
  "first_name": "Test",
  "company_name": "TestCo",
  "signup_source": "web"
}
EOF
  echo ""
  echo "Expected: welcome email arrives at ${TEST_EMAIL} immediately"
  echo "Airtable: new row in Contacts table with has_simulated=false"
  echo "48h later: nudge email IF has_simulated still = false in Airtable"
}

# ============================================================
# Test 3: Simulate user completing a simulation
# Your FounderConsole backend should fire this on first-sim-complete
# This sets has_simulated = true so the 48h nudge is skipped
# ============================================================
test_simulation_complete() {
  echo "→ Testing simulation-complete webhook (skip nudge)..."
  # This assumes you've added a separate webhook node for activation tracking
  # OR you can update Airtable directly via Airtable's API — see below
  AIRTABLE_TOKEN="${AIRTABLE_TOKEN:-REPLACE_ME}"
  AIRTABLE_BASE_ID="${AIRTABLE_BASE_ID:-REPLACE_ME}"
  RECORD_ID="${RECORD_ID:-recXXXXXXX}"

  curl -sS -X PATCH "https://api.airtable.com/v0/${AIRTABLE_BASE_ID}/Contacts/${RECORD_ID}" \
    -H "Authorization: Bearer ${AIRTABLE_TOKEN}" \
    -H "Content-Type: application/json" \
    -d '{
      "fields": {
        "has_simulated": true,
        "p50_survival": 58
      }
    }'
  echo ""
}

# ============================================================
# Test 4: Trigger the Sales Nav scraper manually (n8n UI)
# ============================================================
test_scraper() {
  echo "→ Sales Nav scraper runs on cron — test manually in n8n UI:"
  echo "  1. Open n8n workflow"
  echo "  2. Click the Schedule Trigger node"
  echo "  3. Click 'Execute Node'"
  echo "  4. Check: Prospects Google Sheet gets 1 new row per result"
  echo "  5. Check: each row has email, first_name, linkedin_url"
}

# ============================================================
# Test 5: Inbound AI agent (Gmail Trigger)
# Can't trigger via curl — you need to actually reply to one of your test emails
# ============================================================
test_inbound() {
  echo "→ Inbound AI agent test (manual):"
  echo "  1. Reply to the email #1 you received from Test 1 with: 'how much does this cost?'"
  echo "  2. Check n8n execution log for the Gmail Trigger firing"
  echo "  3. Check classifier output is 'pricing'"
  echo "  4. Check auto-reply arrives at ${TEST_EMAIL}"
}

# ============================================================
# Main
# ============================================================
case "${1:-all}" in
  outbound) test_outbound ;;
  activation) test_activation ;;
  scraper) test_scraper ;;
  inbound) test_inbound ;;
  simcomplete) test_simulation_complete ;;
  all)
    test_scraper
    echo ""
    test_outbound
    echo ""
    echo "Waiting 30s before activation test..."
    sleep 30
    test_activation
    echo ""
    test_inbound
    ;;
  *)
    echo "Usage: $0 [outbound|activation|scraper|inbound|simcomplete|all]"
    exit 1
    ;;
esac
