#!/usr/bin/env python
"""部署後驗證（L76 + L93）—— 三層 200 不代表系統能用。

## 為什麼需要這一支

**L76**（Windows 殭屍埠）：後端 rebuild 後 host:8001 可能仍指向舊行程，
容器 healthy 而公網是死的 —— 所以要驗 host／公網首頁／公網 API 三層。

**L93**（2026-08-16 事故，本支的直接起因）：加 `approved_by` 後
`ExpenseInvoice` 有兩個外鍵指向 `users`，SQLAlchemy mapper 初始化失敗，
所有碰到 User 的查詢爆掉，`POST /api/auth/google` 回 500 ——
**owner 回報「系統無法登入」**。

而當時 **L76 的三層全部是 200**：`/health` 與首頁不觸發 ORM mapper 設定。
連我當天剛建的八條生命跡象也照不到（它們直接查 SQL，不走 ORM relationship）。

→ 所以驗證要多一層：**一條會真的走到 ORM 與認證鏈的端點**。

## 判準

| 層 | 端點 | 它證明什麼 |
|---|---|---|
| 1 | `http://localhost:8001/health` | 容器內服務活著（且 host 埠沒被殭屍佔住）|
| 2 | 公網首頁 | Tunnel 與靜態檔正常 |
| 3 | 公網 `/api/health` | 公網能打到後端 |
| **4** | 公網 `/api/auth/check` | **會走 ORM 與認證鏈** —— 401 是正確答案，**500 代表 mapper 或 DB 壞了** |

⚠️ 第 4 層的正確答案是 **401/403 而不是 200** —— 未帶憑證本來就該被拒絕。
把 401 當失敗會讓這一層永遠紅；把 500 當通過則等於沒有這一層。
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "https://missive.cksurvey.tw"

LAYERS = [
    ("host:8001/health", "http://localhost:8001/health", {200}, "容器內服務活著（L76 殭屍埠）", "GET"),
    ("公網首頁", f"{BASE}/", {200}, "Tunnel 與靜態檔正常", "GET"),
    ("公網 /api/health", f"{BASE}/api/health", {200}, "公網打得到後端", "GET"),
    # L93：這一層才照得到 ORM／認證鏈。401 是正確答案。
    # ⚠️ 必須用 POST：本專案**所有端點都是 POST**（開發規約），
    # 用 GET 打會得到 404 —— 那等於這一層什麼都沒驗到（首版正是如此）。
    # 401 是正確答案（未帶憑證本來就該被拒絕）；**500 才是壞了**。
    ("公網 /api/auth/check", f"{BASE}/api/auth/check",
     {401, 403}, "**會走 ORM 與認證鏈** —— 500 代表 mapper 或 DB 壞了", "POST"),
]


def probe(url: str, method: str = "GET") -> int:
    data = b"{}" if method == "POST" else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"User-Agent": "ck-deploy-verify", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return 0


def main() -> int:
    print("=" * 70)
    print("部署後驗證（L76 三層 + L93 ORM／認證層）")
    print("=" * 70)
    print()

    bad = []
    for name, url, ok, why, method in LAYERS:
        code = probe(url, method)
        good = code in ok
        if not good:
            bad.append((name, code, why))
        mark = "🟢" if good else "🔴"
        expect = "/".join(str(c) for c in sorted(ok))
        print(f"  {mark} {name:<22} {code or '無回應':<8}（預期 {expect}）")
        print(f"       └ {why}")

    print()
    if bad:
        print("Status: [RED] 部署後驗證未通過")
        for n, c, _ in bad:
            print(f"  · {n} 回 {c or '無回應'}")
        print("\n  host:8001 不通 → Windows 殭屍埠（L76）：`docker restart ck_missive_backend`")
        print("  auth/check 回 500 → ORM mapper 或 DB（L93）：看 backend log 找")
        print("  `AmbiguousForeignKeysError` 之類的 mapper 錯誤；改 ORM 後要**重建**不能只 docker cp。")
        return 2
    print("Status: [GREEN] 四層皆通過（含 ORM／認證鏈）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
