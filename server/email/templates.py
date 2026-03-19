"""
Email templates for FounderConsole.
Professional HTML templates using table-based layouts for email client compatibility.
Follows the FounderConsole Email Design System:
  - Max width: 600px
  - Outer bg: #F7F6F2, content card: #FFFFFF
  - Primary: #01696F (Teal), Text: #28251D, Muted: #7A7974
  - CTA: 44px height, 16px padding, #01696F bg, white text, 8px border-radius
  - Footer: Unsubscribe + Email Preferences + CAN-SPAM address
  - Dark mode: @media (prefers-color-scheme: dark)
  - Mobile: single column < 480px, min tap target 44x44px
"""
from datetime import datetime
from typing import Optional, List


COLORS = {
    "primary": "#01696F",
    "primary_dark": "#015256",
    "primary_light": "#e6f2f2",
    "text": "#28251D",
    "text_light": "#4A4740",
    "muted": "#7A7974",
    "muted_light": "#A3A09B",
    "white": "#ffffff",
    "bg_outer": "#F7F6F2",
    "bg_card": "#ffffff",
    "bg_subtle": "#F7F6F2",
    "border": "#E8E6E1",
    "border_light": "#F0EEEA",
    "success": "#2D8A4E",
    "success_bg": "#ECFDF5",
    "warning": "#B45309",
    "warning_bg": "#FFFBEB",
    "danger": "#DC2626",
    "danger_bg": "#FEF2F2",
    "info_bg": "#F0F9FF",
    "info": "#0369A1",
}

FONT_STACK = "system-ui, -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

APP_URL = "https://founderconsole.ai"
PREFERENCES_URL = f"{APP_URL}/settings/notifications"
COMPANY_ADDRESS = "FounderConsole, Inc."


def get_email_wrapper(content: str, preheader: str = "") -> str:
    preheader_html = ""
    if preheader:
        preheader_html = f"""<div style="display:none;font-size:1px;color:{COLORS['bg_outer']};line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">{preheader} &zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;&zwnj;&nbsp;</div>"""

    return f"""<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:o="urn:schemas-microsoft-com:office:office">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="x-apple-disable-message-reformatting">
    <meta name="color-scheme" content="light dark">
    <meta name="supported-color-schemes" content="light dark">
    <title>FounderConsole</title>
    <!--[if mso]>
    <noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript>
    <![endif]-->
    <style type="text/css">
        :root {{ color-scheme: light dark; supported-color-schemes: light dark; }}
        body, table, td, a {{ -webkit-text-size-adjust: 100%; -ms-text-size-adjust: 100%; }}
        table, td {{ mso-table-lspace: 0pt; mso-table-rspace: 0pt; }}
        img {{ -ms-interpolation-mode: bicubic; border: 0; height: auto; line-height: 100%; outline: none; text-decoration: none; }}
        table {{ border-collapse: collapse !important; }}
        body {{ margin: 0 !important; padding: 0 !important; width: 100% !important; }}
        a[x-apple-data-detectors] {{ color: inherit !important; text-decoration: none !important; }}
        @media only screen and (max-width: 600px) {{
            .email-container {{ width: 100% !important; max-width: 100% !important; }}
            .body-content {{ padding: 28px 20px !important; }}
            .mobile-full {{ width: 100% !important; display: block !important; }}
            .mobile-hide {{ display: none !important; }}
            .mobile-pad {{ padding: 12px 16px !important; }}
            .cta-btn {{ display: block !important; width: 100% !important; text-align: center !important; padding: 16px 24px !important; }}
        }}
        @media (prefers-color-scheme: dark) {{
            body, .email-bg {{ background-color: #1a1a17 !important; }}
            .email-container, .card-bg {{ background-color: #2a2923 !important; }}
            .dark-text {{ color: #E8E6E1 !important; }}
            .dark-muted {{ color: #A3A09B !important; }}
            .dark-border {{ border-color: #3d3b35 !important; }}
            .dark-subtle-bg {{ background-color: #33312b !important; }}
            .footer-bg {{ background-color: #22211c !important; }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 0; background-color: {COLORS['bg_outer']}; font-family: {FONT_STACK};" class="email-bg">
    {preheader_html}
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {COLORS['bg_outer']};" class="email-bg">
        <tr>
            <td align="center" style="padding: 40px 16px;">
                <table role="presentation" class="email-container" width="600" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; background-color: {COLORS['bg_card']}; border-radius: 12px; overflow: hidden; border: 1px solid {COLORS['border_light']};" class="card-bg">
                    {content}
                </table>
            </td>
        </tr>
    </table>
</body>
</html>"""


def get_header_html(subtitle: str = "") -> str:
    subtitle_html = ""
    if subtitle:
        subtitle_html = f"""
                <tr>
                    <td align="left" style="padding-top: 6px;">
                        <span style="color: {COLORS['muted']}; font-size: 11px; font-weight: 500; letter-spacing: 1.5px; text-transform: uppercase; font-family: {FONT_STACK};" class="dark-muted">{subtitle}</span>
                    </td>
                </tr>"""

    return f"""
    <tr>
        <td style="padding: 28px 40px 20px 40px;" class="body-content">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                <tr>
                    <td align="left" style="vertical-align: middle;">
                        <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                            <tr>
                                <td style="vertical-align: middle; padding-right: 10px;">
                                    <div style="width: 32px; height: 32px; background-color: {COLORS['primary']}; border-radius: 8px; text-align: center; line-height: 32px; color: {COLORS['white']}; font-weight: 700; font-size: 16px; font-family: {FONT_STACK};">F</div>
                                </td>
                                <td style="vertical-align: middle;">
                                    <span style="font-size: 18px; font-weight: 700; color: {COLORS['text']}; letter-spacing: -0.3px; font-family: {FONT_STACK};" class="dark-text">FounderConsole</span>
                                </td>
                            </tr>
                        </table>
                    </td>
                    <td align="right" style="vertical-align: middle;">
                        <a href="{APP_URL}" target="_blank" style="font-size: 12px; color: {COLORS['muted']}; text-decoration: none; font-family: {FONT_STACK};" class="dark-muted">View in browser</a>
                    </td>
                </tr>{subtitle_html}
            </table>
        </td>
    </tr>
    <tr>
        <td style="padding: 0 40px;" class="body-content">
            <div style="height: 1px; background-color: {COLORS['border']};" class="dark-border"></div>
        </td>
    </tr>"""


