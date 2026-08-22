#!/usr/bin/env bash
# build 時的身分綁定 —— **由工具產生，不手動維護**。
#
# 為什麼是綁定而不是相等（CK_FacilityDev 2026-08-21 的形狀）：
#
#   version = 人給的語意版號（這一輪做了什麼）
#   commit  = 機器算的內容識別（跑的是哪一份程式碼）
#
# 兩者語意不同、不該比對相等，但**綁在一起**就能回答出事時真正要問的那句：
# 「公網跑的 1a0d7d3c，到底是不是 v6.60？」
#
# 三個實作細節都是他們踩過才知道的，這裡逐一遵守：
#   1. 綁定由工具在落檔（build）當下自動寫 —— 手動維護的綁定就是下一個會漂移的東西
#   2. 綁定記在**內容側**（映像的 ENV），不是文件側 ——
#      內容變了一定會經過 build，而文件不一定會跟著改
#   3. 讀不到就回 unknown，不給看起來正常的預設值
#
# 用法：
#   source scripts/deploy/build-args.sh
#   docker compose -f docker-compose.production.yml build backend

set -euo pipefail
_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

CK_BUILD_COMMIT="$(git -C "$_root" rev-parse --short HEAD 2>/dev/null || echo unknown)"
CK_BUILD_TIME="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

# 語意版號取自 CLAUDE.md 的版本行 —— 那是它的 SSOT（人維護的那一份）。
# 讀不到就 unknown，不猜。
# ⚠️ 逐行找，不要用 read(N) 截斷 —— CLAUDE.md 的前幾行本身就是超長的
# 歷代摘要串接，2026-08-21 第一版用 read(4000) 抓不到而回 unknown。
# （那次是「讀不到就回 unknown」的設計讓我看見的 —— 若當初給了一個
#  看起來正常的預設值，這個 bug 會一直躲著。）
# ⚠️ 路徑用**環境變數**傳進 python，不要內插進 `-c` 的字串 ——
# `$_root` 在 Windows/Git Bash 下是 `D:\CKProject\...`，內插後反斜線
# 會被當成跳脫字元吃掉，於是永遠讀不到檔而回 unknown。
# 2026-08-21 為此連錯兩次（先誤判成 read(4000) 截斷、再誤判成正則）——
# 第三次才停下來直接看那一行的實際字元，證明正則與行都是對的。
# **連錯兩次就別再猜第三次，去看實際的東西。**
CK_BUILD_VERSION="$(CK_MD="$_root/CLAUDE.md" python -c "
import io, os, re, sys
try:
    v = 'unknown'
    with io.open(os.environ['CK_MD'], encoding='utf-8') as f:
        for line in f:
            m = re.search(r'\*\*版本\*\*: (v[0-9][0-9.]*)', line)
            if m:
                v = m.group(1); break
    sys.stdout.write(v)
except Exception:
    sys.stdout.write('unknown')
" 2>/dev/null || echo unknown)"

# 工作樹有未提交的**程式碼**變更時，commit 不足以識別跑的是什麼 —— 標出來。
# ⚠️ 排除 runtime 狀態檔：`backend/config/remote_backup.json` 由異地備份排程
# 每次執行寫入（NAS 份數／最新檔／結果），它一直都是「已修改」狀態而
# 不該提交。把它算進 dirty，等於這個標記永遠亮著 ⇒ 亮著等於沒有訊號。
if ! git -C "$_root" diff --quiet HEAD -- backend \
        ':(exclude)backend/config/remote_backup.json' 2>/dev/null; then
    CK_BUILD_COMMIT="${CK_BUILD_COMMIT}-dirty"
fi

export CK_BUILD_COMMIT CK_BUILD_TIME CK_BUILD_VERSION
echo "build 綁定：${CK_BUILD_VERSION} @ ${CK_BUILD_COMMIT} (${CK_BUILD_TIME})"
