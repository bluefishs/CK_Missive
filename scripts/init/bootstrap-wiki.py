#!/usr/bin/env python3
"""
Wiki Bootstrap — 從現有 DB 資料批量建立初始 wiki 頁面

用法:
  cd backend && python ../scripts/init/bootstrap-wiki.py
  cd backend && python ../scripts/init/bootstrap-wiki.py --dry-run
"""
import asyncio
import argparse
import logging
import os
import sys

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


async def bootstrap(dry_run: bool = False):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://ck_user:ck_password_2024@localhost:5434/ck_documents",
    )
    engine = create_async_engine(db_url, pool_size=2)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
    from app.services.wiki_service import get_wiki_service
    svc = get_wiki_service()

    stats = {"agencies": 0, "projects": 0, "vendors": 0}

    async with async_session() as db:
        # 1. Agencies
        rows = (await db.execute(text(
            "SELECT id, name, agency_code, agency_type, address, phone "
            "FROM agencies ORDER BY name LIMIT 100"
        ))).fetchall()
        for r in rows:
            desc = f"**類型**: {r[3] or '未分類'}\n"
            if r[2]:
                desc += f"**機關代碼**: {r[2]}\n"
            if r[4]:
                desc += f"**地址**: {r[4]}\n"
            if r[5]:
                desc += f"**電話**: {r[5]}\n"
            if dry_run:
                logger.info("DRY-RUN: agency %s", r[1])
            else:
                await svc.ingest_entity(
                    name=r[1],
                    entity_type="agency",
                    description=desc,
                    sources=[f"agency:{r[0]}"],
                    tags=["機關", r[3] or "其他"],
                )
            stats["agencies"] += 1

        # 2. Contract Projects
        rows = (await db.execute(text(
            "SELECT id, project_name, case_code, project_code, status, total_amount "
            "FROM contract_projects ORDER BY id LIMIT 100"
        ))).fetchall()
        for r in rows:
            desc = f"**案件代碼**: {r[2] or '–'}\n"
            desc += f"**專案編號**: {r[3] or '–'}\n"
            desc += f"**狀態**: {r[4] or '–'}\n"
            if r[5]:
                desc += f"**金額**: NT$ {r[5]:,.0f}\n"
            if dry_run:
                logger.info("DRY-RUN: project %s", r[1])
            else:
                await svc.ingest_entity(
                    name=r[1] or f"案件-{r[0]}",
                    entity_type="project",
                    description=desc,
                    sources=[f"project:{r[0]}"],
                    tags=["專案", r[4] or "active"],
                )
            stats["projects"] += 1

        # 3. Vendors
        rows = (await db.execute(text(
            "SELECT id, name, vendor_type, tax_id, contact_person "
            "FROM vendors ORDER BY name LIMIT 100"
        ))).fetchall()
        for r in rows:
            desc = f"**類型**: {r[2] or '未分類'}\n"
            if r[3]:
                desc += f"**統編**: {r[3]}\n"
            if r[4]:
                desc += f"**聯絡人**: {r[4]}\n"
            if dry_run:
                logger.info("DRY-RUN: vendor %s", r[1])
            else:
                await svc.ingest_entity(
                    name=r[1],
                    entity_type="vendor",
                    description=desc,
                    sources=[f"vendor:{r[0]}"],
                    tags=["廠商", r[2] or "其他"],
                )
            stats["vendors"] += 1

    # Rebuild index
    if not dry_run:
        counts = await svc.rebuild_index()
        logger.info("Index rebuilt: %s", counts)

    await engine.dispose()
    logger.info("Bootstrap complete: %s", stats)
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap wiki from DB")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()
    asyncio.run(bootstrap(dry_run=args.dry_run))
