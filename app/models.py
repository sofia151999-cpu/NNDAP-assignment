from sqlalchemy import Column, String, Float, Date, DateTime, ForeignKey, Integer
from app.database import Base


class Cow(Base):
    __tablename__ = "cows"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=True)
    birthdate = Column(Date, nullable=True)


class Sensor(Base):
    __tablename__ = "sensors"

    id = Column(String, primary_key=True)
    unit = Column(String, nullable=False)  # "kg" or "L"


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(Integer, primary_key=True, autoincrement=True)

    sensor_id = Column(String, ForeignKey("sensors.id"))
    cow_id = Column(String, ForeignKey("cows.id"))

    timestamp = Column(DateTime, nullable=False)

    value = Column(Float, nullable=True)