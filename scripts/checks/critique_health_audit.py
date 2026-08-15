"""Critique Health Audit (v6.13, 2026-05-31)

對齊 owner「日誌與周報成為實質平臺靈魂」訴求。

揭發背景：
- 5/31 三層覆盤揭發 critiques/ 5/13 後 17 天 0 條
- 真因確認: critic 鏈真實有被呼叫（agent_post_processing.py:181）
- 4 條 trigger rules，只在 hallucination/concern/fail 才寫入磁碟
- 17 天 0 critique 可能意義:
  A. query trace 偏少（5/29-5/31 大段空）
  B. 都「passing」（entity_alignment≥0.5）
  C. critic 鏈 silent skip（不太可能，except 會 log error）

監督機制（本檔）：
- 每週跑一次（cron 週日 02:15）
- 若 7d 內 0 critique 且有 ≥10 query trace → 寫一條 critique-health-empty.md
- LINE 推 owner 揭發 silent dormant 訊號

不改 critic 設計（保留 critique = 質性反省的純度）。
純加偵測層。

執行:
  python scripts/checks/critique_health_audit.py
  python scripts/checks/critique_health_audit.py --window-days 7
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
# 2026-08-15：weekly 跑在 host（cp950），而 ✅🔴⚠ 這些符號 cp950 編不出來。
# 崩潰是**路徑相依**的 —— 平常走 GREEN 分支沒事，偏偏在要報問題的那一刻崩掉，
# 而那時看到的是 UnicodeEncodeError 不是它本來要講的事。同 L49.8（.ps1 的 BOM）家族。
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


# 2026-08-04：預設值原本寫死容器路徑 `/app/wiki`。在 host 上 Windows 會把它解析成
# **磁碟根目錄下的 app/wiki 目錄**（磁碟相對路徑）—— 於是 host 執行時產出
# 靜靜寫進一個沒人讀的雜散目錄，而消費端（producer registry）讀的是 repo 內的路徑。
# 已累積 7 月以來的殘留。改用 **repo 相對路徑**：容器內腳本在 `/app/scripts/checks/`
# → parents[2] = `/app`，host 上 → repo 根，兩邊都對（L52 家族）。
_REPO_ROOT = Path(__file__).resolve().parents[2]
WIKI_MEMORY = Path(os.getenv("CK_WIKI_DIR") or (_REPO_ROOT / "wiki")) / "memory"
CRITIQUES_DIR = WIKI_MEMORY / "critiques"

# 2026-08-05：marker 改寫進**子目錄**，不再與被偵測對象混放。
#
# 原本 marker 檔名是 `critique-health-empty-*.md`，與真 critique 落在同一個目錄，
# 而三個消費端都用 `critique-*.md` 掃這個目錄 → **偵測器的產物被自己算成偵測對象**：
#   1. 本檔 count_critiques()          → total 18 實際只有 14 篇真 critique
#   2. scheduler._check_critique_starvation() → 取最新 mtime 判「逾 28 天無 critique」，
#      而本稽核**每兩週**寫一個 marker → 最新 mtime 永遠 ≤14 天 →
#      **28 天門檻在結構上永遠不可能達到，那道告警不管有沒有真的斷層都不會響**。
#      （查證當下並沒有斷層：真 critique 最新 2026-08-02、近三個月穩定每 1-2 週一篇。
#        所以這是**潛伏**缺陷 —— 安全網從未失效過，是因為從未被需要過。）
#   3. kunge.py 前端顯示的 critique 數
# （Prometheus 的 v7_reference_density_critique_pct 逃過一劫 —— 它的日期 regex
#   `critique-(\d{8})` 剛好對不上 marker 檔名，屬僥倖而非設計。）
#
# 修法選擇：**移出目錄**而不是在三個消費端各加一條排除規則 ——
# 後者是同一件事寫三遍，正是本專案一直在治的異質同工。三個消費端的 glob
# 都是非遞迴的，marker 進子目錄即自動免疫。
HEALTH_MARKER_DIR = CRITIQUES_DIR / "_health"


def count_critiques(window_days: int) -> tuple[int, int]:
    """回傳 (window 內 critique 數, 總 critique 數)"""
    if not CRITIQUES_DIR.is_dir():
        return 0, 0
    cutoff = (datetime.now() - timedelta(days=window_days)).timestamp()
    in_window = 0
    total = 0
    for f in CRITIQUES_DIR.glob("critique-*.md"):
        total += 1
        try:
            if f.stat().st_mtime > cutoff:
                in_window += 1
        except Exception:
            continue
    return in_window, total


async def count_query_traces(window_days: int) -> int:
    """從 DB 撈最近 window_days 的 agent_query_traces 數"""
    try:
        sys.path.insert(0, "/app")
        from app.db.database import AsyncSessionLocal
        from sqlalchemy import text

        async with AsyncSessionLocal() as db:
            r = await db.execute(text(
                f"SELECT COUNT(*) FROM agent_query_traces "
                f"WHERE created_at > NOW() - INTERVAL '{window_days} days'"
            ))
            return r.scalar() or 0
    except Exception as e:
        print(f"WARN: query trace count failed: {e}")
        return -1


def write_health_marker(window_days: int, critiques_count: int, query_trace_count: int) -> Path:
    """寫一條 health-empty.md 紀錄揭發 silent dormant

    寫進 `critiques/_health/`（見 HEALTH_MARKER_DIR 註解）—— 不可寫回 critiques/，
    否則偵測器會把自己的產物算成偵測對象，讓 starvation 告警永遠不觸發。
    """
    HEALTH_MARKER_DIR.mkdir(parents=True, exist_ok=True)
    now = datetime.now()
    filename = f"critique-health-empty-{now.strftime('%Y%m%d-%H%M%S')}.md"
    path = HEALTH_MARKER_DIR / filename

    content = f"""---
