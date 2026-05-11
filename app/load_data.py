import pandas as pd
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from app.database import SessionLocal
from app.models import Cow, Sensor, Measurement

def is_empty(value) -> bool:
    return pd.isna(value)


def load_cows(db) -> tuple[int, int]:
    cows_df = pd.read_parquet("data/cows.parquet")

    loaded = 0
    rejected = 0

    for _, row in cows_df.iterrows():
        if is_empty(row["id"]):
            rejected += 1
            continue

        birthdate = None
        if not is_empty(row["birthdate"]):
            birthdate = pd.to_datetime(row["birthdate"]).date()

        cow = Cow(
            id=str(row["id"]),
            name=None if is_empty(row["name"]) else str(row["name"]),
            birthdate=birthdate,
        )

        db.merge(cow)
        loaded += 1

    db.commit()
    return loaded, rejected


def load_sensors(db) -> tuple[int, int]:
    sensors_df = pd.read_parquet("data/sensors.parquet")

    loaded = 0
    rejected = 0

    for _, row in sensors_df.iterrows():
        if is_empty(row["id"]) or is_empty(row["unit"]):
            rejected += 1
            continue

        sensor = Sensor(
            id=str(row["id"]),
            unit=str(row["unit"]),
        )

        db.merge(sensor)
        loaded += 1

    db.commit()
    return loaded, rejected


def load_measurements(db) -> tuple[int, int]:
    measurements_df = pd.read_parquet("data/measurements.parquet")

    total_rows = len(measurements_df)

    measurements_df["timestamp"] = pd.to_datetime(
        measurements_df["timestamp"],
        unit="s",
        errors="coerce",
    )

    measurements_df["value"] = pd.to_numeric(
        measurements_df["value"],
        errors="coerce",
    )

    # Remove null values
    valid_df = measurements_df.dropna(
        subset=["sensor_id", "cow_id", "timestamp", "value"]
    ).copy()

    # Remove negative values
    valid_df = valid_df[valid_df["value"] >= 0].copy()

    # Convert IDs to string
    valid_df["sensor_id"] = valid_df["sensor_id"].astype(str)
    valid_df["cow_id"] = valid_df["cow_id"].astype(str)

    # Keep only measurements whose cow and sensor already exist
    existing_cow_ids = {
        cow_id for (cow_id,) in db.query(Cow.id).all()
    }

    existing_sensor_ids = {
        sensor_id for (sensor_id,) in db.query(Sensor.id).all()
    }

    valid_df = valid_df[
        valid_df["cow_id"].isin(existing_cow_ids)
        & valid_df["sensor_id"].isin(existing_sensor_ids)
    ].copy()

    # Avoid duplicates inside the file itself
    valid_df = valid_df.drop_duplicates(
        subset=["sensor_id", "cow_id", "timestamp", "value"]
    )

    records = valid_df[
        ["sensor_id", "cow_id", "timestamp", "value"]
    ].to_dict(orient="records")

    loaded = 0
    chunk_size = 20_000

    for start in range(0, len(records), chunk_size):
        chunk = records[start:start + chunk_size]

        statement = sqlite_insert(Measurement).prefix_with("OR IGNORE")

        db.execute(statement, chunk)
        db.commit()

        loaded += len(chunk)
        print(f"Measurements processed so far: {loaded}")

    rejected = total_rows - loaded

    return loaded, rejected


def main() -> None:
    db = SessionLocal()

    try:
        cows_loaded, cows_rejected = load_cows(db)
        print(f"Cows loaded={cows_loaded}, rejected={cows_rejected}")

        sensors_loaded, sensors_rejected = load_sensors(db)
        print(f"Sensors loaded={sensors_loaded}, rejected={sensors_rejected}")

        measurements_loaded, measurements_rejected = load_measurements(db)
        print(
            f"Measurements loaded={measurements_loaded}, "
            f"rejected={measurements_rejected}"
        )

    finally:
        db.close()


if __name__ == "__main__":
    main()