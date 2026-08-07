# -*- coding: utf-8 -*-
"""作業紀錄鏈的語意檢核：完成的成果不該是新事件的前序（2026-08-07）。

## 為什麼需要這一支

owner 2026-08-07 回報派工單 2「時序亂了」。追下去發現 13 筆錯誤前序關聯，橫跨
4/5/7 三個月 —— 也就是**已經錯了四個月而沒有任何人知道**。

原因不是沒人看，是**這類缺陷不產生任何訊號**：
  · 不會拋錯、不會有 4xx/5xx
  · 不改變任何數字（公文數、派工數、進度統計全都一樣）
  · 不影響任何清單內容
  · 頁面渲染完全正常 —— 連瀏覽器走查都是全過（§3.5「斷言全過 ≠ 畫面沒問題」）

它**只**改變縮排與分組。而縮排的用途正是看出事件斷點，所以錯的鏈會把兩件不同
的事畫成同一件；等到被錯接的鏈橫跨數月，後面的鏈看起來就像在往回跳。

唯一的偵測器一直是「人打開頁面覺得不對」。這一支就是要取代那個人。

## 判準

父為 `work_result`、子為 `*_notice` —— 完成的成果被當成後續**新事件**的前序。
成因是新增表單原本會自動把「前序」預設成最後一筆（已於 2026-08-07 移除）。

刻意**只**看這一種組合：時間跨度大不代表關聯錯（工程本來就會拖很久），那需要
人判斷，自動判定只會製造另一種錯誤。寧可少報，不可報不可信的清單。

## 為什麼是 YELLOW 不是 RED

自動預設已移除，新出現的只可能是人手動挑錯 —— 那是資料品質提示、不是系統故障，
需要人看一眼而不是擋住流程。0 → GREEN；≥1 → YELLOW 並列出，讓人去判斷。

## 用法

    python scripts/checks/work_record_chain_semantics_audit.py
    python scripts/checks/work_record_chain_semantics_audit.py --self-test

`--self-test` 用內建樣本驗證判準本身有鑑別力（該抓的抓到、不該抓的不抓），
不碰任何真實資料 —— 否則這支檢核回 0 時，我們分不清是「真的乾淨」還是
「判準根本不會動」。
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

CONTAINER = "ck_missive_postgres"
DB_USER, DB_NAME = "ck_user", "ck_documents"

# 與 scripts/dev/fix_wrong_work_record_parents.py 同一條判準。
# 兩處若各寫一份就會漂移 —— 修復腳本是既有的那份，這裡沿用同樣的 WHERE。
FIND_SQL = """
SELECT c.dispatch_order_id, c.id, p.work_category, p.record_date,
       c.work_category, c.record_date
FROM taoyuan_work_records c
JOIN taoyuan_work_records p ON p.id = c.parent_record_id
WHERE c.dispatch_order_id IS NOT NULL
  AND p.work_category = 'work_result'
  AND c.work_category LIKE '%_notice'
