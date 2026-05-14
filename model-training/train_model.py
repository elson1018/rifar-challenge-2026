import os
import pandas as pd
import numpy as np
import tensorflow as tf
from sklearn.model_selection import train_test_split

# --- PATHS (always relative to this script, not cwd) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'taman_sri_muda_history.csv')
MODEL_PATH = os.path.join(BASE_DIR, 'flood_model.keras')

print(f"TensorFlow Version: {tf.__version__}")

# Check if TensorFlow sees the Mac GPU
physical_devices = tf.config.list_physical_devices('GPU')
if physical_devices:
    print("Success! TensorFlow is using your Mac's GPU (Metal).")
else:
    print("GPU not found. Falling back to CPU.")

# --- 1. LOAD THE DATA ---
print(f"\n1. Loading data from {CSV_PATH}...")
dataset = pd.read_csv(CSV_PATH)

# Note: rainfall_mm is kept in raw mm units — the synthetic targets were computed
# with raw values so normalising here would cause a training/inference mismatch.

# Separate inputs and targets
inputs = dataset[['rainfall_mm', 'upstream_level_m']].values
targets = dataset[['local_water_level_m']].values

# --- 2. TRAIN / TEST SPLIT ---
# Hold out 20% of data to evaluate if the model generalises (unseen data)
X_train, X_test, y_train, y_test = train_test_split(
    inputs, targets, test_size=0.2, random_state=42
)
print(f"   Training samples: {len(X_train)} | Test samples: {len(X_test)}")

# --- 3. BUILD THE AI MODEL ---
# Added hidden layers so the model can learn non-linear flood patterns
model = tf.keras.Sequential([
    tf.keras.layers.Dense(64, activation='relu', input_dim=2),
    tf.keras.layers.Dense(32, activation='relu'),
    tf.keras.layers.Dense(1)
])

# --- 4. COMPILE ---
model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),  # 0.001 is stable default
    loss='mse',
    metrics=['mae']
)

# --- 5. TRAINING LOOP ---
print("\n2. Starting training...")
history = model.fit(
    X_train, y_train,
    validation_data=(X_test, y_test),
    epochs=500,
    verbose=0
)

final_train_loss = history.history['loss'][-1]
final_val_loss = history.history['val_loss'][-1]
final_mae = history.history['val_mae'][-1]

print(f"   Training Loss (MSE):    {final_train_loss:.4f}")
print(f"   Validation Loss (MSE):  {final_val_loss:.4f}")
print(f"   Validation Error (MAE): {final_mae:.4f} meters")

# --- 6. MAKE A REAL PREDICTION ---
# Input: 95mm rain (raw mm), upstream level = 2.8m
print("\n3. Testing hypothetical storm (95mm rain, 2.8m upstream)...")
new_weather = tf.constant([[95.0, 2.8]])
future_water_level = model.predict(new_weather, verbose=0)
print(f">>> Predicted Water Level at Taman Sri Muda: {future_water_level[0][0]:.2f} meters")

# --- 7. SAVE MODEL ---
print(f"\n4. Saving model to {MODEL_PATH}...")
model.save(MODEL_PATH)
print("SUCCESS: Model saved as 'flood_model.keras'.")