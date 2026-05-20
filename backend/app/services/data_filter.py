import math
from typing import Optional

class SensorDataFilter:
    def __init__(self, mount_height: float = 4.0, alpha: float = 0.25):
        """
        Initializes the Exponential Moving Average (EMA) and Range filter.
        
        Args:
            mount_height: Physical height of the sensor in meters (default 4.0m)
            alpha: Smoothing factor in [0.0, 1.0]. Smaller values = smoother but slower reaction.
        """
        self.mount_height = mount_height
        self.alpha = alpha
        self.smoothed_depth: Optional[float] = None

    def validate_and_smooth(self, raw_distance: Optional[float]) -> Optional[float]:
        """
        Validate and apply EMA filtering to raw ultrasonic sensor readings (distance).
        
        Args:
            raw_distance: Measured distance from sensor to water surface in meters.
        Returns:
            Smoothed water depth in meters, or the last known good reading if invalid.
        """
        # 1. Null / NaN checks
        if raw_distance is None or math.isnan(raw_distance):
            return self.smoothed_depth

        # 2. Physical range limits validation
        # Ultrasonic sensors have a physical blind zone (minimum ~0.05m / 5cm)
        # and physical mount maximum is 4.0m (anything past that is a sensor error)
        if raw_distance < 0.05 or raw_distance > self.mount_height:
            return self.smoothed_depth

        # 3. Calculate actual water depth: w = mount_height - distance
        calculated_depth = self.mount_height - raw_distance

        # 4. Apply Exponential Moving Average: y_t = alpha * x_t + (1 - alpha) * y_{t-1}
        if self.smoothed_depth is None:
            self.smoothed_depth = calculated_depth
        else:
            self.smoothed_depth = (self.alpha * calculated_depth) + ((1.0 - self.alpha) * self.smoothed_depth)
        
        return round(self.smoothed_depth, 3)
