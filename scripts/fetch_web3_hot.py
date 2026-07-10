from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.db.database import SessionLocal, init_db
from app.services.web3_hot_service import fetch_and_store_hot_items


async def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Web3 hot feed items.")
    parser.add_argument("--source-type", choices=["rss", "google_news_rss", "x_recent_search", "lunarcrush"], default=None)
    parser.add_argument("--keyword", default=None)
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        result = await fetch_and_store_hot_items(db, source_type=args.source_type, keyword=args.keyword)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
