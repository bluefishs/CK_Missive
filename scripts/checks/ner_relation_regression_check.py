#!/usr/bin/env python
"""NER 關係抽取：修法之後有沒有又長出新的缺口。

## 為什麼不是報「有 572 筆存量」

2026-08-03 修好 NER 關係抽取（system prompt 兩段欄位名不一致，
`relation` vs `relation_type`，validator 只讀前者 → 每條關係被靜默丟掉）。
修法前累積的公文有 entities 卻沒有任何 relations，
而**排程永遠不會回頭處理它們** —— 待處理判準問的是
「有沒有 entities」，要產出的卻是 relations（判準看的是代理指標不是產出）。

存量 572 筆是 owner 已知、待決定要不要重抽的事。
每週報一次「還有 572」只會訓練人略過它，
而這正是本專案反覆記過的告警疲勞。

**所以本支問的是另一個問題：修法日之後，有沒有又出現新的缺口。**
有的話代表 08-03 的修法退回去了 —— 那是真的要有人立刻知道的事。

## 為什麼不能把待處理判準直接改成「沒有 relations」

會踩另一個坑：**真的沒有關係的公文**（LLM 抽出實體但它們之間確實
沒有關係，這完全合法）會被每一輪重抽，永遠不會滿足條件 ——
無限重抽而且每次都花 LLM 呼叫。
要改判準得先有「抽過了」的標記，那是另一件事。

## 判準

- 只有 1 個實體的公文**不算缺口** —— 一個實體在結構上不可能有關係，
  把它算進來就是假陽性（首版查證時 623 筆裡有 51 筆是這種）。
- 缺口公文的**建檔日期晚於修法日** → RED（修法退回）
- 只有修法日之前的存量 → YELLOW 附數字（已知，不催）
- 完全沒有 → GREEN
"""
from __future__ import annotations

import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 08-03 修法日：那天之後建檔的公文若仍無關係，代表修法沒有真的生效
FIX_DATE = "2026-08-03"

SQL = """
WITH gap AS (
  SELECT de.document_id, COUNT(*) AS ents
  FROM document_entities de
  LEFT JOIN entity_relations er ON er.document_id = de.document_id
  WHERE er.id IS NULL
  GROUP BY de.document_id
  HAVING COUNT(*) >= 2          -- 只有 1 個實體不可能有關係，不算缺口
)
SELECT
  COUNT(*) FILTER (WHERE d.created_at::date >  %(fix)s::date) AS after_fix,
  COUNT(*) FILTER (WHERE d.created_at::date <= %(fix)s::date) AS before_fix,
  MAX(d.created_at)::date                                     AS newest
FROM gap JOIN documents d ON d.id = gap.document_id;
"""


def _psql(sql: str) -> list[list[str]] | None:
    """host 走這條：.env 的 DATABASE_URL 指向容器網路（postgres:5432），host 連不到。

    2026-08-16：第一版只寫了直連，於是這支在 **weekly 實際執行的 host 環境跑不起來**
    （`fe_sendauth: no password supplied`），而 exit 2 看起來像「資料庫有事」。
    這是 2026-08-11 記過的同一條：**檢核跑在哪個環境，和它判得對不對一樣重要**。
    作法與 `work_record_chain_semantics_audit` 一致，不自創第二種。
    """
    import subprocess
    try:
        out = subprocess.run(
            ["docker", "exec", "ck_missive_postgres", "psql", "-U", "ck_user",
             "-d", "ck_documents", "-tAF", "|", "-c", sql],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    if out.returncode != 0:
        return None
    return [ln.split("|") for ln in out.stdout.splitlines() if ln.strip()]


def _dsn() -> str:
    host = os.getenv("POSTGRES_HOST") or os.getenv("PGHOST") or "localhost"
    port = os.getenv("POSTGRES_PORT") or os.getenv("PGPORT") or "5434"
    db = os.getenv("POSTGRES_DB") or os.getenv("PGDATABASE") or "ck_documents"
    user = os.getenv("POSTGRES_USER") or os.getenv("PGUSER") or "ck_user"
    pw = os.getenv("POSTGRES_PASSWORD") or os.getenv("PGPASSWORD") or ""
    return f"host={host} port={port} dbname={db} user={user} password={pw}"


def main() -> int:
    print("=" * 70)
    print("NER 關係抽取回歸偵測（修法後有沒有又長出新缺口）")
    print("=" * 70)

    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        print("\n✗ 沒有 psycopg2 —— 無法判定（不視為通過）")
        return 2

    # 兩條路徑，**都不是靜默跳過** —— 兩條都不通就 exit 2
    after = before = 0
    newest = None
    try:
        conn = psycopg2.connect(_dsn())
        try:
            with conn.cursor() as cur:
                cur.execute(SQL, {"fix": FIX_DATE})
                after, before, newest = cur.fetchone()
        finally:
            conn.close()
    except Exception:
        rows = _psql(SQL.replace("%(fix)s", "'" + FIX_DATE + "'"))
        if rows is None:
            print(chr(10) + "✗ 直連與 docker exec 都不通 —— 無法判定（不視為通過）")
            return 2
        r = rows[0]
        after, before = int(r[0] or 0), int(r[1] or 0)
        newest = r[2] or None

    after, before = after or 0, before or 0
    print(f"\n  修法日 {FIX_DATE} 之後建檔卻無關係：{after}")
    print(f"  修法日之前的存量：{before}")
    print(f"  缺口中最新公文：{newest or '-'}")

    if after:
        print(f"\nStatus: [RED] {after} 份修法後的公文仍然沒有任何關係")
        print("  這代表 08-03 的修法退回去了，或有第二條路徑繞過它。")
        print("  先查 entity_extraction_service 的 validator 還認不認得 relation_type，")
        print("  再查 prompt 兩段的欄位名有沒有又分歧。")
        return 2

    if before:
        print(f"\nStatus: [YELLOW] 只有修法前的存量 {before} 份，沒有新增")
        print("  修法有效（新公文都正常抽到關係）。")
        print("  存量要不要重抽是 owner 的決定 —— 排程不會回頭處理它們，")
        print("  因為待處理判準問的是「有沒有 entities」而不是「有沒有 relations」。")
        print("  重抽路徑：scripts/sync/backfill_ner_relations.py（預設 dry-run）")
        return 1

    print("\nStatus: [GREEN] 沒有缺口")
    return 0


if __name__ == "__main__":
    sys.exit(main())
