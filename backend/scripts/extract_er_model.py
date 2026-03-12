#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ER Model 本地提取腳本 — 從開發庫 information_schema 讀取表結構

功能：
  1. 讀取 PostgreSQL information_schema 取得完整表結構
  2. 生成 Mermaid ER Diagram 語法 → docs/er-diagram.md
  3. 生成 JSON 元數據 → docs/er-model.json (供 GitNexus / Agent 讀取)
  4. 可選：寫入 canonical_entities 作為 code_graph 的一部分

用法：
  python scripts/extract_er_model.py                     # 生成 Mermaid + JSON
  python scripts/extract_er_model.py --ingest            # 同時寫入圖譜
  python scripts/extract_er_model.py --tables users,docs  # 僅指定表

@version 1.0.0
@date 2026-03-11
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
DOCS_DIR = PROJECT_ROOT / "docs"

sys.path.insert(0, str(BACKEND_DIR))


def _get_db_url() -> str:
    """Build sync DB URL from .env."""
    from dotenv import load_dotenv

    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_HOST_PORT", os.getenv("POSTGRES_PORT", "5434"))
    db_user = os.getenv("POSTGRES_USER", "ck_missive")
    db_pass = os.getenv("POSTGRES_PASSWORD", "ck_missive")
    db_name = os.getenv("POSTGRES_DB", "ck_documents")
    return f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"


