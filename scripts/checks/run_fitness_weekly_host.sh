#!/bin/bash
# Tier 2 Weekly fitness — host 端執行器（2026-08-07）
#
# ## 為什麼 weekly 必須在 host 跑
#
# weekly 的多數步驟需要 host 才有的東西：`docker` CLI（三者對應稽核要問 FastAPI
# runtime）、`powershell`（Windows 排程存活）、sibling repo（SSO TTL 跨 repo 對照）、
# host 的目錄結構（測試套件、文件掃描）。實測：容器內 32 步有 6 步 RED，host 只有 1 步。
#
# 先前是容器內的 APScheduler 直接跑 run_fitness_weekly.sh —— 那個環境本來就做不到，
# 再加上 CRLF 讓它連 bash 都過不了（2026-W23~W31 連 9 週 RED）。
#
# ## 分工
#
#   host（本腳本，Windows 排程）  → 真的執行 32 步，把結果寫成 JSON
#   容器（fitness_weekly_job）    → 讀該 JSON：寫 history、算連紅週數、發 digest 告警
#
# 這樣既讓檢核在做得到的環境執行，又保留容器端既有的接收者（producer 訊號、
# LINE digest、連紅追蹤）—— 不是把 job 刪掉了事，那會變成「沒有人收」。
#
# 而且交接檔本身帶時間戳：host 排程若停掉，容器端會因為結果過期而報 RED，
# **「檢核沒跑」不會靜靜地變成「檢核通過」**。
#
# 用法（Windows 排程）：
#   run-selfaudit.cmd scripts/checks/run_fitness_weekly_host.sh
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 2

OUT="$ROOT/wiki/memory/fitness_weekly_last_run.json"
LOG_DIR="$ROOT/backend/logs"
mkdir -p "$(dirname "$OUT")" "$LOG_DIR" 2>/dev/null

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMP_OUT="$(mktemp)"
trap 'rm -f "$TMP_OUT"' EXIT

echo "[fitness-weekly-host] $TS 開始"
# 帶 --strict 維持與原容器端 job 一致的語意（子檢核也吃 strict）。
# 註：2026-08-07 起 runner 的 exit 1 已不再以 --strict 為前提 —— 原本「印著
# N step(s) RED、退出碼卻是 0」，我寫這支 wrapper 時就踩了：報 2 步 RED 卻記 rc=0，
# 交接出去會被寫成 PASS。
bash "$ROOT/scripts/checks/run_fitness_weekly.sh" --strict 2>&1 | tee "$TMP_OUT"
RC=${PIPESTATUS[0]}
echo "[fitness-weekly-host] rc=$RC"

# 結果交給容器端消費。tail 只留最後 40 行 —— digest 用得到的就是結論那段，
# 全文留在 host 的 log 裡；把整份塞進 JSON 只會讓交接檔變得沒人想讀。
python - "$OUT" "$TS" "$RC" "$TMP_OUT" <<'PY'
import json, sys
out, ts, rc, tmp = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]
try:
    tail = "\n".join(open(tmp, encoding="utf-8", errors="replace").read().splitlines()[-40:])
except OSError:
    tail = ""
json.dump({"rc": rc, "ts": ts, "tail": tail, "runner": "host"},
          open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"  已寫入交接檔：{out}")
PY

# ── 治理儀表板：在 host 端 regenerate ───────────────────────────────────
# 2026-08-27 加。儀表板唯一的排程是容器內的 02:30 cron，而 §3（最近 commits）
# 與 §4（最近 session）在容器裡**結構上就取不到**（無 git、無 ~/.claude）。
# 保留機制（L73 非 clobber）讓它們不會被洗成空白 —— 但也因此靜靜地留在原地：
# 實測 §3 停在三個月前的 v6.36/v6.37，§4 停在 2026-07-30，
# 而檔頭寫的是「Generated: 今天」。這份檔案的定位是「session 啟動讀它取快照」。
#
# weekly 本來就跑在 host（git 與 ~/.claude 都在），是唯一合適的接手者。
# 刻意不讓它影響 RC —— 儀表板沒生成出來不該把 weekly 判成 RED，
# 但要出聲；真正的哨兵是 §3/§4 保留值上的時間戳年齡。
echo "[fitness-weekly-host] regenerate 治理儀表板（host 端才取得到 §3/§4）"
if python "$ROOT/scripts/checks/generate_governance_dashboard.py" >/dev/null 2>&1; then
    echo "  ✓ 治理儀表板已更新"
else
    echo "  ⚠ 治理儀表板 regenerate 失敗（不影響 weekly 判定，但 §3/§4 會繼續變舊）"
fi

exit "$RC"
