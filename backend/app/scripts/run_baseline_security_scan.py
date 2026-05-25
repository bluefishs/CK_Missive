"""Run a baseline SecurityScanner full scan and print the result.

Usage (inside backend container):
    python -m app.scripts.run_baseline_security_scan
"""

import asyncio
import sys


async def main() -> None:
    sys.path.insert(0, "/app")
    from app.db.database import AsyncSessionLocal
    from app.services.security.scanner import SecurityScanner

    async with AsyncSessionLocal() as db:
        scanner = SecurityScanner(db, project_name="CK_Missive")
        result = await scanner.run_full_scan()
        print("=" * 60)
        print("BASELINE SCAN RESULT")
        print("=" * 60)
        print(f"Scan ID:        {result['scan_id']}")
        print(f"Total issues:   {result['total_issues']}")
        print(f"Duration:       {result['duration_seconds']}s")
        print(f"Critical:       {result['critical']}")
        print(f"High:           {result['high']}")
        print(f"Medium:         {result['medium']}")
        print(f"Low:            {result['low']}")
        print(f"Info:           {result['info']}")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
