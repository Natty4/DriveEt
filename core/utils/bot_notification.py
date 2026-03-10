# core/utils/telegram_notifications.py
import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

def send_screenshot_to_admin(user, transaction, screenshot_url):
    chat_id = settings.ADMIN_CHAT_ID
    message = (
        f"New payment pending approval!\n"
        f"User: {user.tg_id} (@{user.tg_username})\n"
        f"Tier: {transaction.subscription_tier.display_name}\n"
        f"Amount: {transaction.amount} ETB\n"
        f"Reference: {transaction.reference_number or 'N/A'}\n"
        f"Screenshot: {screenshot_url}"
    )

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)


def notify_user_subscription_activated(user_profile, subscription):
    """
    Send Telegram notification using Bot API 9.5 features:
    - Native date formatting via <tg-time>
    - Colored 'Primary' (blue) action button
    """
    if not user_profile.tg_id:
        logger.warning(f"No Telegram ID for user {user_profile.id}")
        return

    miniapp_url = settings.MINIAPP_LINK

    if subscription.expiry_date:
        unix_ts = int(subscription.expiry_date.timestamp())
        # Use 'unix' attribute and provide fallback text as per docs
        fallback_date = subscription.expiry_date.strftime('%d.%m.%Y')
        expiry_display = f'<tg-time unix="{unix_ts}" format="D">{fallback_date}</tg-time>'
    else:
        expiry_display = "Permanent"

    message = (
        f"🎉 <b>Your subscription has been activated!</b>\n\n"
        f"<b>Plan:</b> {subscription.tier.display_name}\n"
        f"<b>Valid until:</b> {expiry_display}\n\n"
        f"❇️ You now have full access to all exams and features.\n\n"
        f"Launch the exam app and enjoy <a href='{miniapp_url}'>Driveet Safe</a>"
    )

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": user_profile.tg_id,
        "text": message,
        "parse_mode": "HTML",
    }
        
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(f"TG API Error, Failed to notify activation to user : {response.text}")
        response.raise_for_status()
    except Exception as e:
        logger.exception(f"TG notification failed: {e}")
 
        
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

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
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
        

def notify_user_subscription_under_review(user_profile, tier):
    """
    Notify user that their payment screenshot was received
    and the subscription verification is in progress.
    """
    if not user_profile.tg_id:
        logger.warning(f"No Telegram ID for user {user_profile.id}")
        return

    message = (
        f"⏳ <b>Payment Received</b>\n\n"
        f"Plan: <b>{tier.display_name}</b>\n\n"
        f"Your payment screenshot has been received and is currently under verification.\n\n"
        f"You will be notified once your subscription is activated."
    )

    url = f"https://api.telegram.org/bot{settings.BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": user_profile.tg_id,
        "text": message,
        "parse_mode": "HTML"
    }

    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            logger.error(f"Failed to notify review status to user {user_profile.tg_id}: {response.text}")
    except Exception:
        logger.exception(f"Telegram review notification failed for user {user_profile.tg_id}")