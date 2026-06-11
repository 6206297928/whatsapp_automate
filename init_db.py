"""One-time database initializer + demo seed.

Run this ONCE against your Neon (or any) PostgreSQL before deploying, so the
tables exist and there is sample data for the agent's tools to read/write.

Usage:
    DATABASE_URL="postgresql://user:pass@host/db?sslmode=require" python init_db.py
"""
import uuid

from database import Base, engine, get_db_session, Person


def main() -> None:
    # 1. Create all tables (persons, tickets, ticket_vendors)
    Base.metadata.create_all(engine)
    print("✅ Tables created (persons, tickets, ticket_vendors)")

    # 2. Seed one demo customer and one demo vendor (idempotent on phone)
    session = get_db_session()
    try:
        seeds = [
            {"phone": "+910000000001", "name": "Demo Customer", "linked_to": "customer"},
            {"phone": "+910000000002", "name": "Demo Vendor", "linked_to": "vendor"},
        ]
        for s in seeds:
            exists = session.query(Person).filter(Person.phone == s["phone"]).first()
            if exists:
                print(f"• {s['linked_to']} {s['phone']} already exists — skipping")
                continue
            session.add(Person(
                id=str(uuid.uuid4()),
                phone=s["phone"],
                name=s["name"],
                linked=True,
                linked_to=s["linked_to"],
            ))
            print(f"✅ Seeded {s['linked_to']}: {s['phone']}")
        session.commit()
    finally:
        session.close()

    print("\n🎉 Database ready. You can now deploy the agent.")


if __name__ == "__main__":
    main()
