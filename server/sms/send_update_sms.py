"""
Send SMS update via Twilio using Replit Connectors API.
"""
import os, sys, json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def get_twilio_credentials():
    hostname = os.getenv("REPLIT_CONNECTORS_HOSTNAME")
    repl_identity = os.getenv("REPL_IDENTITY")
    web_repl_renewal = os.getenv("WEB_REPL_RENEWAL")

    if repl_identity:
        token = f"repl {repl_identity}"
    elif web_repl_renewal:
        token = f"depl {web_repl_renewal}"
    else:
        raise Exception("No Replit token available")

    if not hostname:
        raise Exception("REPLIT_CONNECTORS_HOSTNAME not set")

    import requests
    response = requests.get(
        f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=twilio",
        headers={
            "Accept": "application/json",
            "X_REPLIT_TOKEN": token
        },
        timeout=10
    )

    if response.status_code != 200:
        raise Exception(f"Failed to fetch Twilio credentials: {response.status_code}")

    data = response.json()
    items = data.get("items", [])
    if not items:
        raise Exception("No Twilio connection found")

    settings = items[0].get("settings", {})
    return {
        "account_sid": settings.get("account_sid"),
        "api_key": settings.get("api_key"),
        "api_key_secret": settings.get("api_key_secret"),
        "phone_number": settings.get("phone_number"),
    }


def send_sms(to_number: str, message: str):
    creds = get_twilio_credentials()

    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    api_key_sid = creds["account_sid"]
    api_key_secret = creds["api_key_secret"]
    from_number = creds["phone_number"]

    if not account_sid:
        raise Exception("TWILIO_ACCOUNT_SID secret not set")

    if not all([account_sid, api_key_sid, api_key_secret, from_number]):
        raise Exception(f"Missing Twilio credentials. Have: account_sid={bool(account_sid)}, api_key_sid={bool(api_key_sid)}, api_key_secret={bool(api_key_secret)}, phone_number={bool(from_number)}")

    from twilio.rest import Client
    client = Client(api_key_sid, api_key_secret, account_sid)

    msg = client.messages.create(
        body=message,
        from_=from_number,
        to=to_number
    )

    return msg.sid


SMS_TEXT = """FounderConsole - New Update

The Decisions page has been completely redesigned as a narrative strategic briefing:

1. The Situation - AI-generated assessment of your financial state
2. What We Recommend - Bold action + full rationale (WHY + WHY NOW)
3. What Happens If You Do Nothing - Projections with exhaustion dates
4. Execution Playbook - 6-10 team-ready action items with owners & deadlines
5. Key Risks & Contingency Plans - Mini-paragraph scenarios with pivot deadlines

All sections use your real financial data. No charts, just clear prose.

Check your email for screenshots and full details.

- FounderConsole"""


if __name__ == "__main__":
    to = "+919818540514"
    print(f"Sending SMS to {to}...")
    try:
        sid = send_sms(to, SMS_TEXT)
        print(f"[SENT] Message SID: {sid}")
    except Exception as e:
        print(f"[FAILED] {e}")
