"""Email alerts for cryogenic level thresholds."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sendgrid import SendGridAPIClient  # type: ignore
from sendgrid.helpers.mail import Content, Email, Mail, To  # type: ignore
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from cryodash.config import (
    ALERT_COOLDOWN_HOURS,
    ALERT_EMAIL_FROM,
    ALERT_EMAIL_TO,
    ALERT_THRESHOLDS,
    ENABLE_EMAIL_ALERTS,
    SENDGRID_API_KEY,
)
from cryodash.models import AlertHistory, CryogenReading

logger = logging.getLogger(__name__)


def send_email_alert(subject: str, message: str, to_emails: Optional[list[str]] = None) -> bool:
    """
    Send an email alert via SendGrid.

    Args:
        subject: Email subject
        message: Email body (HTML)
        to_emails: List of recipient emails (uses config if None)

    Returns:
        True if sent successfully, False otherwise
    """
    if not ENABLE_EMAIL_ALERTS or not SENDGRID_API_KEY:
        logger.debug("Email alerts disabled or API key not configured")
        return False

    if not to_emails:
        to_emails = ALERT_EMAIL_TO

    if not to_emails:
        logger.warning("No email recipients configured (ALERT_EMAIL_TO)")
        return False

    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        mail = Mail(
            from_email=Email(ALERT_EMAIL_FROM),
            to_emails=[To(email) for email in to_emails],
            subject=subject,
            html_content=Content("text/html", message),
        )
        response = sg.send(mail)
        logger.info(f"Alert email sent: {subject} (status: {response.status_code})")
        return response.status_code in [200, 201, 202]
    except Exception as e:
        logger.error(f"Failed to send alert email: {e}")
        return False


def check_cryogen_levels(db: Session) -> None:
    """
    Check cryogenic levels against thresholds and send alerts if needed.

    Prevents duplicate alerts within cooldown period.
    """
    if not ENABLE_EMAIL_ALERTS:
        logger.debug("Email alerts disabled")
        return

    logger.debug("Checking cryogenic levels for alerts")

    # Get latest reading for each device/cryogen combination
    # Use subquery since SQLite doesn't support DISTINCT ON

    subquery = (
        db.query(
            CryogenReading.device,
            CryogenReading.cryogen,
            func.max(CryogenReading.id).label("max_id"),
        )
        .group_by(CryogenReading.device, CryogenReading.cryogen)
        .subquery()
    )

    readings = (
        db.query(CryogenReading)
        .join(
            subquery,
            (CryogenReading.device == subquery.c.device)
            & (CryogenReading.cryogen == subquery.c.cryogen)
            & (CryogenReading.id == subquery.c.max_id),
        )
        .all()
    )

    for reading in readings:
        device = reading.device.lower()
        cryogen = reading.cryogen.upper()

        # Get thresholds for this device/cryogen
        thresholds = ALERT_THRESHOLDS.get(device, {}).get(cryogen, {})
        if not thresholds:
            continue

        critical_level = thresholds.get("critical", 0)
        warning_level = thresholds.get("warning", 0)

        # Determine alert level
        alert_level = None
        alert_message = None

        if reading.level <= critical_level:
            alert_level = "critical"
            alert_message = (
                f"⚠️ CRITICAL: {device.upper()} {cryogen} level is {reading.level}% "
                f"(critical threshold: {critical_level}%)"
            )
        elif reading.level <= warning_level:
            alert_level = "warning"
            alert_message = (
                f"⚠️ WARNING: {device.upper()} {cryogen} level is {reading.level}% "
                f"(warning threshold: {warning_level}%)"
            )

        if alert_level and alert_message:
            # Check if alert was recently sent (avoid duplicates)
            cooldown_until = datetime.now(timezone.utc) - timedelta(hours=ALERT_COOLDOWN_HOURS)
            recent_alert = (
                db.query(AlertHistory)
                .filter(
                    AlertHistory.device == device,
                    AlertHistory.cryogen == cryogen,
                    AlertHistory.alert_level == alert_level,
                    AlertHistory.sent_at >= cooldown_until,
                )
                .order_by(desc(AlertHistory.sent_at))
                .first()
            )

            if recent_alert:
                logger.debug(
                    f"Alert cooldown active for {device} {cryogen} "
                    f"(last alert: {recent_alert.sent_at})"
                )
                continue

            # Send the alert
            subject = f"CryoDash Alert: {device.upper()} {cryogen} Low Level"
            html_message = f"""
            <html>
                <body>
                    <h2>CryoDash Cryogenic Level Alert</h2>
                    <p><strong>{alert_message}</strong></p>
                    <hr>
                    <p><strong>Device:</strong> {device.upper()}</p>
                    <p><strong>Cryogen:</strong> {cryogen}</p>
                    <p><strong>Current Level:</strong> {reading.level}%</p>
                    <p><strong>Timestamp:</strong> {reading.timestamp}</p>
                    <p><strong>Alert Level:</strong> {alert_level.upper()}</p>
                    <hr>
                    <p>Please check your instrument and refill if necessary.</p>
                </body>
            </html>
            """

            success = send_email_alert(subject, html_message)

            # Log alert in history regardless of send success
            alert_record = AlertHistory(
                device=device,
                cryogen=cryogen,
                level=reading.level,
                alert_level=alert_level,
                sent_at=datetime.now(timezone.utc),
                sent_successfully=success,
            )
            db.add(alert_record)
            db.commit()

            logger.info(
                f"Alert recorded: {device} {cryogen} at {reading.level}% "
                f"(level: {alert_level}, sent: {success})"
            )
