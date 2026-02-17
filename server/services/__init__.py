"""Services module for FounderConsole."""

from .notifications import (
    send_feature_notification,
    send_deployment_notification,
    NOTIFICATION_RECIPIENTS
)

__all__ = [
    "send_feature_notification",
    "send_deployment_notification", 
    "NOTIFICATION_RECIPIENTS"
]