def extract_schema(db_url: str, table_filter: list[str] | None = None) -> dict[str, Any]:
    """Extract full schema from information_schema."""
    from sqlalchemy import create_engine, text

    engine = create_engine(db_url)
    schema: dict[str, Any] = {"tables": {}, "enums": []}

    with engine.connect() as conn:
        # 1. Get all tables
        tables_sql = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        all_tables = [r[0] for r in conn.execute(tables_sql)]

        if table_filter:
            all_tables = [t for t in all_tables if t in table_filter]

        for table_name in all_tables:
            # Skip alembic
            if table_name == "alembic_version":
                continue

            # 2. Columns
            cols_sql = text("""
                SELECT column_name, data_type, is_nullable,
                       column_default, character_maximum_length,
                       udt_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = :tbl
                ORDER BY ordinal_position
            """)
            columns = []
            for row in conn.execute(cols_sql, {"tbl": table_name}):
                col = {
                    "name": row[0],
                    "type": row[1].upper(),
                    "nullable": row[2] == "YES",
                    "default": row[3],
                    "udt_name": row[5],
                }
                if row[4]:
                    col["max_length"] = row[4]
                # Map user-defined types
                if col["type"] == "USER-DEFINED":
                    col["type"] = row[5].upper()
                elif col["type"] == "ARRAY":
                    col["type"] = f"{row[5].upper()}[]"
                columns.append(col)

            # 3. Primary key
            pk_sql = text("""
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = 'public'
                  AND tc.table_name = :tbl
                  AND tc.constraint_type = 'PRIMARY KEY'
                ORDER BY kcu.ordinal_position
            """)
            pk_cols = [r[0] for r in conn.execute(pk_sql, {"tbl": table_name})]

            # 4. Foreign keys
            fk_sql = text("""
                SELECT kcu.column_name,
                       ccu.table_name AS ref_table,
                       ccu.column_name AS ref_column
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                JOIN information_schema.constraint_column_usage ccu
                  ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_schema = 'public'
                  AND tc.table_name = :tbl
                  AND tc.constraint_type = 'FOREIGN KEY'
            """)
            foreign_keys = []
            for row in conn.execute(fk_sql, {"tbl": table_name}):
                foreign_keys.append({
                    "column": row[0],
                    "ref_table": row[1],
                    "ref_column": row[2],
                })

            # 5. Indexes
            idx_sql = text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE schemaname = 'public' AND tablename = :tbl
            """)
            indexes = []
            for row in conn.execute(idx_sql, {"tbl": table_name}):
                indexes.append({
                    "name": row[0],
                    "definition": row[1],
                })

            # 6. Unique constraints
            uq_sql = text("""
                SELECT tc.constraint_name, kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                WHERE tc.table_schema = 'public'
                  AND tc.table_name = :tbl
                  AND tc.constraint_type = 'UNIQUE'
            """)
            unique_constraints: dict[str, list[str]] = {}
            for row in conn.execute(uq_sql, {"tbl": table_name}):
                unique_constraints.setdefault(row[0], []).append(row[1])

            # 7. Row count estimate
            count_sql = text("""
                SELECT reltuples::bigint
                FROM pg_class
                WHERE relname = :tbl
            """)
            row_count = conn.execute(count_sql, {"tbl": table_name}).scalar() or 0

            schema["tables"][table_name] = {
                "columns": columns,
                "primary_key": pk_cols,
                "foreign_keys": foreign_keys,
                "indexes": indexes,
                "unique_constraints": unique_constraints,
                "row_count_estimate": int(row_count),
            }

        # 8. Get custom enum types
        enum_sql = text("""
            SELECT t.typname, e.enumlabel
            FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            ORDER BY t.typname, e.enumsortorder
        """)
        enums: dict[str, list[str]] = {}
        for row in conn.execute(enum_sql):
            enums.setdefault(row[0], []).append(row[1])
        schema["enums"] = [{"name": k, "values": v} for k, v in enums.items()]

    engine.dispose()
    return schema


def generate_mermaid(schema: dict[str, Any]) -> str:
    """Convert schema to Mermaid erDiagram syntax."""
    lines = ["erDiagram"]

    # Type mapping for Mermaid (keep concise)
    type_map = {
        "INTEGER": "int",
        "BIGINT": "bigint",
        "SMALLINT": "smallint",
        "BOOLEAN": "bool",
        "CHARACTER VARYING": "varchar",
        "TEXT": "text",
        "TIMESTAMP WITHOUT TIME ZONE": "timestamp",
        "TIMESTAMP WITH TIME ZONE": "timestamptz",
        "DATE": "date",
        "DOUBLE PRECISION": "float8",
        "REAL": "float4",
        "NUMERIC": "numeric",
        "UUID": "uuid",
        "JSONB": "jsonb",
        "JSON": "json",
        "BYTEA": "bytea",
        "VECTOR": "vector",
    }

    # Collect FK relationships
    relationships: list[str] = []
    for table_name, table_info in schema["tables"].items():
        for fk in table_info["foreign_keys"]:
            ref = fk["ref_table"]
            if ref in schema["tables"]:
                relationships.append(
                    f'    {ref} ||--o{{ {table_name} : "{fk["column"]}"'
                )

    # Deduplicate relationships
    seen = set()
    for rel in relationships:
        if rel not in seen:
            seen.add(rel)
            lines.append(rel)

    lines.append("")

    # Table definitions
    for table_name, table_info in sorted(schema["tables"].items()):
        lines.append(f"    {table_name} {{")
        pk_set = set(table_info["primary_key"])
        fk_cols = {fk["column"] for fk in table_info["foreign_keys"]}

        for col in table_info["columns"]:
            mtype = type_map.get(col["type"], col["type"].lower())
            markers = []
            if col["name"] in pk_set:
                markers.append("PK")
            if col["name"] in fk_cols:
                markers.append("FK")
            if not col["nullable"] and col["name"] not in pk_set:
                markers.append("NOT NULL")

            marker_str = f' "{",".join(markers)}"' if markers else ""
            lines.append(f'        {mtype} {col["name"]}{marker_str}')
        lines.append("    }")

    return "\n".join(lines)


def save_outputs(
    schema: dict[str, Any],
    mermaid: str,
    docs_dir: Path,
) -> tuple[Path, Path]:
    """Save Mermaid markdown and JSON to docs/."""
    docs_dir.mkdir(parents=True, exist_ok=True)

    # Mermaid ER Diagram
    mermaid_path = docs_dir / "er-diagram.md"
    mermaid_content = f"""# ER Diagram — CK_Missive 資料庫結構

> 自動生成，請勿手動編輯。執行 `python backend/scripts/extract_er_model.py` 重新生成。

```mermaid
{mermaid}
```

## 統計

