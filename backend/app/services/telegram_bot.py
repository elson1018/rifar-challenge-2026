import asyncio
import logging
from httpx import AsyncClient, HTTPStatusError
from app.core.config import settings

logger = logging.getLogger("flood_alerts")

class ResilientTelegramBot:
    def __init__(self, token: str = settings.TELEGRAM_BOT_TOKEN, channel_id: str = settings.TELEGRAM_CHANNEL_ID):
        self.token = token
        self.channel_id = channel_id
        self.api_url = f"https://api.telegram.org/bot{token}/sendMessage"

    async def send_alert_with_retry(self, text: str, max_retries: int = 5) -> bool:
        """
        Sends an alert message to Telegram with retry support for rate limits (429) and network issues.
        """
        if not self.token or not self.channel_id:
            logger.error("Telegram token or channel ID not configured.")
            return False

        payload = {
            "chat_id": self.channel_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        
        async with AsyncClient() as client:
            for attempt in range(1, max_retries + 1):
                try:
                    response = await client.post(self.api_url, json=payload, timeout=10.0)
                    response.raise_for_status()
                    return True
                except HTTPStatusError as exc:
                    if exc.response.status_code == 429:
                        # Parse retry duration from Telegram API parameters if present, fallback to 5s
                        retry_after = exc.response.json().get("parameters", {}).get("retry_after", 5)
                        logger.warning(f"Telegram rate limited! Retrying after {retry_after}s. Attempt {attempt}/{max_retries}")
                        await asyncio.sleep(retry_after)
                    else:
                        logger.error(f"HTTP error sending alert: {exc}")
                        break
                except Exception as exc:
                    # Exponential backoff on network failures
                    wait_time = 2 ** attempt
                    logger.warning(f"Network error: {exc}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
            
            logger.critical("Failed to send Telegram alert after maximum retries.")
            return False
