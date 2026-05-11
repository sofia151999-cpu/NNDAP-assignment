import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_db
from app.models import Sensor


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    db.add(Sensor(id="milk-sensor-test", unit="L"))
    db.add(Sensor(id="weight-sensor-test", unit="kg"))
    db.commit()
    db.close()

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "NNDAP API is running"}


def test_create_cow_generates_numbered_name(client):
    first_response = client.post(
        "/cows",
        json={
            "name": "Lindsey",
            "birthdate": "2020-01-09",
        },
    )

    second_response = client.post(
        "/cows",
        json={
            "name": "Lindsey",
            "birthdate": "2021-02-10",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 201

    first_cow = first_response.json()
    second_cow = second_response.json()

    assert first_cow["id"] is not None
    assert first_cow["name"] == "Lindsey #1"
    assert first_cow["birthdate"] == "2020-01-09"

    assert second_cow["id"] is not None
    assert second_cow["name"] == "Lindsey #2"
    assert second_cow["birthdate"] == "2021-02-10"


def test_create_weight_measurement_by_cow_id(client):
    cow_response = client.post(
        "/cows",
        json={
            "name": "Lindsey",
            "birthdate": "2020-01-09",
        },
    )

    assert cow_response.status_code == 201

    cow = cow_response.json()
    cow_id = cow["id"]

    measurement_response = client.post(
        f"/cows/{cow_id}/measurements/weight",
        json={
            "value": 552.4,
        },
    )

    assert measurement_response.status_code == 201

    measurement = measurement_response.json()

    assert measurement["cow_id"] == cow_id
    assert measurement["cow_name"] == "Lindsey #1"
    assert measurement["sensor_unit"] == "kg"
    assert measurement["value"] == 552.4


def test_create_milk_measurement_by_cow_id(client):
    cow_response = client.post(
        "/cows",
        json={
            "name": "Molly",
            "birthdate": "2021-03-15",
        },
    )

    assert cow_response.status_code == 201

    cow = cow_response.json()
    cow_id = cow["id"]

    measurement_response = client.post(
        f"/cows/{cow_id}/measurements/milk",
        json={
            "value": 4.8,
        },
    )

    assert measurement_response.status_code == 201

    measurement = measurement_response.json()

    assert measurement["cow_id"] == cow_id
    assert measurement["cow_name"] == "Molly #1"
    assert measurement["sensor_unit"] == "L"
    assert measurement["value"] == 4.8


def test_get_cow_by_id_returns_latest_measurement(client):
    cow_response = client.post(
        "/cows",
        json={
            "name": "Lindsey",
            "birthdate": "2020-01-09",
        },
    )

    assert cow_response.status_code == 201

    cow = cow_response.json()
    cow_id = cow["id"]

    measurement_response = client.post(
        f"/cows/{cow_id}/measurements/weight",
        json={
            "value": 552.4,
        },
    )

    assert measurement_response.status_code == 201

    get_response = client.get(f"/cows/{cow_id}")

    assert get_response.status_code == 200

    result = get_response.json()

    assert result["id"] == cow_id
    assert result["name"] == "Lindsey #1"
    assert result["birthdate"] == "2020-01-09"
    assert result["latest_measurement"] is not None
    assert result["latest_measurement"]["value"] == 552.4


def test_measurement_for_unknown_cow_returns_404(client):
    response = client.post(
        "/cows/unknown-cow-id/measurements/weight",
        json={
            "value": 500.0,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Cow with id 'unknown-cow-id' does not exist"


def test_get_unknown_cow_by_id_returns_404(client):
    response = client.get("/cows/unknown-cow-id")

    assert response.status_code == 404
    assert response.json()["detail"] == "Cow with id 'unknown-cow-id' does not exist"


def test_negative_measurement_is_rejected(client):
    response = client.post(
        "/cows/unknown-cow-id/measurements/weight",
        json={
            "value": -10,
        },
    )

    assert response.status_code == 422