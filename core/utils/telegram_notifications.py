# core/utils/telegram_notifications.py
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def notify_user_subscription_activated(user_profile, subscription):
    """
    Send Telegram notification to user when subscription is activated.
    """
    if not user_profile.tg_id:
        logger.warning(f"No Telegram ID for user {user_profile.id}")
        return

    message = (
        f"🎉 Your subscription has been activated!\n\n"
        f"Plan: {subscription.tier.display_name}\n"
        f"Valid until: {subscription.expiry_date.strftime('%Y-%m-%d') if subscription.expiry_date else 'Permanent'}\n"
        f"Enjoy full access to all exams and features!"
    )

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_profile.tg_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(f"Failed to notify user {user_profile.tg_id}: {response.text}")
    except Exception as e:
        logger.exception(f"Telegram notification failed for user {user_profile.tg_id}")
        

def notify_user_subscription_rejected(user_profile):
    """
    Notify user when admin rejects their payment/transaction.
    """
    if not user_profile.tg_id:
        logger.warning(f"No Telegram ID for user {user_profile.id}")
        return

    message = (
        f"❌ Your recent payment was not approved.\n\n"
        f"Please double-check the details and try again, "
        f"or contact support if you believe this is an error.\n"
        f"We appreciate your patience!"
    )

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_profile.tg_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(f"Failed to notify rejection to user {user_profile.tg_id}: {response.text}")
    except Exception as e:
        logger.exception(f"Telegram rejection notification failed for user {user_profile.tg_id}")