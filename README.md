# Cow Farm Automation System

This project is a simplified data platform built for a dairy farm.  
It ingests sensor data about cows (milk production and weight), stores it in a local database, and prepares it for API-based access and reporting.

---

## Project Goal

The system is designed to help a farmer:

- Track milk production per cow over time
- Monitor cow weight and its evolution
- Generate daily reports (future implementation)
- Identify potential health issues based on sensor data (future enhancement)

---

## Architecture Overview
The current implementation follows a simple data pipeline:

## Data Model

The system is built around three main entities:

### Cows
Basic information about each cow:
- id
- name
- birthdate

### Sensors
Defines the type of measurement:
- id
- unit (kg or L)

### Measurements
Time-series sensor readings:
- cow_id
- sensor_id
- timestamp
- value

---

## Database

- Database: SQLite
- File: `farm.db`
- Fully persistent (data is not lost after restart)

The schema is automatically created using SQLAlchemy.

---

## Data Ingestion

A custom Python script loads data from `.parquet` files into the database.

### Files used:
- `cows.parquet`
- `sensors.parquet`
- `measurements.parquet`

### Process:
1. Read files using Pandas
2. Transform timestamps
3. Insert data into SQLite

---