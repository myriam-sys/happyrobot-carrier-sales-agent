"""
Seed script — populates the loads table with 15 realistic freight loads.

Run directly:
    python -m api.seed_data

Or import and call seed() programmatically.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

from api.database import SessionLocal, create_tables, LoadORM


LOADS: list[dict] = [
    {
        "load_id": "LD-001",
        "origin": "Chicago, IL",
        "destination": "Dallas, TX",
        "equipment_type": "Dry Van",
        "weight_lbs": 42000,
        "miles": 921,
        "rate_usd": 2300.00,
        "commodity": "Consumer Electronics",
        "pickup_date": datetime.utcnow() + timedelta(days=1),
        "delivery_date": datetime.utcnow() + timedelta(days=3),
        "available": True,
    },
    {
        "load_id": "LD-002",
        "origin": "Los Angeles, CA",
        "destination": "Phoenix, AZ",
        "equipment_type": "Reefer",
        "weight_lbs": 38000,
        "miles": 372,
        "rate_usd": 1850.00,
        "commodity": "Fresh Produce",
        "pickup_date": datetime.utcnow() + timedelta(days=1),
        "delivery_date": datetime.utcnow() + timedelta(days=2),
        "available": True,
    },
    {
        "load_id": "LD-003",
        "origin": "Houston, TX",
        "destination": "Atlanta, GA",
        "equipment_type": "Flatbed",
        "weight_lbs": 45000,
        "miles": 791,
        "rate_usd": 2750.00,
        "commodity": "Steel Coils",
        "pickup_date": datetime.utcnow() + timedelta(days=2),
        "delivery_date": datetime.utcnow() + timedelta(days=4),
        "available": True,
    },
    {
        "load_id": "LD-004",
        "origin": "Memphis, TN",
        "destination": "Columbus, OH",
        "equipment_type": "Dry Van",
        "weight_lbs": 40000,
        "miles": 511,
        "rate_usd": 1900.00,
        "commodity": "Auto Parts",
        "pickup_date": datetime.utcnow() + timedelta(days=1),
        "delivery_date": datetime.utcnow() + timedelta(days=2),
        "available": True,
    },
    {
        "load_id": "LD-005",
        "origin": "Seattle, WA",
        "destination": "Salt Lake City, UT",
        "equipment_type": "Reefer",
        "weight_lbs": 36000,
        "miles": 835,
        "rate_usd": 3100.00,
        "commodity": "Frozen Seafood",
        "pickup_date": datetime.utcnow() + timedelta(days=2),
        "delivery_date": datetime.utcnow() + timedelta(days=4),
        "available": True,
    },
    {
        "load_id": "LD-006",
        "origin": "Detroit, MI",
        "destination": "Nashville, TN",
        "equipment_type": "Dry Van",
        "weight_lbs": 44000,
        "miles": 462,
        "rate_usd": 1800.00,
        "commodity": "Packaged Goods",
        "pickup_date": datetime.utcnow() + timedelta(days=1),
        "delivery_date": datetime.utcnow() + timedelta(days=2),
        "available": True,
    },
    {
        "load_id": "LD-007",
        "origin": "Denver, CO",
        "destination": "Kansas City, MO",
        "equipment_type": "Flatbed",
        "weight_lbs": 47000,
        "miles": 601,
        "rate_usd": 2950.00,
        "commodity": "Lumber",
        "pickup_date": datetime.utcnow() + timedelta(days=3),
        "delivery_date": datetime.utcnow() + timedelta(days=5),
        "available": True,
    },
    {
        "load_id": "LD-008",
        "origin": "Miami, FL",
        "destination": "Charlotte, NC",
        "equipment_type": "Reefer",
        "weight_lbs": 34000,
        "miles": 654,
        "rate_usd": 2400.00,
        "commodity": "Dairy Products",
        "pickup_date": datetime.utcnow() + timedelta(days=1),
        "delivery_date": datetime.utcnow() + timedelta(days=3),
        "available": True,
    },
    {
        "load_id": "LD-009",
        "origin": "Philadelphia, PA",
        "destination": "Boston, MA",
        "equipment_type": "Dry Van",
        "weight_lbs": 35000,
        "miles": 306,
        "rate_usd": 1820.00,
        "commodity": "Pharmaceuticals",
        "pickup_date": datetime.utcnow() + timedelta(days=1),
        "delivery_date": datetime.utcnow() + timedelta(days=1),
        "available": True,
    },
    {
        "load_id": "LD-010",
        "origin": "Minneapolis, MN",
        "destination": "St. Louis, MO",
        "equipment_type": "Flatbed",
        "weight_lbs": 46000,
        "miles": 558,
        "rate_usd": 2600.00,
        "commodity": "Agricultural Equipment",
        "pickup_date": datetime.utcnow() + timedelta(days=2),
        "delivery_date": datetime.utcnow() + timedelta(days=4),
        "available": True,
    },
    {
        "load_id": "LD-011",
        "origin": "Portland, OR",
        "destination": "San Francisco, CA",
        "equipment_type": "Reefer",
        "weight_lbs": 37000,
        "miles": 640,
        "rate_usd": 2850.00,
        "commodity": "Organic Produce",
        "pickup_date": datetime.utcnow() + timedelta(days=1),
        "delivery_date": datetime.utcnow() + timedelta(days=3),
        "available": True,
    },
    {
        "load_id": "LD-012",
        "origin": "Atlanta, GA",
        "destination": "New York, NY",
        "equipment_type": "Dry Van",
        "weight_lbs": 43000,
        "miles": 875,
        "rate_usd": 3200.00,
        "commodity": "Clothing & Apparel",
        "pickup_date": datetime.utcnow() + timedelta(days=2),
        "delivery_date": datetime.utcnow() + timedelta(days=4),
        "available": True,
    },
    {
        "load_id": "LD-013",
        "origin": "San Antonio, TX",
        "destination": "El Paso, TX",
        "equipment_type": "Flatbed",
        "weight_lbs": 44500,
        "miles": 549,
        "rate_usd": 2450.00,
        "commodity": "Construction Materials",
        "pickup_date": datetime.utcnow() + timedelta(days=3),
        "delivery_date": datetime.utcnow() + timedelta(days=5),
        "available": True,
    },
    {
        "load_id": "LD-014",
        "origin": "Cincinnati, OH",
        "destination": "Indianapolis, IN",
        "equipment_type": "Dry Van",
        "weight_lbs": 41000,
        "miles": 110,
        "rate_usd": 1850.00,
        "commodity": "Household Goods",
        "pickup_date": datetime.utcnow() + timedelta(days=1),
        "delivery_date": datetime.utcnow() + timedelta(days=1),
        "available": True,
    },
    {
        "load_id": "LD-015",
        "origin": "Las Vegas, NV",
        "destination": "Albuquerque, NM",
        "equipment_type": "Reefer",
        "weight_lbs": 32000,
        "miles": 490,
        "rate_usd": 3500.00,
        "commodity": "Temperature-Sensitive Pharmaceuticals",
        "pickup_date": datetime.utcnow() + timedelta(days=2),
        "delivery_date": datetime.utcnow() + timedelta(days=3),
        "available": True,
    },
]


def seed(clear_existing: bool = False) -> None:
    """
    Insert seed loads into the database.

    Parameters
    ----------
    clear_existing:
        If True, delete all existing loads before inserting. Useful for a
        clean reset during development.
    """
    create_tables()
    db = SessionLocal()
    try:
        if clear_existing:
            db.query(LoadORM).delete()
            db.commit()
            print("Cleared existing loads.")

        inserted = 0
        for data in LOADS:
            existing = db.get(LoadORM, data["load_id"])
            if existing:
                continue
            db.add(LoadORM(**data))
            inserted += 1

        db.commit()
        print(f"Seeded {inserted} load(s). ({len(LOADS) - inserted} already existed)")
    finally:
        db.close()


if __name__ == "__main__":
    clear = "--clear" in sys.argv
    seed(clear_existing=clear)
