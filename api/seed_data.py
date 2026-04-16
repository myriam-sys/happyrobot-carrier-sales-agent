"""
Seed script — populates the loads table with 15 realistic freight loads.

Run directly:
    python -m api.seed_data

Or import and call seed() programmatically.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

import uuid

from api.database import SessionLocal, create_tables, drop_tables, migrate_tables, engine, CallLogORM, LoadORM


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


SAMPLE_CALLS: list[dict] = [
    # --- booked (6) ---
    {
        "mc_number": "MC-481923", "carrier_name": "Blue Ridge Logistics LLC",
        "load_id": "LD-001", "initial_rate_offered": 2100.00, "final_agreed_rate": 2300.00,
        "num_negotiation_rounds": 1, "outcome": "booked", "sentiment": "positive",
        "call_duration_seconds": 203, "notes": "Carrier confirmed Friday pickup.",
        "timestamp": datetime.utcnow() - timedelta(days=6, hours=3),
    },
    {
        "mc_number": "MC-774521", "carrier_name": "Apex Freight Solutions",
        "load_id": "LD-003", "initial_rate_offered": 2600.00, "final_agreed_rate": 2750.00,
        "num_negotiation_rounds": 2, "outcome": "booked", "sentiment": "positive",
        "call_duration_seconds": 318, "notes": "Slight rate bump to close.",
        "timestamp": datetime.utcnow() - timedelta(days=5, hours=9),
    },
    {
        "mc_number": "MC-209834", "carrier_name": "Summit Carriers Inc",
        "load_id": "LD-005", "initial_rate_offered": 3100.00, "final_agreed_rate": 3100.00,
        "num_negotiation_rounds": 0, "outcome": "booked", "sentiment": "positive",
        "call_duration_seconds": 142, "notes": "First offer accepted immediately.",
        "timestamp": datetime.utcnow() - timedelta(days=4, hours=11),
    },
    {
        "mc_number": "MC-563017", "carrier_name": "Clearwater Transport Co",
        "load_id": "LD-008", "initial_rate_offered": 2200.00, "final_agreed_rate": 2400.00,
        "num_negotiation_rounds": 2, "outcome": "booked", "sentiment": "positive",
        "call_duration_seconds": 275, "notes": None,
        "timestamp": datetime.utcnow() - timedelta(days=3, hours=7),
    },
    {
        "mc_number": "MC-348821", "carrier_name": "Iron Horse Hauling LLC",
        "load_id": "LD-012", "initial_rate_offered": 3000.00, "final_agreed_rate": 3200.00,
        "num_negotiation_rounds": 1, "outcome": "booked", "sentiment": "positive",
        "call_duration_seconds": 198, "notes": "Carrier requested liftgate at delivery.",
        "timestamp": datetime.utcnow() - timedelta(days=2, hours=5),
    },
    {
        "mc_number": "MC-901456", "carrier_name": "Keystone Freight Partners",
        "load_id": "LD-015", "initial_rate_offered": 3200.00, "final_agreed_rate": 3500.00,
        "num_negotiation_rounds": 2, "outcome": "booked", "sentiment": "positive",
        "call_duration_seconds": 354, "notes": "Reefer load, carrier confirmed temp settings.",
        "timestamp": datetime.utcnow() - timedelta(days=1, hours=2),
    },
    # --- negotiation_failed (3) ---
    {
        "mc_number": "MC-662340", "carrier_name": "Desert Wind Trucking",
        "load_id": "LD-007", "initial_rate_offered": 2700.00, "final_agreed_rate": None,
        "num_negotiation_rounds": 3, "outcome": "negotiation_failed", "sentiment": "frustrated",
        "call_duration_seconds": 412, "notes": "Carrier wanted $3,400. Too far apart.",
        "timestamp": datetime.utcnow() - timedelta(days=5, hours=14),
    },
    {
        "mc_number": "MC-117893", "carrier_name": "Rocky Mountain Express",
        "load_id": "LD-010", "initial_rate_offered": 2500.00, "final_agreed_rate": None,
        "num_negotiation_rounds": 3, "outcome": "negotiation_failed", "sentiment": "hostile",
        "call_duration_seconds": 389, "notes": "Carrier became combative on round 3.",
        "timestamp": datetime.utcnow() - timedelta(days=3, hours=16),
    },
    {
        "mc_number": "MC-445678", "carrier_name": "Gulf Coast Carriers",
        "load_id": "LD-013", "initial_rate_offered": 2300.00, "final_agreed_rate": None,
        "num_negotiation_rounds": 3, "outcome": "negotiation_failed", "sentiment": "frustrated",
        "call_duration_seconds": 445, "notes": "Rate gap could not be bridged.",
        "timestamp": datetime.utcnow() - timedelta(days=1, hours=18),
    },
    # --- carrier_ineligible (2) ---
    {
        "mc_number": "MC-000124", "carrier_name": "Budget Haul Co",
        "load_id": None, "initial_rate_offered": 1900.00, "final_agreed_rate": None,
        "num_negotiation_rounds": 0, "outcome": "carrier_ineligible", "sentiment": "neutral",
        "call_duration_seconds": 87, "notes": "FMCSA: authority not active.",
        "timestamp": datetime.utcnow() - timedelta(days=6, hours=1),
    },
    {
        "mc_number": "MC-883210", "carrier_name": "Sunrise Moving & Freight",
        "load_id": None, "initial_rate_offered": 2050.00, "final_agreed_rate": None,
        "num_negotiation_rounds": 0, "outcome": "carrier_ineligible", "sentiment": "neutral",
        "call_duration_seconds": 94, "notes": "FMCSA: no insurance on file.",
        "timestamp": datetime.utcnow() - timedelta(days=4, hours=20),
    },
    # --- no_match (2) ---
    {
        "mc_number": "MC-531097", "carrier_name": "Lakeside Flatbed LLC",
        "load_id": None, "initial_rate_offered": 1800.00, "final_agreed_rate": None,
        "num_negotiation_rounds": 0, "outcome": "no_match", "sentiment": "neutral",
        "call_duration_seconds": 65, "notes": "Carrier only runs reefer; no dry van available.",
        "timestamp": datetime.utcnow() - timedelta(days=5, hours=6),
    },
    {
        "mc_number": "MC-720445", "carrier_name": "Northern Route Transport",
        "load_id": None, "initial_rate_offered": 2200.00, "final_agreed_rate": None,
        "num_negotiation_rounds": 0, "outcome": "no_match", "sentiment": "neutral",
        "call_duration_seconds": 72, "notes": "No equipment available in origin area.",
        "timestamp": datetime.utcnow() - timedelta(days=2, hours=12),
    },
    # --- hung_up (2) ---
    {
        "mc_number": "MC-194302", "carrier_name": "Fast Lane Freight",
        "load_id": "LD-004", "initial_rate_offered": 1850.00, "final_agreed_rate": None,
        "num_negotiation_rounds": 1, "outcome": "hung_up", "sentiment": "hostile",
        "call_duration_seconds": 38, "notes": "Carrier hung up after first counter.",
        "timestamp": datetime.utcnow() - timedelta(days=4, hours=4),
    },
    {
        "mc_number": "MC-607812", "carrier_name": "Redline Haulers Inc",
        "load_id": "LD-009", "initial_rate_offered": 1800.00, "final_agreed_rate": None,
        "num_negotiation_rounds": 0, "outcome": "hung_up", "sentiment": "frustrated",
        "call_duration_seconds": 21, "notes": "Disconnected immediately after rate quote.",
        "timestamp": datetime.utcnow() - timedelta(days=1, hours=9),
    },
]


def seed_sample_calls() -> None:
    """
    Insert 15 sample call log entries to make the dashboard look operational.

    Idempotent — skips insertion entirely if the call_logs table already
    contains any rows.
    """
    db = SessionLocal()
    try:
        existing_count = db.query(CallLogORM).count()
        if existing_count > 0:
            print(f"Skipped call log seed — {existing_count} record(s) already present.")
            return

        for data in SAMPLE_CALLS:
            db.add(CallLogORM(call_id=str(uuid.uuid4()), **data))

        db.commit()
        print(f"Seeded {len(SAMPLE_CALLS)} sample call log(s).")
    finally:
        db.close()


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
    migrate_tables(engine)
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

    seed_sample_calls()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        drop_tables()
        print("Dropped all tables.")
        create_tables()
        print("Recreated tables with current schema.")
        seed_sample_calls()
    else:
        clear = "--clear" in sys.argv
        seed(clear_existing=clear)
