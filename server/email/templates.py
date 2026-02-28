"""
Email templates for FounderConsole.
Professional HTML templates using table-based layouts for email client compatibility.
All icons use text/Unicode for universal rendering (no SVG data URIs).
"""
from datetime import datetime
from typing import Optional


# Brand colors
COLORS = {
    "primary": "#0ea5e9",      # Electric teal
    "primary_dark": "#0284c7", # Darker teal
    "navy": "#0f172a",         # Deep navy
    "navy_light": "#1e293b",   # Lighter navy
    "white": "#ffffff",
    "off_white": "#f8fafc",
    "gray_50": "#f1f5f9",
    "gray_100": "#e2e8f0",
    "gray_400": "#94a3b8",
    "gray_500": "#64748b",
    "gray_600": "#475569",
    "gray_700": "#334155",
    "success": "#22c55e",
    "warning": "#f59e0b",
}

# Safe font stack
FONT_STACK = "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"


def get_email_wrapper(content: str) -> str:
    """Wrap content in base email HTML structure with table-based layout."""
    return f"""
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <title>FounderConsole</title>
    <!--[if mso]>
    <noscript>
        <xml>
            <o:OfficeDocumentSettings>
                <o:PixelsPerInch>96</o:PixelsPerInch>
            </o:OfficeDocumentSettings>
        </xml>
    </noscript>
    <![endif]-->
    <style type="text/css">
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
        table {{ border-collapse: collapse !important; }}
        body {{ margin: 0 !important; padding: 0 !important; width: 100% !important; }}
        a[x-apple-data-detectors] {{ color: inherit !important; text-decoration: none !important; font-size: inherit !important; font-family: inherit !important; font-weight: inherit !important; line-height: inherit !important; }}
        @media only screen and (max-width: 600px) {{
            .email-container {{ width: 100% !important; max-width: 100% !important; }}
            .body-content {{ padding: 24px !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: {COLORS['gray_50']}; font-family: {FONT_STACK};">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {COLORS['gray_50']};">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" class="email-container" width="560" cellspacing="0" cellpadding="0" border="0" style="max-width: 560px; background-color: {COLORS['white']}; border-radius: 16px; overflow: hidden;">
                    {content}
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""


def get_header_html(subtitle: str) -> str:
    """Generate the header section with text-based logo."""
    return f"""
    <tr>
        <td style="background-color: {COLORS['navy']}; padding: 32px 40px; text-align: center;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                    <td align="center">
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                            <tr>
                                <td style="vertical-align: middle; padding-right: 10px;">
                                    <!--[if mso]>
                                    <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" style="height:36px;v-text-anchor:middle;width:36px;" arcsize="28%" fillcolor="{COLORS['primary']}" stroke="f">
                                        <w:anchorlock/>
                                        <center style="color:{COLORS['white']};font-family:{FONT_STACK};font-size:18px;font-weight:bold;">P</center>
                                    </v:roundrect>
                                    <![endif]-->
                                    <!--[if !mso]><!-->
                                    <div style="width: 36px; height: 36px; background-color: {COLORS['primary']}; border-radius: 10px; text-align: center; line-height: 36px; color: {COLORS['white']}; font-weight: 700; font-size: 18px; font-family: {FONT_STACK};">P</div>
                                    <!--<![endif]-->
                                </td>
                                <td style="vertical-align: middle;">
                                    <span style="font-size: 24px; font-weight: 700; color: {COLORS['white']}; letter-spacing: -0.5px; font-family: {FONT_STACK};">FounderConsole</span>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
                <tr>
                    <td align="center" style="padding-top: 12px;">
                        <span style="color: {COLORS['gray_400']}; font-size: 12px; font-weight: 500; letter-spacing: 1px; text-transform: uppercase; font-family: {FONT_STACK};">{subtitle}</span>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
    """


def get_footer_html() -> str:
    """Generate the footer section."""
    return f"""
    <tr>
        <td style="background-color: {COLORS['off_white']}; padding: 24px 40px; text-align: center; border-top: 1px solid {COLORS['gray_100']};">
            <p style="margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: {COLORS['navy']}; font-family: {FONT_STACK};">FounderConsole</p>
            <p style="margin: 0; font-size: 13px; color: {COLORS['gray_500']}; font-family: {FONT_STACK};">AI-Powered Financial Intelligence</p>
        </td>
    </tr>
    """


def get_cta_button(url: str, text: str) -> str:
    """Generate a CTA button with VML fallback for Outlook."""
    return f"""
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin: 0 auto;">
        <tr>
            <td>
                <!--[if mso]>
                <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{url}" style="height:48px;v-text-anchor:middle;width:200px;" arcsize="21%" fillcolor="{COLORS['primary']}" stroke="f">
                    <w:anchorlock/>
                    <center style="color:{COLORS['white']};font-family:{FONT_STACK};font-size:15px;font-weight:bold;">{text}</center>
                </v:roundrect>
                <![endif]-->
                <!--[if !mso]><!-->
                <a href="{url}" target="_blank" style="display: inline-block; padding: 14px 36px; font-size: 15px; font-weight: 600; color: {COLORS['white']}; text-decoration: none; background-color: {COLORS['primary']}; border-radius: 10px; font-family: {FONT_STACK};">{text}</a>
                <!--<![endif]-->
            </td>
        </tr>
    </table>
    """


def get_info_card_start(title: str) -> str:
    """Start an info card section."""
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {COLORS['gray_50']}; border-radius: 12px; margin: 24px 0;">
        <tr>
            <td style="padding: 24px;">
                <p style="margin: 0 0 16px 0; font-size: 12px; font-weight: 600; color: {COLORS['navy']}; text-transform: uppercase; letter-spacing: 1px; font-family: {FONT_STACK};">{title}</p>
    """


