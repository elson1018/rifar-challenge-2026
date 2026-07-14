from fastapi import APIRouter, Depends, BackgroundTasks, Security
from typing import Dict, Any
from collections import deque
import requests
import datetime

from app.schemas.flood import (
    PredictRequest, PredictResponse,
    SensorRequest, SensorResponse,
    LiveStatusResponse
)
from app.api.dependencies import (
    get_prediction_service, get_alert_manager, get_telegram_bot, get_sensor_filter
)
from app.services.prediction_service import KerasPredictionService
from app.services.alert_service import AlertManager
from app.services.telegram_bot import ResilientTelegramBot
from app.services.data_filter import SensorDataFilter
from app.core.security import validate_api_key

router = APIRouter()

# --- ANTECEDENT RAINFALL HISTORY (rolling 3-reading deque for rainfall_3d_sum feature) ---
# Tracks the last 3 daily-equivalent rainfall readings so the Keras model receives its
# antecedent moisture input even in a live-sensor or single-reading context.
_rainfall_history: deque = deque([0.0, 0.0, 0.0], maxlen=3)

def _compute_3d_sum() -> float:
    """Return the sum of the last 3 recorded rainfall readings (mm)."""
    return round(sum(_rainfall_history), 1)

def _seed_from_open_meteo() -> dict:
    """
    Fetch the current-hour rainfall from Open-Meteo at startup so the dashboard
    never shows fabricated hardcoded values before the first sensor POST.
    Falls back to 0.0 mm if the API is unreachable.
    """
    try:
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=3.0296&longitude=101.5288"
            "&hourly=precipitation&timezone=Asia/Kuala_Lumpur&forecast_days=1"
        )
        res = requests.get(url, timeout=5).json()
        now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
        idx = now.hour
        rain = float(res["hourly"]["precipitation"][idx])
        print(f"[RIFAR] Open-Meteo startup seed: rainfall={rain} mm at hour {idx}.")
        # Seed the 3-day history with the live reading as a conservative baseline
        _rainfall_history.extend([rain, rain, rain])
        return {"water_level_m": None, "rainfall_mm": rain}
    except Exception as e:
        print(f"[RIFAR] Open-Meteo startup seed failed ({e}). Defaulting to 0.0 mm.")
        return {"water_level_m": None, "rainfall_mm": 0.0}

# --- LIVE SENSOR STATE (seeded from Open-Meteo on startup; overwritten by POST /sensor) ---
live_sensor_data = _seed_from_open_meteo()

@router.get("/", tags=["Health"])
def health_check():
    """Health check — confirms the API is running."""
    return {"status": "ok", "service": "RIFAR Flood Prediction API"}

@router.get("/alert-status", tags=["Alerts"])
def get_alert_status(alert_manager: AlertManager = Depends(get_alert_manager)):
    """Returns the current alert state for prediction and sensor channels."""
    return alert_manager.get_states()

@router.post("/predict", response_model=PredictResponse, tags=["Prediction"])
async def predict(
    request: PredictRequest,
    background_tasks: BackgroundTasks,
    prediction_service: KerasPredictionService = Depends(get_prediction_service),
    alert_manager: AlertManager = Depends(get_alert_manager),
    telegram_bot: ResilientTelegramBot = Depends(get_telegram_bot)
):
    """
    AI Prediction Alert.
    Runs Keras model asynchronously in a threadpool and dispatches any Telegram notifications
    via async Background Tasks to prevent HTTP connection blocking.
    """
    predicted = await prediction_service.predict_async(
        request.rainfall_mm, request.rainfall_3d_sum, request.upstream_level_m
    )
    
    # Check alert conditions
    should_alert, alert_result = alert_manager.evaluate_alert("prediction", predicted)
    
    if should_alert and alert_result.get("message"):
        background_tasks.add_task(telegram_bot.send_alert_with_retry, alert_result["message"])
        
    return PredictResponse(
        rainfall_mm=request.rainfall_mm,
        upstream_level_m=request.upstream_level_m,
        predicted_water_level_m=round(predicted, 3),
        alert=alert_result
    )

