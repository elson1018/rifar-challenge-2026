from fastapi import APIRouter, Depends, BackgroundTasks, Security
from typing import Dict, Any

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

