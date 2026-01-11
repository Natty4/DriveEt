# core/utils/telegram_bot.py

import requests
from django.conf import settings

def send_screenshot_to_admin(user, transaction, screenshot_url):
    chat_id = settings.ADMIN_CHAT_ID
    message = (
        f"New payment pending approval!\n"
        f"User: {user.telegram_id} (@{user.telegram_username})\n"
        f"Tier: {transaction.subscription_tier.display_name}\n"
        f"Amount: {transaction.amount} ETB\n"
        f"Reference: {transaction.reference_number or 'N/A'}\n"
        f"Screenshot: {screenshot_url}"
    )

    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    requests.post(url, json=payload)