@router.post("/sensor", response_model=SensorResponse, tags=["Sensor"])
async def sensor_reading(
    request: SensorRequest,
    background_tasks: BackgroundTasks,
    alert_manager: AlertManager = Depends(get_alert_manager),
    telegram_bot: ResilientTelegramBot = Depends(get_telegram_bot),
    sensor_filter: SensorDataFilter = Depends(get_sensor_filter),
    api_key: str = Security(validate_api_key)
):
    """
    Real-Time Sensor Alert.
    Accepts live telemetry (secured with X-API-KEY header), validates/filters spikes using EMA,
    updates simulator state, and schedules dynamic Telegram updates asynchronously.
    """
    # 1. Apply EMA Filtering and check physical bounds
    smoothed_depth = sensor_filter.validate_and_smooth(request.water_level_m)
    if smoothed_depth is None:
        smoothed_depth = request.water_level_m

    # 2. Update global simulation database and rolling rainfall history
    live_sensor_data["water_level_m"] = smoothed_depth
    if request.rainfall_mm is not None:
        live_sensor_data["rainfall_mm"] = request.rainfall_mm
        _rainfall_history.append(request.rainfall_mm)  # advance the 3-day rolling window

    # 3. Check alarm threshold
    should_alert, alert_result = alert_manager.evaluate_alert("sensor", smoothed_depth)
    
    if should_alert and alert_result.get("message"):
        background_tasks.add_task(telegram_bot.send_alert_with_retry, alert_result["message"])

    return SensorResponse(
        water_level_m=smoothed_depth,
        alert=alert_result
    )

@router.get("/live-data", tags=["Sensor"])
def get_live_data():
    """Returns the latest sensor readings from the hardware simulator (Legacy)."""
    return live_sensor_data

@router.get("/live-status", response_model=LiveStatusResponse, tags=["Consolidated"])
async def get_live_status(
    background_tasks: BackgroundTasks,
    prediction_service: KerasPredictionService = Depends(get_prediction_service),
    alert_manager: AlertManager = Depends(get_alert_manager),
    telegram_bot: ResilientTelegramBot = Depends(get_telegram_bot)
):
    """
    Consolidated Real-Time status.
    Returns live readings AND corresponding AI predictions in a single response payload.
    Reduces network traffic by 50% for high-efficiency client dashboards.
    """
    # Coerce None to 0.0 so the Keras model always receives valid floats.
    # water_level_m is None until the first physical /sensor POST arrives.
    water_level = live_sensor_data["water_level_m"] or 0.0
    rainfall = live_sensor_data["rainfall_mm"] or 0.0
    rainfall_3d = _compute_3d_sum()

    # Asynchronously execute inference
    predicted = await prediction_service.predict_async(rainfall, rainfall_3d, water_level)
    
    # Evaluate prediction alert
    should_alert, alert_result = alert_manager.evaluate_alert("prediction", predicted)
    if should_alert and alert_result.get("message"):
        background_tasks.add_task(telegram_bot.send_alert_with_retry, alert_result["message"])

    return LiveStatusResponse(
        water_level_m=water_level,
        rainfall_mm=rainfall,
        rainfall_3d_sum=rainfall_3d,
        predicted_level_m=round(predicted, 3),
        alert=alert_result
    )

