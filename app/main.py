import re
from datetime import date, datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import Cow, Sensor, Measurement


app = FastAPI(title="NNDAP Assignment API")


class CowCreate(BaseModel):
    name: str = Field(..., min_length=1)
    birthdate: date


class CowDatasetCreate(BaseModel):
    name: str | None = None
    birthdate: date | None = None


class SensorCreate(BaseModel):
    unit: str = Field(..., min_length=1)


class SensorResponse(BaseModel):
    id: str
    unit: str


class LatestMeasurementResponse(BaseModel):
    id: int
    sensor_id: str
    timestamp: datetime
    value: float


class CowResponse(BaseModel):
    id: str
    name: str | None
    birthdate: date | None
    latest_measurement: LatestMeasurementResponse | None = None


class MeasurementCreate(BaseModel):
    value: float = Field(..., ge=0)


class SensorMeasurementCreate(BaseModel):
    cow_id: str = Field(..., min_length=1)
    sensor_id: str = Field(..., min_length=1)
    timestamp: datetime
    value: float = Field(..., ge=0)


class MeasurementResponse(BaseModel):
    id: int
    cow_id: str
    cow_name: str | None
    sensor_id: str
    sensor_unit: str
    timestamp: datetime
    value: float


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_next_numbered_name(db: Session, name: str) -> str:
    base_name = name.strip()

    if not base_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cow name cannot be empty",
        )

    pattern = re.compile(
        rf"^{re.escape(base_name)} #(\d+)$",
        re.IGNORECASE,
    )

    cows = db.query(Cow).filter(Cow.name.isnot(None)).all()

    highest_number = 0

    for cow in cows:
        match = pattern.match(cow.name.strip())

        if match:
            number = int(match.group(1))
            highest_number = max(highest_number, number)

    return f"{base_name} #{highest_number + 1}"


def get_cow_by_id(db: Session, cow_id: str) -> Cow:
    cow = db.query(Cow).filter(Cow.id == cow_id).first()

    if cow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Cow with id '{cow_id}' does not exist",
        )

    return cow


def get_sensor_by_id(db: Session, sensor_id: str) -> Sensor:
    sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()

    if sensor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensor with id '{sensor_id}' does not exist",
        )

    return sensor


def get_sensor_by_unit(db: Session, allowed_units: list[str]) -> Sensor:
    allowed_units_lower = [unit.lower() for unit in allowed_units]

    sensor = (
        db.query(Sensor)
        .filter(func.lower(Sensor.unit).in_(allowed_units_lower))
        .first()
    )

    if sensor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No sensor found for units: {allowed_units}",
        )

    return sensor


def build_measurement_response(
    measurement: Measurement,
    cow: Cow,
    sensor: Sensor,
) -> MeasurementResponse:
    return MeasurementResponse(
        id=measurement.id,
        cow_id=cow.id,
        cow_name=cow.name,
        sensor_id=sensor.id,
        sensor_unit=sensor.unit,
        timestamp=measurement.timestamp,
        value=measurement.value,
    )


def create_measurement(
    db: Session,
    cow_id: str,
    value: float,
    allowed_sensor_units: list[str],
) -> MeasurementResponse:
    cow = get_cow_by_id(db, cow_id)
    sensor = get_sensor_by_unit(db, allowed_sensor_units)

    measurement = Measurement(
        sensor_id=sensor.id,
        cow_id=cow.id,
        timestamp=datetime.utcnow(),
        value=value,
    )

    db.add(measurement)
    db.commit()
    db.refresh(measurement)

    return build_measurement_response(measurement, cow, sensor)


def get_latest_measurement(db: Session, cow_id: str) -> LatestMeasurementResponse | None:
    latest_measurement = (
        db.query(Measurement)
        .filter(Measurement.cow_id == cow_id)
        .order_by(Measurement.timestamp.desc(), Measurement.id.desc())
        .first()
    )

    if latest_measurement is None:
        return None

    return LatestMeasurementResponse(
        id=latest_measurement.id,
        sensor_id=latest_measurement.sensor_id,
        timestamp=latest_measurement.timestamp,
        value=latest_measurement.value,
    )


@app.get("/")
def root():
    return {"message": "NNDAP API is running"}


