import os
import requests
import pandas as pd
import numpy as np

# Set seed for reproducible synthetic water level generation
np.random.seed(42)

print("1. Contacting NASA POWER Climate API...")

# Exact coordinates for Taman Sri Muda, Selangor
lat = 3.0296
lon = 101.5288

start_date = "20210101"
end_date = "20260430"

# The API endpoint for daily precipitation (PRECTOTCORR)
url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR&community=RE&longitude={lon}&latitude={lat}&start={start_date}&end={end_date}&format=JSON"

try:
    # Fetch the data
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    # Extract the rainfall data into Pandas DF
    rainfall_data = data['properties']['parameter']['PRECTOTCORR']
    df = pd.DataFrame.from_dict(rainfall_data, orient='index', columns=['rainfall_mm'])
    df.index = pd.to_datetime(df.index, format='%Y%m%d')
    df.index.name = 'date'
    
    print(f"2. Successfully downloaded {len(df)} days of historical satellite data ({df.index.min().date()} to {df.index.max().date()}).")
    
    # NASA POWER uses -999 to indicate missing data — replace with 0
    df.loc[df['rainfall_mm'] < 0, 'rainfall_mm'] = 0.0

    # 3-day accumulated rainfall (antecedent moisture feature)
    # Hydrologically critical: soil saturation state determines flood response severity.
    # min_periods=1 ensures day 1 and 2 are not NaN.
    df['rainfall_3d_sum'] = df['rainfall_mm'].rolling(window=3, min_periods=1).sum()
    
    print("3. Generating physical river metrics based on real rainfall...")
    # Simulate Upstream Level
    # Base level (1.5m) + Rain impact + small random variation
    df['upstream_level_m'] = 1.5 + (df['rainfall_mm'] * 0.02) + np.random.normal(0, 0.05, len(df))
    
    # Simulate Local Flood Level
    # Base level (2.0m) + Upstream pressure + Heavy rain impact + variation
    # Safely sits between 2.0m - 3.0m normally, and breaches 4.5m during 85mm+ rainfall.
    df['local_water_level_m'] = 2.0 + (df['upstream_level_m'] * 0.4) + (df['rainfall_mm'] * 0.015) + np.random.normal(0, 0.08, len(df))
    
    # Ensure water levels don't drop below realistic physical minimums
    df['upstream_level_m'] = df['upstream_level_m'].clip(lower=0.5)
    df['local_water_level_m'] = df['local_water_level_m'].clip(lower=0.5)
    
    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'taman_sri_muda_history.csv')
    df.to_csv(output_path, index=True)  # index=True preserves the date column
    
    print("\nSUCCESS: 'taman_sri_muda_history.csv' has been generated and is ready for training.")

except Exception as e:
    print(f"Error fetching data: {e}")