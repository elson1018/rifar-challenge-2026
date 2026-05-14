import os
import numpy as np
import tensorflow as tf
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from alert_manager import AlertManager

# --- PATHS ---
BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "flood_model.keras")

# --- LOAD MODEL (once at startup) ---
print(f"Loading model from {MODEL_PATH}...")
model = tf.keras.models.load_model(MODEL_PATH)
print("Model loaded successfully.")

# --- ALERT MANAGER (singleton — maintains state across requests) ---
alert_manager = AlertManager()

# --- FASTAPI APP ---
app = FastAPI(
    title="RIFAR Flood Prediction API",
    description="Predicts water levels at Taman Sri Muda and sends Telegram flood alerts.",
    version="1.0.0"
)

# Allow the React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- REQUEST / RESPONSE MODELS ---

class PredictRequest(BaseModel):
    rainfall_mm: float = Field(..., ge=0, description="Rainfall in millimetres (≥ 0)")
    upstream_level_m: float = Field(..., ge=0, description="Upstream river level in metres (≥ 0)")

class SensorRequest(BaseModel):
    water_level_m: float = Field(..., ge=0, description="Live sensor water level reading in metres")

class PredictResponse(BaseModel):
    rainfall_mm: float
    upstream_level_m: float
    predicted_water_level_m: float
    alert: dict

class SensorResponse(BaseModel):
    water_level_m: float
    alert: dict


# --- ENDPOINTS ---

@app.get("/", tags=["Health"])
def health_check():
    """Health check — confirms the API is running."""
    return {"status": "ok", "service": "RIFAR Flood Prediction API"}


@app.get("/alert-status", tags=["Alerts"])
def get_alert_status():
    """Returns the current alert state for prediction and sensor channels."""
    return alert_manager.get_states()


@app.post("/predict", response_model=PredictResponse, tags=["Prediction"])
def predict(request: PredictRequest):
    """
    AI Prediction Alert.

    Accepts rainfall and upstream level, runs the model,
    and triggers a Telegram alert if the predicted level crosses a threshold.
    """
    # Pass raw rainfall_mm — model was trained on raw values (no normalisation)
    input_data = np.array([[request.rainfall_mm, request.upstream_level_m]], dtype=np.float32)
    predicted  = float(model.predict(input_data, verbose=0)[0][0])

    # Check thresholds and send Telegram alert if needed
    alert_result = alert_manager.check_and_send("prediction", predicted)

    return PredictResponse(
        rainfall_mm=request.rainfall_mm,
        upstream_level_m=request.upstream_level_m,
        predicted_water_level_m=round(predicted, 3),
        alert=alert_result
    )


@app.post("/sensor", response_model=SensorResponse, tags=["Sensor"])
def sensor_reading(request: SensorRequest):
    """
    Real-Time Sensor Alert.

    Accepts a live hardware sensor reading and triggers a Telegram alert
    if the water level crosses a threshold.
    """
    alert_result = alert_manager.check_and_send("sensor", request.water_level_m)

    return SensorResponse(
        water_level_m=request.water_level_m,
        alert=alert_result
    )
