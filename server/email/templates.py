"""
Email templates for Predixen Intelligence OS.
Provides HTML templates for various transactional emails.
"""
from datetime import datetime
from typing import Optional


def get_base_styles() -> str:
    """Common CSS styles for email templates."""
    return """
    <style>
        body {
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #1a1a2e;
            margin: 0;
            padding: 0;
            background-color: #f4f4f8;
        }
        .email-container {
            max-width: 600px;
            margin: 0 auto;
            background-color: #ffffff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .email-header {
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            padding: 32px 24px;
            text-align: center;
        }
        .email-header h1 {
            color: #ffffff;
            margin: 0;
            font-size: 24px;
            font-weight: 700;
        }
        .email-header .logo {
            font-size: 28px;
            font-weight: 800;
            color: #ffffff;
            margin-bottom: 8px;
        }
        .email-body {
            padding: 32px 24px;
        }
        .email-body h2 {
            color: #1a1a2e;
            font-size: 20px;
            margin-top: 0;
            margin-bottom: 16px;
        }
        .email-body p {
            color: #4a4a68;
            margin-bottom: 16px;
        }
        .cta-button {
            display: inline-block;
            background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
            color: #ffffff !important;
            text-decoration: none;
            padding: 14px 32px;
            border-radius: 8px;
            font-weight: 600;
            font-size: 16px;
            margin: 16px 0;
            text-align: center;
        }
        .cta-button:hover {
            opacity: 0.9;
        }
        .info-box {
            background-color: #f0f0ff;
            border-left: 4px solid #6366f1;
            padding: 16px;
            margin: 24px 0;
            border-radius: 0 8px 8px 0;
        }
        .info-box p {
            margin: 0;
            color: #4a4a68;
        }
        .email-footer {
            background-color: #f8f8fc;
            padding: 24px;
            text-align: center;
            border-top: 1px solid #e8e8f0;
        }
        .email-footer p {
            color: #8888a0;
            font-size: 13px;
            margin: 4px 0;
        }
        .highlight {
            color: #6366f1;
            font-weight: 600;
        }
        .role-badge {
            display: inline-block;
            background-color: #e0e7ff;
            color: #4338ca;
            padding: 4px 12px;
            border-radius: 16px;
            font-size: 14px;
            font-weight: 500;
        }
        .expiry-notice {
            color: #f59e0b;
            font-size: 14px;
        }
    </style>
    """


def get_email_wrapper(content: str) -> str:
    """Wrap content in base email HTML structure."""
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    {get_base_styles()}
</head>
<body>
    <div style="padding: 24px;">
        <div class="email-container">
            {content}
        </div>
    </div>
</body>
</html>
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
    
    if early_access:
        header_title = "Early Access Invitation"
        intro_text = f"""
            <p style="font-size: 18px; color: #4a4a68; margin-bottom: 24px;">
                You've been selected for <span class="highlight">exclusive early access</span> to Predixen Intelligence OS.
            </p>
            <p>
                <span class="highlight">{invited_by_email}</span> has personally invited you to be among the first to experience 
                our AI-powered financial intelligence platform. Your role: <span class="role-badge">{role_display}</span>
            </p>
        """
        early_badge = """
            <div style="text-align: center; margin-bottom: 24px;">
                <span style="display: inline-block; background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%); 
                      color: white; padding: 6px 16px; border-radius: 20px; font-size: 12px; font-weight: 600; 
                      text-transform: uppercase; letter-spacing: 1px;">
                    Early Access Member
                </span>
            </div>
        """
        value_prop = """
            <div class="info-box">
                <p><strong>As an early access member, you'll get:</strong></p>
                <p>• <strong>First look</strong> at new features before public release</p>
                <p>• <strong>AI-powered analysis</strong> of your financial documents (PDF & Excel)</p>
                <p>• <strong>Monte Carlo simulations</strong> for cash flow forecasting</p>
                <p>• <strong>Decision recommendations</strong> ranked by survival, growth & risk</p>
                <p>• <strong>Direct feedback channel</strong> to shape the product roadmap</p>
            </div>
        """
    else:
        header_title = "You're Invited!"
        intro_text = f"""
            <p>You've been invited by <span class="highlight">{invited_by_email}</span> to join Predixen Intelligence OS as a <span class="role-badge">{role_display}</span>.</p>
            <p>Predixen is an AI-powered financial intelligence platform that helps startups with investor-grade diligence, probabilistic simulation, and ranked decision recommendations.</p>
        """
        early_badge = ""
        value_prop = """
            <div class="info-box">
                <p><strong>What you'll get access to:</strong></p>
                <p>• Financial metrics extraction and analysis</p>
                <p>• Monte Carlo simulations for forecasting</p>
                <p>• AI-powered decision recommendations</p>
                <p>• Real-time runway and burn tracking</p>
            </div>
        """
    
    content = f"""
        <div class="email-header">
            <div class="logo">Predixen</div>
            <h1>{header_title}</h1>
        </div>
        <div class="email-body">
            {early_badge}
            <h2>Join Predixen Intelligence OS</h2>
            {intro_text}
            
            <div style="text-align: center; margin: 32px 0;">
                <a href="{invite_url}" class="cta-button">Accept Your Invitation</a>
            </div>
            
            {value_prop}
            
            <p class="expiry-notice" style="text-align: center;">This invitation expires on {expires_formatted}.</p>
            
            <p style="font-size: 13px; color: #8888a0; margin-top: 24px;">If you weren't expecting this invitation, you can safely ignore this email.</p>
        </div>
        <div class="email-footer">
            <p><strong>Predixen Intelligence OS</strong></p>
            <p>AI-Powered Financial Intelligence for Startups</p>
        </div>
    """
    return get_email_wrapper(content)


