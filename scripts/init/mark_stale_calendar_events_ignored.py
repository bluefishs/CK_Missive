# -*- coding: utf-8 -*-
"""歷史案件註記忽略 — 陳年逾期行事曆事件批次標記為 ignored

背景（2026-07-30 覆盤）：
    `document_calendar_events` 有 690 筆過去日期仍為 `pending`（最早 2025-01-02），
    因為公文提醒事件**沒有關閉路徑**——公文辦結了，事件永遠 pending。
    吹哨者每天把其中最老的 20 筆重新掃出並建立通知（無去重）→ 每日 66 筆、
    累積 4094 筆、未讀 4708 → 通知中心實質已死。

    owner 決策（2026-07-30）：歷史案件**註記忽略**（非刪除、非標完成）。

設計：
  * 用 `status='ignored'`（新值）而非 `cancelled` —— 語意誠實：這些不是「被取消」，
    是「不再追蹤」。前端已同步支援此狀態顯示與篩選。
  * **不碰 `google_sync_status`** → 不會觸發 Google Calendar 重新同步
    （同步排程只看 google_sync_status，不看 status）。
  * 走 raw SQL 而非 ORM → 不觸發 before_update 日期正規化監聽器等副作用。
  * **可逆**：執行前把受影響 id 全數寫入 JSON manifest，可用 --revert 還原。
  * 冪等：重跑不會多做事。

用法（容器內）：
    python scripts/init/mark_stale_calendar_events_ignored.py --dry-run
    python scripts/init/mark_stale_calendar_events_ignored.py --apply
    python scripts/init/mark_stale_calendar_events_ignored.py --revert <manifest.json>
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# L52 家族：host 與容器路徑不同（容器內 /app 即 repo 的 backend/，scripts/ 為 bind-mount）
for _cand in (Path("/app"), Path(__file__).resolve().parents[2] / "backend"):
    if (_cand / "app" / "db" / "database.py").exists():
        sys.path.insert(0, str(_cand))
        break

from sqlalchemy import text  # noqa: E402

from app.db.database import AsyncSessionLocal  # noqa: E402

# 與 proactive_triggers.STALE_OVERDUE_DAYS 對齊（逾期分級門檻）
STALE_DAYS = 90

MANIFEST_DIR = (Path("/app") if Path("/app/logs").exists()
                else Path(__file__).resolve().parents[2] / "backend") / "logs"

SELECT_SQL = f"""
    SELECT id, title, end_date::date, status
    FROM document_calendar_events
    WHERE end_date IS NOT NULL
      AND end_date < CURRENT_DATE - INTERVAL '{STALE_DAYS} days'
      AND status = 'pending'
    ORDER BY end_date
"""


async def run(apply: bool) -> int:
    async with AsyncSessionLocal() as db:
        rows = (await db.execute(text(SELECT_SQL))).fetchall()
        print(f"符合條件（逾期 > {STALE_DAYS} 天且仍 pending）: {len(rows)} 筆")
        if rows:
            print("最舊 3 筆:")
            for r in rows[:3]:
                print(f"  id={r[0]} {r[2]} {str(r[1])[:50]}")
            print("最新 3 筆:")
            for r in rows[-3:]:
                print(f"  id={r[0]} {r[2]} {str(r[1])[:50]}")

        if not apply:
            print("\n[DRY-RUN] 未變更任何資料。加 --apply 才會執行。")
            return 0
        if not rows:
            print("無資料可處理（冪等）。")
            return 0

        ids = [r[0] for r in rows]
        MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        manifest = MANIFEST_DIR / f"stale_events_ignored_{stamp}.json"
        manifest.write_text(json.dumps({
            "created_at": datetime.now().isoformat(),
            "stale_days": STALE_DAYS,
            "from_status": "pending",
            "to_status": "ignored",
            "ids": ids,
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\n已寫入可逆 manifest: {manifest}")

        result = await db.execute(
            text("UPDATE document_calendar_events SET status='ignored' "
                 "WHERE id = ANY(:ids) AND status='pending'"),
            {"ids": ids},
        )
        await db.commit()
        print(f"已標記 ignored: {result.rowcount} 筆")
        return result.rowcount


async def revert(manifest_path: str) -> int:
    data = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    ids = data["ids"]
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("UPDATE document_calendar_events SET status=:back "
                 "WHERE id = ANY(:ids) AND status='ignored'"),
            {"ids": ids, "back": data.get("from_status", "pending")},
        )
        await db.commit()
        print(f"已還原: {result.rowcount} 筆 → {data.get('from_status', 'pending')}")
        return result.rowcount


async def mark_old_alerts_read(apply: bool) -> int:
    """把「今日之前」的 proactive_alert 通知標為已讀（不刪除）。

    這些是同一批陳年案件在去重機制上線前、每天重複產生的歷史堆積（4094 筆 / 未讀 4708），
    使通知中心實質不可用。標已讀＝忽略，資料保留、可還原。
    今日（含）的不動，以免蓋掉剛產生的真實告警。
    """
    async with AsyncSessionLocal() as db:
        ids = [r[0] for r in (await db.execute(text(
            "SELECT id FROM system_notifications "
            "WHERE notification_type='proactive_alert' AND is_read = false "
            "AND created_at < CURRENT_DATE"
        ))).fetchall()]
        print(f"今日之前未讀的 proactive_alert: {len(ids)} 筆")
        if not apply:
            print("[DRY-RUN] 未變更。加 --apply 才會執行。")
            return 0
        if not ids:
            return 0

        MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        manifest = MANIFEST_DIR / f"old_alerts_marked_read_{stamp}.json"
        manifest.write_text(json.dumps(
            {"created_at": datetime.now().isoformat(), "ids": ids},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"已寫入可逆 manifest: {manifest}")

        res = await db.execute(
            text("UPDATE system_notifications SET is_read=true, read_at=NOW() "
                 "WHERE id = ANY(:ids) AND is_read=false"),
            {"ids": ids},
        )
        await db.commit()
        print(f"已標為已讀: {res.rowcount} 筆")
        return res.rowcount


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--revert", metavar="MANIFEST")
    ap.add_argument("--alerts-read", action="store_true",
                    help="改為處理歷史 proactive_alert 通知堆積（標已讀，不刪除）")
    args = ap.parse_args()

    if args.revert:
        asyncio.run(revert(args.revert))
    elif args.alerts_read:
        asyncio.run(mark_old_alerts_read(apply=args.apply))
    else:
        asyncio.run(run(apply=args.apply))
