# -*- coding: utf-8 -*-
"""異地備份完整性稽核 —— 問的是「現在真的還原得回來嗎」（2026-08-10）。

## 為什麼要有這一支

2026-08-10 owner 問「確認 NAS 有完整備份」，查下去答案是**沒有**：

    公文資料  → NAS 30 份 dump          ✓
    公文附件  → **一份都沒有**            ✗  異地同步腳本第 97 行寫死 robocopy "*.sql"
    金鑰憑證  → **一份都沒有**            ✗  .env 95 項含 15 把金鑰，只有 D 槽一份

而本機那份附件備份也早就停了：`attachments_latest` 最後更新 2026-05-18，
**84 天沒動過**，落後 317 檔 / 362MB —— 根因是 scheduler 裡根本沒有附件備份的排程，
它只能從 /admin/backup 手動觸發，而最後一次按是 05-18。
所以在那天之前，那 317 個附件在全世界只有一份。

三個缺口沒有任何一個會報錯。`remote_backup.json` 顯示 `last_sync_result: success`、
Windows 排程 `LastTaskResult=0`、NAS 上檔案一天比一天多 —— **全都是綠的**。
因為沒有任何人在問「備份的東西夠不夠還原出一套能跑的系統」。

## 判準：四類缺一不可

  1. 資料庫 dump   —— 份數、最新一份的新鮮度、**尾端完整性**
  2. 里程碑快照     —— 存在即可（不輪替，是回得去某時間點的錨點）
  3. 公文附件       —— 涵蓋率（本機每一個檔都要在 NAS 有對應）
  4. 金鑰與憑證     —— 加密檔的新鮮度

**尾端完整性是刻意加的**：截斷的 dump 症狀是「檔案在、大小看起來也還好、
還原到一半才斷」。只看檔案存不存在、大小合不合理，抓不到它。
pg_dump 的輸出結尾一定是 `PostgreSQL database dump complete`。

## 這支不做什麼

不做完整還原測試（500MB × 每週太貴）。完整還原測試是**月度**動作，
程序寫在 `docs/runbooks/disaster-recovery.md`。
本檔只回答「素材齊不齊、有沒有腐爛」，不回答「還原出來的系統對不對」——
後者 2026-08-10 實測過一次，發現兩個缺陷（見該 runbook）。

## 用法

  python scripts/checks/offsite_backup_completeness_audit.py
  python scripts/checks/offsite_backup_completeness_audit.py --self-test
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # pragma: no cover
    pass

REPO = Path(__file__).resolve().parents[2]
NAS = Path(r"\\CKNAS\CK_Project\#Project_data")

DB_DIR = NAS / "missive_databsae"
MS_DIR = DB_DIR / "_milestones"
ATTACH_DIR = NAS / "missive_attachments"
SECRETS_DIR = NAS / "missive_secrets"
LOCAL_UPLOADS = REPO / "backend" / "uploads"

MIN_DUMPS = 20            # 保留 30 份，低於 20 代表輪替或同步出問題
DUMP_MAX_AGE_H = 30       # 每日 02:00 產、03:00 同步 → 逾 30h 就是漏了一天
SECRETS_MAX_AGE_H = 30
DUMP_TAIL_MARKER = b"PostgreSQL database dump complete"


def _age_hours(p: Path) -> float:
    return (datetime.now() - datetime.fromtimestamp(p.stat().st_mtime)).total_seconds() / 3600


def check_db(reds: list[str], rows: list[str]) -> None:
    if not DB_DIR.exists():
        reds.append(f"資料庫備份目錄不存在: {DB_DIR}")
        rows.append("  [RED  ] 資料庫 dump        目錄不存在")
        return
    dumps = sorted(DB_DIR.glob("ck_missive_backup_*.sql"), key=lambda p: p.stat().st_mtime)
    if len(dumps) < MIN_DUMPS:
        reds.append(f"資料庫 dump 只有 {len(dumps)} 份（低於 {MIN_DUMPS}）")
    if not dumps:
        rows.append("  [RED  ] 資料庫 dump        0 份")
        return
    latest = dumps[-1]
    age = _age_hours(latest)
    if age > DUMP_MAX_AGE_H:
        reds.append(f"最新 dump 已 {age:.1f}h 未更新（{latest.name}）")

    # 尾端完整性：截斷的 dump 大小看起來正常，只有結尾看得出來
    tail_ok = False
    try:
        with open(latest, "rb") as fh:
            fh.seek(max(0, latest.stat().st_size - 4096))
            tail_ok = DUMP_TAIL_MARKER in fh.read()
    except OSError as exc:
        reds.append(f"無法讀取最新 dump 尾端: {exc}")
    if not tail_ok:
        reds.append(f"最新 dump 尾端缺少完成標記 → 可能截斷（{latest.name}）")

    size_mb = latest.stat().st_size / 1024 / 1024
    rows.append(f"  [{'GREEN' if tail_ok and age <= DUMP_MAX_AGE_H else 'RED  '}] "
                f"資料庫 dump        {len(dumps)} 份｜最新 {latest.name[-19:-4]} "
                f"({size_mb:.0f}MB, {age:.1f}h 前)｜尾端{'完整' if tail_ok else '不完整'}")


def check_milestones(reds: list[str], rows: list[str]) -> None:
    if not MS_DIR.exists():
        reds.append("里程碑快照目錄不存在（PREUPGRADE / pre_pm2 等回得去的錨點）")
        rows.append("  [RED  ] 里程碑快照        目錄不存在")
        return
    files = [p for p in MS_DIR.iterdir() if p.is_file()]
    if not files:
        reds.append("里程碑快照目錄是空的")
    total_mb = sum(p.stat().st_size for p in files) / 1024 / 1024
    rows.append(f"  [{'GREEN' if files else 'RED  '}] 里程碑快照        "
                f"{len(files)} 份 / {total_mb:.0f}MB")


def check_attachments(reds: list[str], rows: list[str]) -> None:
    if not LOCAL_UPLOADS.exists():
        reds.append(f"本機附件目錄不存在: {LOCAL_UPLOADS}")
        return
    if not ATTACH_DIR.exists():
        reds.append(f"附件異地目錄不存在: {ATTACH_DIR} —— 附件沒有任何異地備份")
        rows.append("  [RED  ] 公文附件          異地目錄不存在")
        return
    local = sum(1 for _ in LOCAL_UPLOADS.rglob("*") if _.is_file())
    archive_dir = ATTACH_DIR / "_longname_archive"
    remote = 0
    archived_zips = 0
    for p in ATTACH_DIR.rglob("*"):
        if not p.is_file():
            continue
        if archive_dir in p.parents:
            archived_zips += 1
        else:
            remote += 1
    # 長檔名（>255 bytes，中文約 85 字）存不進 Linux/Samba，改打包上傳。
    # 因此本機檔數 > NAS 直接檔數是預期的，差額必須被 zip 覆蓋。
    gap = local - remote
    ok = gap == 0 or (gap > 0 and archived_zips > 0)
    if not ok:
        reds.append(f"附件涵蓋不全：本機 {local} 檔、NAS {remote} 檔、缺 {gap} 且無打包封存")
    rows.append(f"  [{'GREEN' if ok else 'RED  '}] 公文附件          "
                f"本機 {local}｜NAS 直接 {remote}｜打包封存 {archived_zips} "
                f"({'涵蓋完整' if ok else f'缺 {gap}'})")


def check_secrets(reds: list[str], rows: list[str]) -> None:
    if not SECRETS_DIR.exists():
        reds.append(f"金鑰異地目錄不存在: {SECRETS_DIR} —— "
                    "沒有它，資料還原回來系統仍然起不來")
        rows.append("  [RED  ] 金鑰與憑證        異地目錄不存在")
        return
    encs = sorted(SECRETS_DIR.glob("secrets_*.enc"), key=lambda p: p.stat().st_mtime)
    if not encs:
        reds.append("金鑰異地目錄是空的")
        rows.append("  [RED  ] 金鑰與憑證        0 份")
        return
    latest = encs[-1]
    age = _age_hours(latest)
    if age > SECRETS_MAX_AGE_H:
        reds.append(f"最新金鑰備份已 {age:.1f}h 未更新（{latest.name}）")
    rows.append(f"  [{'GREEN' if age <= SECRETS_MAX_AGE_H else 'RED  '}] 金鑰與憑證        "
                f"{len(encs)} 份｜最新 {latest.name} ({age:.1f}h 前)")


def self_test() -> int:
    """判準若不會動，看起來會跟很乾淨一模一樣。用假資料驗它會不會紅。"""
    import tempfile
    print("=== 判準鑑別力自我測試 ===")
    failed = 0
    tmp = Path(tempfile.mkdtemp())

    # 尾端完整性：完整 vs 截斷
    good = tmp / "good.sql"
    good.write_bytes(b"x" * 100 + b"--\n-- PostgreSQL database dump complete\n--\n")
    bad = tmp / "bad.sql"
    bad.write_bytes(b"x" * 200)
    for label, f, expect in (("完整 dump 不該紅", good, False), ("截斷 dump 必須紅", bad, True)):
        with open(f, "rb") as fh:
            fh.seek(max(0, f.stat().st_size - 4096))
            has = DUMP_TAIL_MARKER in fh.read()
        got = not has
        mark = "✓" if got == expect else "✗"
        if got != expect:
            failed += 1
        print(f"  {mark} {label:<28} 預期紅={int(expect)} 實際={int(got)}")

    # 附件涵蓋率判準
    cases = [
        ("本機=NAS 不該紅", 100, 100, 0, False),
        ("缺檔但有打包 不該紅", 100, 98, 1, False),
        ("缺檔且無打包 必須紅", 100, 98, 0, True),
        ("NAS 全空 必須紅", 100, 0, 0, True),
    ]
    for label, local, remote, zips, expect in cases:
        gap = local - remote
        ok = gap == 0 or (gap > 0 and zips > 0)
        got = not ok
        mark = "✓" if got == expect else "✗"
        if got != expect:
            failed += 1
        print(f"  {mark} {label:<28} 預期紅={int(expect)} 實際={int(got)}")

    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    if failed:
        print(f"\n✗ 判準有 {failed} 項不符預期")
        return 2
    print("\n✓ 判準有鑑別力（正向 3 例、負向 3 例）")
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    print("=" * 70)
    print("異地備份完整性稽核 —— 現在真的還原得回來嗎")
    print("=" * 70)

    if not NAS.exists():
        print(f"\n✗ NAS 不可達: {NAS}")
        print("  拒絕執行 —— 「連不上」不得被讀成「備份沒問題」。")
        return 2

    reds: list[str] = []
    rows: list[str] = []
    check_db(reds, rows)
    check_milestones(reds, rows)
    check_attachments(reds, rows)
    check_secrets(reds, rows)

    print()
    for r in rows:
        print(r)

    print("\n" + "=" * 70)
    if reds:
        print(f"RED: {len(reds)} 項")
        for r in reds:
            print(f"  · {r}")
        print("\n  四類缺一不可 —— 少任何一類，災難時就是「資料回得來、系統起不來」。")
        return 2
    print("GREEN: 四類異地備份齊全且新鮮（資料庫／里程碑／附件／金鑰）")
    print("  註：本檔只驗素材齊不齊，不驗還原出來對不對。")
    print("      完整還原測試是月度動作，見 docs/runbooks/disaster-recovery.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
