from app.database import engine, Base
from app import models


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    print("Database created successfully")


if __name__ == "__main__":
    init_db()