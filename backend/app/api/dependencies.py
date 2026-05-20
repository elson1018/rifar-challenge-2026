from app.services.prediction_service import KerasPredictionService
from app.services.alert_service import AlertManager
from app.services.telegram_bot import ResilientTelegramBot
from app.services.data_filter import SensorDataFilter
from app.core.config import settings

# Shared global singletons
_prediction_service = None
_alert_manager = AlertManager()
_telegram_bot = ResilientTelegramBot()
_sensor_filter = SensorDataFilter(mount_height=4.0, alpha=0.25)

def get_prediction_service() -> KerasPredictionService:
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = KerasPredictionService()
    return _prediction_service

def get_alert_manager() -> AlertManager:
    return _alert_manager

def get_telegram_bot() -> ResilientTelegramBot:
    return _telegram_bot

def get_sensor_filter() -> SensorDataFilter:
    return _sensor_filter
