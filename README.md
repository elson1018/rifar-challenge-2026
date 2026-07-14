# RIFAR / SIFMS — Taman Sri Muda Flood Prediction AI

Smart Integrated Flood Monitoring System (SIFMS) for Taman Sri Muda, Selangor.  
Ingests NASA POWER satellite rainfall data, applies a 3-feature TensorFlow/Keras neural network, and exposes predictions via a FastAPI backend to a live React dashboard with Leaflet flood-risk overlays.

## Architecture

| Layer | Technology | Role |
|---|---|---|
| Data | NASA POWER Climate API + Open-Meteo | Historical training data & live 10-day forecasts |
| Model | TensorFlow / Keras (3-input Dense NN) | Predicts local water level from `rainfall_mm`, `rainfall_3d_sum`, `upstream_level_m` |
| Backend | FastAPI + Uvicorn | Routes predictions, manages sensor telemetry, fires Telegram alerts |
| Frontend | React + Vite + Chart.js + Leaflet | Live trend chart, 7-horizon forecast cards, OpenStreetMap flood-risk overlay |
| Alerts | Telegram Bot (async, multilingual) | EN / BM / 中文 / தமிழ் push notifications with anti-spam state machine |

## Model Features

The Keras model uses **3 input features** (training order must be preserved at inference):

| # | Feature | Description |
|---|---|---|
| 1 | `rainfall_mm` | Current daily rainfall (mm) from NASA POWER / sensor |
| 2 | `rainfall_3d_sum` | 3-day accumulated rainfall — antecedent soil moisture proxy |
| 3 | `upstream_level_m` | Upstream river level (m) from sensor or hydrological estimate |

## Setup

### 1 — Model Training

```bash
cd model-training

# Activate the virtual environment
source rifar-env/bin/activate

# Step 1: Fetch real NASA POWER satellite rainfall data (2021–2026)
#         and regenerate taman_sri_muda_history.csv with the 3d rolling sum
python fetch_nasa_data.py

# Step 2: Train the 3-input Keras model and export flood_model.keras
python train_model.py
```

### 2 — Backend

```bash
cd backend

# Activate the same venv
source ../model-training/rifar-env/bin/activate

# Start the API server (hot-reload for development)
uvicorn main:app --reload
```

API runs at `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

### 3 — Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard runs at `http://localhost:5173`

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/live-status` | Live sensor + AI prediction (consolidated, polled every 3 s by dashboard) |
| `GET` | `/forecast-risk` | 7-horizon proactive forecast (+1h → +3 days) via Open-Meteo |
| `GET` | `/forecast-risk?demo=true` | High-impact storm simulation for presentations |
| `POST` | `/predict` | Manual AI prediction (`rainfall_mm`, `rainfall_3d_sum`, `upstream_level_m`) |
| `POST` | `/sensor` | Receive live IoT sensor telemetry (requires `X-API-KEY` header) |
| `GET` | `/alert-status` | Current Telegram alert state machine status |

## Environment Variables

Copy `.env.example` to `.env` in `backend/` and fill in:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id
API_SECURITY_KEY=your_sensor_push_key
CORS_ALLOWED_ORIGINS=http://localhost:5173
```

For the frontend, create `frontend/.env.local`:

```env
VITE_API_URL=http://localhost:8000
```

## Location

**Taman Sri Muda, Shah Alam, Selangor** — coordinates `3.0296°N, 101.5288°E`  
Severely affected by major flood events in December 2021 and subsequent years.