def render_welcome_template(
    user_name: Optional[str] = None,
    login_url: str = "https://predixen.ai/login"
) -> str:
    """Render the welcome email template."""
    greeting = f"Welcome, {user_name}!" if user_name else "Welcome!"
    
    content = f"""
        <div class="email-header">
            <div class="logo">Predixen</div>
            <h1>Welcome Aboard!</h1>
        </div>
        <div class="email-body">
            <h2>{greeting}</h2>
            <p>Your account has been created successfully. You're now ready to start making data-driven decisions for your startup.</p>
            
            <div style="text-align: center;">
                <a href="{login_url}" class="cta-button">Go to Dashboard</a>
            </div>
            
            <div class="info-box">
                <p><strong>Getting Started:</strong></p>
                <p>1. Upload your financial documents (PDF or Excel)</p>
                <p>2. Review your Truth Scan metrics</p>
                <p>3. Run simulations to forecast scenarios</p>
                <p>4. Get AI-powered recommendations</p>
            </div>
            
            <p>Need help? Our platform includes an AI Copilot that can guide you through any feature.</p>
        </div>
        <div class="email-footer">
            <p>Predixen Intelligence OS</p>
            <p>AI-Powered Financial Intelligence for Startups</p>
        </div>
    """
    return get_email_wrapper(content)


def render_password_reset_template(
    reset_url: str
) -> str:
    """Render the password reset email template."""
    content = f"""
        <div class="email-header">
            <div class="logo">Predixen</div>
            <h1>Password Reset</h1>
        </div>
        <div class="email-body">
            <h2>Reset Your Password</h2>
            <p>We received a request to reset the password for your Predixen account. Click the button below to create a new password.</p>
            
            <div style="text-align: center;">
                <a href="{reset_url}" class="cta-button">Reset Password</a>
            </div>
            
            <div class="info-box">
                <p><strong>Security Notice:</strong></p>
                <p>This link will expire in 1 hour for security reasons. If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
            </div>
            
            <p style="font-size: 13px; color: #8888a0;">If you didn't request this password reset, you can safely ignore this email.</p>
        </div>
        <div class="email-footer">
            <p>Predixen Intelligence OS</p>
            <p>AI-Powered Financial Intelligence for Startups</p>
        </div>
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
            "invite_url": "https://predixen.ai/register?token=sample_token_abc123",
            "role": "analyst",
            "invited_by_email": "admin@company.com",
            "expires_at": datetime.now(),
            "early_access": True
        },
        "welcome": {
            "user_name": "John Doe",
            "login_url": "https://predixen.ai/login"
        },
        "password_reset": {
            "reset_url": "https://predixen.ai/reset-password?token=sample_reset_token"
        }
    }
    
    if template_type == "invite":
        return render_invite_template(**sample_data["invite"])
    elif template_type == "welcome":
        return render_welcome_template(**sample_data["welcome"])
    elif template_type == "password_reset":
        return render_password_reset_template(**sample_data["password_reset"])
    
    return None