def get_info_card_end() -> str:
    """End an info card section."""
    return """
            </td>
        </tr>
    </table>
    """


def get_check_item(text: str) -> str:
    """Generate a list item with a colored circle and checkmark character."""
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 12px;">
        <tr>
            <td width="32" valign="top" style="padding-right: 12px;">
                <!--[if mso]>
                <v:oval xmlns:v="urn:schemas-microsoft-com:vml" style="width:20px;height:20px;" fillcolor="{COLORS['primary']}" stroke="f">
                    <v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:t">
                        <center style="color:{COLORS['white']};font-size:12px;font-family:Arial,sans-serif;line-height:20px;">&#10003;</center>
                    </v:textbox>
                </v:oval>
                <![endif]-->
                <!--[if !mso]><!-->
                <div style="width: 20px; height: 20px; background-color: {COLORS['primary']}; border-radius: 50%; text-align: center; line-height: 20px; color: {COLORS['white']}; font-size: 12px; font-family: Arial, sans-serif;">&#10003;</div>
                <!--<![endif]-->
            </td>
            <td valign="top" style="font-size: 14px; color: {COLORS['gray_600']}; line-height: 1.5; font-family: {FONT_STACK};">
                {text}
            </td>
        </tr>
    </table>
    """


def get_numbered_step(num: str, title: str, desc: str) -> str:
    """Generate a numbered step item."""
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 16px;">
        <tr>
            <td width="42" valign="top" style="padding-right: 14px;">
                <!--[if mso]>
                <v:oval xmlns:v="urn:schemas-microsoft-com:vml" style="width:28px;height:28px;" fillcolor="{COLORS['primary']}" stroke="f">
                    <v:textbox inset="0,0,0,0" style="mso-fit-shape-to-text:t">
                        <center style="color:{COLORS['white']};font-size:13px;font-weight:bold;font-family:Arial,sans-serif;line-height:28px;">{num}</center>
                    </v:textbox>
                </v:oval>
                <![endif]-->
                <!--[if !mso]><!-->
                <div style="width: 28px; height: 28px; background-color: {COLORS['primary']}; border-radius: 50%; text-align: center; line-height: 28px; color: {COLORS['white']}; font-weight: 600; font-size: 13px; font-family: {FONT_STACK};">{num}</div>
                <!--<![endif]-->
            </td>
            <td valign="top">
                <p style="margin: 0 0 2px 0; font-weight: 600; color: {COLORS['navy']}; font-size: 14px; font-family: {FONT_STACK};">{title}</p>
                <p style="margin: 0; color: {COLORS['gray_500']}; font-size: 13px; font-family: {FONT_STACK};">{desc}</p>
            </td>
        </tr>
    </table>
    """


