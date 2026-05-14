# RIFAR Challenge 2026 — Taman Sri Muda Flood Prediction AI

A flood prediction system for Taman Sri Muda, Selangor. Uses NASA satellite rainfall data, a TensorFlow neural network, FastAPI backend, and a React dashboard.

## Stack

| Layer | Tech |
|-------|------|
| Data | NASA POWER Climate API |
| Model | TensorFlow + Keras |
| Backend | FastAPI + Uvicorn |
| Frontend | React + Vite + Chart.js |

## Setup

### Model Training
```bash
cd model-training
source rifar-env/bin/activate
python rifar-env/fetch_nasa_data.py   # fetch NASA data
python train_model.py                 # train and export model
```

### Backend
```bash
cd backend
source ../model-training/rifar-env/bin/activate
uvicorn main:app --reload
```
API runs at `http://localhost:8000`

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Dashboard runs at `http://localhost:5173`

## Location
Taman Sri Muda, Selangor (3.0296, 101.5288) — severely affected by the December 2021 floods.
