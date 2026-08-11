# -*- coding: utf-8 -*-
"""資料庫連線狀態健檢 —— 抓「交易中止卻未 rollback」的現行犯（2026-08-08）。

## 為什麼需要這一支

2026-08-08 複查時發現 lvrland 後端 **hang 住、API 對真實使用者完全不可用**，
而且已持續一段時間：

  · 所有端點逾時、log 零錯誤（接受連線但不回應）
  · CPU 4.68%、記憶體正常 —— **不是資源耗盡**
  · **公網首頁仍回 200**（前端靜態檔正常）→ 表面看起來是好的
  · DB 有 `idle in transaction (aborted)` × 5 —— 交易中止卻未 rollback、佔住連線

那 5 條連線是唯一指向真因的證據，而**沒有任何機制在看它**。
重啟可以止血，但根因會讓它再度累積。

## 為什麼用執行期狀態而不是靜態掃描

同 repo 已移植 `transaction_pollution_audit.py`（靜態掃 try/except 是否缺 rollback），
但它在此 repo 回報 **73 個候選、橫跨 27 個檔**，腳本自己也註明是啟發式、會有假陽性。
73 條無法逐一核實的清單，依既有判準**不得作為判斷依據**。

本檢核改問**現在的實際狀態**：資料庫此刻有沒有中止未回收的交易。
抓到就是真的，不需要猜。兩者互補：靜態找「可能寫錯的地方」，本支找「已經在發生的事」。

## 判準

  · `idle in transaction (aborted)` 任一條 → **RED**（交易已中止卻沒 rollback，
    該連線永遠不會自己好，只會累積到把連線池吃光）
  · `idle in transaction` 超過門檻秒數 → **YELLOW**（尚未中止，但長時間佔住）
  · 連線數逼近上限 → **YELLOW**

## 用法

    python scripts/checks/db_transaction_health_check.py
    python scripts/checks/db_transaction_health_check.py --self-test
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 連線走 DB 容器內的 psql —— 與本 repo 其他檢核一致，不另外要求 host 裝 driver。
import os
# 2026-08-08：容器辨識由環境變數指定，讓**同一份**能跨 repo 使用。
# 寫死 repo 名就等於每個 repo 各一份，那正是這支要避免的異質同工。
CONTAINER_HINT = os.environ.get("DB_CONTAINER_HINT", "missive")
IDLE_IN_TX_WARN_SECONDS = 300  # 5 分鐘
CONN_USAGE_WARN_PCT = 80

SQL = """
SELECT COALESCE(state, 'unknown'),
       count(*),
       COALESCE(max(EXTRACT(EPOCH FROM (now() - state_change)))::int, 0)