def get_footer_html(unsubscribe_url: str = None) -> str:
    unsub_url = unsubscribe_url or f"{APP_URL}/unsubscribe"
    return f"""
    <tr>
        <td style="padding: 0 40px;" class="body-content">
            <div style="height: 1px; background-color: {COLORS['border']};" class="dark-border"></div>
        </td>
    </tr>
    <tr>
        <td style="padding: 24px 40px 32px 40px; text-align: center;" class="body-content footer-bg">
            <p style="margin: 0 0 12px 0; font-size: 13px; color: {COLORS['muted']}; font-family: {FONT_STACK};" class="dark-muted">
                <a href="{unsub_url}" target="_blank" style="color: {COLORS['muted']}; text-decoration: underline;">Unsubscribe</a>
                &nbsp;&middot;&nbsp;
                <a href="{PREFERENCES_URL}" target="_blank" style="color: {COLORS['muted']}; text-decoration: underline;">Email Preferences</a>
                &nbsp;&middot;&nbsp;
                <a href="{APP_URL}" target="_blank" style="color: {COLORS['muted']}; text-decoration: underline;">Open App</a>
            </p>
            <p style="margin: 0; font-size: 12px; color: {COLORS['muted_light']}; font-family: {FONT_STACK}; line-height: 1.5;" class="dark-muted">
                {COMPANY_ADDRESS}<br>
                AI-Powered Financial Intelligence for Startups
            </p>
        </td>
    </tr>"""


def get_cta_button(url: str, text: str, secondary: bool = False) -> str:
    if secondary:
        bg = "transparent"
        color = COLORS['primary']
        border = f"2px solid {COLORS['primary']}"
    else:
        bg = COLORS['primary']
        color = COLORS['white']
        border = "none"

    return f"""
    <table role="presentation" cellspacing="0" cellpadding="0" border="0" align="center" style="margin: 0 auto;">
        <tr>
            <td>
                <!--[if mso]>
                <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" xmlns:w="urn:schemas-microsoft-com:office:word" href="{url}" style="height:44px;v-text-anchor:middle;width:220px;" arcsize="18%" fillcolor="{bg}" stroke="f">
                    <w:anchorlock/>
                    <center style="color:{color};font-family:{FONT_STACK};font-size:15px;font-weight:600;">{text}</center>
                </v:roundrect>
                <![endif]-->
                <!--[if !mso]><!-->
                <a href="{url}" target="_blank" class="cta-btn" style="display: inline-block; padding: 13px 32px; font-size: 15px; font-weight: 600; color: {color}; text-decoration: none; background-color: {bg}; border-radius: 8px; border: {border}; font-family: {FONT_STACK}; min-height: 44px; line-height: 18px;">{text}</a>
                <!--<![endif]-->
            </td>
        </tr>
    </table>"""


def get_cta_row(primary_url: str, primary_text: str, secondary_url: str = None, secondary_text: str = None) -> str:
    secondary_html = ""
    if secondary_url and secondary_text:
        secondary_html = f"""
                    <td width="12"></td>
                    <td>{get_cta_button(secondary_url, secondary_text, secondary=True)}</td>"""
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 28px 0;">
        <tr>
            <td align="center">
                <table role="presentation" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                        <td>{get_cta_button(primary_url, primary_text)}</td>{secondary_html}
                    </tr>
                </table>
            </td>
        </tr>
    </table>"""


def get_info_card(title: str, items_html: str) -> str:
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {COLORS['bg_subtle']}; border-radius: 8px; margin: 24px 0;" class="dark-subtle-bg">
        <tr>
            <td style="padding: 24px;" class="mobile-pad">
                <p style="margin: 0 0 16px 0; font-size: 12px; font-weight: 600; color: {COLORS['text']}; text-transform: uppercase; letter-spacing: 1.5px; font-family: {FONT_STACK};" class="dark-text">{title}</p>
                {items_html}
            </td>
        </tr>
    </table>"""


def get_check_item(text: str) -> str:
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 10px;">
        <tr>
            <td width="28" valign="top" style="padding-right: 10px;">
                <div style="width: 20px; height: 20px; background-color: {COLORS['primary']}; border-radius: 50%; text-align: center; line-height: 20px; color: {COLORS['white']}; font-size: 11px;">&#10003;</div>
            </td>
            <td valign="top" style="font-size: 14px; color: {COLORS['text_light']}; line-height: 1.5; font-family: {FONT_STACK};" class="dark-text">
                {text}
            </td>
        </tr>
    </table>"""


def get_numbered_step(num: str, title: str, desc: str, url: str = None) -> str:
    title_html = f'<a href="{url}" style="color: {COLORS["primary"]}; text-decoration: none; font-weight: 600;">{title}</a>' if url else f'<span style="font-weight: 600; color: {COLORS["text"]};" class="dark-text">{title}</span>'
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 16px;">
        <tr>
            <td width="40" valign="top" style="padding-right: 12px;">
                <div style="width: 28px; height: 28px; background-color: {COLORS['primary']}; border-radius: 50%; text-align: center; line-height: 28px; color: {COLORS['white']}; font-weight: 600; font-size: 13px; font-family: {FONT_STACK};">{num}</div>
            </td>
            <td valign="top">
                <p style="margin: 0 0 2px 0; font-size: 15px; font-family: {FONT_STACK};">{title_html}</p>
                <p style="margin: 0; color: {COLORS['muted']}; font-size: 13px; line-height: 1.5; font-family: {FONT_STACK};" class="dark-muted">{desc}</p>
            </td>
        </tr>
    </table>"""


def get_kpi_card(label: str, value: str, delta: str = None, status: str = "neutral") -> str:
    delta_html = ""
    if delta:
        delta_color = COLORS['success'] if status == "good" else COLORS['danger'] if status == "bad" else COLORS['muted']
        arrow = "&#9650;" if status == "good" else "&#9660;" if status == "bad" else ""
        delta_html = f'<span style="font-size: 12px; color: {delta_color}; font-weight: 500;">{arrow} {delta}</span>'

    return f"""
    <td align="center" style="padding: 14px; background-color: {COLORS['bg_subtle']}; border-radius: 8px; width: 25%;" class="dark-subtle-bg mobile-full">
        <p style="margin: 0; font-size: 11px; color: {COLORS['muted']}; text-transform: uppercase; letter-spacing: 0.5px; font-family: {FONT_STACK};" class="dark-muted">{label}</p>
        <p style="margin: 4px 0 2px 0; font-size: 22px; font-weight: 700; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">{value}</p>
        {delta_html}
    </td>"""


