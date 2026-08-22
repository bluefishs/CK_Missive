#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""無認證端點稽核 —— 用 FastAPI runtime dependency 樹，不是 grep。

## 為什麼有這支

owner 2026-08-21：「不應有資訊外漏問題，請加強與規劃作業」。

公網實測（未帶任何憑證）曾取得業務資料：

    /api/documents-enhanced/statistics → 200
    {"total":2017,"current_year_count":496,
     "delivery_method_stats":{"electronic":459,"paper":144}}

根因不是某個端點忘了加，是 `TUNNEL_GUARD_ENABLED=false`
（2026-08-03 的既有決策 —— 它是 all-or-nothing，開了會擋掉整個 SPA）⇒
**所有沒有自帶認證的端點一律對公網開放**。

## 為什麼不沿用既有的 security_scan 規則

`security_issues` 裡「端點缺少認證裝飾器」那條 grep 規則產生了
**122 個被人工標為誤判的 high** —— 誤判是真問題（23 個 open）的 6 倍。
它認不出 `Depends(require_auth())` 這類寫法，於是報一堆假的，
真的反而淹沒在噪音裡。

FastAPI 的 dependency 樹是**權威來源**：端點實際會不會跑認證，
它說了算。同一份資產已用在 `admin_endpoint_ui_consumers.py`。

## 判準

* 在**應用實際執行的容器內**載入 app（host 沒有相依，
  且「檢核要在它保護的東西實際執行的環境裡驗」是本專案已立的判準）；
* 走訪每條 `/api/*` route 的 dependency 樹，找認證相依；
* 不在白名單（登入／webhook／健康檢查／API 文件）的無認證端點即為缺口；
* baseline 內的已知項不判紅（逐步清），**新增的一律 RED**。

退出碼：0 GREEN／2 RED（新增無認證端點，或探測不可用而無法下結論）。
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

#: 預設容器；跨 repo 用 --container 指定
#: （lvrland: ck_lvrland_webmap-backend-1／pile: ck_pilemgmt-backend-1／
#:  dataform: ck_lvrland_dataform-backend-1／DT: ck-tunnel-api-1）
CONTAINER = os.getenv("AUTH_AUDIT_CONTAINER", "ck_missive_backend")
BASELINE = Path(__file__).with_name("public_endpoint_auth_baseline.json")

#: 刻意公開 —— 每一條都要能回答「為什麼它不需要登入」。
#:
#: ⚠️ **跨 repo 用這支時，這份白名單不會自動適用**（2026-08-21 實測）：
#: 對 lvrland 掃出 147 條無認證，其中前幾條是 `/api/auth/{login,register,
#: refresh,logout}` —— 登入流程本來就該公開。CK_lvrland session 起初判斷
#: 「探測跑在 `enforce_route_auth` 之前所以看到未強化的 app」，**那不成立**：
#: 用與容器啟動指令完全相同的匯入方式（`/app` + `backend.app.main`）重跑，
#: log 明確印出 `route_auth_policy_enforced hardened_routes=276`，
#: 結果仍是 147 條。真因是**我把「無認證」直接當成「缺口」而沒套該 repo 的
#: 白名單**。⇒ 跨 repo 使用時必須先由該 repo 自己列出 INTENDED，
#: 否則得到的是一份不可採信的清單（本專案已立的判準：先驗鑑別力再交付）。
#:
#: ⚠️⚠️ **座標系有兩半，白名單只是其中一半**（lvrland 2026-08-21 補充後查證）：
#: 他們用本 repo 的判定本尊逐一歸類 147 條，結果 **真缺口 0** ——
#: 96 條是白名單命中，**另 ~49 條是「有認證，但用的是 service-token 家族」**
#: （`require_service_scope`／`get_user_or_service`／`verify_telegram_secret` 等，
#: 本檔預設 AUTH 清單認不得）。⇒ **只帶白名單不帶認證名單，仍會拿到 49 條假陽性。**
#: 跨 repo 用 `--auth-names` 或 `AUTH_AUDIT_EXTRA_NAMES` 補上該 repo 的認證家族。
INTENDED = [
    (r"^/api/auth/", "登入流程本身（未登入才會打）"),
    (r"^/api/health", "健康檢查（cloudflared/監控要用）"),
    (r"^/api/line/", "LINE webhook（走 X-Line-Signature 驗簽）"),
    (r"^/api/telegram/", "Telegram webhook（走 token 路徑）"),
    (r"^/api/discord/", "Discord interactions（走簽章驗證）"),
    (r"^/api/hermes/", "Hermes ACP（走 X-Service-Token）"),
    (r"^/api/public/", "刻意公開的唯讀端點"),
    (r"^/api/(docs|redoc|openapi)", "API 文件（另有來源守衛擋公網，見 main.py）"),
    (r"^/api/security/csp-report", "瀏覽器自動回報 CSP 違規，無法帶憑證"),
    (r"^/api/secure-site-management/csrf-token", "CSRF 自癒需要（L68），必須未登入可取"),
    # ⚠️ 2026-08-21 複驗更正：原本寫「生產實測 404/403」是**未經驗證的宣稱**
    # （CK_FacilityDev 提醒「baseline 收的是現況，不保證現況是對的」後回頭驗）。
    # 實測 6 條 debug 路由（含會吐業務資料的 documents/count 與 documents/raw）：
    # POST 一律 401、GET 一律 404 —— 擋住了，但**回的是 401 不是 403**。
    #
    # 更重要的是它暴露本工具的限制：dependency 樹說這些端點沒有認證相依，
    # 實際卻回 401 ⇒ **認證來自中介層而不是 dependency**，而本工具看不到中介層。
    # ⇒ 「無認證」這個判定是**保守的**（可能高估），但反過來不成立：
    # 中介層若有例外路徑，dependency 樹也看不出來。跨 repo 尤其要注意。
    (r"^/api/debug/", "開發除錯端點（2026-08-21 公網實測：POST 401／GET 404，"
                      "認證由中介層提供，dependency 樹看不到）"),
]

