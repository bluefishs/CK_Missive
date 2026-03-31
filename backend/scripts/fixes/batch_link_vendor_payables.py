"""批次配對 ERPVendorPayable → PartnerVendor

找出所有 vendor_id IS NULL 的 ERPVendorPayable，
依序嘗試精確/包含比對 PartnerVendor，
無法配對者自動新建 PartnerVendor (vendor_type='subcontractor')。

Usage:
    # Dry-run（預設，只顯示配對結果）
    python scripts/fixes/batch_link_vendor_payables.py

    # 實際執行
    python scripts/fixes/batch_link_vendor_payables.py --execute
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select, update  # noqa: E402
from app.db.database import AsyncSessionLocal  # noqa: E402
from app.extended.models.core import PartnerVendor  # noqa: E402
from app.extended.models.erp import ERPVendorPayable  # noqa: E402


async def batch_link(dry_run: bool = True):
    async with AsyncSessionLocal() as db:
        # 1. Get distinct unlinked vendor names
        result = await db.execute(
            select(ERPVendorPayable.vendor_name)
            .where(ERPVendorPayable.vendor_id.is_(None))
            .distinct()
        )
        unlinked_names = [r[0] for r in result.all() if r[0]]

        if not unlinked_names:
            print("No unlinked ERPVendorPayable records found.")
            return

        # 2. Get all existing partners (both types for matching)
        result = await db.execute(select(PartnerVendor))
        partners = result.scalars().all()
        partner_map = {p.vendor_name: p.id for p in partners}

        matched: list[tuple[str, int, str]] = []
        to_create: list[str] = []

        for name in sorted(unlinked_names):
            # Exact match
            if name in partner_map:
                matched.append((name, partner_map[name], "exact"))
                continue

            # Contains match (payable name in partner name, or vice versa)
            found = False
            for pname, pid in partner_map.items():
                if name in pname or pname in name:
                    matched.append((name, pid, f"partial: '{pname}'"))
                    found = True
                    break

            if not found:
                to_create.append(name)

        # Print summary
        print("=" * 50)
        print(f"  Unlinked vendor names : {len(unlinked_names)}")
        print(f"  Matched (existing)    : {len(matched)}")
        print(f"  To create (new)       : {len(to_create)}")
        print("=" * 50)
        print()

        if matched:
            print("--- Matched ---")
            for name, vid, match_type in matched:
                print(f"  [{match_type}] {name} -> vendor_id={vid}")
            print()

        if to_create:
            print("--- To Create ---")
            for name in to_create:
                print(f"  NEW: {name}")
            print()

        if dry_run:
            print("[DRY RUN] No changes made. Use --execute to apply.")
            return

        # 3. Create new PartnerVendor records
        for name in to_create:
            new_vendor = PartnerVendor(
                vendor_name=name,
                vendor_type="subcontractor",
            )
            db.add(new_vendor)
            await db.flush()
            matched.append((name, new_vendor.id, "created"))
            print(f"  CREATED: {name} -> vendor_id={new_vendor.id}")

        # 4. Update ERPVendorPayable records
        updated_total = 0
        for name, vid, _ in matched:
            result = await db.execute(
                update(ERPVendorPayable)
                .where(
                    ERPVendorPayable.vendor_name == name,
                    ERPVendorPayable.vendor_id.is_(None),
                )
                .values(vendor_id=vid)
            )
            updated_total += result.rowcount

        await db.commit()
        print(f"\nUpdated {updated_total} ERPVendorPayable records.")


if __name__ == "__main__":
    execute = "--execute" in sys.argv
    asyncio.run(batch_link(dry_run=not execute))
