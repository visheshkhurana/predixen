"""
Email templates for Predixen Intelligence OS.
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
    <title>Predixen</title>
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
                                    <span style="font-size: 24px; font-weight: 700; color: {COLORS['white']}; letter-spacing: -0.5px; font-family: {FONT_STACK};">Predixen</span>
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
            <p style="margin: 0 0 4px 0; font-size: 16px; font-weight: 600; color: {COLORS['navy']}; font-family: {FONT_STACK};">Predixen</p>
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
            You've been selected for <span style="color: {COLORS['primary']}; font-weight: 600;">exclusive early access</span> to Predixen Intelligence OS.
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
            <span style="color: {COLORS['primary']}; font-weight: 600;">{invited_by_email}</span> has invited you to join Predixen Intelligence OS as a {role_badge}
        </p>
        <p style="font-size: 15px; color: {COLORS['gray_600']}; margin: 0 0 16px 0; line-height: 1.7; font-family: {FONT_STACK};">
            Predixen helps startups make data-driven financial decisions with AI-powered analysis and probabilistic forecasting.
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
    login_url: str = "https://predixen.app/auth"
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
    {get_header_html("WELCOME TO PREDIXEN")}
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


def render_password_reset_template(
    reset_url: str
) -> str:
    """Render the password reset email template."""
    content = f"""
    {get_header_html("PASSWORD RESET")}
    <tr>
        <td class="body-content" style="padding: 40px;">
            <h2 style="margin: 0 0 16px 0; font-size: 24px; font-weight: 600; color: {COLORS['navy']}; letter-spacing: -0.3px; font-family: {FONT_STACK};">Reset Your Password</h2>
            <p style="font-size: 15px; color: {COLORS['gray_600']}; margin: 0 0 16px 0; line-height: 1.7; font-family: {FONT_STACK};">We received a request to reset the password for your Predixen account. Click the button below to create a new password.</p>
            
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
            
            <p style="color: {COLORS['gray_500']}; font-size: 13px; margin: 0; font-family: {FONT_STACK};">For security reasons, never share this link with anyone. Predixen will never ask for your password via email.</p>
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
        "subject": "You're invited to Predixen Early Access",
        "render_fn": "render_invite_template"
    },
    "welcome": {
        "name": "Welcome Email",
        "description": "Sent after a user completes registration",
        "variables": ["user_name", "login_url"],
        "subject": "Welcome to Predixen Intelligence OS",
        "render_fn": "render_welcome_template"
    },
    "password_reset": {
        "name": "Password Reset Email",
        "description": "Sent when a user requests a password reset",
        "variables": ["reset_url"],
        "subject": "Reset Your Predixen Password",
        "render_fn": "render_password_reset_template"
    }
}


def get_template_preview(template_type: str) -> Optional[str]:
    """
    Get a preview of an email template with sample data.
    
    Args:
        template_type: One of 'invite', 'welcome', 'password_reset'
    
    Returns:
        HTML content of the template with sample data
    """
    sample_data = {
        "invite": {
            "invite_url": "https://predixen.app/auth?invite=sample_token_abc123",
            "role": "analyst",
            "invited_by_email": "admin@company.com",
            "expires_at": datetime.now(),
            "early_access": True
        },
        "welcome": {
            "user_name": "John Doe",
            "login_url": "https://predixen.app/auth"
        },
        "password_reset": {
            "reset_url": "https://predixen.app/reset-password?token=sample_reset_token"
        }
    }
    
    if template_type == "invite":
        return render_invite_template(**sample_data["invite"])
    elif template_type == "welcome":
        return render_welcome_template(**sample_data["welcome"])
    elif template_type == "password_reset":
        return render_password_reset_template(**sample_data["password_reset"])
    
    return None
