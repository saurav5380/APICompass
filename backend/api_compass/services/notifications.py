from __future__ import annotations

import logging
from typing import Iterable

from api_compass.core.config import settings
from api_compass.models.enums import AlertChannel

logger = logging.getLogger(__name__)


def send_email_alert(subject: str, body: str, recipients: Iterable[str] | None = None) -> bool:
    if recipients is None:
        default_recipient = settings.alerts_default_recipient
        if default_recipient:
            recipients = [default_recipient]
        else:
            recipients = []

    recipients_list = [recipient for recipient in recipients if recipient]
    if not recipients_list:
        logger.info("Alert email dropped (no recipients): %s", subject)
        return False

    sender = settings.alerts_email_sender
    logger.info(
        "ALERT EMAIL\nFrom: %s\nTo: %s\nSubject: %s\n\n%s",
        sender,
        ", ".join(recipients_list),
        subject,
        body,
    )
    return True


def send_slack_dm(message: str, user_id: str | None = None) -> bool:
    # Placeholder for future Slack integration.
    logger.info("Slack DM (%s): %s", user_id or "default", message)
    return True


CHANNEL_DISPATCH = {
    AlertChannel.EMAIL: send_email_alert,
    AlertChannel.SLACK: send_slack_dm,
}