def get_divider() -> str:
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
        <tr>
            <td style="padding: 20px 0;">
                <div style="height: 1px; background-color: {COLORS['border']};" class="dark-border"></div>
            </td>
        </tr>
    </table>"""


def get_alert_banner(alert_type: str, severity: str = "warning") -> str:
    if severity == "critical":
        bg = COLORS['danger_bg']
        border_color = COLORS['danger']
        text_color = COLORS['danger']
        icon = "&#9888;"
    elif severity == "warning":
        bg = COLORS['warning_bg']
        border_color = COLORS['warning']
        text_color = COLORS['warning']
        icon = "&#9888;"
    else:
        bg = COLORS['info_bg']
        border_color = COLORS['info']
        text_color = COLORS['info']
        icon = "&#8505;"

    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
        <tr>
            <td style="background-color: {bg}; border-left: 4px solid {border_color}; border-radius: 0 8px 8px 0; padding: 14px 20px;">
                <p style="margin: 0; font-size: 14px; font-weight: 600; color: {text_color}; font-family: {FONT_STACK}; text-transform: uppercase; letter-spacing: 0.5px;">{icon} {alert_type}</p>
            </td>
        </tr>
    </table>"""


def get_callout_box(text: str, style: str = "info") -> str:
    if style == "warning":
        bg = COLORS['warning_bg']
        border = COLORS['warning']
    elif style == "success":
        bg = COLORS['success_bg']
        border = COLORS['success']
    elif style == "danger":
        bg = COLORS['danger_bg']
        border = COLORS['danger']
    else:
        bg = COLORS['bg_subtle']
        border = COLORS['border']

    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 20px 0;">
        <tr>
            <td style="background-color: {bg}; border-left: 3px solid {border}; border-radius: 0 8px 8px 0; padding: 14px 18px;">
                <p style="margin: 0; color: {COLORS['text_light']}; font-size: 14px; line-height: 1.6; font-family: {FONT_STACK};" class="dark-text">{text}</p>
            </td>
        </tr>
    </table>"""


def get_feature_card(title: str, description: str, icon: str) -> str:
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid {COLORS['border']}; border-radius: 8px; margin-bottom: 12px;" class="dark-border">
        <tr>
            <td style="padding: 18px;" class="mobile-pad">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                        <td width="40" valign="top" style="padding-right: 14px;">
                            <div style="width: 36px; height: 36px; background-color: {COLORS['primary_light']}; border-radius: 8px; text-align: center; line-height: 36px; font-size: 18px;">{icon}</div>
                        </td>
                        <td valign="top">
                            <p style="margin: 0 0 4px 0; font-weight: 600; color: {COLORS['text']}; font-size: 15px; font-family: {FONT_STACK};" class="dark-text">{title}</p>
                            <p style="margin: 0; color: {COLORS['muted']}; font-size: 13px; line-height: 1.5; font-family: {FONT_STACK};" class="dark-muted">{description}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>"""


def get_stat_box(value: str, label: str) -> str:
    return f"""
    <td align="center" style="padding: 14px; background-color: {COLORS['bg_subtle']}; border-radius: 8px;" class="dark-subtle-bg">
        <p style="margin: 0 0 2px 0; font-size: 24px; font-weight: 700; color: {COLORS['primary']}; font-family: {FONT_STACK};">{value}</p>
        <p style="margin: 0; font-size: 11px; color: {COLORS['muted']}; text-transform: uppercase; letter-spacing: 0.5px; font-family: {FONT_STACK};" class="dark-muted">{label}</p>
    </td>"""


# ---------------------------------------------------------------------------
# Template Renderers
# ---------------------------------------------------------------------------

def render_email_verification_template(verify_url: str) -> str:
    content = f"""
    {get_header_html("EMAIL VERIFICATION")}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            <h2 style="margin: 0 0 12px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">Verify your email address</h2>
            <p style="font-size: 15px; color: {COLORS['muted']}; margin: 0 0 4px 0; line-height: 1.6; font-family: {FONT_STACK};" class="dark-muted">Thanks for signing up for FounderConsole. Click the button below to confirm your email and activate your account.</p>

            {get_cta_row(verify_url, "Verify Email Address")}

            {get_callout_box("This link expires in 24 hours. If you didn't create an account, you can safely ignore this email.")}
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader="Confirm your email to start using FounderConsole")


def render_welcome_template(
    user_name: Optional[str] = None,
    login_url: str = "https://founderconsole.ai/auth"
) -> str:
    greeting = f"Welcome aboard, {user_name}!" if user_name else "Welcome aboard!"
    dashboard_url = f"{APP_URL}/overview"
    data_url = f"{APP_URL}/data-input"
    sim_url = f"{APP_URL}/simulation"

    steps_html = ""
    steps_html += get_numbered_step("1", "Enter your financials", "Upload a CSV/PDF or type in your key numbers. Takes about 2 minutes.", url=data_url)
    steps_html += get_numbered_step("2", "Run your first simulation", "See your probabilistic runway with P10/P50/P90 confidence bands.", url=sim_url)
    steps_html += get_numbered_step("3", "Get your GO / NO-GO score", "Receive AI-ranked decision recommendations based on your data.", url=dashboard_url)

    content = f"""
    {get_header_html()}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            <h2 style="margin: 0 0 12px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">{greeting}</h2>
            <p style="font-size: 15px; color: {COLORS['muted']}; margin: 0 0 24px 0; line-height: 1.6; font-family: {FONT_STACK};" class="dark-muted">Your AI CFO is ready. Get your first financial simulation running in under 5 minutes.</p>

            {get_info_card("Get Started in 3 Steps", steps_html)}

            {get_cta_row(dashboard_url, "Go to Dashboard")}

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {COLORS['bg_subtle']}; border-radius: 8px; margin-top: 8px;" class="dark-subtle-bg">
                <tr>
                    <td style="padding: 18px 20px; text-align: center;">
                        <p style="margin: 0; color: {COLORS['muted']}; font-size: 13px; font-family: {FONT_STACK};" class="dark-muted">Need help? Reply to this email or use the AI Copilot inside your dashboard.</p>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader="Get your first financial simulation running in under 5 minutes")