@app.post(
    "/cows",
    response_model=CowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cow(cow_data: CowCreate, db: Session = Depends(get_db)):
    cow = Cow(
        id=str(uuid4()),
        name=get_next_numbered_name(db, cow_data.name),
        birthdate=cow_data.birthdate,
    )

    db.add(cow)
    db.commit()
    db.refresh(cow)

    return CowResponse(
        id=cow.id,
        name=cow.name,
        birthdate=cow.birthdate,
        latest_measurement=None,
    )


@app.post(
    "/cows/{cow_id}",
    response_model=CowResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cow_from_dataset(
    cow_id: str,
    cow_data: CowDatasetCreate,
    db: Session = Depends(get_db),
):
    """
    Used by the sensor simulation script.

    It creates cows using the ID provided in cows.parquet.
    """
    existing_cow = db.query(Cow).filter(Cow.id == cow_id).first()

    if existing_cow is not None:
        return CowResponse(
            id=existing_cow.id,
            name=existing_cow.name,
            birthdate=existing_cow.birthdate,
            latest_measurement=get_latest_measurement(db, existing_cow.id),
        )

    cow = Cow(
        id=cow_id,
        name=cow_data.name,
        birthdate=cow_data.birthdate,
    )

    db.add(cow)
    db.commit()
    db.refresh(cow)

    return CowResponse(
        id=cow.id,
        name=cow.name,
        birthdate=cow.birthdate,
        latest_measurement=None,
    )


@app.post(
    "/sensors/{sensor_id}",
    response_model=SensorResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_sensor_from_dataset(
    sensor_id: str,
    sensor_data: SensorCreate,
    db: Session = Depends(get_db),
):
    """
    Used by the sensor simulation script.

    It creates sensors using the ID provided in sensors.parquet.
    """
    existing_sensor = db.query(Sensor).filter(Sensor.id == sensor_id).first()

    if existing_sensor is not None:
        return SensorResponse(
            id=existing_sensor.id,
            unit=existing_sensor.unit,
        )

    sensor = Sensor(
        id=sensor_id,
        unit=sensor_data.unit,
    )

    db.add(sensor)
    db.commit()
    db.refresh(sensor)

    return SensorResponse(
        id=sensor.id,
        unit=sensor.unit,
    )


@app.post(
    "/measurements",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_measurement_from_sensor_event(
    measurement_data: SensorMeasurementCreate,
    db: Session = Depends(get_db),
):
    """
    Used by the sensor simulation script.

    Each record from measurements.parquet is sent individually to this endpoint.
    """
    cow = get_cow_by_id(db, measurement_data.cow_id)
    sensor = get_sensor_by_id(db, measurement_data.sensor_id)

    existing_measurement = (
        db.query(Measurement)
        .filter(Measurement.cow_id == measurement_data.cow_id)
        .filter(Measurement.sensor_id == measurement_data.sensor_id)
        .filter(Measurement.timestamp == measurement_data.timestamp)
        .filter(Measurement.value == measurement_data.value)
        .first()
    )

    if existing_measurement is not None:
        return build_measurement_response(existing_measurement, cow, sensor)

    measurement = Measurement(
        cow_id=measurement_data.cow_id,
        sensor_id=measurement_data.sensor_id,
        timestamp=measurement_data.timestamp,
        value=measurement_data.value,
    )

    db.add(measurement)
    db.commit()
    db.refresh(measurement)

    return build_measurement_response(measurement, cow, sensor)


@app.post(
    "/cows/{cow_id}/measurements/milk",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_milk_measurement(
    cow_id: str,
    measurement_data: MeasurementCreate,
    db: Session = Depends(get_db),
):
    return create_measurement(
        db=db,
        cow_id=cow_id,
        value=measurement_data.value,
        allowed_sensor_units=["l", "L", "liter", "litre", "liters", "litres"],
    )


@app.post(
    "/cows/{cow_id}/measurements/weight",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_weight_measurement(
    cow_id: str,
    measurement_data: MeasurementCreate,
    db: Session = Depends(get_db),
):
    return create_measurement(
        db=db,
        cow_id=cow_id,
        value=measurement_data.value,
        allowed_sensor_units=["kg", "kilogram", "kilograms"],
    )


@app.get(
    "/cows/{cow_id}",
    response_model=CowResponse,
)
def get_cow(cow_id: str, db: Session = Depends(get_db)):
    cow = get_cow_by_id(db, cow_id)

    return CowResponse(
        id=cow.id,
        name=cow.name,
        birthdate=cow.birthdate,
        latest_measurement=get_latest_measurement(db, cow.id),
    )