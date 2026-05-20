import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from app.core.config import settings

# Alert level constants
NORMAL  = "NORMAL"
WARNING = "WARNING"
DANGER  = "DANGER"

logger = logging.getLogger("flood_alerts")

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

    def _classify(self, water_level_m: float) -> str:
        """Return alert level based on water level reading."""
        if water_level_m >= settings.DANGER_LEVEL:
            return DANGER
        elif water_level_m >= settings.WARNING_LEVEL:
            return WARNING
        else:
            return NORMAL

    def _build_message(self, alert_type: str, level: str, water_level_m: float) -> str:
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

    def evaluate_alert(self, alert_type: str, water_level_m: float) -> Tuple[bool, Dict[str, Any]]:
        """
        Evaluate if an alert should be triggered.
        Does not perform network calls. Mutates internal state when an alert is approved.
        
        Args:
            alert_type: "prediction" or "sensor"
            water_level_m: current or predicted water level in meters
        Returns:
            Tuple of (should_send: bool, alert_result_dict: dict)
        """
        if alert_type not in self._states:
            raise ValueError(f"Unknown alert_type '{alert_type}'. Use 'prediction' or 'sensor'.")

        state = self._states[alert_type]
        new_level = self._classify(water_level_m)
        now = datetime.now()

        # Level dropped back to normal — reset state so next event fires fresh
        if new_level == NORMAL:
            state["state"] = NORMAL
            state["last_sent_at"] = None
            state["last_level"] = NORMAL
            return False, {"alerted": False, "reason": "Water level is normal.", "level": NORMAL}

        is_escalation = (new_level == DANGER and state["state"] == WARNING)
        is_new_state = (new_level != state["last_level"])
        cooldown_ok = (
            state["last_sent_at"] is None or
            (now - state["last_sent_at"]) > timedelta(minutes=settings.COOLDOWN_MINUTES)
        )

        should_send = is_escalation or (is_new_state and cooldown_ok)

        if should_send:
            message = self._build_message(alert_type, new_level, water_level_m)
            # Mutate state locally (assuming background task will execute the send)
            state["state"] = new_level
            state["last_sent_at"] = now
            state["last_level"] = new_level
            return True, {"alerted": True, "level": new_level, "message": message}
        else:
            minutes_left = ""
            if state["last_sent_at"]:
                elapsed = (now - state["last_sent_at"]).seconds // 60
                remaining = settings.COOLDOWN_MINUTES - elapsed
                if remaining > 0:
                    minutes_left = f" ({remaining} min remaining in cooldown)"
            return False, {
                "alerted": False,
                "level": new_level,
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
