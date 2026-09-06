#!/usr/bin/env bash
# 視覺走查週排程（weekly 116，**僅報告**）—— 2026-09-06 機制圖缺口 4 的另一半。
#
# 為什麼不判紅：這一層要的是**人看圖**才看得出的東西（截字、遮蔽、配色、版面感）。
# 能機械判定的部分已經在 weekly 111（手機品質五指標）與 109（整頁溢出）擋著了。
# 把「人要看」的東西做成閘門，只會得到一個沒有人看的紅燈。
#
# 所以這支只負責一件事：**每週把圖拍下來、留在同一個地方**，
# 讓 session 內要判讀時有東西可看，而不是每次都要有人想起來手動跑一次。
#
# 產出：docs/health/visual/<YYYYMMDD>/*.png ＋ 統一結果契約 visual_walk.json
set -uo pipefail
cd "$(dirname "$0")/../.." || exit 0

DAY="$(date +%Y%m%d)"
OUT="docs/health/visual/${DAY}"

echo "=== 視覺走查（weekly 116，僅報告）==="
if [ ! -f scripts/checks/.shared-selfaudit/run.sh ]; then
  echo "  [SKIP] 找不到走查引擎"
  exit 0
fi

# 代表頁：手機最常看的五頁（owner 09-05「優先處理 RWD」那批）
ROUTES="dashboard,documents,contract-cases,erp/quotations,pm/cases"
# routes 不帶前導斜線 —— git bash 會把 /x 轉成 Windows 路徑（L 家族的老坑）
bash scripts/checks/.shared-selfaudit/run.sh --visual "--routes=${ROUTES}" >/tmp/visual_walk.log 2>&1
RC=$?

N=$(find "${OUT}" -name '*.png' 2>/dev/null | wc -l | tr -d ' ')
if [ "${N}" = "0" ]; then
  echo "  [SKIP] 沒有拍到圖（憑證或引擎不可用）—— 不當成綠燈"
  SUMMARY="未拍到圖（rc=${RC}）"
else
  echo "  拍了 ${N} 張 → ${OUT}"
  echo "  ⚠️ 這一層要人看：下一個 session 判讀時開這個目錄，別只看數字。"
  SUMMARY="拍了 ${N} 張圖 → ${OUT}"
fi

PYTHONIOENCODING=utf-8 python - "$SUMMARY" "$N" <<'PY' 2>/dev/null || true
import sys
from pathlib import Path
sys.path.insert(0, str(Path("scripts/checks").resolve()))
from lib.result_contract import write_result
write_result("visual_walk", 0, sys.argv[1], {"screenshots": int(sys.argv[2] or 0)}, report_only=True)
PY
exit 0
