#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
程式圖譜全掃 reconcile（mark-and-sweep）— 根治 stale orphan（含搬移型）

★ 授權執行（2026-07-17，owner 選 A）：承 orphan prune 保守批（62 真刪除），剩
  1970 搬移型（symbol 在新路徑）。逐一重指脆弱 → 正解＝全掃 mark-and-sweep：
  1. 記 sweep_start = now()
  2. 全掃 ingest（incremental=False）：對所有現存 symbol upsert，每筆 stamp
     last_seen_at=now()、**保留 embedding**（on_conflict 不動 embedding 欄）
  3. sweep：刪 code entity 中 last_seen_at < sweep_start 者（＝本輪全掃未見＝stale）

安全閘（防部分失敗誤刪存活）：
  - 全掃後統計「本輪 stamp（last_seen_at >= sweep_start）」數量，< MIN_STAMPED 則 ABORT
  - --apply 前備份被刪列（CSV）；今晨全庫 backup 作雙保險

★ 必須在【容器內】執行（用 app 的 ingest service + DB）：
    docker exec ck_missive_backend python /app/scripts/code_graph_reconcile.py            # DRY-RUN
    docker exec ck_missive_backend python /app/scripts/code_graph_reconcile.py --apply    # 全掃+sweep
  （腳本需先 docker cp 進容器，或 mount；見執行說明）
"""
from __future__ import annotations

import argparse
import asyncio
import sys

# ⚠️ backend 容器【無 frontend/src】→ 全掃無法 stamp ts_* 前端 entity（存活但會誤判 stale）。
#    故 sweep **僅限 Python 型**（容器有 backend 源可 stamp）；ts_* 留待前端可見環境另 reconcile。
PY_TYPES = "('py_function','py_class','py_module','api_endpoint','service','repository','schema')"
MIN_STAMPED = 3500  # 全掃後至少 stamp 這麼多【Python】entity 才准 sweep（現源 ~7200）


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    from app.db.database import async_session_maker
    from app.services.ai.graph.code_graph_service import CodeGraphIngestionService
    from app.core.paths import BACKEND_DIR, FRONTEND_DIR
    from sqlalchemy import text

    print("=" * 60)
    print("程式圖譜全掃 reconcile（mark-and-sweep）")
    print("=" * 60)

    async with async_session_maker() as db:
        # 1. sweep_start（naive timestamp 對齊 last_seen_at 欄型；避 tz-aware 比較錯誤）
        sweep_start = await db.scalar(text("SELECT now()::timestamp without time zone"))
        before = await db.scalar(text("SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='code'"))
        print(f"\nsweep_start={sweep_start}  code entity（前）={before}")

        # 2. 全掃 ingest
        print("\n執行全掃 ingest（incremental=False，保留 embedding）...")
        backend_dir = BACKEND_DIR / "app"
        frontend_dir = FRONTEND_DIR / "src"
        service = CodeGraphIngestionService(db)
        stats = await service.ingest(
            backend_app_dir=backend_dir,
            incremental=False,
            frontend_src_dir=frontend_dir if frontend_dir.exists() else None,
        )
        await db.commit()
        print(f"  ingest stats: modules={stats.get('modules',0)} classes={stats.get('classes',0)} "
              f"functions={stats.get('functions',0)}")

        # 3. 安全閘：本輪 stamp 數量（僅計 Python 型，因 ts_* 容器內無源不能 stamp）
        stamped = await db.scalar(text(
            f"SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='code' "
            f"AND entity_type IN {PY_TYPES} AND last_seen_at >= :ts"
        ), {"ts": sweep_start})
        stale = await db.scalar(text(
            f"SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='code' "
            f"AND entity_type IN {PY_TYPES} AND (last_seen_at < :ts OR last_seen_at IS NULL)"
        ), {"ts": sweep_start})
        print(f"\n本輪 stamp（Python live）={stamped}  Python 未見（stale 候選）={stale}")
        print("  （ts_* 前端型不納入 sweep：容器無 frontend 源）")

        if stamped < MIN_STAMPED:
            print(f"\n⛔ ABORT：Python stamp {stamped} < 安全閾 {MIN_STAMPED}"
                  f"（全掃可能部分失敗）→ 不 sweep，避免誤刪存活。")
            return 1

        # embedding 保留驗證
        emb = await db.scalar(text(
            "SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='code' AND embedding IS NOT NULL"))
        print(f"  embedding 保留（live+stale 合計仍有）={emb}")

        if not args.apply:
            print("\n" + "=" * 60)
            print(f"DRY-RUN：全掃已 stamp {stamped} live；stale 候選 {stale} 待 sweep。")
            print("--apply 才會備份 + 刪除 stale。（本次全掃 upsert 已 commit，無害）")
            return 0

        # 4. 備份 stale 列（CSV）
        import csv
        import os
        bdir = "/tmp/code_graph_prune"
        os.makedirs(bdir, exist_ok=True)
        rows = await db.execute(text(
            f"SELECT id, canonical_name, entity_type FROM canonical_entities "
            f"WHERE graph_domain='code' AND entity_type IN {PY_TYPES} "
            f"AND (last_seen_at < :ts OR last_seen_at IS NULL)"
        ), {"ts": sweep_start})
        rows = rows.all()
        bpath = f"{bdir}/reconcile_stale_20260717.csv"
        with open(bpath, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "canonical_name", "entity_type"])
            for r in rows:
                w.writerow([r[0], r[1], r[2]])
        print(f"\n備份 {len(rows)} stale 列 → {bpath}")

        # 5. sweep（僅 Python 型；cascade 自動處理關聯）
        result = await db.execute(text(
            f"DELETE FROM canonical_entities WHERE graph_domain='code' AND entity_type IN {PY_TYPES} "
            f"AND (last_seen_at < :ts OR last_seen_at IS NULL)"
        ), {"ts": sweep_start})
        await db.commit()
        after = await db.scalar(text("SELECT COUNT(*) FROM canonical_entities WHERE graph_domain='code'"))
        print(f"  已 sweep：{result.rowcount}  code entity（後）={after}")
        print(f"\n✅ 完成。全掃 reconcile：{before} → {after}（sweep {result.rowcount} stale）。")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
