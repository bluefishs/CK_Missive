#!/usr/bin/env bash
# 能力使用度快照入口（2026-08-01）
#
# 必須在 host 執行 —— Prometheus 綁 127.0.0.1:19090，容器內的 localhost 不是它。
# 退出碼 2（資料不足/無法查詢）不視為失敗，屬「未驗完」：本腳本回 0 讓排程
# 不誤報，真正的停跑偵測由 producer registry 的 file_fresh 負責。
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 1
PYTHONIOENCODING=utf-8 python scripts/checks/capability_usage_snapshot.py
code=$?
case $code in
  0) echo "[capability-usage] 資料足夠，已產出" ;;
  2) echo "[capability-usage] 未驗完（資料不足或無法查詢）—— 已寫入快照供後續判定" ;;
  *) echo "[capability-usage] 執行失敗 exit=$code"; exit $code ;;
esac