ORDER BY c.dispatch_order_id, c.record_date
"""


def is_wrong_link(parent_category: str, child_category: str) -> bool:
    """判準本體。抽出來是為了能在不碰資料庫的情況下驗它有沒有鑑別力。"""
    return parent_category == "work_result" and child_category.endswith("_notice")


def self_test() -> int:
    """該抓的要抓到、不該抓的不能抓 —— 只驗其中一邊等於沒驗。"""
    should_flag = [
        ("work_result", "meeting_notice"),
        ("work_result", "admin_notice"),
        ("work_result", "dispatch_notice"),
    ]
    should_not_flag = [
        ("dispatch_notice", "work_result"),   # 通知 → 成果：正常順序
        ("meeting_notice", "meeting_record"), # 通知 → 紀錄：正常順序
        ("work_result", "work_result"),       # 連續成果：不在本判準範圍
        ("admin_notice", "meeting_notice"),   # 通知接通知：不在本判準範圍
    ]
    bad = []
    for p, c in should_flag:
        if not is_wrong_link(p, c):
            bad.append(f"該抓卻沒抓到：{p} → {c}")
    for p, c in should_not_flag:
        if is_wrong_link(p, c):
            bad.append(f"不該抓卻抓了：{p} → {c}")
    if bad:
        print("✗ 判準無鑑別力：")
        for b in bad:
            print(f"    {b}")
        return 2
    print(f"✓ 判準有鑑別力（正向 {len(should_flag)} 例、負向 {len(should_not_flag)} 例皆符合）")
    return 0


def _query_direct() -> list[list[str]] | None:
    """容器內走這條：有 DATABASE_URL 與 psycopg2，直接連。連不上回 None 交由外層判定。"""
    url = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")
    if not url:
        return None
    try:
        import psycopg2  # type: ignore
    except Exception:
        return None
    conn = psycopg2.connect(url, connect_timeout=10)
    try:
        cur = conn.cursor()
        cur.execute(FIND_SQL)
        rows = [[("" if v is None else str(v)) for v in r] for r in cur.fetchall()]
        cur.close()
        return rows
    finally:
        conn.close()


def _query_docker() -> list[list[str]] | None:
    """host 走這條：.env 的 DATABASE_URL 指向容器網路（postgres:5432），host 連不到。"""
    try:
        out = subprocess.run(
            ["docker", "exec", CONTAINER, "psql", "-U", DB_USER, "-d", DB_NAME,
             "-tAF", "|", "-c", FIND_SQL],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if out.returncode != 0:
        return None
    return [ln.split("|") for ln in out.stdout.splitlines() if ln.strip()]


def query() -> list[list[str]]:
    """兩條路徑，但**都不是靜默跳過** —— 兩條都不通就 exit 2。

    2026-08-07：第一版只有 docker exec，而 weekly 實際是**容器內的 APScheduler**
    在跑（`fitness_weekly_job` → subprocess 執行 run_fitness_weekly.sh），容器裡
    沒有 docker CLI → 每週必然 exit 2 = 永久 RED，而我手動在 host 跑是全綠的。
    這正是 L52/L49 家族：**手動跑得動 ≠ 排程情境跑得動**。

    兩條路徑不是「兩份事實」—— SQL 只有一份（FIND_SQL），差別只在怎麼連到同一個
    資料庫：容器內用 DATABASE_URL 直連，host 端因 .env 指向容器網路而必須借道
    docker exec。
    """
    for fn in (_query_direct, _query_docker):
        try:
            rows = fn()
        except Exception as e:  # noqa: BLE001
            print(f"  （{fn.__name__} 失敗：{str(e)[:120]}）")
            continue
        if rows is not None:
            return rows
    print("✗ 兩種連線方式都不可用（容器內 DATABASE_URL / host 端 docker exec）")
    print("  —— 本檢核需要能連上資料庫，無法執行不等於通過")
    raise SystemExit(2)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true", help="只驗判準鑑別力，不碰資料")
    ap.add_argument("--strict", action="store_true", help="（相容 runner，行為相同）")
    ap.add_argument("--ci", action="store_true", help="（相容 runner，行為相同）")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    print("=== 作業紀錄鏈語意檢核：完成的成果不該是新事件的前序 ===")
    rows = query()
    if not rows:
        print("  GREEN — 0 筆")
        print("  （判準鑑別力可用 --self-test 驗證，避免「不會動」被讀成「很乾淨」）")
        return 0

    print(f"  YELLOW — {len(rows)} 筆：新事件被掛在已完成的成果之下")
    for r in rows:
        print(f"    派工單{r[0]:>4}  紀錄#{r[1]:<5} {r[2]}({r[3]}) → {r[4]}({r[5]})")
    print()
    print("  縮排的用途是看出事件斷點；這些鏈把兩件不同的事畫成了同一件。")
    print("  修法：python scripts/dev/fix_wrong_work_record_parents.py --apply（先備份、可還原）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
