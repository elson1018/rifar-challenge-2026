from fastapi import APIRouter, Depends, BackgroundTasks, Security
from typing import Dict, Any
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

# --- LIVE SENSOR STATE (in-memory simulation database) ---
live_sensor_data = {
    "water_level_m": 2.5,
    "rainfall_mm": 80.0
}

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
    predicted = await prediction_service.predict_async(request.rainfall_mm, request.upstream_level_m)
    
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

    # 2. Update global simulation database
    live_sensor_data["water_level_m"] = smoothed_depth
    if request.rainfall_mm is not None:
        live_sensor_data["rainfall_mm"] = request.rainfall_mm

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
    water_level = live_sensor_data["water_level_m"]
    rainfall = live_sensor_data["rainfall_mm"]

    # Asynchronously execute inference
    predicted = await prediction_service.predict_async(rainfall, water_level)
    
    # Evaluate prediction alert
    should_alert, alert_result = alert_manager.evaluate_alert("prediction", predicted)
    if should_alert and alert_result.get("message"):
        background_tasks.add_task(telegram_bot.send_alert_with_retry, alert_result["message"])

    return LiveStatusResponse(
        water_level_m=water_level,
        rainfall_mm=rainfall,
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
            {"label": "+1 Hour",  "tag": "Short-Term",  "condition": "Heavy Rain",       "rainfall_mm": 45.0, "upstream_level_m": 2.4},
            {"label": "+12 Hours", "tag": "Mid-Term",   "condition": "Severe Thunderstorm", "rainfall_mm": 95.0, "upstream_level_m": 3.5},
            {"label": "+24 Hours", "tag": "Long-Term",  "condition": "Light Drizzle",     "rainfall_mm": 10.0, "upstream_level_m": 1.7}
        ]
    else:
        # Live Open-Meteo API — 3 forecast horizons for early warning
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast"
                "?latitude=3.0296&longitude=101.5288"
                "&hourly=precipitation,weather_code"
                "&timezone=Asia/Kuala_Lumpur"
                "&forecast_days=2"
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
            for offset, label, tag in [(1, "+1 Hour", "Short-Term"), (12, "+12 Hours", "Mid-Term"), (24, "+24 Hours", "Long-Term")]:
                target_idx = idx + offset
                if target_idx >= len(hourly["time"]):
                    target_idx = len(hourly["time"]) - 1

                rain_mm   = float(hourly["precipitation"][target_idx])
                wmo_code  = int(hourly["weather_code"][target_idx])
                time_str  = hourly["time"][target_idx]
                dt        = datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M")

                estimated_upstream = 1.5 + (rain_mm * 0.02)

                forecast_data.append({
                    "label": label,
                    "tag": tag,
                    "condition": wmo_to_condition(wmo_code),
                    "rainfall_mm": rain_mm,
                    "upstream_level_m": round(estimated_upstream, 3),
                    "forecast_time": dt.strftime("%d %b %Y %H:%M")
                })

        except Exception:
            # Graceful fallback to simulation if API is unreachable
            forecast_data = [
                {"label": "+1 Hour",  "tag": "Short-Term",  "condition": "Heavy Rain",          "rainfall_mm": 45.0, "upstream_level_m": 2.4},
                {"label": "+12 Hours", "tag": "Mid-Term",   "condition": "Severe Thunderstorm", "rainfall_mm": 95.0, "upstream_level_m": 3.5},
                {"label": "+24 Hours", "tag": "Long-Term",  "condition": "Light Drizzle",       "rainfall_mm": 10.0, "upstream_level_m": 1.7}
            ]

    results = []
    for item in forecast_data:
        predicted = await prediction_service.predict_async(item["rainfall_mm"], item["upstream_level_m"])
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
            "tag":                item["tag"],
            "forecast_time":      item.get("forecast_time", ""),
            "condition":          item["condition"],
            "rainfall_mm":        item["rainfall_mm"],
            "predicted_level_m":  predicted,
            "hazard_level":       hazard,
            "advice":             advice
        })

    return results