def get_divider() -> str:
    """Generate a horizontal divider."""
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td style="padding: 24px 0;">
                <div style="height: 1px; background-color: {COLORS['gray_100']};"></div>
            </td>
        </tr>
    </table>
    """


def render_invite_template(
    invite_url: str,
    role: str,
    invited_by_email: str,
    expires_at: datetime,
    early_access: bool = True
) -> str:
    """Render the invite email template."""
    role_display = role.title()
    expires_formatted = expires_at.strftime("%B %d, %Y at %I:%M %p UTC")
    
    header_subtitle = "EARLY ACCESS INVITATION" if early_access else "PLATFORM INVITATION"
    
    early_badge = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
            <td align="center">
                <span style="display: inline-block; background-color: {COLORS['warning']}; color: {COLORS['white']}; padding: 6px 16px; border-radius: 20px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-family: {FONT_STACK};">Early Access</span>
            </td>
        </tr>
    </table>
    """ if early_access else ""
    
    role_badge = f"""<span style="display: inline-block; background-color: #e0f2fe; color: {COLORS['primary_dark']}; padding: 4px 14px; border-radius: 20px; font-size: 13px; font-weight: 600; font-family: {FONT_STACK};">{role_display}</span>"""
    
    if early_access:
        intro_text = f"""
        <p style="font-size: 16px; color: {COLORS['gray_600']}; margin: 0 0 16px 0; line-height: 1.7; font-family: {FONT_STACK};">
            You've been selected for <span style="color: {COLORS['primary']}; font-weight: 600;">exclusive early access</span> to FounderConsole.
        </p>
        <p style="font-size: 15px; color: {COLORS['gray_600']}; margin: 0 0 16px 0; line-height: 1.7; font-family: {FONT_STACK};">
            <span style="color: {COLORS['primary']}; font-weight: 600;">{invited_by_email}</span> has personally invited you to join as a {role_badge}
        </p>
        """
        features = [
            "First look at new features before public release",
            "AI-powered extraction from financial documents",
            "Monte Carlo simulations for cash flow forecasting",
            "Decision recommendations ranked by survival & risk",
            "Direct feedback channel to shape the roadmap"
        ]
    else:
        intro_text = f"""
        <p style="font-size: 15px; color: {COLORS['gray_600']}; margin: 0 0 16px 0; line-height: 1.7; font-family: {FONT_STACK};">
            <span style="color: {COLORS['primary']}; font-weight: 600;">{invited_by_email}</span> has invited you to join FounderConsole as a {role_badge}
        </p>
        <p style="font-size: 15px; color: {COLORS['gray_600']}; margin: 0 0 16px 0; line-height: 1.7; font-family: {FONT_STACK};">
            FounderConsole helps startups make data-driven financial decisions with AI-powered analysis and probabilistic forecasting.
        </p>
        """
        features = [
            "Financial metrics extraction and analysis",
            "Monte Carlo simulations for forecasting",
            "AI-powered decision recommendations",
            "Real-time runway and burn tracking"
        ]
    
    features_html = "".join([get_check_item(f) for f in features])
    
    content = f"""
    {get_header_html(header_subtitle)}
    <tr>
        <td class="body-content" style="padding: 40px;">
            {early_badge}
            <h2 style="margin: 0 0 16px 0; font-size: 24px; font-weight: 600; color: {COLORS['navy']}; letter-spacing: -0.3px; font-family: {FONT_STACK};">You're Invited</h2>
            {intro_text}
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 32px 0;">
                <tr>
                    <td align="center">
                        {get_cta_button(invite_url, "Accept Invitation")}
                    </td>
                </tr>
            </table>
            
            {get_info_card_start("What You'll Get")}
            {features_html}
            {get_info_card_end()}
            
            <p style="text-align: center; color: {COLORS['gray_500']}; font-size: 13px; margin: 24px 0 0 0; font-family: {FONT_STACK};">This invitation expires on {expires_formatted}</p>
            
            {get_divider()}
            
            <p style="color: {COLORS['gray_500']}; font-size: 13px; margin: 0; font-family: {FONT_STACK};">If you weren't expecting this invitation, you can safely ignore this email.</p>
        </td>
    </tr>
    {get_footer_html()}
    """
    return get_email_wrapper(content)


def render_welcome_template(
    user_name: Optional[str] = None,
    login_url: str = "https://founderconsole.ai/auth"
) -> str:
    """Render the welcome email template."""
    greeting = f"Welcome aboard, {user_name}!" if user_name else "Welcome aboard!"
    
    steps = [
        ("1", "Upload Financial Data", "Import your financial documents (PDF, Excel) or connect your tools"),
        ("2", "Review Truth Scan", "See your metrics benchmarked against industry standards"),
        ("3", "Run Simulations", "Model scenarios with Monte Carlo forecasting"),
        ("4", "Get Recommendations", "Receive AI-powered decision guidance"),
    ]
    
    steps_html = "".join([get_numbered_step(num, title, desc) for num, title, desc in steps])
    
    content = f"""
    {get_header_html("WELCOME TO FOUNDERCONSOLE")}
    <tr>
        <td class="body-content" style="padding: 40px;">
            <h2 style="margin: 0 0 16px 0; font-size: 24px; font-weight: 600; color: {COLORS['navy']}; letter-spacing: -0.3px; font-family: {FONT_STACK};">{greeting}</h2>
            <p style="font-size: 15px; color: {COLORS['gray_600']}; margin: 0 0 16px 0; line-height: 1.7; font-family: {FONT_STACK};">Your account has been created successfully. You're now ready to start making data-driven decisions for your startup.</p>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 32px 0;">
                <tr>
                    <td align="center">
                        {get_cta_button(login_url, "Go to Dashboard")}
                    </td>
                </tr>
            </table>
            
            {get_info_card_start("Getting Started")}
            {steps_html}
            {get_info_card_end()}
            
            {get_divider()}
            
            <p style="color: {COLORS['gray_500']}; font-size: 13px; margin: 0; font-family: {FONT_STACK};">Need help? Our AI Copilot is available in-platform to guide you through any feature or answer questions about your financial data.</p>
        </td>
    </tr>
    {get_footer_html()}
    """
    return get_email_wrapper(content)


