from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes import router as api_router
from app.api.dependencies import get_prediction_service

# --- FASTAPI APP ---
app = FastAPI(
    title="RIFAR Flood Prediction API",
    description="Production-hardened API that predicts water levels at Taman Sri Muda and dispatches secure, filtered Telegram alerts.",
    version="2.0.0"
)

# Allow React frontend to call this API with CORS origins loaded from environment
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Register routes router
app.include_router(api_router)

@app.on_event("startup")
def startup_event():
    # Warm up / load Keras model at startup so the first request doesn't suffer latency
    print("Pre-warming neural network model...")
    get_prediction_service()
    print("Neural network loaded and ready.")
