#!/usr/bin/env bash
# 走查共用入口（canonical: shared-modules/selfaudit/src/run.sh）— 2026-08-09
#
# ## 為什麼要有這一支
#
# 導入第 5 個 repo 時量到：`run_selfaudit.sh` 在 lvrland 與 pile **去註解後差異 0 行**
# ——兩份完全相同的副本各自維護；DT 那份只因認證型別不同而差 33 行；
# 而 canonical 的原生 repo（CK_Missive）那份反而最舊：容器名與 adapter 路徑**寫死**、
# 不讀 config，明明 config 裡早就有 `auth.container`。
#
# 這正是模組化策略點名的「copy 式」根因：不是沒有規範，是同一段邏輯有 N 份。
# 症狀不會是「其中一份比較舊」，而是**改了一份、其他四份靜靜不同步**，
# 而且沒有任何 gate 會發現（引擎有 drift 稽核，入口腳本沒有）。
#
# ## 分工（刻意不做成萬用 runner）
#
#   共用（本檔）：定位 config → 在容器內簽發憑證 → 傳給引擎 → 選深度/廣度
#   各 repo 保留：認證 adapter（`selfaudit_auth.py`，登入態形狀本來就不同）
#                 + 該 repo 特有的前後置步驟（如 CK_Missive 的業務資料護欄）
#
# repo 特有步驟**不做成 config hook** —— 那會把「跑一段任意指令」的能力放進共用層，
# 下一個 repo 就會往裡面塞第二種、第三種，最後共用層變成五個 repo 的細節總和。
# 薄包裝腳本已經足夠表達「先做 A、再跑走查、最後做 B」。
#
# ## 憑證傳遞：不再逐一列舉變數名
#
# adapter 印出 `KEY=VALUE` 行，本檔**照單全收**（限白名單）。
# 舊寫法是各 repo 各自 `grep '^COOKIE='`、`grep '^USER_INFO='` ——
# 於是 DT 新增 `LOCAL_STORAGE` 時，必須同時改 runner，否則憑證靜靜傳丟
# （2026-08-08 就是這樣把 COOKIE 傳丟、查了五個錯方向）。
# 現在新增一種憑證只要改 adapter 與引擎，入口不必動。
#
# ## 用法（由各 repo 的薄包裝呼叫）
#
#   bash scripts/checks/.shared-selfaudit/run.sh            # 深度（flows）
#   bash scripts/checks/.shared-selfaudit/run.sh --sweep    # 廣度（全站路由）
#   bash scripts/checks/.shared-selfaudit/run.sh --visual   # 視覺走查（拍圖供判讀）
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# 引擎位於 <repo>/scripts/checks/.shared-selfaudit/ → 上推三層即 repo 根
ROOT="$(cd "$HERE/../../.." && pwd)"

# 憑證白名單：只接受這幾個 key。
# 不用「照單全收任意 key」—— adapter 的 stdout 若混進別的東西（警告、debug 行），
# 會變成把任意字串注入成環境變數。
CRED_KEYS="COOKIE USER_INFO LOCAL_STORAGE"

CONFIG_WIN="$ROOT/selfaudit.config.json"
if command -v cygpath >/dev/null 2>&1; then
  CONFIG_WIN="$(cygpath -w "$ROOT/selfaudit.config.json" 2>/dev/null || echo "$CONFIG_WIN")"
fi

# 讀 config 取容器名與 adapter 路徑。兩個既知的坑：
#   1. config 含中文 → Windows python 預設 cp950 讀取會 UnicodeDecodeError（L49.8 家族）
#   2. Git Bash 的 /d/... 路徑 python 認不得 → 用 cygpath 轉回 D:/...
read_cfg() {
  python -c "
import io,json,sys
d=json.load(io.open(sys.argv[1],encoding='utf-8'))
cur=d
for k in sys.argv[2].split('.'):
    cur=(cur or {}).get(k) if isinstance(cur,dict) else None
print(cur if cur is not None else '')
" "$CONFIG_WIN" "$1" 2>/dev/null
}

CONTAINER="$(read_cfg auth.container)"
# adapter 一律以 host 檔案經 stdin 執行：各 repo 容器的掛載結構不同
# （lvrland 的 /app 不是 backend/、DT 的程式在 /app/src），
# 用容器內路徑會在移植時逐一踩雷。預設值涵蓋既有命名。
ADAPTER_REL="$(read_cfg auth.adapter_host_script)"
[ -n "$ADAPTER_REL" ] || ADAPTER_REL="scripts/checks/selfaudit_auth.py"
ADAPTER="$ROOT/$ADAPTER_REL"