_PROBE = r'''
import json, sys
# 各 repo 的容器結構不同：Missive 是 /app::main，lvrland/pile 是
# /app/backend::app.main。逐個候選試，**找不到就說找不到，不猜也不回空**
# —— 回空會被讀成「沒有無認證端點」，那是最糟的假綠。
import importlib
app = None
_tried = []
for _path, _mod in (("/app", "main"), ("/app/backend", "main"),
                    ("/app/backend", "app.main"), ("/app", "app.main"),
                    ("/app", "backend.main")):
    if _path not in sys.path:
        sys.path.insert(0, _path)
    try:
        _m = importlib.import_module(_mod)
        _c = getattr(_m, "app", None)
        if _c is not None and hasattr(_c, "routes"):
            app = _c
            break
    except Exception as _e:
        _tried.append(f"{_path}::{_mod} -> {type(_e).__name__}")
if app is None:
    print("@@JSON@@" + json.dumps({"_error": "app not found", "tried": _tried[:5]}))
    sys.exit(0)
AUTH = tuple(n for n in "__AUTH_NAMES__".split(",") if n)
def deps(route):
    out, d = set(), getattr(route, "dependant", None)
    if not d:
        return out
    stack = [d]
    while stack:
        cur = stack.pop()
        c = getattr(cur, "call", None)
        if c is not None:
            out.add(getattr(c, "__qualname__", getattr(c, "__name__", str(c))))
        stack.extend(getattr(cur, "dependencies", []) or [])
    return out
rows = []
for r in app.routes:
    p = getattr(r, "path", None)
    if not p or not p.startswith("/api"):
        continue
    names = deps(r)
    # 帶上 method：同一路徑可能 GET 有認證而 POST 沒有，只以 path 為單位
    # 會把兩者混成一筆而看不出差別（CK_AaaP session 2026-08-21 指出的盲區，
    # 他們的形態是「只探 GET，而 POST-only 的端點回 405 被讀成沒問題」；
    # 這裡讀的是 runtime 樹本來就涵蓋所有方法，缺的是**報告要印出來**）。
    ms = sorted(getattr(r, "methods", None) or [])
    ms = [m for m in ms if m not in ("HEAD", "OPTIONS")] or ms
    rows.append({"path": p, "methods": ms,
                 "authed": any(any(a in n for a in AUTH) for n in names)})
print("@@JSON@@" + json.dumps(rows, ensure_ascii=False))
'''