def get_feature_card(title: str, description: str, icon: str, screenshot_url: str = None) -> str:
    """Generate a feature card with optional screenshot."""
    screenshot_html = ""
    if screenshot_url:
        screenshot_html = f"""
        <tr>
            <td style="padding: 16px 0 0 0;">
                <img src="{screenshot_url}" alt="{title}" width="100%" style="border-radius: 8px; border: 1px solid {COLORS['gray_100']}; display: block;" />
            </td>
        </tr>
        """
    
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {COLORS['white']}; border: 1px solid {COLORS['gray_100']}; border-radius: 12px; margin-bottom: 16px;">
        <tr>
            <td style="padding: 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                        <td width="40" valign="top" style="padding-right: 14px;">
                            <div style="width: 36px; height: 36px; background-color: {COLORS['primary']}; border-radius: 10px; text-align: center; line-height: 36px; color: {COLORS['white']}; font-size: 18px; font-family: Arial, sans-serif;">{icon}</div>
                        </td>
                        <td valign="top">
                            <p style="margin: 0 0 6px 0; font-weight: 600; color: {COLORS['navy']}; font-size: 16px; font-family: {FONT_STACK};">{title}</p>
                            <p style="margin: 0; color: {COLORS['gray_500']}; font-size: 14px; line-height: 1.5; font-family: {FONT_STACK};">{description}</p>
                        </td>
                    </tr>
                    {screenshot_html}
                </table>
            </td>
        </tr>
    </table>
    """


def get_stat_box(value: str, label: str) -> str:
    """Generate a statistics box."""
    return f"""
    <td align="center" style="padding: 16px; background-color: {COLORS['gray_50']}; border-radius: 8px;">
        <p style="margin: 0 0 4px 0; font-size: 28px; font-weight: 700; color: {COLORS['primary']}; font-family: {FONT_STACK};">{value}</p>
        <p style="margin: 0; font-size: 12px; color: {COLORS['gray_500']}; text-transform: uppercase; letter-spacing: 0.5px; font-family: {FONT_STACK};">{label}</p>
    </td>
    """


def render_app_overview_template(
    user_name: str = None,
    login_url: str = "https://founderconsole.ai/dashboard",
    dashboard_screenshot_url: str = None,
    truth_scan_screenshot_url: str = None,
    simulation_screenshot_url: str = None,
    decision_screenshot_url: str = None
) -> str:
    """Render the app overview email template with screenshots."""
    greeting = f"Hello {user_name}," if user_name else "Hello,"
    
    # Hero section with main screenshot
    hero_screenshot = ""
    if dashboard_screenshot_url:
        hero_screenshot = f"""
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0;">
            <tr>
                <td>
                    <img src="{dashboard_screenshot_url}" alt="FounderConsole Dashboard" width="100%" style="border-radius: 12px; border: 1px solid {COLORS['gray_100']}; display: block;" />
                </td>
            </tr>
        </table>
        """
    
    # Feature cards
    features = [
        {
            "title": "Truth Scan",
            "description": "Automatically extract and validate 24+ financial metrics from your PDFs, Excel files, or pitch decks. Benchmarked against industry standards with confidence scores.",
            "icon": "&#128202;",
            "screenshot_url": truth_scan_screenshot_url
        },
        {
            "title": "Monte Carlo Simulation",
            "description": "Run probabilistic forecasts with up to 10,000 iterations. Model different scenarios, custom events, and see P10/P50/P90 confidence intervals for your runway.",
            "icon": "&#128200;",
            "screenshot_url": simulation_screenshot_url
        },
        {
            "title": "AI Decision Engine",
            "description": "Get ranked recommendations based on survival probability, growth potential, downside risk, and dilution impact. Each decision comes with a composite score and detailed analysis.",
            "icon": "&#9889;",
            "screenshot_url": decision_screenshot_url
        }
    ]
    
    features_html = ""
    for feature in features:
        features_html += get_feature_card(
            feature["title"],
            feature["description"],
            feature["icon"],
            feature.get("screenshot_url")
        )
    
    content = f"""
    {get_header_html("INTELLIGENCE OS")}
    <tr>
        <td class="body-content" style="padding: 40px;">
            <p style="font-size: 15px; color: {COLORS['gray_600']}; margin: 0 0 8px 0; font-family: {FONT_STACK};">{greeting}</p>
            <h2 style="margin: 0 0 16px 0; font-size: 26px; font-weight: 700; color: {COLORS['navy']}; letter-spacing: -0.5px; line-height: 1.3; font-family: {FONT_STACK};">Your AI-Powered Financial Command Center</h2>
            <p style="font-size: 16px; color: {COLORS['gray_600']}; margin: 0 0 8px 0; line-height: 1.7; font-family: {FONT_STACK};">
                FounderConsole gives startups <span style="color: {COLORS['primary']}; font-weight: 600;">investor-grade financial analysis</span> in minutes, not weeks.
            </p>
            <p style="font-size: 15px; color: {COLORS['gray_500']}; margin: 0 0 24px 0; line-height: 1.6; font-family: {FONT_STACK};">
                Upload your financials, run simulations, and get ranked recommendations to maximize survival and growth.
            </p>
            
            {hero_screenshot}
            
            <!-- Stats row -->
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0;">
                <tr>
                    {get_stat_box("24+", "Metrics")}
                    <td width="12"></td>
                    {get_stat_box("10K", "Simulations")}
                    <td width="12"></td>
                    {get_stat_box("P90", "Confidence")}
                </tr>
            </table>
            
            {get_divider()}
            
            <h3 style="margin: 0 0 20px 0; font-size: 18px; font-weight: 600; color: {COLORS['navy']}; font-family: {FONT_STACK};">Core Capabilities</h3>
            
            {features_html}
            
            <!-- Additional features list -->
            {get_info_card_start("Also Included")}
            {get_check_item("AI Copilot for guided analysis and Q&A")}
            {get_check_item("Smart alerts for anomalies and runway warnings")}
            {get_check_item("Scenario versioning with diff and rollback")}
            {get_check_item("Sensitivity analysis with tornado charts")}
            {get_check_item("QuickBooks & Salesforce integrations (coming soon)")}
            {get_info_card_end()}
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 32px 0;">
                <tr>
                    <td align="center">
                        {get_cta_button(login_url, "Go to Dashboard")}
                    </td>
                </tr>
            </table>
            
            {get_divider()}
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {COLORS['navy']}; border-radius: 12px; margin-top: 8px;">
                <tr>
                    <td style="padding: 24px; text-align: center;">
                        <p style="margin: 0 0 8px 0; font-size: 14px; color: {COLORS['gray_400']}; font-family: {FONT_STACK};">Need help getting started?</p>
                        <p style="margin: 0; font-size: 15px; color: {COLORS['white']}; font-family: {FONT_STACK};">Our <span style="color: {COLORS['primary']};">AI Copilot</span> is available 24/7 inside the platform to guide you through every feature.</p>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
    {get_footer_html()}
    """
    return get_email_wrapper(content)


def render_password_reset_template(
    reset_url: str
) -> str:
    """Render the password reset email template."""
    content = f"""
    {get_header_html("PASSWORD RESET")}
    <tr>
        <td class="body-content" style="padding: 40px;">
            <h2 style="margin: 0 0 16px 0; font-size: 24px; font-weight: 600; color: {COLORS['navy']}; letter-spacing: -0.3px; font-family: {FONT_STACK};">Reset Your Password</h2>
            <p style="font-size: 15px; color: {COLORS['gray_600']}; margin: 0 0 16px 0; line-height: 1.7; font-family: {FONT_STACK};">We received a request to reset the password for your FounderConsole account. Click the button below to create a new password.</p>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 32px 0;">
                <tr>
                    <td align="center">
                        {get_cta_button(reset_url, "Reset Password")}
                    </td>
                </tr>
            </table>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: #fef3c7; border-left: 3px solid {COLORS['warning']}; border-radius: 0 8px 8px 0; margin: 24px 0;">
                <tr>
                    <td style="padding: 16px 20px;">
                        <p style="margin: 0; color: {COLORS['gray_700']}; font-size: 14px; font-family: {FONT_STACK};"><strong>Security Notice:</strong> This link expires in 1 hour. If you didn't request this reset, please ignore this email or contact support if you have concerns.</p>
                    </td>
                </tr>
            </table>
            
            {get_divider()}
            
            <p style="color: {COLORS['gray_500']}; font-size: 13px; margin: 0; font-family: {FONT_STACK};">For security reasons, never share this link with anyone. FounderConsole will never ask for your password via email.</p>
        </td>
    </tr>
    {get_footer_html()}
    """
    return get_email_wrapper(content)


def render_email_verification_template(
    verify_url: str
) -> str:
    content = f"""
    {get_header_html("EMAIL VERIFICATION")}
    <tr>
        <td class="body-content" style="padding: 40px;">
            <h2 style="margin: 0 0 16px 0; font-size: 24px; font-weight: 600; color: {COLORS['navy']}; letter-spacing: -0.3px; font-family: {FONT_STACK};">Verify Your Email</h2>
            <p style="font-size: 15px; color: {COLORS['gray_600']}; margin: 0 0 16px 0; line-height: 1.7; font-family: {FONT_STACK};">Thanks for signing up for FounderConsole. Please click the button below to verify your email address and activate your account.</p>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 32px 0;">
                <tr>
                    <td align="center">
                        {get_cta_button(verify_url, "Verify Email")}
                    </td>
                </tr>
            </table>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {COLORS['gray_50']}; border-radius: 8px; margin: 24px 0;">
                <tr>
                    <td style="padding: 16px 20px;">
                        <p style="margin: 0; color: {COLORS['gray_600']}; font-size: 14px; font-family: {FONT_STACK};">This link expires in 24 hours. If you didn't create an account, please ignore this email.</p>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
    {get_footer_html()}
    """
    return get_email_wrapper(content)


def render_copilot_pitch_template(
    recipient_name: Optional[str] = None,
    cta_url: str = "https://founderconsole.ai"
) -> str:
    """Render the AI Copilot sales pitch email template."""
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi there,"
    
    content = f"""
    {get_header_html("AI Copilot")}
    <tr>
        <td class="body-content" style="padding: 40px;">
            <p style="color: {COLORS['gray_700']}; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                {greeting}
            </p>
            <p style="color: {COLORS['gray_700']}; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                What if you could ask a seasoned CFO any question about your business and get an instant, data-backed answer?
            </p>
            <p style="color: {COLORS['gray_700']}; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                <strong style="color: {COLORS['navy']};">Introducing FounderConsole AI Copilot</strong> - your always-available financial intelligence partner.
            </p>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 24px 0; background-color: {COLORS['gray_50']}; border-radius: 12px;">
                <tr>
                    <td style="padding: 24px;">
                        <p style="color: {COLORS['navy']}; font-weight: 600; font-size: 14px; margin: 0 0 12px 0;">Simply ask questions in plain English:</p>
                        <p style="color: {COLORS['gray_600']}; font-size: 14px; font-style: italic; margin: 0 0 8px 0;">"What's my real runway?"</p>
                        <p style="color: {COLORS['gray_600']}; font-size: 14px; font-style: italic; margin: 0 0 8px 0;">"What happens if our Series A slips 3 months?"</p>
                        <p style="color: {COLORS['gray_600']}; font-size: 14px; font-style: italic; margin: 0 0 8px 0;">"How do I extend runway without layoffs?"</p>
                        <p style="color: {COLORS['gray_600']}; font-size: 14px; font-style: italic; margin: 0;">"Who are my competitors and how do I differentiate?"</p>
                    </td>
                </tr>
            </table>
            
            <p style="color: {COLORS['navy']}; font-weight: 600; font-size: 16px; margin: 32px 0 16px 0;">Three Specialized AI Agents Working For You</p>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 0 0 24px 0;">
                <tr>
                    <td style="padding: 16px; background-color: {COLORS['gray_50']}; border-radius: 8px; margin-bottom: 8px;">
                        <p style="color: {COLORS['primary']}; font-weight: 600; font-size: 14px; margin: 0 0 4px 0;">CFO Agent</p>
                        <p style="color: {COLORS['gray_600']}; font-size: 13px; margin: 0;">Runway analysis, burn optimization, unit economics deep-dives</p>
                    </td>
                </tr>
                <tr><td style="height: 8px;"></td></tr>
                <tr>
                    <td style="padding: 16px; background-color: {COLORS['gray_50']}; border-radius: 8px;">
                        <p style="color: {COLORS['primary']}; font-weight: 600; font-size: 14px; margin: 0 0 4px 0;">Market Agent</p>
                        <p style="color: {COLORS['gray_600']}; font-size: 13px; margin: 0;">Competitor analysis, industry benchmarks, differentiation strategy</p>
                    </td>
                </tr>
                <tr><td style="height: 8px;"></td></tr>
                <tr>
                    <td style="padding: 16px; background-color: {COLORS['gray_50']}; border-radius: 8px;">
                        <p style="color: {COLORS['primary']}; font-weight: 600; font-size: 14px; margin: 0 0 4px 0;">Strategy Agent</p>
                        <p style="color: {COLORS['gray_600']}; font-size: 13px; margin: 0;">GTM planning, 30/60/90 day roadmaps, growth vs. efficiency trade-offs</p>
                    </td>
                </tr>
            </table>
            
            <p style="color: {COLORS['gray_700']}; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                The Copilot analyzes your actual financials and responds with specific, actionable recommendations - not generic advice.
            </p>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 32px 0;">
                <tr>
                    <td align="center">
                        <a href="{cta_url}" style="display: inline-block; padding: 14px 32px; background-color: {COLORS['primary']}; color: {COLORS['white']}; text-decoration: none; font-weight: 600; font-size: 14px; border-radius: 8px;">Try Copilot Free</a>
                    </td>
                </tr>
            </table>
            
            <p style="color: {COLORS['gray_500']}; font-size: 14px; line-height: 1.6; margin: 24px 0 0 0; text-align: center;">
                Upload your financials once. Ask unlimited questions forever.
            </p>
        </td>
    </tr>
    {get_footer_html()}
    """
    return get_email_wrapper(content)


# Standard template configurations for admin UI
TEMPLATE_CONFIGS = {
    "invite": {
        "name": "Early Access Invitation",
        "description": "Sent to early users with exclusive access messaging",
        "variables": ["invite_url", "role", "invited_by_email", "expires_at", "early_access"],
        "subject": "You're invited to FounderConsole Early Access",
        "render_fn": "render_invite_template"
    },
    "welcome": {
        "name": "Welcome Email",
        "description": "Sent after a user completes registration",
        "variables": ["user_name", "login_url"],
        "subject": "Welcome to FounderConsole",
        "render_fn": "render_welcome_template"
    },
    "password_reset": {
        "name": "Password Reset Email",
        "description": "Sent when a user requests a password reset",
        "variables": ["reset_url"],
        "subject": "Reset Your FounderConsole Password",
        "render_fn": "render_password_reset_template"
    },
    "app_overview": {
        "name": "App Overview",
        "description": "Product showcase email with screenshots explaining key features",
        "variables": ["user_name", "login_url", "dashboard_screenshot_url", "truth_scan_screenshot_url", "simulation_screenshot_url", "decision_screenshot_url"],
        "subject": "Discover FounderConsole - Your AI Financial Command Center",
        "render_fn": "render_app_overview_template"
    },
    "copilot_pitch": {
        "name": "AI Copilot Pitch",
        "description": "Sales pitch email for the AI Copilot feature",
        "variables": ["recipient_name", "cta_url"],
        "subject": "Ask any financial question. Get CFO-grade answers.",
        "render_fn": "render_copilot_pitch_template"
    }
}


def get_template_preview(template_type: str) -> Optional[str]:
    """
    Get a preview of an email template with sample data.
    
    Args:
        template_type: One of 'invite', 'welcome', 'password_reset', 'app_overview'
    
    Returns:
        HTML content of the template with sample data
    """
    sample_data = {
        "invite": {
            "invite_url": "https://founderconsole.ai/auth?invite=sample_token_abc123",
            "role": "analyst",
            "invited_by_email": "admin@company.com",
            "expires_at": datetime.now(),
            "early_access": True
        },
        "welcome": {
            "user_name": "John Doe",
            "login_url": "https://founderconsole.ai/auth"
        },
        "password_reset": {
            "reset_url": "https://founderconsole.ai/reset-password?token=sample_reset_token"
        },
        "app_overview": {
            "user_name": "John",
            "login_url": "https://founderconsole.ai/dashboard",
            "dashboard_screenshot_url": None,
            "truth_scan_screenshot_url": None,
            "simulation_screenshot_url": None,
            "decision_screenshot_url": None
        },
        "copilot_pitch": {
            "recipient_name": "Nikita",
            "cta_url": "https://founderconsole.ai/copilot"
        }
    }
    
    if template_type == "invite":
        return render_invite_template(**sample_data["invite"])
    elif template_type == "welcome":
        return render_welcome_template(**sample_data["welcome"])
    elif template_type == "password_reset":
        return render_password_reset_template(**sample_data["password_reset"])
    elif template_type == "app_overview":
        return render_app_overview_template(**sample_data["app_overview"])
    elif template_type == "copilot_pitch":
        return render_copilot_pitch_template(**sample_data["copilot_pitch"])
    elif template_type == "platform_update":
        return render_platform_update_template(
            updates=[
                {"title": "Sample Feature", "description": "This is a sample update."}
            ],
            app_url="https://founderconsole.ai"
        )
    
    return None


def render_platform_update_template(
    updates: list,
    app_url: str
) -> str:
    """
    Render platform update email template.
    
    Args:
        updates: List of dicts with 'title' and 'description' keys
        app_url: URL to the application
    
    Returns:
        Complete HTML email content
    """
    update_items_html = ""
    for update in updates:
        title = update.get("title", "")
        description = update.get("description", "")
        update_items_html += f"""
        <tr>
            <td style="padding: 16px 0; border-bottom: 1px solid {COLORS['gray_100']};">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                        <td style="width: 24px; vertical-align: top; padding-right: 12px;">
                            <div style="width: 24px; height: 24px; background-color: {COLORS['primary']}; border-radius: 50%; text-align: center; line-height: 24px; color: {COLORS['white']}; font-size: 14px; font-weight: 600;">&#10003;</div>
                        </td>
                        <td style="vertical-align: top;">
                            <p style="margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: {COLORS['navy']}; font-family: {FONT_STACK};">{title}</p>
                            <p style="margin: 0; font-size: 14px; color: {COLORS['gray_600']}; font-family: {FONT_STACK}; line-height: 1.5;">{description}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """
    
    content = f"""
    {get_header_html("Platform Updates")}
    <tr>
        <td class="body-content" style="padding: 40px;">
            <h1 style="margin: 0 0 16px 0; font-size: 24px; font-weight: 700; color: {COLORS['navy']}; font-family: {FONT_STACK};">New Features & Updates</h1>
            <p style="margin: 0 0 24px 0; font-size: 16px; color: {COLORS['gray_600']}; line-height: 1.6; font-family: {FONT_STACK};">
                We've been busy improving FounderConsole! Here's what's new in the last 24 hours:
            </p>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 32px;">
                {update_items_html}
            </table>
            
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                    <td align="center" style="padding: 16px 0;">
                        {get_cta_button(app_url, "Try It Now")}
                    </td>
                </tr>
            </table>
            
            <p style="margin: 24px 0 0 0; font-size: 14px; color: {COLORS['gray_500']}; text-align: center; font-family: {FONT_STACK};">
                Click the button above to explore these new features in your dashboard.
            </p>
        </td>
    </tr>
    {get_footer_html()}
    """
    
    return get_email_wrapper(content)


def render_text_only_update_template(
    updates: list,
    app_url: str,
    tracking_id: str = None
) -> str:
    """
    Render a text-only platform update email with tracking pixel.
    
    Args:
        updates: List of dicts with 'title' and 'description' keys
        app_url: URL to the application
        tracking_id: Unique ID for tracking opens (used in pixel URL)
    
    Returns:
        Minimal HTML email with text content and tracking pixel
    """
    update_lines = ""
    for i, update in enumerate(updates, 1):
        title = update.get("title", "")
        description = update.get("description", "")
        update_lines += f"""
        <p style="margin: 0 0 16px 0; font-family: {FONT_STACK}; font-size: 15px; color: {COLORS['gray_700']}; line-height: 1.6;">
            <strong style="color: {COLORS['navy']};">{i}. {title}</strong><br/>
            {description}
        </p>
        """
    
    tracking_pixel = ""
    if tracking_id:
        tracking_pixel = f'<img src="{app_url}/api/email/track/{tracking_id}" width="1" height="1" alt="" style="display:block;width:1px;height:1px;border:0;" />'
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 32px; background-color: {COLORS['white']}; font-family: {FONT_STACK};">
    <p style="margin: 0 0 24px 0; font-size: 16px; color: {COLORS['navy']}; font-weight: 600;">
        FounderConsole - Latest Updates
    </p>
    
    {update_lines}
    
    <p style="margin: 24px 0 0 0; font-size: 14px; color: {COLORS['gray_500']};">
        <a href="{app_url}" style="color: {COLORS['primary']}; text-decoration: none;">Open FounderConsole</a> to try these features.
    </p>
    
    <p style="margin: 32px 0 0 0; font-size: 13px; color: {COLORS['gray_400']};">
        - The FounderConsole Team
    </p>
    {tracking_pixel}
</body>
</html>"""