MODE="flow"
# 2026-08-24（C3）：走查身分。預設 admin ⇒ **不帶參數時行為與先前完全相同**。
# `--role user` 讓走查以一般同仁身分跑一遍 —— 那個維度先前不存在，
# 而 2026-08-20「同仁變成代碼」就藏在裡面（五個人員下拉對非管理員一律是空的，
# 而走查、tsc、py_compile、模組匯入掃描全部綠燈）。
ROLE="admin"
ARGS=()
for a in "$@"; do
  if [ "$a" = "--sweep" ]; then MODE="sweep"
  elif [ "$a" = "--visual" ]; then MODE="visual"
  elif [ "$a" = "--role" ]; then NEXT_IS_ROLE=1
  elif [ "${NEXT_IS_ROLE:-0}" = "1" ]; then ROLE="$a"; NEXT_IS_ROLE=0
  else ARGS+=("$a"); fi
done

# ── 1. 簽發臨時憑證 ────────────────────────────────────────────────
CRED_ENV=()
if [ -n "$CONTAINER" ] && [ -f "$ADAPTER" ]; then
  echo "[1/2] 簽發臨時檢核憑證（$CONTAINER｜身分=$ROLE）..."
  AUTH_OUT="$(mktemp)"
  trap 'rm -f "$AUTH_OUT"' EXIT
  # role 走**環境變數**：入口用 stdin 傳 adapter，傳不了 CLI 參數。
  # adapter 不支援 role 時這個變數對它無效、照舊跑 —— 不會壞（五 repo 共用）。
  if ! MSYS_NO_PATHCONV=1 docker exec -i -e "SELFAUDIT_ROLE=$ROLE" "$CONTAINER" python - < "$ADAPTER" > "$AUTH_OUT" 2>/dev/null; then
    # 「沒取到」必須說出來：靜靜往下跑會讓整批頁面被導回登入頁，
    # 而症狀（全部 SKIP）看起來像「這些頁面需要登入」，把真正的原因藏起來。
    echo "  ⚠️  簽發失敗（容器未啟動？）—— 僅能跑免登入項目"
  fi
  got=""
  for k in $CRED_KEYS; do
    v="$(grep "^$k=" "$AUTH_OUT" 2>/dev/null | sed "s/^$k=//" | tr -d '\r\n')"
    if [ -n "$v" ]; then CRED_ENV+=("$k=$v"); got="$got $k"; fi
  done
  if [ -n "$got" ]; then
    # 只印 key 不印值 —— 憑證不進 log
    echo "  ✓ 憑證已取得（$got ｜不印任何憑證值）"
  else
    echo "  ⚠️  未取得任何憑證 —— 後續頁面多半會被判未驗"
  fi
else
  # 免登入型（如 CK_Website 靜態站）是正常情況，不是錯誤。
  echo "[1/2] 未設定認證 adapter —— 以未登入身分走查"
fi

# ── 2. 執行引擎 ───────────────────────────────────────────────────
if [ "$MODE" = "sweep" ]; then
  echo "[2/2] 全站頁面健康掃描（廣度）..."
  ENTRY_JS="$HERE/ui_page_sweep.cjs"
elif [ "$MODE" = "visual" ]; then
  # 視覺走查：只負責把圖拍齊，判讀由人或 session 內的 AI 進行。
  # **刻意不進 cron** —— cron 裡沒有人在看圖。約定為每次覆盤輪跑一次。
  echo "[2/2] 視覺走查（拍圖供判讀，不做自動判定）..."
  ENTRY_JS="$HERE/ui_visual_walk.cjs"
else
  echo "[2/2] 流程檢核（深度）..."
  ENTRY_JS="$HERE/ui_flow_smoke.cjs"
fi
if command -v cygpath >/dev/null 2>&1; then ENTRY_JS="$(cygpath -w "$ENTRY_JS")"; fi

# ⚠️ 環境變數與 node 之間**不得插入註解**：註解一旦落在 `\` 續行裡，
# 賦值會被截斷、變數完全沒傳給 node（2026-08-08 在 pile 就是這樣把 COOKIE 傳丟，
# 表面症狀是「走查大量失敗」，查了五個錯誤方向才發現）。
env SELFAUDIT_CONFIG="$CONFIG_WIN" "${CRED_ENV[@]+"${CRED_ENV[@]}"}" \
  node "$ENTRY_JS" "${ARGS[@]+"${ARGS[@]}"}"
