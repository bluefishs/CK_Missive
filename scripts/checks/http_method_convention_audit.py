#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""端點一律 POST 的慣例，有沒有人在管（C1）。

## 為什麼有這支

`.claude/rules/development-rules.md` 第 24 行白紙黑字寫著「**所有 endpoint POST**」，
而 2026-08-24 盤點發現：**175 支檢核腳本裡沒有一支在驗 HTTP 方法**。

規範寫了，但它只是文字 —— 這正是 CK_AaaP 同日那句
「**散文不帶設定**」：文件裡寫「這支排程可回溯版控」不代表有東西在強制它。

實測 740 個端點裡 21 條是純 GET（2.9%），其中 **15 條是外部工具強制的**
（healthcheck 只發 GET、SSE 的 EventSource 只能 GET、Swagger 是瀏覽器導覽），
**5 條是真違反**。

## 判準

* 純 GET 且不在 `FORCED_GET` 白名單 ⇒ 缺口；
* baseline 內的已知項不判紅（逐步清），**新增的一律 RED**；
* 白名單每一條都要能回答「**為什麼它只能是 GET**」——
  不是「為什麼它是 GET」，而是「為什麼它**不能**改成 POST」。

## ⚠️ 為什麼不直接把那 5 條改成 POST

**改出口就要改整條鏈**（L81）。其中 `/api/ai/memory/digest` 的消費端在
**CK_Hermes** 的 `query.py`（不在本 repo 的 skill 包裡）—— 單方面改會
讓那條整合鏈斷掉，而它的失敗會看起來像「Hermes 壞了」。
⇒ 列入 baseline、走跨 repo 協作，不在這裡逕改。

退出碼：0 GREEN／2 RED（新增違反慣例的 GET，或探測不可用）。
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

CONTAINER = "ck_missive_backend"
BASELINE = Path(__file__).with_name("http_method_convention_baseline.json")

#: 只能是 GET 的路徑 —— 每一條要回答「為什麼它**不能**改成 POST」。
FORCED_GET = [
    (r"^/api/health", "cloudflared healthcheck、Prometheus blackbox exporter、"
                      "Docker HEALTHCHECK **只發 GET**，改 POST 它們就探不到"),
    (r"^/api/(docs|redoc)$", "Swagger UI／ReDoc 是瀏覽器導覽，POST 開不了頁"),
    (r"/live-activity/stream$", "SSE —— 瀏覽器的 `EventSource` API **只能發 GET**，"
                               "沒有 POST 版本"),
    (r"^/api/debug/cors$", "CORS 測試端點：預檢與簡單請求本來就是 GET 語意"),
]

_PROBE = r'''
import json, sys
sys.path.insert(0, "/app")
from main import app
out = []
for r in app.routes:
    p = getattr(r, "path", None)
    if not p or not str(p).startswith("/api"):
        continue
    ms = sorted(m for m in (getattr(r, "methods", None) or []) if m not in ("HEAD", "OPTIONS"))
    out.append({"path": str(p), "methods": ms})
print("@@JSON@@" + json.dumps(out))
'''


def probe() -> list[dict] | None:
    try:
        r = subprocess.run(
            ["docker", "exec", "-i", "-e", "PYTHONIOENCODING=utf-8",
             "-w", "/app", CONTAINER, "python", "-"],
            input=_PROBE.encode("utf-8"), capture_output=True, timeout=180)
    except FileNotFoundError:
        print("[RED] 找不到 docker CLI —— 無法取得 runtime 事實，不下結論", file=sys.stderr)
        return None
    except subprocess.TimeoutExpired:
        print("[RED] 容器探測逾時", file=sys.stderr)
        return None
    for line in (r.stdout or b"").decode("utf-8", "replace").splitlines():
        if line.startswith("@@JSON@@"):
            return json.loads(line[len("@@JSON@@"):])
    print(f"[RED] 探測沒有回傳結果：{(r.stderr or b'').decode('utf-8', 'replace')[-300:]}",
          file=sys.stderr)
    return None


def why_forced(path: str) -> str | None:
    for pat, reason in FORCED_GET:
        if re.search(pat, path):
            return reason
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="端點 POST 慣例稽核")
    ap.add_argument("--ci", action="store_true", help="新增違反即 exit 2")
    ap.add_argument("--update-baseline", action="store_true",
                    help="把目前的違反寫成 baseline（只在**每條都已決定接受**時用）")
    args = ap.parse_args()

    rows = probe()
    if rows is None:
        return 2

    get_only = sorted({r["path"] for r in rows if r["methods"] == ["GET"]})
    # 找不到東西不得回綠 —— 740 個端點不可能一條 GET 都沒有（/api/health 一定在）
    if not rows:
        print("[RED] 探測回空清單 —— 那是掃描壞了不是現況", file=sys.stderr)
        return 2

    gaps = [p for p in get_only if not why_forced(p)]

    base = []
    if BASELINE.exists():
        try:
            base = json.loads(BASELINE.read_text(encoding="utf-8")).get("known", [])
        except Exception:
            base = []
    new = sorted(set(gaps) - set(base))
    fixed = sorted(set(base) - set(gaps))

    if args.update_baseline:
        BASELINE.write_text(json.dumps(
            {"_why": "已知違反 POST 慣例的 GET 端點，逐步清；新增的一律 RED。"
                     "每一條要嘛改成 POST，要嘛加進 FORCED_GET 並寫明"
                     "「為什麼它不能改成 POST」。",
             "known": sorted(gaps)}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"baseline 已更新：{len(gaps)} 條")
        return 0

    print("=" * 66)
    print("端點 POST 慣例稽核（runtime methods）")
    print("=" * 66)
    print(f"  /api 端點總數      : {len(rows)}")
    print(f"  純 GET             : {len(get_only)}")
    print(f"  其中外部工具強制   : {len(get_only) - len(gaps)}")
    print(f"  違反慣例           : {len(gaps)}   baseline {len(base)}")

    if fixed:
        print(f"\n  ✓ 已改好 {len(fixed)} 條 —— 請跑 --update-baseline 鎖住改善：")
        for p in fixed:
            print(f"      {p}")
    if new:
        print(f"\n  [RED] 新增 {len(new)} 條違反 POST 慣例的 GET 端點：")
        for p in new:
            print(f"      {p}")
        print("\n  規範：`.claude/rules/development-rules.md` §24「所有 endpoint POST」")
        print("  若它**不能**改成 POST（外部工具強制），加進本檔 FORCED_GET 並寫明理由。")
        return 2 if args.ci else 1

    print("\n  [GREEN] 沒有新增違反慣例的 GET 端點")
    if gaps:
        print(f"  （baseline 內仍有 {len(gaps)} 條待清）")
        print("  ⚠️ 其中 `/api/ai/memory/digest` 的消費端在 **CK_Hermes** 的 query.py ——")
        print("     改它是跨 repo 的事（L81：換了出口就要換整條鏈），走協作不逕改。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
