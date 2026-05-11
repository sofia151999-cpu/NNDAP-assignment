import os
from datetime import date, datetime

import httpx
import pandas as pd


API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def serialize_date(value) -> str | None:
    if pd.isna(value):
        return None

    parsed_date = pd.to_datetime(value, errors="coerce")

    if pd.isna(parsed_date):
        return None

    return parsed_date.date().isoformat()


def serialize_timestamp(value) -> str | None:
    if pd.isna(value):
        return None

    parsed_timestamp = pd.to_datetime(value, unit="s", errors="coerce")

    if pd.isna(parsed_timestamp):
        return None

    return parsed_timestamp.to_pydatetime().isoformat()


def serialize_float(value) -> float | None:
    if pd.isna(value):
        return None

    return float(value)


def post_cows(client: httpx.Client) -> tuple[int, int]:
    cows_df = pd.read_parquet("data/cows.parquet")

    accepted = 0
    rejected = 0

    for _, row in cows_df.iterrows():
        cow_id = None if pd.isna(row["id"]) else str(row["id"])

        if cow_id is None:
            rejected += 1
            continue

        payload = {
            "name": None if pd.isna(row["name"]) else str(row["name"]),
            "birthdate": serialize_date(row["birthdate"]),
        }

        response = client.post(f"/cows/{cow_id}", json=payload)

        if response.status_code in (200, 201):
            accepted += 1
        else:
            rejected += 1
            print(f"Cow rejected: {cow_id} -> {response.status_code} {response.text}")

    return accepted, rejected


def post_sensors(client: httpx.Client) -> tuple[int, int]:
    sensors_df = pd.read_parquet("data/sensors.parquet")

    accepted = 0
    rejected = 0

    for _, row in sensors_df.iterrows():
        sensor_id = None if pd.isna(row["id"]) else str(row["id"])

        if sensor_id is None or pd.isna(row["unit"]):
            rejected += 1
            continue

        payload = {
            "unit": str(row["unit"]),
        }

        response = client.post(f"/sensors/{sensor_id}", json=payload)

        if response.status_code in (200, 201):
            accepted += 1
        else:
            rejected += 1
            print(
                f"Sensor rejected: {sensor_id} -> "
                f"{response.status_code} {response.text}"
            )

    return accepted, rejected


def post_measurements(client: httpx.Client) -> tuple[int, int]:
    measurements_df = pd.read_parquet("data/measurements.parquet")

    accepted = 0
    rejected = 0

    for index, row in measurements_df.iterrows():
        payload = {
            "cow_id": None if pd.isna(row["cow_id"]) else str(row["cow_id"]),
            "sensor_id": None if pd.isna(row["sensor_id"]) else str(row["sensor_id"]),
            "timestamp": serialize_timestamp(row["timestamp"]),
            "value": serialize_float(row["value"]),
        }

        response = client.post("/measurements", json=payload)

        if response.status_code in (200, 201):
            accepted += 1
        else:
            rejected += 1

            if rejected <= 10:
                print(
                    f"Measurement rejected at row {index}: "
                    f"{response.status_code} {response.text}"
                )

        if (index + 1) % 10_000 == 0:
            print(f"Measurements sent so far: {index + 1}")

    return accepted, rejected


def main() -> None:
    print("Starting sensor simulation...")
    print(f"API base URL: {API_BASE_URL}")
    print("")

    with httpx.Client(base_url=API_BASE_URL, timeout=30.0) as client:
        cows_accepted, cows_rejected = post_cows(client)
        print(f"Cows sent={cows_accepted}, rejected={cows_rejected}")

        sensors_accepted, sensors_rejected = post_sensors(client)
        print(f"Sensors sent={sensors_accepted}, rejected={sensors_rejected}")

        measurements_accepted, measurements_rejected = post_measurements(client)
        print(
            f"Measurements sent={measurements_accepted}, "
            f"rejected={measurements_rejected}"
        )

    print("")
    print("Sensor simulation finished.")


if __name__ == "__main__":
    main()