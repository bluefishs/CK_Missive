#!/usr/bin/env bash
# 自我檢核入口（CK_Missive）
#
# 走查本身的實作在 `scripts/checks/.shared-selfaudit/run.sh`
# （canonical: shared-modules/selfaudit/src/run.sh）—— **禁手改**，要改回上游改；
# drift 由 `bash ../shared-modules/sync-vendored.sh --check` 擋。
#
# 2026-08-09 轉為薄包裝。轉換前這一份是**五個 repo 裡最舊的**：
# 容器名與 adapter 路徑寫死、不讀 config，儘管 config 早就有 `auth.container`。
# 「canonical 的原生 repo 自己最落後」在本專案已是第二次
# （前次是它一度以手動 cp 消費引擎，見 sync-vendored.sh 的註解）。
# **原生不等於豁免。**
#
# 本檔保留的是 CK_Missive 特有的一件事：**業務資料護欄**。
# 走查會真的點擊頁面，理論上可能誤觸寫入；前後各取一次業務表計數比對，
# 有變動即 exit 2。這是本 repo 才需要的（它是唯一有大量業務寫入的系統），
# 刻意不做成共用層的 config hook —— 那會把「跑任意指令」的能力放進共用層。
#
#   bash scripts/checks/run_ui_smoke.sh           # 深度（flows）
#   bash scripts/checks/run_ui_smoke.sh --sweep   # 廣度（全站路由）
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

SNAP="$(mktemp)"
trap 'rm -f "$SNAP"' EXIT
python "$ROOT/scripts/checks/ui_smoke_data_guard.py" --snapshot > "$SNAP" 2>/dev/null || SNAP=""

bash "$ROOT/scripts/checks/.shared-selfaudit/run.sh" "$@"
RC=$?

if [ -n "$SNAP" ]; then
  echo ""
  # 資料被動到就是 exit 2（未驗完/需人看），不因走查本身「跑完了」而放行
  python "$ROOT/scripts/checks/ui_smoke_data_guard.py" --compare "$SNAP" || RC=2
fi
exit $RC
