"""
Background email triggers for activity reports.
Sends emails asynchronously when simulations complete, documents are generated, or decisions are made.
"""
import asyncio
import logging
import threading
from typing import Optional

logger = logging.getLogger(__name__)


def _send_in_background(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        def _run():
            try:
                asyncio.run(coro)
            except Exception as e:
                logger.warning(f"Background email send failed: {e}")
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()


def _unsubscribe_url(email: str) -> Optional[str]:
    try:
        from server.email.lifecycle_guard import page_unsubscribe_url_for_email
        return page_unsubscribe_url_for_email(email)
    except Exception as e:
        logger.warning(f"Could not build unsubscribe url: {e}")
        return None


async def _send_activity_email(to: str, subject: str, html: str, campaign: str):
    try:
        from server.email.service import send_lifecycle_email, is_email_configured
        if not is_email_configured():
            logger.debug("Email not configured, skipping activity email")
            return
        result = await send_lifecycle_email(
            to=to,
            subject=subject,
            html_content=html,
            category="lifecycle",
            template=campaign,
            campaign=campaign,
        )
        if result.get("success"):
            logger.info(f"Activity email sent to {to}: {subject}")
        elif result.get("skipped"):
            logger.info("Activity email skipped for %s reason=%s", to, result.get("reason"))
        else:
            logger.warning(f"Activity email failed for {to}: {result.get('error')}")
    except Exception as e:
        logger.warning(f"Activity email error for {to}: {e}")


def trigger_simulation_report_email(
    user_email: str,
    company_name: str,
    scenario_name: str,
    runway: dict,
    survival: dict,
    n_simulations: int = 500,
    horizon_months: int = 24,
    comparison: list = None,
):
    try:
        from server.email.templates import render_simulation_report_template
        html = render_simulation_report_template(
            company_name=company_name,
            scenario_name=scenario_name,
            runway=runway,
            survival=survival,
            n_simulations=n_simulations,
            horizon_months=horizon_months,
            comparison=comparison,
            unsubscribe_url=_unsubscribe_url(user_email),
        )
        subject = f"Simulation Complete — {scenario_name} Results for {company_name}"
        _send_in_background(_send_activity_email(user_email, subject, html, "activity_simulation"))
    except Exception as e:
        logger.warning(f"Failed to trigger simulation report email: {e}")


def trigger_document_generated_email(
    user_email: str,
    company_name: str,
    doc_type: str,
    doc_name: str,
    sections_count: int = 0,
    sections: list = None,
):
    try:
        from server.email.templates import render_document_generated_template
        html = render_document_generated_template(
            company_name=company_name,
            doc_type=doc_type,
            doc_name=doc_name,
            sections_count=sections_count,
            sections=sections,
            unsubscribe_url=_unsubscribe_url(user_email),
        )
        subject = f"Your {doc_name} is Ready — {company_name}"
        _send_in_background(_send_activity_email(user_email, subject, html, "activity_document"))
    except Exception as e:
        logger.warning(f"Failed to trigger document generated email: {e}")


def trigger_decision_report_email(
    user_email: str,
    company_name: str,
    recommendations_count: int = 0,
    top_recommendations: list = None,
):
    try:
        from server.email.templates import render_decision_report_template
        html = render_decision_report_template(
            company_name=company_name,
            recommendations_count=recommendations_count,
            top_recommendations=top_recommendations,
            unsubscribe_url=_unsubscribe_url(user_email),
        )
        subject = f"Decision Recommendations Ready — {company_name}"
        _send_in_background(_send_activity_email(user_email, subject, html, "activity_decision"))
    except Exception as e:
        logger.warning(f"Failed to trigger decision report email: {e}")
