#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程式圖譜 orphan 偵測（Code-Graph Stale-Orphan Detector）— DRY-RUN 只報不刪

★ 立法緣起（2026-07-17）：程式圖譜自我優化的前置。code_semantic_duplication_audit
  揭發圖譜累積 stale orphan（tender.py 已縮為 12L wrapper，圖譜卻仍存 tender::
  analytics_dashboard 等舊 entity），污染語意去重查詢。根因＝incremental ingest
  只更新重解析的檔、不修剪已刪除符號，且 last_seen_at 對「未變更檔的存活 entity」
  同樣是舊值 → **不可用 last_seen_at 判 orphan（會誤刪存活）**。

安全信號＝ground truth：對照**實際原始碼**——entity 宣稱的 symbol 是否還定義在
  其 file_path 指的檔案裡。symbol 不存在 or 檔案不存在 → orphan（高信心）。

範圍：僅 Python code entity（py_function/py_class/api_endpoint/service/repository/
  schema），symbol 可靠 AST/regex 偵測。ts_* 偵測較複雜，暫不納（未來擴充）。

★ 本工具**只報告不刪除**。實際 prune（soft-delete via valid_to / 硬刪）須：
  ①owner 看過本報告確認範圍合理 ②獨立授權 ③soft-delete + grace period 優先。

host 側執行（read-only 查 KG + 讀 source）。cp950 韌性。
用法：
    python scripts/checks/code_graph_orphan_audit.py            # 摘要
    python scripts/checks/code_graph_orphan_audit.py --list     # 列全部 orphan
    python scripts/checks/code_graph_orphan_audit.py --strict   # 超 baseline exit 1
"""
from __future__ import annotations

import argparse
import asyncio
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

try:
    import asyncpg
except ImportError:
    print("需要 asyncpg", file=sys.stderr)
    sys.exit(0)

ROOT = Path(__file__).resolve().parents[2]
DSN = "postgresql://ck_user:ck_password_2024@localhost:5434/ck_documents"

PY_TYPES = ("py_function", "py_class", "api_endpoint", "service", "repository", "schema")
# orphan 數 baseline：2026-07-17 首跑 2032（主因 Wave 1-8 DDD 檔案搬移舊路徑未修剪）。
# 設 2100 略高於現況＝report-only 不誤報既有 backlog；**prune 後應大幅下降**，
# 屆時 owner 調低 baseline 以捕捉新 orphan（新遷移未同步圖譜）。
BASE_ORPHANS = 2100


def normalize_path(fpath: str) -> Path | None:
    """host-abs (D:/CKProject/CK_Missive/...) 或 container (/app/...) → repo 相對絕對路徑。"""
    if not fpath:
        return None
    fpath = fpath.replace("\\", "/")
    if "CK_Missive/" in fpath:
        rel = fpath.split("CK_Missive/", 1)[1]
    elif fpath.startswith("/app/"):
        rel = "backend/" + fpath[len("/app/"):]
    elif fpath.startswith("backend/") or fpath.startswith("frontend/"):
        rel = fpath
    else:
        return None
    return ROOT / rel


def symbol_defined(file_text: str, symbol: str) -> bool:
    """symbol 是否以 def/async def/class 定義於檔（regex，orphan 偵測足夠）。"""
    pat = re.compile(rf"^\s*(async\s+def|def|class)\s+{re.escape(symbol)}\b", re.M)
    return bool(pat.search(file_text))


async def collect() -> list[dict]:
    conn = await asyncpg.connect(DSN)
    try:
        rows = await conn.fetch(f"""
            SELECT id, canonical_name,
                   description::jsonb->>'file_path' AS fpath
            FROM canonical_entities
            WHERE graph_domain='code'
              AND entity_type IN {PY_TYPES}
              AND description IS NOT NULL
        """)
    finally:
        await conn.close()

    # 依檔分組，每檔只讀一次
    file_cache: dict[Path, str | None] = {}
    orphans = []
    for r in rows:
        name = r["canonical_name"]
        if "::" not in name:
            continue
        # symbol 可能是 method（ClassName.method）→ 實際定義名是最後一個點分量
        symbol = name.split("::")[-1].split(".")[-1]
        if not symbol or symbol == "__init__":
            continue  # __init__ 等 dunder 幾乎必存在，跳過避免噪音
        p = normalize_path(r["fpath"] or "")
        if p is None:
            continue  # 無法解析路徑，保守跳過（不判 orphan）
        if p not in file_cache:
            try:
                file_cache[p] = p.read_text(encoding="utf-8", errors="ignore") if p.exists() else None
            except Exception:
                file_cache[p] = None
        text = file_cache[p]
        if text is None:
            orphans.append({"name": name, "reason": "file-missing", "path": str(p)})
        elif not symbol_defined(text, symbol):
            orphans.append({"name": name, "reason": "symbol-absent", "path": str(p)})
    return orphans


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    print("=" * 66)
    print("程式圖譜 orphan 偵測（ground truth 對照 source，DRY-RUN 只報不刪）")
    print("=" * 66)
    try:
        orphans = asyncio.run(collect())
    except Exception as e:
        print(f"[SKIP] DB 不可達或查詢失敗：{e}")
        return 0

    missing = [o for o in orphans if o["reason"] == "file-missing"]
    absent = [o for o in orphans if o["reason"] == "symbol-absent"]
    print(f"\nPython code entity orphan：{len(orphans)}")
    print(f"  - 檔案不存在（file-missing）：{len(missing)}")
    print(f"  - symbol 已刪（symbol-absent）：{len(absent)}")

    # 依模組聚合 top（看哪些模組漂移最重）
    from collections import Counter
    mods = Counter(o["name"].split("::")[0] for o in orphans)
    print("\n漂移最重的模組 top 12（module → orphan 數）：")
    for mod, n in mods.most_common(12):
        print(f"  {n:4d}  {mod}")

    if args.list:
        print("\n--- 全部 orphan ---")
        for o in orphans:
            print(f"  [{o['reason']}] {o['name']}")

    print("\n" + "=" * 66)
    print(f"orphan {len(orphans)} (baseline<= {BASE_ORPHANS})")
    print("→ 只報不刪。實際 prune 須 owner 確認範圍 + 獨立授權 + soft-delete 優先。")
    if len(orphans) > BASE_ORPHANS and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