def probe(container: str = CONTAINER, extra_auth: str = "") -> list[dict] | None:
    # 用 stdin 傳程式碼，不寫檔 —— 寫檔要依賴該容器剛好有某個可寫掛載，
    # 而那是 Missive 專有的（`backend/logs:/app/logs`）。2026-08-21 跨 repo
    # 實測：對 lvrland 直接回 "can't open file '/app/logs/_auth_probe.py'"。
    # 明確帶 PYTHONIOENCODING，否則含中文註解的程式碼在部分容器會解碼失敗。
    names = list(AUTH_DEFAULT) + [n.strip() for n in (extra_auth or "").split(",") if n.strip()]
    code = _PROBE.replace("__AUTH_NAMES__", ",".join(dict.fromkeys(names)))
    try:
        r = subprocess.run(
            ["docker", "exec", "-i", "-e", "PYTHONIOENCODING=utf-8",
             "-w", "/app", container, "python", "-"],
            input=code.encode("utf-8"),
            capture_output=True, timeout=180,
        )
        r = subprocess.CompletedProcess(
            r.args, r.returncode,
            (r.stdout or b"").decode("utf-8", "replace"),
            (r.stderr or b"").decode("utf-8", "replace"))
    except FileNotFoundError:
        print("[RED] 找不到 docker CLI —— 無法取得 runtime 事實，不下結論", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[RED] 容器探測逾時", file=sys.stderr)
        return None
    for line in (r.stdout or "").splitlines():
        if line.startswith("@@JSON@@"):
            return json.loads(line[len("@@JSON@@"):])
    print(f"[RED] 探測沒有回傳結果：{(r.stderr or '')[-300:]}", file=sys.stderr)
    return None


#: 認證相依名稱 —— **單一來源**。先前這份清單同時存在於 `_PROBE` 字串裡
#: 與模組層，兩份會各自演化（正是本專案反覆記的「同一件事有兩份說法」）。
#: 現在只有這一份，探測時注入進去。
AUTH_DEFAULT = (
    "require_auth", "require_admin", "require_superuser", "get_current_user",
    "optional_auth", "is_admin_user", "is_superuser_user", "verify_service_token",
    "get_admin", "service_auth", "require_service", "require_scope",
    "get_current_active_user", "verify_token", "auth_required",
)

#: 座標檔位置（相對於該 repo 根）。**由本腳本產生，不手寫** ——
#: SSOT 仍是上面的 INTENDED 與 AUTH 常數，JSON 只是它們的機器可讀投影。
#: 手寫會立刻變成第二份事實（本專案反覆踩過：兩份說法不一致時沒有一方會報錯）。
COORD_REL = "docs/health/auth-coordinates.json"


def coordinates_fingerprint() -> str:
    """座標系的內容指紋 —— 鎖住「條目數不變而內容改了」。

    2026-08-21 CK_FacilityDev 的實例：他們第一版指紋只取 `(型別, 值域筆數)`，
    結果套了 **814 處 `required` 旗標而指紋竟然沒變** —— 旗標改變行為卻不動型別。
    **「數量不變而內容全變」是最難察覺的漂移。**

    對應到這裡：baseline 只鎖「缺口清單」，鎖不住
    ①白名單 pattern 改了但條目數相同 ②**理由改了**（理由改＝判斷改，
    而判斷才是白名單真正的內容）③認證名單換掉一個名稱但數量相同。
    ⇒ 指紋取 **(pattern, 理由) 與認證名單的全文**，不是條目數。
    """
    import hashlib
    payload = json.dumps(
        {"intended": [[p, r] for p, r in INTENDED], "auth": sorted(AUTH_DEFAULT)},
        ensure_ascii=False, sort_keys=True)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()[:8]


def load_coordinates(repo_root: str) -> dict | None:
    """讀目標 repo 自己宣告的審計座標系。

    2026-08-21 lvrland 提的源頭解：跨 repo 工具讀不到目標 repo 的座標系
    （認證函式名單＋公開白名單＋退出碼語意），只能靠人肉傳 —— 於是
    「判準 11：跨 repo 要先套該 repo 的白名單」永遠停在紀律層次，
    而紀律會被忘記。**有這份檔就自動讀，判準就從紀律變成機制。**

    找不到不是錯 —— 該 repo 還沒落檔而已，退回預設並在報告裡說明。
    """
    p = Path(repo_root) / COORD_REL
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        # 壞掉的座標檔比沒有更危險：它會讓人以為已經套上了
        print(f"[RED] 座標檔無法解析：{p}\n      {type(e).__name__}: {e}", file=sys.stderr)
        raise SystemExit(2)


def why_intended(path: str, extra: list[tuple[str, str]] | None = None) -> str | None:
    for pat, reason in list(INTENDED) + list(extra or []):
        if re.search(pat, path):
            return reason
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="無認證端點稽核（runtime dependency 樹）")
    ap.add_argument("--ci", action="store_true", help="新增缺口即 exit 2")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--container", default=CONTAINER,
                    help="要探測的後端容器（跨 repo 用）")
    ap.add_argument("--auth-names", default=os.getenv("AUTH_AUDIT_EXTRA_NAMES", ""),
                    help="該 repo 額外的認證相依名稱（逗號分隔）。"
                         "**認證名單與白名單一樣是座標系的一部分** —— "
                         "只帶白名單不帶認證名單，仍會得到假陽性"
                         "（lvrland 實測：49 條走 service-token 家族"
                         "`require_service_scope`／`get_user_or_service`／"
                         "`verify_telegram_secret`，本檔預設清單認不得）")
    ap.add_argument("--repo", default=".",
                    help=f"目標 repo 根 —— 會自動讀 {COORD_REL}（若有），"
                         "把該 repo 自己宣告的認證名單與公開白名單套上去")
    ap.add_argument("--emit-coordinates", action="store_true",
                    help=f"把本 repo 的座標系輸出成 {COORD_REL} 供其他 repo 的"
                         "工具讀取（由常數產生，不手寫，避免第二份事實）")
    ap.add_argument("--update-baseline", action="store_true",
                    help="把目前的缺口寫成 baseline（只在**確認每一條都已處理或已決定接受**時用）")
    args = ap.parse_args()

    if args.emit_coordinates:
        out = Path(args.repo) / COORD_REL
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({
            "_why": "本 repo 的審計座標系。由 public_endpoint_auth_audit.py "
                    "--emit-coordinates 產生，**不要手寫** —— SSOT 是該腳本的"
                    "INTENDED 與 AUTH 常數，手寫會立刻變成第二份事實。",
            "_schema": "portfolio/auth-coordinates/v1",
            "repo": Path(args.repo).resolve().name,
            "container": args.container,
            "auth_dependency_names": sorted(AUTH_DEFAULT),
            "public_routes": [{"pattern": p, "reason": r} for p, r in INTENDED],
            "exit_code_semantics": {"0": "GREEN", "2": "RED 或探測不可用（不下結論）"},
            "fingerprint": coordinates_fingerprint(),
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"座標檔已產生：{out}")
        print(f"  認證名單 {len(AUTH_DEFAULT)} 個｜公開白名單 {len(INTENDED)} 條")
        return 0

    coords = load_coordinates(args.repo)
    extra_intended: list[tuple[str, str]] = []
    if coords and coords.get("container") and coords["container"] != args.container:
        # 座標系不匹配 —— 這正是今天要治的病症本身，不能靜靜套下去。
        # 2026-08-21 實測：`--container ck_lvrland_webmap-backend-1` 而
        # `--repo` 用預設 `.` ⇒ 讀到 Missive 自己的座標檔，還印
        # 「已套用 CK_Missive 宣告的座標系」。結果碰巧沒差，訊息卻是錯的。
        print(f"[RED] 座標系不匹配：你在掃 `{args.container}`，"
              f"而 {args.repo} 的座標檔宣告的是 `{coords['container']}`。\n"
              f"      請用 `--repo <目標 repo 根>` 指向該 repo 自己的 "
              f"{COORD_REL}；若該 repo 還沒落檔，請它先跑 --emit-coordinates。",
              file=sys.stderr)
        return 2
    if coords:
        names = coords.get("auth_dependency_names") or []
        merged = ",".join(sorted(set(names) - set(AUTH_DEFAULT)))
        args.auth_names = ",".join(x for x in (args.auth_names, merged) if x)
        extra_intended = [(e["pattern"], e.get("reason", "（該 repo 未寫理由）"))
                          for e in (coords.get("public_routes") or [])
                          if e.get("pattern")]
        print(f"  已套用 {coords.get('repo', '?')} 宣告的座標系："
              f"認證名單 +{len(set(names) - set(AUTH_DEFAULT))}／"
              f"白名單 +{len(extra_intended)}")

    rows = probe(args.container, args.auth_names)
    if rows is None:
        # 探測不到就是不知道 —— 不得靜靜回綠（本專案已立此判準）
        return 2

    no_auth = [r["path"] for r in rows if not r["authed"]]
    gaps = [p for p in no_auth if not why_intended(p, extra_intended)]
    #: path -> 該路徑下無認證的方法（報告要印，否則看不出是哪個動詞漏了）
    gap_methods: dict[str, list[str]] = {}
    for r in rows:
        if not r["authed"] and r["path"] in set(gaps):
            gap_methods.setdefault(r["path"], []).extend(r.get("methods") or [])
    #: 同一路徑「有的方法要認證、有的不要」—— 最容易漏看的形態，一律點名
    by_path: dict[str, set[bool]] = {}
    for r in rows:
        by_path.setdefault(r["path"], set()).add(r["authed"])
    mixed = sorted(p for p, st in by_path.items()
                   if len(st) > 1 and not why_intended(p, extra_intended))

    base = []
    if BASELINE.exists():
        try:
            base = json.loads(BASELINE.read_text(encoding="utf-8")).get("known_gaps", [])
        except Exception:
            base = []
    new_gaps = sorted(set(gaps) - set(base))
    fixed = sorted(set(base) - set(gaps))

    if args.update_baseline:
        BASELINE.write_text(json.dumps(
            {"_why": "已知的無認證端點，逐步清；新增的一律 RED。",
             "_fingerprint_why": "座標系（白名單 pattern＋理由＋認證名單）的內容指紋。"
                                 "條目數不變而理由改了 ⇒ 判斷改了 ⇒ 這個值會變，"
                                 "而只鎖缺口清單抓不到那種漂移。",
             "coordinates_fingerprint": coordinates_fingerprint(),
             "known_gaps": sorted(gaps)}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"baseline 已更新：{len(gaps)} 條")
        return 0

    if args.json:
        print(json.dumps({"total": len(rows), "no_auth": len(no_auth),
                          "gaps": sorted(gaps), "new_gaps": new_gaps,
                          "fixed_since_baseline": fixed}, ensure_ascii=False, indent=2))
        return 2 if (args.ci and new_gaps) else 0

    print("=" * 64)
    print("無認證端點稽核（FastAPI runtime dependency 樹）")
    print("=" * 64)
    print(f"  API 端點總數      : {len(rows)}")
    print(f"  無認證            : {len(no_auth)}")
    print(f"  其中刻意公開      : {len(no_auth) - len(gaps)}")
    print(f"  缺口（需要認證）  : {len(gaps)}   baseline {len(base)}")
    if fixed:
        print(f"\n  ✓ 已修好 {len(fixed)} 條 —— 請跑 --update-baseline 鎖住改善：")
        for p in fixed[:10]:
            print(f"      {p}")
    if mixed:
        print(f"\n  [注意] {len(mixed)} 條路徑「有的方法要認證、有的不要」：")
        for p in mixed[:10]:
            has = [f"{'+' if r['authed'] else '-'}{'/'.join(r.get('methods') or [])}"
                   for r in rows if r["path"] == p]
            print(f"      {p}   {' '.join(has)}")
    if new_gaps:
        print(f"\n  [RED] 新增 {len(new_gaps)} 條無認證端點：")
        for p in new_gaps:
            print(f"      [{'/'.join(sorted(set(gap_methods.get(p) or []))) or '?'}] {p}")
        print("\n  修法：在該 router 加 `APIRouter(dependencies=[Depends(require_auth())])`")
        print("        —— 逐一改端點參數會漏，而漏掉的那條不會有人發現。")
        print("  若是刻意公開，請加進本檔的 INTENDED 並**寫明理由**。")
        return 2 if args.ci else 1
    print("\n  [GREEN] 沒有新增的無認證端點")
    if gaps:
        print(f"  （baseline 內仍有 {len(gaps)} 條待清，見 {BASELINE.name}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
