#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""測試資料庫的 schema 不得落後正式庫。

## 為什麼有這一支

2026-08-29：我在正式庫加了公文的 6 個欄位並跑了 migration，
**測試庫沒跑**。三支既有測試因此 500：

    column documents.contract_case does not exist

而我當下的判定方法**不夠力**：我把 `rls_filter.py` 暫存起來重跑，
三支照樣失敗 ⇒ 我下了「不是我造成的」的結論。
**錯在暫存的不是造成失敗的那個改動**（ORM 欄位早已 commit）。
⇒ 排除法只有在「排除的範圍涵蓋所有嫌疑」時才成立。

實查根因比那三支測試更大：

    測試庫**根本沒有 alembic_version 表** —— 它從來不在 migration
    控制之下，是一次性建好就沒再更新。

所以每一支新 migration 都會讓它再漂一次，而且**沒有任何機制會說**。
當日實測差 **20 個欄位／5 張表**，其中 `erp_quotation_items`
（線上報價單的明細表）**整張不存在**。

## 這一支為什麼不是「永遠綠的稽核」

本 repo 反覆記過：永遠綠的訊號與沒有訊號是同一個下場，所以加檢核前要先
問「它現在紅不紅」。**這一支在寫下來的當天就是 RED 20 個**（已修為 0），
而且每一支未同步的 migration 都會讓它再紅一次 —— 它有真實的觸發條件。

## 判準

比對兩庫 `information_schema.columns` 的 `table.column` 集合：

  RED  正式庫有而測試庫沒有 —— 測試會在那些欄位上 500，
       而失敗訊息長得像「測試壞了」不像「schema 落後了」
  ok   測試庫多出來的欄位**不判紅** —— 那通常是測試夾具自己建的

⚠️ 排序必須用 `LC_ALL=C`：第一次量的時候 `comm` 自己警告
「input is not in sorted order」，而我差點把那個輸出當結論。
**工具說自己有問題時，它的數字就不是證據。**

## 誰跑它

weekly step 87（`run_fitness_weekly.sh`）。
"""
import os
import subprocess
import sys

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONTAINER = os.environ.get("CK_PG_CONTAINER", "ck_missive_postgres")
DB_USER = os.environ.get("POSTGRES_USER", "ck_user")
DB_PROD = os.environ.get("POSTGRES_DB", "ck_documents")
DB_TEST = os.environ.get("CK_TEST_DB", "ck_documents_test")

_SQL = (
    "SELECT table_name||'.'||column_name FROM information_schema.columns "
    "WHERE table_schema='public'"
)


def _columns(db: str) -> set:
    """取一個庫的 table.column 集合。取不到就讓例外往外拋 —— 見下方註解。"""
    out = subprocess.run(
        ["docker", "exec", "-i", CONTAINER,
         "psql", "-U", DB_USER, "-d", db, "-Atc", _SQL],
        capture_output=True, text=True, timeout=120,
        env={**os.environ, "MSYS_NO_PATHCONV": "1", "LC_ALL": "C"},
    )
    if out.returncode != 0:
        raise RuntimeError(f"{db}: {out.stderr.strip()[:200]}")
    return {ln.strip() for ln in out.stdout.splitlines() if ln.strip()}


def main() -> int:
    try:
        prod = _columns(DB_PROD)
        test = _columns(DB_TEST)
    except Exception as e:
        # 明確失敗，**不當成通過** —— 「查不到」與「沒有漂移」在輸出上一樣，
        # 那正是本檢核要防的東西（ADR-0028）。
        print(f"✗ 無法比對兩庫 schema：{e}")
        return 2

    if not prod:
        print("✗ 正式庫查不到任何欄位 —— 判定不可信，不視為通過")
        return 2

    missing = sorted(prod - test)
    extra = len(test - prod)

    print(f"正式庫欄位 {len(prod)}｜測試庫 {len(test)}")
    if extra:
        # 測試夾具自建的欄位不判紅，但要說出來（沉默地忽略會養出第二種漂移）
        print(f"  （測試庫多出 {extra} 個，不判紅 —— 通常是測試夾具自建）")

    if not missing:
        print("✓ 測試庫 schema 未落後正式庫")
        return 0

    by_table: dict = {}
    for col in missing:
        by_table.setdefault(col.split(".", 1)[0], []).append(col)

    print(f"\n✗ 測試庫缺 {len(missing)} 個欄位（跨 {len(by_table)} 張表）")
    print("  症狀會是測試 500 `column X does not exist`，"
          "而那看起來像「測試壞了」不像「schema 落後了」。")
    for tbl, cols in sorted(by_table.items(), key=lambda kv: -len(kv[1])):
        shown = ", ".join(c.split(".", 1)[1] for c in cols[:6])
        more = f" …共 {len(cols)} 個" if len(cols) > 6 else ""
        print(f"    {tbl}: {shown}{more}")
    print("\n  修法：把對應的 migration 套到測試庫，"
          "或直接 `alembic upgrade head`（測試庫 2026-08-29 起有 alembic_version）。")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
