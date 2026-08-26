#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""公網探測的客戶端指紋守衛 —— 「403」不一定是應用層擋的。

## 為什麼有這支

Cloudflare 依 **User-Agent** 擋請求。實測同一個**已知未受保護**的端點
（`/api/health`）：

    curl 預設 UA          → 200
    urllib 預設 UA        → 403   ← Python-urllib/3.x
    urllib 帶瀏覽器 UA    → 200

⇒ 用 Python 預設 UA 去探公網，**每一條都回 403**，而那個 403
**長得正好像「認證有效」**，不像「我被擋在門外」。

本專案 2026-08-21 因此四次得出「已經擋住了」的錯誤結論；
CK_AaaP 2026-08-24 在 pile 一個**進行中的 P0 外洩**上重現同一件事 ——
他們手動 curl 得 200、腳本 urllib 得 403，第一反應是「P0 被修好了」。

**若只用其中任何一個工具，兩種情況下都會寫下一個確信的結論。**

## 判準

拿一個**已知未受保護**的端點當對照組：

* `curl` 與帶瀏覽器 UA 的 urllib 都必須回 200 —— 否則對照組本身不成立，
  這支不下結論（exit 2）；
* 預設 UA 若被擋（403），印出警告並記錄 —— 那是**環境事實**不是故障，
  但任何用預設 UA 探公網的腳本都不可信。

## ⚠️ 本專案的稽核為什麼不受影響

`public_endpoint_auth_audit`／`http_method_convention_audit`／
`router_level_auth_mixing_audit` **完全不對外打 HTTP** ——
它們讀容器內的 FastAPI runtime dependency 樹。結構上免疫。

這支守的是**臨時探測腳本**與**未來可能新增的 HTTP 型檢核**。

退出碼：0（對照組成立且已檢查）／2（對照組不成立，不下結論）。
"""
from __future__ import annotations

import subprocess
import sys
import urllib.error
import urllib.request

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

#: 對照組必須是**已知未受保護**的端點 —— 用受保護的端點當對照，
#: 401/403 分不出是「認證擋的」還是「邊界擋的」，等於沒有對照。
CONTROL_URL = "https://missive.cksurvey.tw/api/health"

#: 保證不存在的路徑 —— 用來測「這個站有沒有 SPA catch-all」。
#: CK_AaaP 2026-08-26 用外部探測證明：本站任意不存在的路徑回
#: **200 + text/html**，只有 `/api/*` 才回 404 JSON。複測確認。
#: ⇒ **「200 ＝ 端點存在且未受保護」會把 catch-all 讀成認證繞過**，
#:   而且兩個方向都會錯：誤判有洞，或漏掉真的洞。
#:   判定必須看 **content-type**，不能只看狀態碼。
CATCHALL_URL = "https://missive.cksurvey.tw/__nonexistent_probe_7f3a9z"
BROWSER_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def via_urllib(ua: str | None, url: str | None = None) -> object:
    rq = urllib.request.Request(
        url or CONTROL_URL, headers={"User-Agent": ua} if ua else {}, method="GET")
    try:
        with urllib.request.urlopen(rq, timeout=20) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception as e:  # noqa: BLE001
        return f"ERR {type(e).__name__}"


def probe_type(url: str) -> tuple:
    """回 (status, content_type) —— catch-all 判定要看 content-type。

    ⚠️ 只看狀態碼分不出「SPA 首頁」與「應用回應了這條路徑」，
    而那兩件事在安全稽核上意思完全相反。
    """
    rq = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA}, method="GET")
    try:
        with urllib.request.urlopen(rq, timeout=20) as r:
            return r.status, (r.headers.get("Content-Type") or "").split(";")[0].strip()
    except urllib.error.HTTPError as e:
        return e.code, (e.headers.get("Content-Type") or "").split(";")[0].strip()
    except Exception as e:  # noqa: BLE001
        return None, f"ERR {type(e).__name__}"


def via_curl() -> object:
    try:
        r = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", "20", CONTROL_URL],
            capture_output=True, text=True, timeout=40)
        return (r.stdout or "").strip() or "?"
    except FileNotFoundError:
        return "no-curl"
    except subprocess.TimeoutExpired:
        return "timeout"


def main() -> int:
    c = via_curl()
    default_ua = via_urllib(None)
    browser_ua = via_urllib(BROWSER_UA)

    print("=" * 62)
    print("公網探測的客戶端指紋守衛")
    print("=" * 62)
    print(f"  對照組（已知未受保護）: {CONTROL_URL}")
    print(f"    curl 預設 UA        → {c}")
    print(f"    urllib 預設 UA      → {default_ua}   ← Python-urllib/3.x")
    print(f"    urllib 帶瀏覽器 UA  → {browser_ua}")

    if str(c) not in ("200", "no-curl") or browser_ua != 200:
        print("\n  [RED] 對照組本身不成立 —— 這支不下結論。")
        print("        可能是公網暫時不可達、或那條端點已改為需認證")
        print("        （那樣它就不再是「已知未受保護」，要換一條）。", file=sys.stderr)
        return 2

    if default_ua == 403:
        print("\n  [注意] **預設 UA 被邊界擋掉（403）**")
        print("    ⇒ 任何用 Python 預設 UA 探公網的腳本，**每一條都會回 403**，")
        print("      而那個 403 長得正好像「認證有效」。")
        print("    ⇒ 探公網一律帶瀏覽器 UA；`requests` 的預設是")
        print("      `python-requests/x.y.z`，同樣帶指紋。")
        print("\n  本專案的三支端點稽核**不對外打 HTTP**（讀容器內 runtime")
        print("  dependency 樹），結構上免疫。這支守的是臨時探測腳本。")
    else:
        print(f"\n  [GREEN] 預設 UA 未被擋（{default_ua}）—— 邊界目前不做 UA 過濾。")
        print("    ⚠️ 這是**環境當下的事實**，不是保證：邊界規則會變，")
        print("       所以探公網仍應主動帶瀏覽器 UA，不要依賴這個結果。")
    # ── 第二種指紋：SPA catch-all ──
    st, ct = probe_type(CATCHALL_URL)
    print(f"\n  SPA catch-all 對照: {CATCHALL_URL}")
    print(f"    保證不存在的路徑 → {st} {ct}")
    if st is None:
        print("    ⚪ 對照組打不到 —— 這一項未驗完，不下結論。")
    elif st == 200 and ct.startswith("text/html"):
        print("    [注意] **任意不存在的路徑回 200 + text/html** —— 本站有 SPA catch-all。")
        print("      ⇒ 探測若以「200 ＝ 端點存在且未受保護」判定，**每一條都會命中**。")
        print("      判定必須看 content-type：`text/html` 是 SPA 首頁，")
        print("      `application/json` 才是應用真的回應了那條路徑。")
        print("      （CK_AaaP 2026-08-26 指出；本 repo 的 `public_exposure_audit`")
        print("       判的是「200 **且**內容命中特徵」，結構上免疫。）")
    elif st == 200:
        print(f"    [注意] 不存在的路徑回 200（{ct}）—— 仍是 catch-all，判定不可只看狀態碼。")
    else:
        print(f"    [GREEN] 不存在的路徑回 {st} —— 沒有 catch-all 混淆。")

    return 0


if __name__ == "__main__":
    sys.exit(main())
