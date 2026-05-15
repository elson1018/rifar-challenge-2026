import asyncio
from datetime import datetime, timedelta
import telegram
from telegram_config import (
    BOT_TOKEN, CHANNEL_ID,
    WARNING_LEVEL, DANGER_LEVEL, COOLDOWN_MINUTES
)

# Alert level constants
NORMAL  = "NORMAL"
WARNING = "WARNING"
DANGER  = "DANGER"


def _classify(water_level_m: float) -> str:
    """Return alert level based on water level reading."""
    if water_level_m >= DANGER_LEVEL:
        return DANGER
    elif water_level_m >= WARNING_LEVEL:
        return WARNING
    else:
        return NORMAL


def _build_message(alert_type: str, level: str, water_level_m: float) -> str:
    """Build the Telegram alert message string."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

    if alert_type == "prediction":
        source = "🤖 AI Prediction"
        action = "Stay alert. Monitor official updates."
    else:
        source = "📡 Live Sensor"
        action = "EVACUATE immediately if in low-lying areas."

    if level == DANGER:
        icon  = "🚨"
        title = "FLOOD DANGER ALERT"
    else:
        icon  = "⚠️"
        title = "FLOOD WARNING"

    return (
        f"{icon} *{title} — Taman Sri Muda*\n"
        f"Source: {source}\n"
        f"Water Level: *{water_level_m:.2f} m*\n"
        f"Time: {timestamp}\n\n"
        f"{action}"
    )


async def _send_telegram(message: str):
    """Send a message to the configured Telegram channel."""
    bot = telegram.Bot(token=BOT_TOKEN)
    await bot.send_message(
        chat_id=CHANNEL_ID,
        text=message,
        parse_mode="Markdown"
    )


class AlertManager:
    """
    Manages flood alert state and enforces anti-spam rules.

    Rules:
    - Only sends an alert when the state TRANSITIONS (e.g. NORMAL → WARNING).
    - Escalation (WARNING → DANGER) always fires immediately.
    - Same-level re-alerts are blocked for COOLDOWN_MINUTES.
    - State resets to NORMAL when water level drops below WARNING_LEVEL.
    """

    def __init__(self):
        # Separate state tracking for prediction vs sensor alerts
        self._states = {
            "prediction": {"state": NORMAL, "last_sent_at": None, "last_level": None},
            "sensor":     {"state": NORMAL, "last_sent_at": None, "last_level": None},
        }

    def check_and_send(self, alert_type: str, water_level_m: float):
        """
        Evaluate water level, apply state machine, and send Telegram alert if needed.

        Args:
            alert_type:    "prediction" or "sensor"
            water_level_m: current or predicted water level in meters
        """
        if alert_type not in self._states:
            raise ValueError(f"Unknown alert_type '{alert_type}'. Use 'prediction' or 'sensor'.")

        state      = self._states[alert_type]
        new_level  = _classify(water_level_m)
        now        = datetime.now()

        # Level dropped back to normal — reset state so next event fires fresh
        if new_level == NORMAL:
            state["state"] = NORMAL
            state["last_sent_at"] = None
            state["last_level"] = NORMAL
            return {"alerted": False, "reason": "Water level is normal."}

        is_escalation   = (new_level == DANGER and state["state"] == WARNING)
        is_new_state    = (new_level != state["last_level"])
        cooldown_ok     = (
            state["last_sent_at"] is None or
            (now - state["last_sent_at"]) > timedelta(minutes=COOLDOWN_MINUTES)
        )

        should_send = is_escalation or (is_new_state and cooldown_ok)

        if should_send:
            message = _build_message(alert_type, new_level, water_level_m)
            try:
                asyncio.run(_send_telegram(message))
                state["state"]       = new_level
                state["last_sent_at"] = now
                state["last_level"]  = new_level
                return {"alerted": True, "level": new_level, "message": message}
            except Exception as e:
                return {"alerted": False, "reason": f"Telegram error: {str(e)}"}
        else:
            minutes_left = ""
            if state["last_sent_at"]:
                elapsed  = (now - state["last_sent_at"]).seconds // 60
                remaining = COOLDOWN_MINUTES - elapsed
                minutes_left = f" ({remaining} min remaining in cooldown)"
            return {
                "alerted": False,
                "reason": f"Already alerted at {state['last_level']} level{minutes_left}."
            }

    def get_states(self) -> dict:
        """Return current alert states (for debugging / status endpoint)."""
        return {
            k: {
                "state": v["state"],
                "last_sent_at": v["last_sent_at"].isoformat() if v["last_sent_at"] else None,
                "last_level": v["last_level"],
            }
            for k, v in self._states.items()
        }