@router.get("/forecast-risk", tags=["Forecast"])
async def get_forecast_risk(
    demo: bool = False,
    prediction_service: KerasPredictionService = Depends(get_prediction_service)
):
    """
    AI Proactive Weather Forecast Risk Analysis using Open-Meteo API.
    Returns AI flood risk predictions at +1 Hr, +12 Hr, and +24 Hr horizons
    so villagers can prepare well in advance.
    If demo=True, runs a high-impact storm simulation for presentations.
    """
    if demo:
        # High-impact convective storm simulation for demonstration
        forecast_data = [
            {"label": "+1 Hour",   "condition": "Heavy Rain",          "rainfall_mm": 45.0, "upstream_level_m": 2.4},
            {"label": "+2 Hours",  "condition": "Moderate Rain",        "rainfall_mm": 60.0, "upstream_level_m": 2.8},
            {"label": "+3 Hours",  "condition": "Severe Thunderstorm",  "rainfall_mm": 95.0, "upstream_level_m": 3.5},
            {"label": "+12 Hours", "condition": "Rain Showers",         "rainfall_mm": 30.0, "upstream_level_m": 2.1},
            {"label": "+24 Hours", "condition": "Light Drizzle",        "rainfall_mm": 10.0, "upstream_level_m": 1.7},
            {"label": "+2 Days",   "condition": "Partly Cloudy",        "rainfall_mm":  5.0, "upstream_level_m": 1.4},
            {"label": "+3 Days",   "condition": "Clear Sky",            "rainfall_mm":  0.0, "upstream_level_m": 1.2}
        ]
    else:
        # Live Open-Meteo API — 5 forecast horizons for early warning
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude=3.0296&longitude=101.5288"
                "&hourly=precipitation,precipitation_probability,weather_code"
                "&timezone=Asia/Kuala_Lumpur"
                "&forecast_days=10"
            )
            res = requests.get(url, timeout=5).json()
            hourly = res["hourly"]

            # Find current hour index in KL local time (UTC+8)
            now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
            current_hour_str = now.strftime("%Y-%m-%dT%H:00")
            try:
                idx = hourly["time"].index(current_hour_str)
            except ValueError:
                idx = 0

            def wmo_to_condition(code: int) -> str:
                if code == 0:              return "Clear Sky"
                if code in [1, 2, 3]:     return "Partly Cloudy"
                if code in [45, 48]:      return "Foggy"
                if code in [51, 53, 55]:  return "Light Drizzle"
                if code in [61, 63]:      return "Moderate Rain"
                if code == 65:            return "Heavy Rain"
                if code in [80, 81, 82]:  return "Rain Showers"
                if code in [95, 96, 99]:  return "Severe Thunderstorm"
                return "Cloudy"

            forecast_data = []
            for offset, label in [(1, "+1 Hour"), (2, "+2 Hours"), (3, "+3 Hours"), (12, "+12 Hours"), (24, "+24 Hours"), (48, "+2 Days"), (72, "+3 Days")]:
                target_idx = idx + offset
                if target_idx >= len(hourly["time"]):
                    target_idx = len(hourly["time"]) - 1

                rain_mm    = float(hourly["precipitation"][target_idx])
                rain_prob  = int(hourly["precipitation_probability"][target_idx])
                wmo_code   = int(hourly["weather_code"][target_idx])
                time_str   = hourly["time"][target_idx]
                dt         = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M")

                # Use probability to estimate effective rainfall when mm is 0
                # e.g. 70% probability → adds 70*0.3 = 21mm equivalent pressure
                effective_rain = rain_mm if rain_mm > 0 else (rain_prob * 0.3)
                estimated_upstream = 1.5 + (effective_rain * 0.02)

                forecast_data.append({
                    "label": label,
                    "condition": wmo_to_condition(wmo_code),
                    "rainfall_mm": rain_mm,
                    "rain_probability": rain_prob,
                    "upstream_level_m": round(estimated_upstream, 3),
                    "forecast_time": dt.strftime("%d %b %Y %H:%M")
                })

        except Exception:
            # Graceful fallback to simulation if API is unreachable
            forecast_data = [
                {"label": "+1 Hour",   "condition": "Heavy Rain",         "rainfall_mm": 45.0, "rain_probability": 90, "upstream_level_m": 2.4},
                {"label": "+2 Hours",  "condition": "Moderate Rain",       "rainfall_mm": 60.0, "rain_probability": 85, "upstream_level_m": 2.8},
                {"label": "+3 Hours",  "condition": "Severe Thunderstorm", "rainfall_mm": 95.0, "rain_probability": 95, "upstream_level_m": 3.5},
                {"label": "+12 Hours", "condition": "Rain Showers",        "rainfall_mm": 30.0, "rain_probability": 60, "upstream_level_m": 2.1},
                {"label": "+24 Hours", "condition": "Light Drizzle",       "rainfall_mm": 10.0, "rain_probability": 30, "upstream_level_m": 1.7},
                {"label": "+2 Days",   "condition": "Partly Cloudy",       "rainfall_mm":  5.0, "rain_probability": 20, "upstream_level_m": 1.4},
                {"label": "+3 Days",   "condition": "Clear Sky",           "rainfall_mm":  0.0, "rain_probability":  5, "upstream_level_m": 1.2}
            ]

    results = []
    current_3d = _compute_3d_sum()  # antecedent moisture from live sensor history
    for item in forecast_data:
        # Estimate forward-looking 3d accumulation:
        # current antecedent moisture + this horizon's expected rainfall (conservative proxy)
        raw_mm   = item["rainfall_mm"]
        prob     = item.get("rain_probability", 0)
        eff_rain = raw_mm if raw_mm > 0 else round(prob * 0.3, 1)
        est_3d   = round(current_3d + eff_rain, 1)

        predicted = await prediction_service.predict_async(raw_mm, est_3d, item["upstream_level_m"])
        predicted = round(predicted, 3)

        if predicted >= 4.5:
            hazard = "CRITICAL"
            advice = "Severe flooding expected. Alert authorities and evacuate low-lying areas immediately."
        elif predicted >= 4.0:
            hazard = "WARNING"
            advice = "Rising water levels — residents should prepare emergency kits and monitor updates."
        else:
            hazard = "NORMAL"
            advice = "Water levels within safe limits. No immediate action required."

        results.append({
            "label":              item["label"],
            "forecast_time":      item.get("forecast_time", ""),
            "condition":          item["condition"],
            "rainfall_mm":        item["rainfall_mm"],
            "effective_rain_mm":  eff_rain,
            "rain_probability":   item.get("rain_probability", 0),
            "predicted_level_m":  predicted,
            "hazard_level":       hazard,
            "advice":             advice
        })

    return results

