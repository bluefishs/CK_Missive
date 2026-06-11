"""Calendar Title Standard Audit — 命名標準 SSOT 強制（2026-06-11，強化圖譜治理 / 防多重標準）

owner 疑慮：「為何還是有多重標準」。日曆事件標題應只有 2 套 SSOT：
  - 公文事件：`[提醒]/[會議]/[審查]/[參考]/[截止]`（event_auto_builder.EVENT_TYPE_PREFIX_MAP）
  - 派工事件：`【…】`（calendar_title_template）
任何不符前綴 = 競爭/遺留格式（如已正規化的「公文提醒:」），應收斂。

此 audit 查 DB document_calendar_events 標題前綴分佈，非標準前綴比例 > 門檻 → 警示。
可 host（無 DB 則 SKIP）或容器內跑。

Usage:
  python scripts/checks/calendar_title_standard_audit.py
  python scripts/checks/calendar_title_standard_audit.py --strict   # 超門檻 exit 1
"""
from __future__ import annotations

import argparse
import os
import sys

# 公文事件標準前綴（與 event_auto_builder.EVENT_TYPE_PREFIX_MAP 對齊 — 改 builder 須同步此處）
DOC_PREFIXES = ("[提醒]", "[會議]", "[審查]", "[參考]", "[截止]")
# 派工事件以全形【】開頭
DISPATCH_PREFIX = "【"
NONCONFORM_THRESHOLD_PCT = 1.0  # 非標準前綴占比門檻


def _db_url() -> str | None:
    return os.environ.get("DATABASE_URL") or os.environ.get("CK_DATABASE_URL")


def main(strict: bool = False) -> int:
    try:
        import psycopg2  # type: ignore
    except Exception:
        print("[SKIP] psycopg2 不可用（host 端）— 此 audit 需 DB，請於容器內跑")
        return 0

    url = _db_url()
    if not url:
        print("[SKIP] 無 DATABASE_URL")
        return 0
    # asyncpg url → psycopg2
    url = url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        conn = psycopg2.connect(url)
    except Exception as e:
        print(f"[SKIP] DB 連線失敗: {e}")
        return 0

    cur = conn.cursor()
    # 只稽核「自動建立」事件（有 document_id）— 手動建立(NULL)為自由命名、合法豁免。
    # 自動事件由 builder 產生 → 必須符合 SSOT 前綴；不符=builder 漏網或遺留格式。
    cur.execute("SELECT title FROM document_calendar_events WHERE document_id IS NOT NULL")
    rows = cur.fetchall()
    total = len(rows)
    if total == 0:
        print("[INFO] 無自動建立事件")
        return 0

    conform = nonconform = 0
    samples: list[str] = []
    for (title,) in rows:
        t = (title or "").lstrip()
        if t.startswith(DOC_PREFIXES) or t.startswith(DISPATCH_PREFIX):
            conform += 1
        else:
            nonconform += 1
            if len(samples) < 8:
                samples.append((title or "")[:40])

    pct = nonconform / total * 100
    print("=== Calendar Title Standard Audit（命名 SSOT 強制）===")
    print(f"  總事件 {total} | 符合 2 套 SSOT 前綴 {conform} | 非標準 {nonconform} ({pct:.1f}%)")
    if samples:
        print("  非標準樣本:")
        for s in samples:
            print(f"    - {s}")

    status = "GREEN" if pct <= NONCONFORM_THRESHOLD_PCT else "RED"
    print(f"\nStatus: {status}（門檻 ≤{NONCONFORM_THRESHOLD_PCT}%）")
    cur.close()
    conn.close()

    if status == "RED":
        print("[WARN] 非標準命名占比超門檻 → 收斂至 event_auto_builder / calendar_title_template SSOT")
        if strict:
            return 1
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    sys.exit(main(strict=args.strict))
