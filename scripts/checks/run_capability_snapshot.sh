#!/usr/bin/env bash
# 能力使用度快照入口（2026-08-01）
#
# 必須在 host 執行 —— Prometheus 綁 127.0.0.1:19090，容器內的 localhost 不是它。
#
# 2026-08-10：底層腳本的退出碼改為三態後，本包裝跟著改。
# 原本把 exit 2 一律當「未驗完」吞成 0 —— 那時 2 同時代表「資料還在累積」
# 與「Prometheus 掛了」，吞掉是不得已；但吞掉的代價是**觀測棧真的掛了也沒人知道**。
# 現在底層已分開：
#   0 = 未到判定時點，資料在累積（正常）
#   1 = 判定時點已到 → 提請決策，必須讓它傳出去
#   2 = Prometheus 不可達／標籤不符 → 真故障，必須讓它傳出去
# 停跑偵測仍由 producer registry 的 file_fresh 負責（那問的是另一件事：有沒有跑）。
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1
PYTHONIOENCODING=utf-8 python scripts/checks/capability_usage_snapshot.py
code=$?
case $code in
  0) echo "[capability-usage] 正常（資料累積中或已足夠，未到判定時點）" ;;
  1) echo "[capability-usage] 🟡 判定時點已到 —— 需人工下結論或改寫下一個檢視點"; exit 1 ;;
  *) echo "[capability-usage] ✗ 執行失敗 exit=$code（多為 Prometheus 不可達）"; exit "$code" ;;
esac