type: critique_health_marker
verdict: silent_dormant
created_at: {now.isoformat(timespec='seconds')}
window_days: {window_days}
critiques_in_window: {critiques_count}
query_traces_in_window: {query_trace_count}
generator: critique_health_audit
tags: [critique, silent-dormant, health-check]
---

# Critique Health Marker — 揭發 silent dormant

**揭發時間**: {now.strftime('%Y-%m-%d %H:%M:%S')}

## 訊號

- 最近 {window_days} 天 critique 數: **{critiques_count}**
- 最近 {window_days} 天 query trace 數: **{query_trace_count}**

## 可能含義

{f"⚠️ 有 {query_trace_count} 個 query 但 0 critique → agent 完全無質性反省" if query_trace_count >= 10 else f"⚠️ 僅 {query_trace_count} query 且 0 critique → agent 較少被使用"}

## 設計意圖

critique 只在 critic 偵測到以下情況才 persist:
1. entity_alignment < 0.5 (hallucination 警示)
2. completeness < 0.3 且 answer < 100 字
3. 所有工具失敗但 answer > 200 字
4. tools ≥ 3 但 entity_alignment < 0.5

→ 0 critique 不一定壞，但長期 silent 是異常訊號

## 建議

- 檢查 agent_query_traces.eval_score 分佈
- 若 entity_alignment 都 ≥ 0.5 → 質性反省機制太嚴 (downgrade threshold?)
- 若 query 數量本來就少 → 推 owner 多互動

---

> 對齊 owner「日誌與周報成為實質平臺靈魂」
> 此 marker 本身即一條反省 (auto-generated 但有意義)
"""
    path.write_text(content, encoding="utf-8")
    return path


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window-days", type=int, default=7)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-queries-threshold", type=int, default=5,
                       help="少於這數量 query 不視為 silent dormant")
    args = parser.parse_args()

    in_window, total = count_critiques(args.window_days)
    query_count = await count_query_traces(args.window_days)

    print(f"Critique Health Audit (window={args.window_days}d):")
    print(f"  critiques 總數: {total}")
    print(f"  critiques 最近 {args.window_days}d: {in_window}")
    print(f"  query traces 最近 {args.window_days}d: {query_count}")
    print()

    if in_window > 0:
        print(f"✅ HEALTHY: {in_window} critiques 有真活")
        return 0

    if query_count < args.min_queries_threshold:
        print(f"🟡 SKIP: query trace ({query_count}) < threshold ({args.min_queries_threshold})")
        print(f"   query 太少不視為 silent dormant — 推 owner 多互動較合適")
        return 0

    # 0 critique 且 query ≥ threshold → 揭發
    print(f"🔴 SILENT DORMANT DETECTED:")
    print(f"   {query_count} query 但 0 critique → 質性反省可能斷層")

    if args.dry_run:
        print("[DRY-RUN] 預計寫 critique-health-empty marker")
        return 1

    marker = write_health_marker(args.window_days, in_window, query_count)
    print(f"WROTE: {marker}")
    return 1  # 非 0 exit 表示揭發 silent dormant


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
