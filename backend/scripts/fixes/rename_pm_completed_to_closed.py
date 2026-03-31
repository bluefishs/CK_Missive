"""Rename PM Case status 'completed' to 'closed'

This only affects pm_cases.status, NOT milestones, calendar events, or contract projects.
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.db.database import AsyncSessionLocal
from sqlalchemy import text


async def migrate():
    async with AsyncSessionLocal() as db:
        result = await db.execute(text(
            "UPDATE pm_cases SET status = 'closed' WHERE status = 'completed'"
        ))
        count = result.rowcount
        await db.commit()
        print(f'Updated {count} PM cases: completed -> closed')


if __name__ == "__main__":
    asyncio.run(migrate())
