from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.database import SessionLocal, init_db
from app.services.pre_event_service import fetch_and_store_pre_events


async def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch upcoming pre-event topics.")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--category", action="append", help="Category to fetch. Can be repeated.")
    parser.add_argument("--force-refresh", action="store_true")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        result = await fetch_and_store_pre_events(db, args.days, args.category, args.force_refresh)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