def render_password_reset_template(reset_url: str) -> str:
    content = f"""
    {get_header_html("PASSWORD RESET")}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            <h2 style="margin: 0 0 12px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">Reset your password</h2>
            <p style="font-size: 15px; color: {COLORS['muted']}; margin: 0 0 4px 0; line-height: 1.6; font-family: {FONT_STACK};" class="dark-muted">We received a request to reset the password for your FounderConsole account. Click the button below to create a new password.</p>

            {get_cta_row(reset_url, "Reset Password")}

            {get_callout_box("<strong>Security Notice:</strong> This link expires in 1 hour. If you didn't request this reset, please ignore this email or contact support.", style="warning")}

            <p style="color: {COLORS['muted']}; font-size: 13px; margin: 0; font-family: {FONT_STACK};" class="dark-muted">For security, never share this link. FounderConsole will never ask for your password via email.</p>
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader="Reset your FounderConsole password — link expires in 1 hour")


def render_invite_template(
    invite_url: str,
    role: str,
    invited_by_email: str,
    expires_at: datetime,
    early_access: bool = True
) -> str:
    role_display = role.title()
    expires_formatted = expires_at.strftime("%B %d, %Y at %I:%M %p UTC")

    header_subtitle = "EARLY ACCESS INVITATION" if early_access else "PLATFORM INVITATION"

    early_badge = ""
    if early_access:
        early_badge = f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 20px;">
        <tr>
            <td>
                <span style="display: inline-block; background-color: {COLORS['primary_light']}; color: {COLORS['primary']}; padding: 4px 12px; border-radius: 4px; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; font-family: {FONT_STACK};">Early Access</span>
            </td>
        </tr>
    </table>"""

    role_badge = f'<span style="display: inline-block; background-color: {COLORS["primary_light"]}; color: {COLORS["primary"]}; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; font-family: {FONT_STACK};">{role_display}</span>'

    features = [
        "AI-powered financial metric extraction from documents",
        "Monte Carlo simulations for cash flow forecasting",
        "Decision recommendations ranked by survival & risk",
        "Real-time runway and burn rate tracking",
    ]
    if early_access:
        features.append("Direct feedback channel to shape the roadmap")

    features_html = "".join([get_check_item(f) for f in features])

    content = f"""
    {get_header_html(header_subtitle)}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            {early_badge}
            <h2 style="margin: 0 0 12px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">You're invited to FounderConsole</h2>
            <p style="font-size: 15px; color: {COLORS['muted']}; margin: 0 0 16px 0; line-height: 1.6; font-family: {FONT_STACK};" class="dark-muted">
                <span style="color: {COLORS['primary']}; font-weight: 600;">{invited_by_email}</span> has invited you to join as a {role_badge}
            </p>

            {get_cta_row(invite_url, "Accept Invitation")}

            {get_info_card("What You'll Get", features_html)}

            <p style="text-align: center; color: {COLORS['muted']}; font-size: 13px; margin: 20px 0 0 0; font-family: {FONT_STACK};" class="dark-muted">This invitation expires on {expires_formatted}</p>

            {get_divider()}

            <p style="color: {COLORS['muted']}; font-size: 13px; margin: 0; font-family: {FONT_STACK};" class="dark-muted">If you weren't expecting this, you can safely ignore this email.</p>
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader=f"{invited_by_email} invited you to FounderConsole")


def render_platform_update_template(
    updates: list,
    app_url: str
) -> str:
    update_items_html = ""
    for update in updates:
        title = update.get("title", "")
        description = update.get("description", "")
        item_type = update.get("type", "feature")

        if item_type == "fix":
            icon_char = "&#128295;"
            badge = f'<span style="display:inline-block;padding:2px 7px;background-color:{COLORS["success_bg"]};color:{COLORS["success"]};font-size:10px;font-weight:600;border-radius:4px;margin-left:8px;vertical-align:middle;text-transform:uppercase;letter-spacing:0.5px;">Fix</span>'
        else:
            icon_char = "&#10024;"
            badge = f'<span style="display:inline-block;padding:2px 7px;background-color:{COLORS["primary_light"]};color:{COLORS["primary"]};font-size:10px;font-weight:600;border-radius:4px;margin-left:8px;vertical-align:middle;text-transform:uppercase;letter-spacing:0.5px;">New</span>'

        update_items_html += f"""
        <tr>
            <td style="padding: 14px 0; border-bottom: 1px solid {COLORS['border_light']};" class="dark-border">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                    <tr>
                        <td style="width: 32px; vertical-align: top; padding-right: 12px;">
                            <div style="width: 28px; height: 28px; background-color: {COLORS['bg_subtle']}; border-radius: 6px; text-align: center; line-height: 28px; font-size: 14px;" class="dark-subtle-bg">{icon_char}</div>
                        </td>
                        <td style="vertical-align: top;">
                            <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">{title}{badge}</p>
                            <p style="margin: 0; font-size: 13px; color: {COLORS['muted']}; font-family: {FONT_STACK}; line-height: 1.5;" class="dark-muted">{description}</p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>"""

    content = f"""
    {get_header_html("PLATFORM UPDATES")}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            <h2 style="margin: 0 0 8px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">New Features &amp; Bug Fixes</h2>
            <p style="margin: 0 0 24px 0; font-size: 15px; color: {COLORS['muted']}; line-height: 1.6; font-family: {FONT_STACK};" class="dark-muted">
                Here's everything we just shipped:
            </p>

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 24px;">
                {update_items_html}
            </table>

            {get_cta_row(app_url, "Try It Now")}

            <p style="margin: 0; font-size: 13px; color: {COLORS['muted']}; text-align: center; font-family: {FONT_STACK};" class="dark-muted">
                Click above to explore these updates in your dashboard.
            </p>
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader="New features and fixes just shipped to FounderConsole")


