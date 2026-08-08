# -*- coding: utf-8 -*-
"""公網暴露稽核 —— API 文件不得對外開放（2026-08-05）。

## 起因

owner 指示：**「有資安風險皆不應該公開」**。

依此掃全 portfolio，實測發現兩個系統把完整 API schema 放在公網上：
  * `lvrland.cksurvey.tw/openapi.json` — 約 1.5 MB 完整 schema，不需憑證
  * `digitaltwin.cksurvey.tw/openapi.json` — 196 個端點的完整 schema
    （來源是 Vite dev server 直接供應 `frontend/openapi.json` 這個產物檔）
  * DT 的 tunnel allowlist 甚至明確寫著「API 文件（公開）」

一份完整 schema 等於把攻擊面地圖交出去：有哪些管理端點、哪些欄位可控、
哪些參數沒有長度限制，一次看完。

## 為什麼要自動化

這三處都不是今天才長出來的，而是**沒有任何機制在問「我們對外開了什麼」**。
修好一次不代表不會再開 —— 新服務、新路由、新的產物檔落進靜態目錄都會再犯。

## ⚠️ 判定必須看內容，不能只看狀態碼

本專案踩過兩次：
  1. SPA fallback 讓任何路徑都回 200（CK_Missive 2026-07-30）
  2. 首版偵測用 `grep redoc`，而擋下的回應 `{"detail":"...","path":"/api/redoc"}`
     本身含 "redoc" 字樣 → **把已經擋好的 pile 誤報成暴露**（2026-08-05，我自己）

所以只認真正的 schema 特徵：JSON 的 `"openapi": "3.x"`，或 HTML 的
swagger-ui / redoc bundle。狀態碼只用來跳過明顯的非 200。

用法：
    python scripts/checks/public_exposure_audit.py
    python scripts/checks/public_exposure_audit.py --ci
退出碼：0 無暴露 / 2 有暴露或無法驗完（--ci 時 exit 1 以外一律視為需處理）
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

HOSTS = [
    "missive.cksurvey.tw",
    "lvrland.cksurvey.tw",
    "pilemgmt.cksurvey.tw",
    "digitaltwin.cksurvey.tw",
    "www.cksurvey.tw",
]

DOC_PATHS = [
    "/openapi.json",
    "/docs",
    "/redoc",
    "/api/openapi.json",
    "/api/docs",
    "/api/redoc",
    "/api/v1/openapi.json",
    "/swagger.json",
]

# ── dev server 外洩（2026-08-08 新增維度）──
#
# 2026-08-08 實測：digitaltwin.cksurvey.tw 公網一直由 Vite **dev server** 提供，
# /src/App.tsx 回 200、**92,129 bytes 完整原始碼公開可讀**。正式 nginx 路徑早已定義
# 卻從未啟動成功過，於是有人接了一條「跑得動」的替代路徑（L84）。
#
# 為何用「探公網產出」而不是「檢查 .env / PM2 狀態」：
#   · .env 已 gitignore、PM2 狀態不在版控 —— 檢查設定等於檢查一個不會傳播的東西
#   · 真正要守的是「公網不得洩漏原始碼」，那與用什麼手段達成無關
#   · 這個判準對五個站台一體適用，任何一站不小心把 dev server 推上公網都會被抓到
DEV_SERVER_PATHS = ["/src/App.tsx", "/src/main.tsx", "/@vite/client", "/@react-refresh"]

# 必須看**內容**而非狀態碼：SPA fallback 會讓任何路徑都回 200 index.html。
# 這些是編譯前原始碼／dev client 才有的特徵。
_DEV_SOURCE = re.compile(
    r"__vite__cjsImport|/@react-refresh|jsxDEV\(|import\s+.*\s+from\s+[\"']/src/|createHotContext",
)


def is_dev_server_leak(body: str) -> tuple[bool, str]:
    """回傳 (是否洩漏, 原因)。空 body 或 SPA fallback 皆不算。"""
    if not body:
        return False, ""
    m = _DEV_SOURCE.search(body)
    return (True, f"dev server 原始碼特徵「{m.group(0)[:28]}」") if m else (False, "")


# 真正的 schema / 互動文件特徵
_SCHEMA_JSON = re.compile(r'"openapi"\s*:\s*"3')
_DOC_HTML = re.compile(r"swagger-ui-bundle|redoc\.standalone\.js|<redoc", re.I)

TIMEOUT = 15


def fetch(url: str) -> tuple[int, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "ck-public-exposure-audit"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read(400_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception:
        return 0, ""


def is_exposed(body: str) -> tuple[bool, str]:
    """只認真正的 schema/文件內容 —— 狀態碼與關鍵字出現都不足以判定。"""
    head = body[:2000]
    if _SCHEMA_JSON.search(head):
        try:
            n = len(json.loads(body).get("paths", {}))
            return True, f"完整 schema，{n} 個端點"
        except Exception:
            return True, "完整 schema（過大或截斷）"
    if _DOC_HTML.search(body):
        return True, "互動式 API 文件頁"
    return False, ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ci", action="store_true")
    args = ap.parse_args()

    print("=" * 70)
    print("公網暴露稽核 —— API 文件與原始碼皆不得對外開放")
    print("=" * 70)

    exposed: list[str] = []
    unreachable: list[str] = []

    for host in HOSTS:
        reachable = False
        for path in DOC_PATHS:
            status, body = fetch(f"https://{host}{path}")
            if status:
                reachable = True
            if status != 200 or not body:
                continue
            bad, why = is_exposed(body)
            if bad:
                exposed.append(f"{host}{path} — {why}")
        for path in DEV_SERVER_PATHS:
            status, body = fetch(f"https://{host}{path}")
            if status:
                reachable = True
            if status != 200 or not body:
                continue
            bad, why = is_dev_server_leak(body)
            if bad:
                exposed.append(f"{host}{path} — {why}")
        if not reachable:
            unreachable.append(host)
        print(f"  {'✗' if any(host in e for e in exposed) else '✓'} {host}")

    if unreachable:
        print(f"\n⚪ 無法連線 {len(unreachable)} 個站台（未驗完，不等於安全）：")
        for h in unreachable:
            print(f"     {h}")

    print("\n" + "=" * 70)
    if exposed:
        print(f"🔴 {len(exposed)} 處對公網開放：")
        for e in exposed:
            print(f"  - {e}")
        print("\n一份完整 schema 等於把攻擊面地圖交出去。")
        print("修法參考：各 repo 的 ApiDocsGuardMiddleware（依來源判斷、回 404 不透露路徑）。")
        return 2
    if unreachable:
        print("🟡 未驗完：有站台連不上，不能判定為安全")
        return 2
    print(f"GREEN: {len(HOSTS)} 個站台皆未對外暴露 API 文件或原始碼")
    return 0


if __name__ == "__main__":
    sys.exit(main())
