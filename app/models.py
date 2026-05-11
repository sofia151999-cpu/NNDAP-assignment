from sqlalchemy import (
    Column,
    String,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    Index,
)

from app.database import Base


class Cow(Base):
    __tablename__ = "cows"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    birthdate = Column(Date, nullable=True)


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(String, primary_key=True)
    unit = Column(String, nullable=False)  # Example: "kg" or "L"


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sensor_id = Column(String, ForeignKey("sensors.id"), nullable=False)
    cow_id = Column(String, ForeignKey("cows.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    value = Column(Float, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "sensor_id",
            "cow_id",
            "timestamp",
            "value",
            name="uq_measurement_sensor_cow_timestamp_value",
        ),
        Index("ix_measurements_cow_timestamp", "cow_id", "timestamp"),
        Index("ix_measurements_sensor_timestamp", "sensor_id", "timestamp"),
    )