def render_text_only_update_template(
    updates: list,
    app_url: str,
    tracking_id: str = None
) -> str:
    update_lines = ""
    for i, update in enumerate(updates, 1):
        title = update.get("title", "")
        description = update.get("description", "")
        item_type = update.get("type", "feature")
        tag = "[Fix]" if item_type == "fix" else "[New]"
        update_lines += f"""
        <p style="margin: 0 0 16px 0; font-family: {FONT_STACK}; font-size: 15px; color: {COLORS['text_light']}; line-height: 1.6;">
            <strong style="color: {COLORS['text']};">{i}. {title}</strong> <span style="font-size:11px;color:{COLORS['muted']};text-transform:uppercase;">{tag}</span><br/>
            {description}
        </p>"""

    tracking_pixel = ""
    if tracking_id:
        tracking_pixel = f'<img src="{app_url}/api/email/track/{tracking_id}" width="1" height="1" alt="" style="display:block;width:1px;height:1px;border:0;" />'

    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin: 0; padding: 32px; background-color: {COLORS['white']}; font-family: {FONT_STACK};">
    <p style="margin: 0 0 24px 0; font-size: 18px; color: {COLORS['text']}; font-weight: 600;">FounderConsole — Latest Updates</p>
    {update_lines}
    <p style="margin: 24px 0 0 0; font-size: 14px; color: {COLORS['muted']};">
        <a href="{app_url}" style="color: {COLORS['primary']}; text-decoration: none;">Open FounderConsole</a> to try these features.
    </p>
    <p style="margin: 32px 0 0 0; font-size: 13px; color: {COLORS['muted_light']};">— The FounderConsole Team</p>
    <p style="margin: 16px 0 0 0; font-size: 12px; color: {COLORS['muted_light']};">
        <a href="{APP_URL}/unsubscribe" style="color: {COLORS['muted_light']}; text-decoration: underline;">Unsubscribe</a> &middot;
        <a href="{PREFERENCES_URL}" style="color: {COLORS['muted_light']}; text-decoration: underline;">Email Preferences</a>
    </p>
    {tracking_pixel}
</body></html>"""


def render_app_overview_template(
    user_name: str = None,
    login_url: str = "https://founderconsole.ai/overview",
    dashboard_screenshot_url: str = None,
    truth_scan_screenshot_url: str = None,
    simulation_screenshot_url: str = None,
    decision_screenshot_url: str = None
) -> str:
    greeting = f"Hello {user_name}," if user_name else "Hello,"

    hero_screenshot = ""
    if dashboard_screenshot_url:
        hero_screenshot = f"""
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 20px 0;">
            <tr><td><img src="{dashboard_screenshot_url}" alt="FounderConsole Dashboard" width="100%" style="border-radius: 8px; border: 1px solid {COLORS['border']}; display: block;" /></td></tr>
        </table>"""

    features_html = ""
    features_html += get_feature_card("Truth Scan", "Extract and validate 24+ financial metrics from your documents. Benchmarked against industry standards.", "&#128202;")
    features_html += get_feature_card("Monte Carlo Simulation", "Run probabilistic forecasts with up to 10,000 iterations. See P10/P50/P90 confidence intervals.", "&#128200;")
    features_html += get_feature_card("AI Decision Engine", "Get ranked recommendations based on survival probability, growth potential, and dilution impact.", "&#9889;")

    also_html = ""
    also_html += get_check_item("AI Copilot for guided analysis and Q&A")
    also_html += get_check_item("Smart alerts for anomalies and runway warnings")
    also_html += get_check_item("Cap table management with dilution modeling")
    also_html += get_check_item("Board deck generation and export")
    also_html += get_check_item("37 data integrations (QuickBooks, Stripe, Gusto, and more)")

    content = f"""
    {get_header_html()}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            <p style="font-size: 15px; color: {COLORS['muted']}; margin: 0 0 8px 0; font-family: {FONT_STACK};" class="dark-muted">{greeting}</p>
            <h2 style="margin: 0 0 12px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; letter-spacing: -0.3px; line-height: 1.3; font-family: {FONT_STACK};" class="dark-text">Your AI-Powered Financial Command Center</h2>
            <p style="font-size: 15px; color: {COLORS['muted']}; margin: 0 0 24px 0; line-height: 1.6; font-family: {FONT_STACK};" class="dark-muted">
                FounderConsole gives startups <span style="color: {COLORS['primary']}; font-weight: 600;">investor-grade financial analysis</span> in minutes, not weeks.
            </p>

            {hero_screenshot}

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 20px 0;">
                <tr>
                    {get_stat_box("24+", "Metrics")}
                    <td width="10"></td>
                    {get_stat_box("10K", "Simulations")}
                    <td width="10"></td>
                    {get_stat_box("P90", "Confidence")}
                </tr>
            </table>

            {get_divider()}

            <h3 style="margin: 0 0 16px 0; font-size: 16px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">Core Capabilities</h3>
            {features_html}

            {get_info_card("Also Included", also_html)}

            {get_cta_row(login_url, "Go to Dashboard")}

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="background-color: {COLORS['bg_subtle']}; border-radius: 8px;" class="dark-subtle-bg">
                <tr>
                    <td style="padding: 18px 20px; text-align: center;">
                        <p style="margin: 0; color: {COLORS['muted']}; font-size: 13px; font-family: {FONT_STACK};" class="dark-muted">Need help? Our AI Copilot is available 24/7 inside the platform.</p>
                    </td>
                </tr>
            </table>
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader="Investor-grade financial analysis in minutes, not weeks")


