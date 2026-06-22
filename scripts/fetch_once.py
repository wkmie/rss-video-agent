import asyncio
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.db.database import SessionLocal, init_db
from app.services.news_service import fetch_and_store


async def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        result = await fetch_and_store(db)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())

