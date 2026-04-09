#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Code Graph Ingestion CLI (代碼圖譜入圖工具)

將 CK_Missive 程式碼結構寫入知識圖譜 (canonical_entities + entity_relationships)。

用法：
  python -m app.scripts.ingest_code_graph --check           # 乾跑：顯示會建立的實體
  python -m app.scripts.ingest_code_graph --ingest          # 執行入圖
  python -m app.scripts.ingest_code_graph --ingest --clean  # 先清除再入圖
  python -m app.scripts.ingest_code_graph --stats           # 顯示統計
  python -m app.scripts.ingest_code_graph --check --skip-schema  # 跳過 DB schema

@version 1.0.0
@date 2026-03-08
"""

import asyncio
import argparse
import logging
import os
import sys

# Ensure project root is on path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("code_graph")


def _get_backend_app_dir() -> Path:
    """Resolve backend/app/ directory."""
    # This script is at backend/app/scripts/ingest_code_graph.py
    return Path(__file__).parent.parent  # -> backend/app/


def _get_frontend_src_dir() -> Path:
    """Resolve frontend/src/ directory."""
    project_root = Path(__file__).parent.parent.parent.parent
    return project_root / "frontend" / "src"


def _get_sync_db_url() -> str:
    """Build synchronous DB URL from env."""
    from dotenv import load_dotenv
    # Load project root .env
    project_root = Path(__file__).parent.parent.parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_user = os.getenv("POSTGRES_USER", "ck_missive")
    db_pass = os.getenv("POSTGRES_PASSWORD", "ck_missive")
    db_name = os.getenv("POSTGRES_DB", "ck_missive")
    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


async def cmd_check(args: argparse.Namespace) -> None:
    """Dry-run: show what would be ingested."""
    from app.db.database import AsyncSessionLocal
    from app.services.ai.graph.code_graph_service import CodeGraphIngestionService

    db_url = None if args.skip_schema else _get_sync_db_url()
    backend_app = _get_backend_app_dir()
    frontend_src = _get_frontend_src_dir() if args.frontend else None

    async with AsyncSessionLocal() as db:
        svc = CodeGraphIngestionService(db)
        result = await svc.check(backend_app, db_url=db_url, frontend_src_dir=frontend_src)

    print("\n=== Code Graph Dry Run ===")
    print(f"Files scanned: {result['files_scanned']}")
    print(f"\nEntities by type:")
    for etype, count in sorted(result["entities_by_type"].items()):
        print(f"  {etype}: {count}")
    print(f"  TOTAL: {result['total_entities']}")
    print(f"\nRelations by type:")
    for rtype, count in sorted(result["relations_by_type"].items()):
        print(f"  {rtype}: {count}")
    print(f"  TOTAL: {result['total_relations']}")
    if result["errors"]:
        print(f"\nErrors: {result['errors']}")


async def cmd_ingest(args: argparse.Namespace) -> None:
    """Execute ingestion pipeline."""
    from app.db.database import AsyncSessionLocal
    from app.services.ai.graph.code_graph_service import CodeGraphIngestionService

    db_url = None if args.skip_schema else _get_sync_db_url()
    backend_app = _get_backend_app_dir()
    frontend_src = _get_frontend_src_dir() if args.frontend else None

    async with AsyncSessionLocal() as db:
        svc = CodeGraphIngestionService(db)
        stats = await svc.ingest(
            backend_app,
            db_url=db_url,
            clean=args.clean,
            frontend_src_dir=frontend_src,
        )

    print("\n=== Code Graph Ingestion Complete ===")
    print(f"  Modules:      {stats['modules']}")
    print(f"  Classes:      {stats['classes']}")
    print(f"  Functions:    {stats['functions']}")
    print(f"  Tables:       {stats['tables']}")
    print(f"  TS Modules:   {stats['ts_modules']}")
    print(f"  TS Components:{stats['ts_components']}")
    print(f"  TS Hooks:     {stats['ts_hooks']}")
    print(f"  Relations:    {stats['relations']}")
    print(f"  Errors:       {stats['errors']}")
    print(f"  Elapsed:      {stats['elapsed_s']}s")


async def cmd_stats(args: argparse.Namespace) -> None:
    """Show code graph statistics from DB."""
    from app.db.database import AsyncSessionLocal
    from app.services.ai.graph.code_graph_service import CodeGraphIngestionService

    async with AsyncSessionLocal() as db:
        svc = CodeGraphIngestionService(db)
        stats = await svc.get_stats()

    print("\n=== Code Graph Statistics ===")
    print(f"\nEntities ({stats['total_entities']} total):")
    for etype, count in sorted(stats["entities"].items()):
        print(f"  {etype}: {count}")
    print(f"\nRelations ({stats['total_relations']} total):")
    for rtype, count in sorted(stats["relations"].items()):
        print(f"  {rtype}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Code Graph Ingestion (代碼圖譜入圖工具)"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="乾跑：顯示會建立的實體數")
    group.add_argument("--ingest", action="store_true", help="執行入圖")
    group.add_argument("--stats", action="store_true", help="顯示已入圖統計")

    parser.add_argument("--clean", action="store_true", help="入圖前先清除既有 code graph 資料")
    parser.add_argument("--skip-schema", action="store_true", help="跳過 DB schema reflection")
    parser.add_argument("--frontend", action="store_true", default=True, help="包含前端 TypeScript/React 提取（預設啟用）")
    parser.add_argument("--no-frontend", action="store_false", dest="frontend", help="跳過前端 TypeScript/React 提取")
    parser.add_argument("-v", "--verbose", action="store_true", help="詳細輸出")

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.check:
        asyncio.run(cmd_check(args))
    elif args.ingest:
        asyncio.run(cmd_ingest(args))
    elif args.stats:
        asyncio.run(cmd_stats(args))


if __name__ == "__main__":
    main()
