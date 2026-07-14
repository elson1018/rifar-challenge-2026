import numpy as np
import tensorflow as tf
import asyncio
import os

class KerasPredictionService:
    def __init__(self, model_filename: str = "flood_model.keras"):
        """
        Loads the TensorFlow Keras model from the base backend directory.
        """
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.model_path = os.path.join(base_dir, model_filename)
        
        print(f"Loading Keras model from {self.model_path}...")
        self.model = tf.keras.models.load_model(self.model_path)
        print("Keras model loaded successfully.")

    def _sync_predict(self, rainfall: float, rainfall_3d_sum: float, upstream: float) -> float:
        # Use model.predict_on_batch for optimized single predictions.
        # Input order MUST match training: [rainfall_mm, rainfall_3d_sum, upstream_level_m]
        input_data = np.array([[rainfall, rainfall_3d_sum, upstream]], dtype=np.float32)
        predicted_batch = self.model.predict_on_batch(input_data)
        return float(predicted_batch[0][0])

    async def predict_async(self, rainfall: float, rainfall_3d_sum: float, upstream: float) -> float:
        """
        Runs neural network inference in a non-blocking asynchronous worker thread.
        """
        return await asyncio.to_thread(self._sync_predict, rainfall, rainfall_3d_sum, upstream)
