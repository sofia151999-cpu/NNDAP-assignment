import pandas as pd

from app.database import SessionLocal
from app.models import Cow, Sensor, Measurement

db = SessionLocal()

# Cows
cows_df = pd.read_parquet("data/cows.parquet")

for _, row in cows_df.iterrows():
    cow = Cow(
        id=row["id"],
        name=row["name"],
        birthdate=row["birthdate"])
    db.merge(cow)

db.commit()
print("Cows loaded")

# Sensors

sensors_df = pd.read_parquet("data/sensors.parquet")

for _, row in sensors_df.iterrows():
    sensor = Sensor(
        id=row["id"],
        unit=row["unit"])
    db.merge(sensor)

db.commit()
print("Sensors loaded")

# Measurements
measurements_df = pd.read_parquet("data/measurements.parquet")

# UNIX -> datetime
measurements_df["timestamp"] = pd.to_datetime(
    measurements_df["timestamp"],
    unit="s")

for _, row in measurements_df.iterrows():
    m = Measurement(
        sensor_id=row["sensor_id"],
        cow_id=row["cow_id"],
        timestamp=row["timestamp"],
        value=row["value"])
    db.add(m)

db.commit()
print("Measurements loaded")