| 指標 | 數值 |
|------|------|
| 總表數 | {len(schema["tables"])} |
| 總欄位數 | {sum(len(t["columns"]) for t in schema["tables"].values())} |
| 外鍵關聯 | {sum(len(t["foreign_keys"]) for t in schema["tables"].values())} |
| 自訂列舉型別 | {len(schema["enums"])} |
"""
    mermaid_path.write_text(mermaid_content, encoding="utf-8")

    # JSON metadata (for GitNexus / Agent)
    json_path = docs_dir / "er-model.json"
    json_path.write_text(
        json.dumps(schema, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8",
    )

    return mermaid_path, json_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="ER Model 本地提取 — 讀取 information_schema 生成 Mermaid + JSON"
    )
    parser.add_argument(
        "--tables", type=str, default=None,
        help="僅提取指定表（逗號分隔），例如 --tables users,official_documents",
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="輸出目錄（預設 docs/）",
    )
    parser.add_argument(
        "--ingest", action="store_true",
        help="同時寫入 canonical_entities 作為 code_graph 的一部分",
    )
    parser.add_argument(
        "--diff", action="store_true",
        help="比較現有 er-model.json 與實際 DB schema 差異",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ER Model 本地提取工具")
    print("=" * 60)

    db_url = _get_db_url()
    print(f"\n連線: {db_url.split('@')[1] if '@' in db_url else db_url}")

    table_filter = args.tables.split(",") if args.tables else None
    if table_filter:
        print(f"篩選表: {table_filter}")

    # Extract
    print("\n提取 information_schema...")
    schema = extract_schema(db_url, table_filter)
    print(f"  表: {len(schema['tables'])}")
    print(f"  欄位: {sum(len(t['columns']) for t in schema['tables'].values())}")
    print(f"  外鍵: {sum(len(t['foreign_keys']) for t in schema['tables'].values())}")
    print(f"  列舉: {len(schema['enums'])}")

    # Generate Mermaid
    print("\n生成 Mermaid ER Diagram...")
    mermaid = generate_mermaid(schema)

    # Save
    output_dir = Path(args.output_dir) if args.output_dir else DOCS_DIR
    mermaid_path, json_path = save_outputs(schema, mermaid, output_dir)
    print(f"\n輸出:")
    print(f"  Mermaid: {mermaid_path}")
    print(f"  JSON:    {json_path}")

    # B7: Diff mode — compare with existing er-model.json
    if args.diff:
        existing_json = output_dir / "er-model.json"
        if existing_json.exists():
            old_schema = json.loads(existing_json.read_text(encoding="utf-8"))
            old_tables = set(old_schema.get("tables", {}).keys())
            new_tables = set(schema["tables"].keys())

            added_tables = new_tables - old_tables
            removed_tables = old_tables - new_tables
            common_tables = old_tables & new_tables

            print("\n=== ER Schema Diff ===")
            if added_tables:
                print(f"\n  新增表 ({len(added_tables)}):")
                for t in sorted(added_tables):
                    print(f"    + {t}")
            if removed_tables:
                print(f"\n  移除表 ({len(removed_tables)}):")
                for t in sorted(removed_tables):
                    print(f"    - {t}")

            col_changes = 0
            for tbl in sorted(common_tables):
                old_cols = {c["name"] for c in old_schema["tables"][tbl].get("columns", [])}
                new_cols = {c["name"] for c in schema["tables"][tbl].get("columns", [])}
                added_cols = new_cols - old_cols
                removed_cols = old_cols - new_cols
                if added_cols or removed_cols:
                    col_changes += 1
                    print(f"\n  表 {tbl} 欄位變更:")
                    for c in sorted(added_cols):
                        print(f"    + {c}")
                    for c in sorted(removed_cols):
                        print(f"    - {c}")

            if not added_tables and not removed_tables and col_changes == 0:
                print("\n  無變更 — Schema 與 er-model.json 一致")
            else:
                print(f"\n  總計: +{len(added_tables)} 表, -{len(removed_tables)} 表, {col_changes} 表有欄位變更")
        else:
            print(f"\n找不到 {existing_json}，無法比較差異。請先執行一次不帶 --diff 的提取。")

        if not args.ingest:
            print("\n完成！")
            return

    # Optional: ingest into code_graph
    if args.ingest:
        import asyncio
        sys.path.insert(0, str(BACKEND_DIR))
        os.chdir(str(BACKEND_DIR))

        async def _do_ingest():
            from app.db.database import AsyncSessionLocal
            from app.services.ai.code_graph_service import SchemaReflector, CodeGraphIngestionService

            reflector = SchemaReflector()
            schema_ents, schema_rels = reflector.reflect_tables(db_url)
            print(f"\n入圖: {len(schema_ents)} tables, {len(schema_rels)} FK relations")

            async with AsyncSessionLocal() as db:
                svc = CodeGraphIngestionService(db)
                entity_map = await svc._upsert_entities(
                    schema_ents,
                    __import__("app.extended.models", fromlist=["CanonicalEntity"]).CanonicalEntity,
                )
                from app.extended.models import EntityRelationship
                rel_count = await svc._recreate_relations(
                    schema_rels, entity_map, EntityRelationship,
                )
                await db.commit()
                print(f"  寫入 {len(entity_map)} entities, {rel_count} relations")

        asyncio.run(_do_ingest())

    print("\n完成！")


if __name__ == "__main__":
    main()