def render_copilot_pitch_template(
    recipient_name: Optional[str] = None,
    cta_url: str = "https://founderconsole.ai"
) -> str:
    greeting = f"Hi {recipient_name}," if recipient_name else "Hi there,"

    content = f"""
    {get_header_html()}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            <p style="color: {COLORS['muted']}; font-size: 15px; line-height: 1.6; margin: 0 0 16px 0; font-family: {FONT_STACK};" class="dark-muted">{greeting}</p>
            <h2 style="margin: 0 0 16px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">What if you could ask a CFO any question about your business?</h2>
            <p style="color: {COLORS['muted']}; font-size: 15px; line-height: 1.6; margin: 0 0 24px 0; font-family: {FONT_STACK};" class="dark-muted">
                <strong style="color: {COLORS['text']};" class="dark-text">FounderConsole AI Copilot</strong> gives you an always-available financial intelligence partner that knows your numbers.
            </p>

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 0 0 24px 0; background-color: {COLORS['bg_subtle']}; border-radius: 8px;" class="dark-subtle-bg">
                <tr>
                    <td style="padding: 20px;">
                        <p style="color: {COLORS['text']}; font-weight: 600; font-size: 13px; margin: 0 0 10px 0; text-transform: uppercase; letter-spacing: 1px;" class="dark-text">Ask in plain English</p>
                        <p style="color: {COLORS['muted']}; font-size: 14px; font-style: italic; margin: 0 0 6px 0; font-family: {FONT_STACK};" class="dark-muted">"What's my real runway?"</p>
                        <p style="color: {COLORS['muted']}; font-size: 14px; font-style: italic; margin: 0 0 6px 0; font-family: {FONT_STACK};" class="dark-muted">"What happens if our Series A slips 3 months?"</p>
                        <p style="color: {COLORS['muted']}; font-size: 14px; font-style: italic; margin: 0 0 6px 0; font-family: {FONT_STACK};" class="dark-muted">"How do I extend runway without layoffs?"</p>
                        <p style="color: {COLORS['muted']}; font-size: 14px; font-style: italic; margin: 0; font-family: {FONT_STACK};" class="dark-muted">"Who are my competitors and how do I differentiate?"</p>
                    </td>
                </tr>
            </table>

            <h3 style="margin: 0 0 12px 0; font-size: 15px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">Three specialized AI agents working for you</h3>

            {get_feature_card("CFO Agent", "Runway analysis, burn optimization, unit economics deep-dives", "&#128176;")}
            {get_feature_card("Market Agent", "Competitor analysis, industry benchmarks, differentiation strategy", "&#127760;")}
            {get_feature_card("Strategy Agent", "GTM planning, 30/60/90 day roadmaps, growth vs. efficiency trade-offs", "&#127919;")}

            <p style="color: {COLORS['muted']}; font-size: 15px; line-height: 1.6; margin: 20px 0 0 0; font-family: {FONT_STACK};" class="dark-muted">
                The Copilot analyzes <strong style="color: {COLORS['text']};" class="dark-text">your actual financials</strong> and responds with specific, actionable recommendations — not generic advice.
            </p>

            {get_cta_row(cta_url, "Try Copilot Free")}

            <p style="color: {COLORS['muted']}; font-size: 13px; margin: 0; text-align: center; font-family: {FONT_STACK};" class="dark-muted">
                Upload your financials once. Ask unlimited questions.
            </p>
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader="Ask any financial question. Get CFO-grade answers instantly.")


# ---------------------------------------------------------------------------
# Activity Report Templates (Simulation, Document, Decision)
# ---------------------------------------------------------------------------

def render_simulation_report_template(
    company_name: str,
    scenario_name: str,
    runway: dict,
    survival: dict,
    n_simulations: int = 500,
    horizon_months: int = 24,
    comparison: list = None,
) -> str:
    p10 = runway.get("p10", "—")
    p50 = runway.get("p50", "—")
    p90 = runway.get("p90", "—")

    surv_12 = survival.get("12m", survival.get("12", "—"))
    surv_18 = survival.get("18m", survival.get("18", "—"))
    surv_24 = survival.get("24m", survival.get("24", "—"))

    def fmt_pct(v):
        if isinstance(v, (int, float)):
            return f"{v:.0f}%" if v > 1 else f"{v*100:.0f}%"
        return str(v)

    def fmt_mo(v):
        if isinstance(v, (int, float)):
            return f"{v:.0f}"
        return str(v)

    p50_status = "good" if isinstance(p50, (int, float)) and p50 >= 18 else "bad" if isinstance(p50, (int, float)) and p50 < 12 else "neutral"

    comparison_html = ""
    if comparison and len(comparison) > 1:
        rows = ""
        for c in comparison[:5]:
            score = c.get("composite_score", 0)
            score_display = f"{score:.0f}" if isinstance(score, (int, float)) else str(score)
            rows += f"""
            <tr>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['border_light']}; font-size: 14px; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text dark-border">{c.get('name', '—')}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['border_light']}; font-size: 14px; color: {COLORS['text']}; text-align: center; font-family: {FONT_STACK};" class="dark-text dark-border">{fmt_mo(c.get('runway_p50', '—'))} mo</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['border_light']}; font-size: 14px; color: {COLORS['text']}; text-align: center; font-family: {FONT_STACK};" class="dark-text dark-border">{fmt_pct(c.get('survival_18m', '—'))}</td>
                <td style="padding: 8px 12px; border-bottom: 1px solid {COLORS['border_light']}; font-size: 14px; color: {COLORS['primary']}; text-align: center; font-weight: 600; font-family: {FONT_STACK};">{score_display}</td>
            </tr>"""

        comparison_html = f"""
            {get_divider()}
            <h3 style="margin: 0 0 12px 0; font-size: 15px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">Scenario Comparison</h3>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid {COLORS['border']}; border-radius: 8px; overflow: hidden;" class="dark-border">
                <tr style="background-color: {COLORS['bg_subtle']};" class="dark-subtle-bg">
                    <td style="padding: 8px 12px; font-size: 11px; font-weight: 600; color: {COLORS['muted']}; text-transform: uppercase; letter-spacing: 0.5px;" class="dark-muted">Scenario</td>
                    <td style="padding: 8px 12px; font-size: 11px; font-weight: 600; color: {COLORS['muted']}; text-transform: uppercase; letter-spacing: 0.5px; text-align: center;" class="dark-muted">Runway P50</td>
                    <td style="padding: 8px 12px; font-size: 11px; font-weight: 600; color: {COLORS['muted']}; text-transform: uppercase; letter-spacing: 0.5px; text-align: center;" class="dark-muted">Surv. 18m</td>
                    <td style="padding: 8px 12px; font-size: 11px; font-weight: 600; color: {COLORS['muted']}; text-transform: uppercase; letter-spacing: 0.5px; text-align: center;" class="dark-muted">Score</td>
                </tr>
                {rows}
            </table>"""

    sim_url = f"{APP_URL}/simulation"

    content = f"""
    {get_header_html("SIMULATION REPORT")}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            <h2 style="margin: 0 0 8px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">Simulation Complete</h2>
            <p style="margin: 0 0 24px 0; font-size: 15px; color: {COLORS['muted']}; line-height: 1.6; font-family: {FONT_STACK};" class="dark-muted">
                <strong style="color: {COLORS['text']};" class="dark-text">{scenario_name}</strong> for {company_name} &mdash; {n_simulations:,} Monte Carlo iterations over {horizon_months} months.
            </p>

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 0 0 24px 0;">
                <tr>
                    {get_kpi_card("P10 Runway", f"{fmt_mo(p10)} mo", status="bad")}
                    <td width="8"></td>
                    {get_kpi_card("P50 Runway", f"{fmt_mo(p50)} mo", status=p50_status)}
                    <td width="8"></td>
                    {get_kpi_card("P90 Runway", f"{fmt_mo(p90)} mo", status="good")}
                </tr>
            </table>

            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin: 0 0 24px 0;">
                <tr>
                    {get_kpi_card("Surv. 12m", fmt_pct(surv_12))}
                    <td width="8"></td>
                    {get_kpi_card("Surv. 18m", fmt_pct(surv_18))}
                    <td width="8"></td>
                    {get_kpi_card("Surv. 24m", fmt_pct(surv_24))}
                </tr>
            </table>

            {get_callout_box(f"<strong>Tip:</strong> Adjust the burn rate slider by &minus;10% in the What-If Explorer and see how your P50 shifts. Most founders find 2&ndash;3 key levers that change everything.")}

            {comparison_html}

            {get_cta_row(sim_url, "View Full Results", f"{APP_URL}/decisions", "Get Recommendations")}
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader=f"P10/P50/P90 results are in for {company_name}. See your runway outlook.")