FROM pg_stat_activity
WHERE datname IS NOT NULL
GROUP BY 1
"""

SQL_LIMIT = "SELECT setting::int FROM pg_settings WHERE name='max_connections'"


def _db_container() -> str | None:
    try:
        out = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=30,
        ).stdout
    except Exception:
        return None
    for n in out.split():
        low = n.lower()
        if CONTAINER_HINT in low and ("db" in low or "postgres" in low):
            return n
    return None


def _local_psql_env() -> dict[str, str] | None:
    """本行程能不能直接連上 DB？可以就回 psql 需要的環境變數。

    2026-08-11：本支原本只有一條路 —— `docker exec <db 容器> psql`。
    在 host 執行沒問題，但 CK_Missive 的 daily 是**容器內** APScheduler 在跑，
    而應用容器裡沒有 docker CLI（L49.1 那一族），於是 `_db_container()` 永遠回 None，
    這一步**每天必紅、每天推一則 LINE**，紅的原因卻不是資料庫有問題。

    而它其實根本不需要 docker：要的是一條 DB 連線，應用容器本來就有
    （PG* 環境變數齊全、映像檔內含 psql）。改為先試 docker、再試直連。
    """
    host = os.environ.get("POSTGRES_HOST") or os.environ.get("PGHOST")
    user = os.environ.get("POSTGRES_USER") or os.environ.get("PGUSER")
    db = os.environ.get("POSTGRES_DB") or os.environ.get("PGDATABASE")
    if not (host and user and db):
        return None
    if not shutil.which("psql"):
        return None
    env = dict(os.environ)
    env.update({
        "PGHOST": host,
        "PGPORT": os.environ.get("POSTGRES_PORT") or os.environ.get("PGPORT") or "5432",
        "PGUSER": user,
        "PGDATABASE": db,
    })
    pw = os.environ.get("POSTGRES_PASSWORD") or os.environ.get("PGPASSWORD")
    if pw:
        env["PGPASSWORD"] = pw
    return env


def _psql(container: str | None, sql: str, env: dict[str, str] | None = None) -> list[list[str]]:
    """外部依賴缺失一律非零 —— 「查不到」不得與「沒問題」長得一樣。"""
    flat = sql.replace("\n", " ")
    if container is None:
        # 直連（容器內／host 已設好 PG* 時）
        out = subprocess.run(
            ["psql", "-tAF|", "-c", flat],
            capture_output=True, text=True, encoding="utf-8", timeout=60, env=env,
        )
        if out.returncode != 0:
            print(f"✗ psql 查詢失敗（直連）：{(out.stderr or '').strip()[:180]}")
            raise SystemExit(2)
        return [ln.split("|") for ln in out.stdout.splitlines() if ln.strip()]
    cmd = ["docker", "exec", container, "sh", "-c",
           'psql -U ${POSTGRES_USER:-postgres} -d ${POSTGRES_DB:-postgres} -tAF"|" -c "'
           + flat.replace('"', '\\"') + '"']
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", timeout=60)
    if out.returncode != 0:
        print(f"✗ psql 查詢失敗：{(out.stderr or '').strip()[:180]}")
        raise SystemExit(2)
    return [ln.split("|") for ln in out.stdout.splitlines() if ln.strip()]


def judge(rows: list[tuple[str, int, int]], max_conn: int) -> tuple[int, list[str]]:
    """回傳 (退出碼, 訊息)。抽出來才驗得了鑑別力。"""
    msgs: list[str] = []
    worst = 0
    total = sum(n for _, n, _ in rows)
    for state, n, age in rows:
        if state == "idle in transaction (aborted)":
            msgs.append(
                f"🔴 {n} 條連線處於 idle in transaction (aborted)（最久 {age}s）"
                " —— 交易已中止卻沒 rollback，該連線不會自己好，只會累積到把連線池吃光"
            )
            worst = max(worst, 2)
        elif state == "idle in transaction" and age > IDLE_IN_TX_WARN_SECONDS:
            msgs.append(f"🟡 idle in transaction 已達 {age}s（門檻 {IDLE_IN_TX_WARN_SECONDS}s）")
            worst = max(worst, 1)
    if max_conn and total >= max_conn * CONN_USAGE_WARN_PCT / 100:
        msgs.append(f"🟡 連線數 {total}/{max_conn} 已達 {CONN_USAGE_WARN_PCT}%")
        worst = max(worst, 1)
    return worst, msgs


def self_test() -> int:
    """證明判準會動 —— 否則「0 條」可能只是永遠不會紅。"""
    cases = [
        ("有中止交易", [("idle in transaction (aborted)", 1, 10), ("idle", 3, 5)], 100, 2),
        ("長時間未提交", [("idle in transaction", 2, 600)], 100, 1),
        ("連線逼近上限", [("idle", 85, 5)], 100, 1),
        ("一切正常", [("idle", 3, 5), ("active", 1, 0)], 100, 0),
        ("短時間未提交不報", [("idle in transaction", 1, 30)], 100, 0),
    ]
    bad = []
    for name, rows, mc, expect in cases:
        got, _ = judge(rows, mc)
        ok = got == expect
        print(f"  {'✓' if ok else '✗'} {name:16s} 預期 exit={expect} 實際={got}")
        if not ok:
            bad.append(name)
    if bad:
        print(f"\n✗ 判準無鑑別力：{bad}")
        return 2
    print("\n✓ 判準有鑑別力（正向 3 例、負向 2 例皆符合）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument(
        "--red-exit", type=int, default=2, choices=(1, 2),
        help=(
            "RED 時的退出碼。預設 2（portfolio 標準：0=GREEN/1=YELLOW/2+=RED）。"
            "但 CK_lvrland_Webmap 的 run_checks.sh 用的是另一套：1=FAIL、**2=未驗完**。"
            "2026-08-09 查證發現本檔以預設 2 進入該 runner 時，真的抓到中止交易會被"
            "報成「SKIP（未驗完）」且 static-checks.json 的 fail=0 —— "
            "亦即為了防止 08-08 那次停機而寫的檢核，在該 repo 是啞的。"
            "約定衝突無法兩全，故由**呼叫端明示**，不讓它靜靜取預設值。"
        ),
    )
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    red_code = args.red_exit

    print("=== 資料庫連線狀態健檢（交易中止未 rollback）===")
    # 先 docker（host 情境），再直連（容器內情境）；兩條都不通才是無法判定。
    container = _db_container()
    env = None
    if container:
        print(f"  連線方式：docker exec {container}")
    else:
        env = _local_psql_env()
        if env is None:
            print("✗ 既找不到 DB 容器、本行程也無法直連（缺 PG* 設定或 psql）"
                  " —— 無法判定，不視為通過")
            return 2
        print(f"  連線方式：直連 {env['PGHOST']}:{env['PGPORT']}/{env['PGDATABASE']}")
    rows_raw = _psql(container, SQL, env)
    rows = [(r[0], int(r[1]), int(r[2])) for r in rows_raw if len(r) >= 3]
    limit_raw = _psql(container, SQL_LIMIT, env)
    max_conn = int(limit_raw[0][0]) if limit_raw and limit_raw[0] else 0

    for state, n, age in sorted(rows, key=lambda x: -x[1]):
        print(f"  {state:34s} {n:4d} 條（最久 {age}s）")
    print(f"  {'max_connections':34s} {max_conn}")

    code, msgs = judge(rows, max_conn)
    print()
    if not msgs:
        print("Status: [GREEN] 無中止未回收的交易")
        return 0
    for m in msgs:
        print(f"  {m}")
    print(f"\nStatus: [{'RED' if code >= 2 else 'YELLOW'}]")
    if code >= 2:
        print("  處置：重啟後端可止血，但根因在「except 吞掉 DB 錯誤卻沒 rollback」，")
        print("  參考 transaction_pollution_audit.py 的候選清單逐一核實。")
    return red_code if code >= 2 else code


if __name__ == "__main__":
    sys.exit(main())
