# NNDAP Data Engineering Assignment

A simple backend for Ingrid's farm.

This project stores cows, sensors and sensor measurements in a persistent SQLite database and exposes a small FastAPI service to:

- create cows;
- receive milk production and weight measurements;
- query cow details with the latest sensor data record;
- generate daily farm reports.

The solution focuses on the data engineering requirements of the assignment: persistent storage, API-based ingestion, validation, reproducible loading from parquet datasets, and report generation.

## Contents

- [Requirements](#requirements)
- [Project structure](#project-structure)
- [Setup](#setup)
- [Running the API](#running-the-api)
- [Simulating sensor data](#simulating-sensor-data)
- [API endpoints](#api-endpoints)
- [Reports](#reports)
- [Testing](#testing)
- [Validation and assumptions](#validation-and-assumptions)
- [Production considerations](#production-considerations)
- [Data flow](#data-flow)

## Requirements

- Python 3.10+
- `fastapi`
- `uvicorn`
- `sqlalchemy`
- `pandas`
- `pyarrow`
- `pytest`
- `httpx`

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Project structure

```text
nndap-assignment/
  app/
    __init__.py
    database.py
    models.py
    main.py
    init_db.py
    simulate_sensors.py
    generate_report.py
    load_data.py
  tests/
    test_api.py
  data/
    cows.parquet
    sensors.parquet
    measurements.parquet
  README.md
  requirements.txt
  .gitignore
```

Run all commands from the project root folder.

## Setup

Create the database tables:

```bash
python -m app.init_db
```

Start the API server:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

The interactive API documentation is available at:

```text
http://127.0.0.1:8000/docs
```

## Running the API

Start the service with:

```bash
uvicorn app.main:app --reload
```

The root endpoint can be tested with:

```bash
curl http://127.0.0.1:8000/
```

Expected response:

```json
{
  "message": "NNDAP API is running"
}
```

## Simulating sensor data

The assignment requires the sensor datasets to be simulated by looping over the provided records and sending each record individually to the API.

This is implemented in:

```text
app/simulate_sensors.py
```

Run the simulation with the API already running:

```bash
python -m app.simulate_sensors
```

This script reads:

```text
data/cows.parquet
data/sensors.parquet
data/measurements.parquet
```

and sends the data through API requests:

```text
POST /cows/{cow_id}
POST /sensors/{sensor_id}
POST /measurements
```

Each measurement record from `measurements.parquet` is sent individually to the `/measurements` endpoint.

Progress is printed while the measurements are being sent.

Example output:

```text
Starting sensor simulation...
API base URL: http://127.0.0.1:8000

Cows sent=128, rejected=0
Sensors sent=200, rejected=0
Measurements sent so far: 10000
Measurements sent so far: 20000
...
Measurements sent=563627, rejected=0

Sensor simulation finished.
```

## Optional fast local loader

The file below is included only as a local development utility:

```text
app/load_data.py
```

It loads data directly into SQLite and can be useful for debugging or quickly rebuilding the database.

However, the assignment-compliant ingestion path is:

```bash
python -m app.simulate_sensors
```

because it sends every dataset record through the API.

## Database

The application uses a SQLite database file:

```text
farm.db
```

The data is persisted, so restarting the API does not delete existing cows, sensors or measurements.

## API endpoints

### 1. Create a cow manually

- Method: `POST`
- Path: `/cows`

Request body:

```json
{
  "name": "Lindsey",
  "birthdate": "2020-01-09"
}
```

The service generates:

- a GUID cow ID;
- an automatically numbered cow name.

Example naming behavior:

```text
Lindsey #1
Lindsey #2
Lindsey #3
```

Example response:

```json
{
  "id": "c821a6b7-8dd0-4b4e-9835-1c0c57264ba4",
  "name": "Lindsey #1",
  "birthdate": "2020-01-09",
  "latest_measurement": null
}
```

### 2. Create a cow from dataset simulation

- Method: `POST`
- Path: `/cows/{cow_id}`

This endpoint is used by the sensor simulation script.

It creates cows using the ID provided in `cows.parquet`.

Request body:

```json
{
  "name": "Lindsey #1",
  "birthdate": "2020-01-09"
}
```

### 3. Create a sensor from dataset simulation

- Method: `POST`
- Path: `/sensors/{sensor_id}`

This endpoint is used by the sensor simulation script.

Request body:

```json
{
  "unit": "kg"
}
```

or:

```json
{
  "unit": "L"
}
```

### 4. Receive sensor measurement data

- Method: `POST`
- Path: `/measurements`

This endpoint receives individual sensor records from the simulation script.

Request body:

```json
{
  "cow_id": "cow-id-from-dataset",
  "sensor_id": "sensor-id-from-dataset",
  "timestamp": "2020-07-10T08:30:00",
  "value": 552.4
}
```

The endpoint validates:

- the cow exists;
- the sensor exists;
- the timestamp is valid;
- the value is not negative;
- duplicated records are not inserted twice.

### 5. Add a milk production measurement manually

- Method: `POST`
- Path: `/cows/{cow_id}/measurements/milk`

Request body:

```json
{
  "value": 4.8
}
```

If the cow exists, the API selects an available milk sensor and stores the measurement.

Example response:

```json
{
  "id": 563628,
  "cow_id": "c821a6b7-8dd0-4b4e-9835-1c0c57264ba4",
  "cow_name": "Lindsey #1",
  "sensor_id": "milk-sensor-id",
  "sensor_unit": "L",
  "timestamp": "2026-05-10T15:30:00",
  "value": 4.8
}
```

### 6. Add a weight measurement manually

- Method: `POST`
- Path: `/cows/{cow_id}/measurements/weight`

Request body:

```json
{
  "value": 552.4
}
```

If the cow exists, the API selects an available weight sensor and stores the measurement.

Example response:

```json
{
  "id": 563629,
  "cow_id": "c821a6b7-8dd0-4b4e-9835-1c0c57264ba4",
  "cow_name": "Lindsey #1",
  "sensor_id": "weight-sensor-id",
  "sensor_unit": "kg",
  "timestamp": "2026-05-10T15:35:00",
  "value": 552.4
}
```

### 7. Get cow details

- Method: `GET`
- Path: `/cows/{cow_id}`

Example response:

```json
{
  "id": "c821a6b7-8dd0-4b4e-9835-1c0c57264ba4",
  "name": "Lindsey #1",
  "birthdate": "2020-01-09",
  "latest_measurement": {
    "id": 563629,
    "sensor_id": "weight-sensor-id",
    "timestamp": "2026-05-10T15:35:00",
    "value": 552.4
  }
}
```

This endpoint returns cow metadata plus the latest recorded sensor measurement.

## Reports

Generate a daily report for a specific date with:

```bash
python -m app.generate_report YYYY-MM-DD
```

Example:

```bash
python -m app.generate_report 2020-07-10
```

The report includes:

- milk production per cow for the selected day;
- current weight per cow;
- average weight per cow over the last 30 days.

Reports are saved in:

```text
reports/
```

Example file name:

```text
reports/daily_report_2020-07-10.txt
```

For this assignment, the report is invoked manually. In a real production system, this process would be scheduled to run daily.

## Testing

Run the test suite with:

```bash
pytest
```

The tests check that:

- the API is running;
- cows are created with automatically numbered names;
- milk measurements can be created by cow ID;
- weight measurements can be created by cow ID;
- cows can be retrieved by cow ID;
- the latest measurement is returned with the cow details;
- negative measurement values are rejected;
- requests for unknown cows return an error.

## Validation and assumptions

The implementation makes the following assumptions:

- Cow and sensor IDs from the provided datasets are valid identifiers.
- Manual cow creation generates a new GUID internally.
- Manual cow names are automatically numbered.
- New sensor measurements require an existing cow ID and sensor ID.
- Negative measurement values are rejected.
- Null values are rejected or ignored during ingestion.
- Measurements are linked to existing cows and sensors.
- Duplicate measurements are not inserted twice.
- For this simplified assignment, the API selects the first available sensor matching the requested manual measurement type.
- SQLite is used to keep the assignment lightweight and easy to run locally.

## Production considerations

For a production system or a larger-scale scenario, such as handling many farms across Europe, I would consider:

- PostgreSQL instead of SQLite;
- indexes and possible partitioning by timestamp;
- asynchronous ingestion of sensor events;
- retries for failed sensor events;
- structured logging;
- monitoring and alerting;
- automated tests in the deployment pipeline;
- scheduled daily reporting with cron, Airflow, Azure Data Factory or another workflow scheduler.

The current implementation sends each measurement individually because this was explicitly requested in the assignment. In production, I would evaluate batching or streaming depending on throughput, latency and reliability requirements.

## Bonus: illness detection

The bonus question was not implemented as a final feature.

A possible future approach would be to flag cows that may require attention based on:

- sudden drops in milk production;
- abnormal deviation from the cow's 30-day average weight;
- missing sensor readings;
- inconsistent or extreme measurements.

This would require defining business thresholds with the farm owner or using historical data to build anomaly detection rules.

## Data flow

Assignment-compliant flow:

```text
Parquet datasets -> simulate_sensors.py -> API POST requests -> SQLite database -> daily report
```

Optional development flow:

```text
Parquet datasets -> load_data.py -> SQLite database
```
