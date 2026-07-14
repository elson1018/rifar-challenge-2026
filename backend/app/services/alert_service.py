import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple
from app.core.config import settings

# Alert level constants
NORMAL   = "NORMAL"
WARNING  = "WARNING"
CRITICAL = "CRITICAL"

logger = logging.getLogger("flood_alerts")

class AlertManager:
    """
    Manages flood alert state and enforces anti-spam rules.
    
    Rules:
    - Only sends an alert when the state TRANSITIONS (e.g. NORMAL → WARNING).
    - Escalation (WARNING → CRITICAL) always fires immediately.
    - Periodic re-alerts fire whenever the cooldown window expires.
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
            return CRITICAL
        elif water_level_m >= settings.WARNING_LEVEL:
            return WARNING
        else:
            return NORMAL

    def _build_message(self, alert_type: str, level: str, water_level_m: float) -> str:
        """Build the multilingual (EN/BM/ZH/TA) Telegram alert message string."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # 1. Dynamic Header based on Severity Level
        if level == CRITICAL:
            header = "🚨 *CRITICAL FLOOD ALERT / AMARAN BANJIR KRITIKAL* 🚨"
        else:
            header = "⚠️ *EARLY WARNING NOTIFICATION / AMARAN AWAL BANJIR* ⚠️"

        # 2. Dynamic Data Labels based on Source Type
        source_text = "SIFMS AI Predictive Model" if alert_type == "prediction" else "SIFMS Live Sensor Telemetry"
        level_text = "Projected Water Level" if alert_type == "prediction" else "Current Water Level"

        return (
            f"{header}\n"
            f"Location: Taman Sri Muda\n"
            f"{level_text} / Paras Air: *{water_level_m:.2f} m*\n"
            f"Time / Masa: {timestamp}\n\n"
            f"Residents are advised to stay vigilant and follow safety guidelines provided by local authorities.\n"
            f"Penduduk dinasihatkan supaya berjaga-jaga dan mematuhi arahan keselamatan daripada pihak berkuasa.\n"
            f"请居民保持警惕，并遵循地方当局的安全指示。\n"
            f"குடியிருப்பாளர்கள் விழிப்புடன் இருக்குமாறும், உள்ளூர் அதிகாரிகளின் பாதுகாப்பு வழிகாட்டுதல்களைப் பின்பற்றுமாறும் அறிவுறுத்தப்படுகிறார்கள்.\n\n"
            f"_System: {source_text}_"
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

        is_escalation = (new_level == CRITICAL and state["state"] == WARNING)
        is_new_state = (new_level != state["last_level"])
        cooldown_ok = (
            state["last_sent_at"] is None or
            (now - state["last_sent_at"]) > timedelta(minutes=settings.COOLDOWN_MINUTES)
        )

        # Fire if: escalation (WARNING→CRITICAL), new state transition, OR cooldown window expired
        # (cooldown_ok alone acts as a periodic reminder while the level remains elevated)
        should_send = is_escalation or is_new_state or cooldown_ok

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