def render_document_generated_template(
    company_name: str,
    doc_type: str,
    doc_name: str,
    sections_count: int = 0,
    sections: list = None,
) -> str:
    doc_type_icons = {
        "board-deck": "&#128203;",
        "monthly-update": "&#128203;",
        "fundraising-prep": "&#128188;",
        "scenario-analysis": "&#128200;",
        "financial-model": "&#128200;",
        "investor-memo": "&#128188;",
        "board-memo": "&#128196;",
        "kpi-report": "&#128202;",
        "pitch-deck-outline": "&#127916;",
        "scenario-brief": "&#128209;",
    }
    icon = doc_type_icons.get(doc_type, "&#128196;")

    sections_html = ""
    if sections:
        items = ""
        for s in sections[:8]:
            title = s.get("title", "") if isinstance(s, dict) else str(s)
            items += get_check_item(title)
        sections_html = get_info_card("Sections Included", items)

    view_url = f"{APP_URL}/board-export" if "board" in doc_type or doc_type in ["monthly-update", "fundraising-prep", "scenario-analysis"] else f"{APP_URL}/doc-generator"

    content = f"""
    {get_header_html("DOCUMENT READY")}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="margin-bottom: 20px;">
                <tr>
                    <td width="48" valign="top" style="padding-right: 14px;">
                        <div style="width: 44px; height: 44px; background-color: {COLORS['primary_light']}; border-radius: 10px; text-align: center; line-height: 44px; font-size: 22px;">{icon}</div>
                    </td>
                    <td valign="middle">
                        <h2 style="margin: 0 0 4px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">Your {doc_name} is Ready</h2>
                        <p style="margin: 0; font-size: 14px; color: {COLORS['muted']}; font-family: {FONT_STACK};" class="dark-muted">Generated for {company_name}</p>
                    </td>
                </tr>
            </table>

            <p style="font-size: 15px; color: {COLORS['muted']}; margin: 0 0 20px 0; line-height: 1.6; font-family: {FONT_STACK};" class="dark-muted">
                Your document has been generated with {sections_count} AI-powered sections using your latest financial data.
            </p>

            {sections_html}

            {get_cta_row(view_url, "View Document", f"{APP_URL}/overview", "Go to Dashboard")}

            {get_callout_box(f"<strong>Next step:</strong> Review and customize the AI-generated narratives, then export as PDF or share directly with your board or investors.")}
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader=f"Your {doc_name} for {company_name} is ready to review")


def render_decision_report_template(
    company_name: str,
    recommendations_count: int = 0,
    top_recommendations: list = None,
) -> str:
    recs_html = ""
    if top_recommendations:
        for i, rec in enumerate(top_recommendations[:5], 1):
            title = rec.get("title", rec.get("action", "Recommendation"))
            score = rec.get("composite_score", rec.get("score", 0))
            impact = rec.get("impact_summary", rec.get("description", ""))

            score_display = f"{score:.0f}" if isinstance(score, (int, float)) else str(score)

            badge_color = COLORS['success'] if isinstance(score, (int, float)) and score >= 70 else COLORS['warning'] if isinstance(score, (int, float)) and score >= 40 else COLORS['danger']

            recs_html += f"""
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border: 1px solid {COLORS['border']}; border-radius: 8px; margin-bottom: 10px;" class="dark-border">
                <tr>
                    <td style="padding: 16px;" class="mobile-pad">
                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0">
                            <tr>
                                <td valign="top" style="padding-right: 12px;">
                                    <div style="width: 24px; height: 24px; background-color: {COLORS['primary']}; border-radius: 50%; text-align: center; line-height: 24px; color: {COLORS['white']}; font-size: 12px; font-weight: 600; font-family: {FONT_STACK};">{i}</div>
                                </td>
                                <td valign="top" style="width: 100%;">
                                    <p style="margin: 0 0 4px 0; font-size: 15px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">{title}</p>
                                    <p style="margin: 0; font-size: 13px; color: {COLORS['muted']}; line-height: 1.5; font-family: {FONT_STACK};" class="dark-muted">{impact[:120]}{"..." if len(impact) > 120 else ""}</p>
                                </td>
                                <td valign="top" style="padding-left: 12px; white-space: nowrap;">
                                    <span style="display: inline-block; padding: 4px 10px; background-color: {badge_color}; color: {COLORS['white']}; border-radius: 4px; font-size: 12px; font-weight: 600; font-family: {FONT_STACK};">{score_display}</span>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>"""

    decisions_url = f"{APP_URL}/decisions"

    content = f"""
    {get_header_html("DECISION REPORT")}
    <tr>
        <td class="body-content" style="padding: 32px 40px 40px 40px;">
            <h2 style="margin: 0 0 8px 0; font-size: 22px; font-weight: 600; color: {COLORS['text']}; font-family: {FONT_STACK};" class="dark-text">Decision Recommendations Ready</h2>
            <p style="margin: 0 0 24px 0; font-size: 15px; color: {COLORS['muted']}; line-height: 1.6; font-family: {FONT_STACK};" class="dark-muted">
                {recommendations_count} AI-ranked recommendation{"s" if recommendations_count != 1 else ""} generated for <strong style="color: {COLORS['text']};" class="dark-text">{company_name}</strong>, scored by survival probability, growth impact, and risk.
            </p>

            {recs_html}

            {get_cta_row(decisions_url, "View All Recommendations", f"{APP_URL}/simulation", "Run New Simulation")}

            {get_callout_box("<strong>How scoring works:</strong> Each recommendation is evaluated across survival rate improvement (45%), runway extension (20%), efficiency gains (15%), and growth impact (20%), with risk penalties applied.")}
        </td>
    </tr>
    {get_footer_html()}"""
    return get_email_wrapper(content, preheader=f"{recommendations_count} decision recommendations ready for {company_name}")


# ---------------------------------------------------------------------------
# Template Config Registry
# ---------------------------------------------------------------------------

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
        "subject": "Welcome to FounderConsole — your AI CFO is ready",
        "render_fn": "render_welcome_template"
    },
    "password_reset": {
        "name": "Password Reset Email",
        "description": "Sent when a user requests a password reset",
        "variables": ["reset_url"],
        "subject": "Reset Your FounderConsole Password",
        "render_fn": "render_password_reset_template"
    },
    "email_verification": {
        "name": "Email Verification",
        "description": "Sent after signup to verify the email address",
        "variables": ["verify_url"],
        "subject": "Verify Your FounderConsole Email",
        "render_fn": "render_email_verification_template"
    },
    "app_overview": {
        "name": "App Overview",
        "description": "Product showcase email with screenshots explaining key features",
        "variables": ["user_name", "login_url", "dashboard_screenshot_url", "truth_scan_screenshot_url", "simulation_screenshot_url", "decision_screenshot_url"],
        "subject": "Discover FounderConsole — Your AI Financial Command Center",
        "render_fn": "render_app_overview_template"
    },
    "copilot_pitch": {
        "name": "AI Copilot Pitch",
        "description": "Sales pitch email for the AI Copilot feature",
        "variables": ["recipient_name", "cta_url"],
        "subject": "Ask any financial question. Get CFO-grade answers.",
        "render_fn": "render_copilot_pitch_template"
    },
    "platform_update": {
        "name": "Platform Update",
        "description": "Announces new features and bug fixes",
        "variables": ["updates", "app_url"],
        "subject": "FounderConsole — New Features & Fixes Just Shipped",
        "render_fn": "render_platform_update_template"
    },
    "simulation_report": {
        "name": "Simulation Report",
        "description": "Sent after a Monte Carlo simulation completes",
        "variables": ["company_name", "scenario_name", "runway", "survival", "n_simulations", "horizon_months"],
        "subject": "Simulation Complete — {scenario_name} Results Ready",
        "render_fn": "render_simulation_report_template"
    },
    "document_generated": {
        "name": "Document Generated",
        "description": "Sent after a board deck or document is generated",
        "variables": ["company_name", "doc_type", "doc_name", "sections_count"],
        "subject": "Your {doc_name} is Ready",
        "render_fn": "render_document_generated_template"
    },
    "decision_report": {
        "name": "Decision Report",
        "description": "Sent after AI decision recommendations are generated",
        "variables": ["company_name", "recommendations_count", "top_recommendations"],
        "subject": "Decision Recommendations Ready for {company_name}",
        "render_fn": "render_decision_report_template"
    },
}


def get_template_preview(template_type: str) -> Optional[str]:
    sample_data = {
        "invite": {
            "invite_url": "https://founderconsole.ai/auth?invite=sample_token_abc123",
            "role": "analyst",
            "invited_by_email": "admin@company.com",
            "expires_at": datetime.now(),
            "early_access": True
        },
        "welcome": {
            "user_name": "John",
            "login_url": "https://founderconsole.ai/auth"
        },
        "password_reset": {
            "reset_url": "https://founderconsole.ai/reset-password?token=sample_reset_token"
        },
        "email_verification": {
            "verify_url": "https://founderconsole.ai/verify-email?token=sample_verify_token"
        },
        "app_overview": {
            "user_name": "John",
            "login_url": "https://founderconsole.ai/overview",
        },
        "copilot_pitch": {
            "recipient_name": "Nikita",
            "cta_url": "https://founderconsole.ai/copilot"
        },
        "platform_update": {
            "updates": [
                {"title": "Investor Data Room", "description": "Upload and organize due diligence documents by category."},
                {"title": "Board Deck HTML Export", "description": "Export board decks as HTML for Google Slides or PowerPoint.", "type": "feature"},
                {"title": "Headcount Bug Fix", "description": "Fixed headcount not propagating from Simple Mode.", "type": "fix"},
            ],
            "app_url": "https://founderconsole.ai"
        },
        "simulation_report": {
            "company_name": "Acme Corp",
            "scenario_name": "Baseline",
            "runway": {"p10": 8, "p50": 14, "p90": 22},
            "survival": {"12m": 72, "18m": 55, "24m": 38},
            "n_simulations": 500,
            "horizon_months": 24,
        },
        "document_generated": {
            "company_name": "Acme Corp",
            "doc_type": "monthly-update",
            "doc_name": "Monthly Board Update",
            "sections_count": 6,
            "sections": [
                {"title": "Key Metrics Overview"},
                {"title": "Revenue & Burn Trend"},
                {"title": "Executive Summary"},
            ],
        },
        "decision_report": {
            "company_name": "Acme Corp",
            "recommendations_count": 3,
            "top_recommendations": [
                {"title": "Reduce SaaS Tool Spend", "composite_score": 82, "impact_summary": "Cut $12K/mo in redundant tools. Extends runway by 2 months."},
                {"title": "Accelerate Enterprise Sales", "composite_score": 71, "impact_summary": "Focus on 3 high-value deals in pipeline to increase MRR by 15%."},
                {"title": "Defer Hiring Plan by 60 Days", "composite_score": 65, "impact_summary": "Postpone 2 engineering hires. Saves $30K/mo with minimal velocity impact."},
            ],
        },
    }

    renderers = {
        "invite": render_invite_template,
        "welcome": render_welcome_template,
        "password_reset": render_password_reset_template,
        "email_verification": render_email_verification_template,
        "app_overview": render_app_overview_template,
        "copilot_pitch": render_copilot_pitch_template,
        "platform_update": render_platform_update_template,
        "simulation_report": render_simulation_report_template,
        "document_generated": render_document_generated_template,
        "decision_report": render_decision_report_template,
    }

    if template_type in renderers and template_type in sample_data:
        return renderers[template_type](**sample_data[template_type])
    return None
