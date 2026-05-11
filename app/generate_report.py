import os
import sys
from datetime import date, datetime, time, timedelta

from sqlalchemy import func

from app.database import SessionLocal
from app.models import Cow, Sensor, Measurement


MILK_UNITS = {"l", "liter", "litre", "liters", "litres"}
WEIGHT_UNITS = {"kg", "kilogram", "kilograms"}


def get_report_date() -> date:
    if len(sys.argv) < 2:
        return date.today()

    try:
        return datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Date must use format YYYY-MM-DD")


def get_sensor_ids_by_units(db, allowed_units: set[str]) -> list[str]:
    sensors = db.query(Sensor).all()

    return [
        sensor.id
        for sensor in sensors
        if sensor.unit and sensor.unit.lower() in allowed_units
    ]


def generate_daily_report(report_date: date) -> str:
    db = SessionLocal()

    try:
        day_start = datetime.combine(report_date, time.min)
        day_end = datetime.combine(report_date, time.max)
        thirty_days_start = day_start - timedelta(days=29)

        milk_sensor_ids = get_sensor_ids_by_units(db, MILK_UNITS)
        weight_sensor_ids = get_sensor_ids_by_units(db, WEIGHT_UNITS)

        lines = []
        lines.append(f"Daily farm report - {report_date}")
        lines.append("=" * 50)
        lines.append("")

        # -------------------------------------------------
        # 1. Milk production per cow per day
        # -------------------------------------------------
        lines.append("Milk production per cow")
        lines.append("-" * 50)

        if not milk_sensor_ids:
            lines.append("No milk sensors found.")
        else:
            milk_rows = (
                db.query(
                    Cow.name,
                    func.sum(Measurement.value).label("total_milk"),
                )
                .join(Measurement, Measurement.cow_id == Cow.id)
                .filter(Measurement.sensor_id.in_(milk_sensor_ids))
                .filter(Measurement.timestamp >= day_start)
                .filter(Measurement.timestamp <= day_end)
                .group_by(Cow.id, Cow.name)
                .order_by(Cow.name)
                .all()
            )

            if not milk_rows:
                lines.append("No milk production data for this date.")
            else:
                for cow_name, total_milk in milk_rows:
                    lines.append(f"{cow_name}: {round(total_milk, 2)} L")

        lines.append("")

        # -------------------------------------------------
        # 2. Current weight and average weight last 30 days
        # -------------------------------------------------
        lines.append("Weight per cow")
        lines.append("-" * 50)

        if not weight_sensor_ids:
            lines.append("No weight sensors found.")
        else:
            cows = db.query(Cow).order_by(Cow.name).all()

            # Average weight in the last 30 days.
            # One query for all cows, not one query per cow.
            average_rows = (
                db.query(
                    Measurement.cow_id,
                    func.avg(Measurement.value).label("average_weight"),
                )
                .filter(Measurement.sensor_id.in_(weight_sensor_ids))
                .filter(Measurement.timestamp >= thirty_days_start)
                .filter(Measurement.timestamp <= day_end)
                .group_by(Measurement.cow_id)
                .all()
            )

            average_by_cow = {
                cow_id: average_weight
                for cow_id, average_weight in average_rows
            }

            # Latest weight per cow using a window function.
            row_number = func.row_number().over(
                partition_by=Measurement.cow_id,
                order_by=(
                    Measurement.timestamp.desc(),
                    Measurement.id.desc(),
                ),
            ).label("row_number")

            latest_weight_subquery = (
                db.query(
                    Measurement.cow_id.label("cow_id"),
                    Measurement.value.label("value"),
                    Measurement.timestamp.label("timestamp"),
                    row_number,
                )
                .filter(Measurement.sensor_id.in_(weight_sensor_ids))
                .filter(Measurement.timestamp <= day_end)
                .subquery()
            )

            latest_rows = (
                db.query(
                    latest_weight_subquery.c.cow_id,
                    latest_weight_subquery.c.value,
                    latest_weight_subquery.c.timestamp,
                )
                .filter(latest_weight_subquery.c.row_number == 1)
                .all()
            )

            latest_by_cow = {
                cow_id: {
                    "value": value,
                    "timestamp": timestamp,
                }
                for cow_id, value, timestamp in latest_rows
            }

            for cow in cows:
                latest_weight = latest_by_cow.get(cow.id)
                average_weight = average_by_cow.get(cow.id)

                if latest_weight is None:
                    lines.append(f"{cow.name}: no weight data")
                    continue

                if average_weight is None:
                    lines.append(
                        f"{cow.name}: current weight "
                        f"{round(latest_weight['value'], 2)} kg, "
                        f"average last 30 days: no data"
                    )
                else:
                    lines.append(
                        f"{cow.name}: current weight "
                        f"{round(latest_weight['value'], 2)} kg, "
                        f"average last 30 days "
                        f"{round(average_weight, 2)} kg"
                    )

        lines.append("")
        lines.append("Implementation note")
        lines.append("-" * 50)
        lines.append(
            "For this assignment, the report is generated manually. "
            "In production, this process would be scheduled to run daily "
            "with a scheduler such as cron, Airflow or Prefect, and the "
            "execution should be logged and monitored."
        )

        return "\n".join(lines)

    finally:
        db.close()


def save_report(report_date: date, report_text: str) -> str:
    os.makedirs("reports", exist_ok=True)

    file_path = f"reports/daily_report_{report_date}.txt"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(report_text)

    return file_path


def main() -> None:
    report_date = get_report_date()
    report_text = generate_daily_report(report_date)
    file_path = save_report(report_date, report_text)

    print(report_text)
    print("")
    print(f"Report saved to: {file_path}")


if __name__ == "__main__":
    main()