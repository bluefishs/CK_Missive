#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""RWD 手機品質閘門（weekly 111）——把「人看圖才會抱怨」的五件事變成會紅的數字。

owner 2026-09-05：「加強視覺檢核機制，確保 RWD 設計正確性」。

## 為什麼

weekly 109 只守「整頁有沒有被撐寬」；視覺走查拍圖但要人看，而 cron 裡沒有人在看。
這支在 host 上以 390px 登入（adapter 簽臨時憑證，同 run.sh）跑 `rwd_mobile_quality_probe.cjs`，
量五件斷言量得出來的視覺缺陷：截字／字級過小／點擊目標過小／浮動元件遮住控制項／統計卡獨佔一列。

## 判準（09-05 基準校準；門檻寫在下方常數，改門檻要附當時的基準數）

RED    crushedCol ≥ 1（表格欄被壓到 <70px，見下方 reds 的說明）；narrowSelect ≥ 1（下拉被壓到 <80px，手機與 1440 桌面都量）；covered ≥ 1（「功能遮蔽」正是 owner 09-05 的回報）；loneCard ≥ 1（§2.6 ① 手機兩張一列，owner 09-05 明令統一）；
       clipped 超過基線（基線檔 `.rwd_quality_baseline.json`，存量不判紅、新增才紅——同 lib_adoption 的節奏）
YELLOW tinyFont／smallTap 超過基線；探針被導回登入頁 ≥ 1
GREEN  其餘

不動 `.shared-selfaudit/`（vendored）。憑證值不印。
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402
from lib.docker_exec import exec_in  # noqa: E402
from lib.result_contract import write_result  # noqa: E402

ROOT = repo_root()  # 不自算路徑（weekly 93）：自算算錯是靜默的，會讀到別的檔
PROBE = ROOT / "scripts" / "checks" / "rwd_mobile_quality_probe.cjs"
RESULT = ROOT / "wiki" / "memory" / "integration-health" / "rwd-quality.json"
BASELINE = ROOT / "scripts" / "checks" / ".rwd_quality_baseline.json"
CONFIG = ROOT / "selfaudit.config.json"


def _mint_credential() -> dict:
    """同 run.sh：在容器內跑 adapter，只取 COOKIE／USER_INFO 兩行，不印值。"""
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    auth = cfg.get("auth") or {}
    container = auth.get("container")
    adapter = ROOT / (auth.get("adapter_host_script") or "scripts/checks/ui_smoke_auth.py")
    if not container or not adapter.exists():
        return {}
    # 2026-09-06：改走共用層（weekly 93）——`exec_in` 同日補了 env_vars，
    # 它自己處理 MSYS_NO_PATHCONV 與「容器不在回 None」，不必每支腳本各記一次。
    out = exec_in(
        ["python", "-"], container=container, timeout=120,
        stdin=adapter.read_text(encoding="utf-8"), env_vars={"SELFAUDIT_ROLE": "admin"},
    )
    if out is None:
        print("  [WARN] 簽發臨時憑證失敗（容器不在或腳本非 0 退出）")
        return {}
    creds = {}
    for line in out.splitlines():
        for k in ("COOKIE", "USER_INFO", "LOCAL_STORAGE"):
            if line.startswith(k + "="):
                creds[k] = line[len(k) + 1:].strip()
    print(f"  憑證：{'已取得 ' + ' '.join(sorted(creds)) if creds else '未取得（頁面多半會被導回登入）'}")
    return creds


RESULT_DESKTOP = ROOT / "wiki" / "memory" / "integration-health" / "rwd-quality-desktop.json"


def _run_probe(creds: dict, width: int = 390, out: Path = RESULT) -> bool:
    env = dict(os.environ, SELFAUDIT_CONFIG=str(CONFIG), **creds)
    p = subprocess.run(["node", str(PROBE), f"--width={width}", f"--out={out}"], cwd=str(ROOT), env=env, capture_output=True, timeout=900)
    out = p.stdout.decode("utf-8", errors="replace")
    for ln in out.splitlines():
        print("  " + ln)
    if p.returncode != 0:
        print("  [probe stderr] " + p.stderr.decode("utf-8", errors="replace")[-400:])
    return p.returncode == 0


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=== RWD 手機品質閘門（weekly 111）===")
    if not PROBE.exists():
        print("[YELLOW] 探針不存在")
        return 1
    # 判準自檢：`crushedCol` 09-07 新增當天全站跑出 0，而 **0 有兩種意思**
    # （沒有這個問題／這個判準永遠不會紅）。控制測試用判準自己的實作跑造出來的表：
    # 正向一定要紅、兩個負向一定不能紅。它失敗代表**判準壞了**，不是頁面壞了。
    ctl = subprocess.run(["node", str(ROOT / "scripts/checks/rwd_crushed_column_control.cjs")],
                         cwd=str(ROOT), capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=180)
    if ctl.returncode != 0:
        print("[YELLOW] crushedCol 判準的正負向控制沒過——先修判準再看結果")
        print((ctl.stdout or ctl.stderr or "").strip()[:400])
    else:
        print("  判準自檢：crushedCol 正向會紅、負向不紅 ✓")

    creds = _mint_credential()
    if not _run_probe(creds) or not RESULT.exists():
        print("[YELLOW] 探針沒跑完，未驗")
        return 1
    d = json.loads(RESULT.read_text(encoding="utf-8"))
    rows = [r for r in d.get("rows") or [] if not r.get("error") and not r.get("blocked")]
    blocked = int(d.get("blocked") or 0)
    base = json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}
    tot = {k: sum(int(r.get(k) or 0) for r in rows) for k in ("clipped", "tinyFont", "smallTap", "covered", "loneCard", "narrowSelect", "crushedCol")}
    # 桌面 1440 也跑一遍：下拉塌陷／截字／遮蔽在桌面同樣是缺陷（09-05 的桌面回歸手機量不到——手機走收合區、Select 100% 寬）
    drows: list[dict] = []
    if _run_probe(creds, 1440, RESULT_DESKTOP) and RESULT_DESKTOP.exists():
        dd = json.loads(RESULT_DESKTOP.read_text(encoding="utf-8"))
        drows = [r for r in dd.get("rows") or [] if not r.get("error") and not r.get("blocked")]
    print(f"{len(rows)} 頁 @{d.get('width')}px；截字 {tot['clipped']}（基線 {base.get('clipped', '—')}）／字級<11px {tot['tinyFont']}"
          f"（基線 {base.get('tinyFont', '—')}）／點擊目標<28px {tot['smallTap']}（基線 {base.get('smallTap', '—')}）"
          f"／遮蔽 {tot['covered']}／統計卡獨列 {tot['loneCard']}")

    reds: list[str] = []
    yels: list[str] = []
    for r in rows + drows:
        for c in (r.get("narrowTop") or []):
            reds.append(f"{r['route']} @{r.get('width')}px：下拉 {c.get('sel')} 只剩 {c.get('w')}px（選中的值看不到）")
        # 欄位塌陷：AntD 在 scroll.x 下用 table-layout: fixed，固定寬度總和一旦超過 scroll.x，
        # 沒給寬度的那一欄會被壓成幾乎 0 寬而只留 ellipsis —— 09-07 加兩個新欄位後
        # 委託單位／協力廠商兩頁的名稱欄各發生一次，而當時沒有任何判準會紅
        # （整頁不溢出、是 ellipsis 不是硬截、字級與點擊目標都正常）。
        for c in (r.get("crushedTop") or []):
            reds.append(f"{r['route']} @{r.get('width')}px：表格欄「{c.get('text')}」只剩 {c.get('w')}px"
                        f"——固定欄寬總和超過 scroll.x，未給寬度的欄被壓扁")
    for r in drows:
        for c in (r.get("coveredTop") or []):
            reds.append(f"{r['route']} @1440px：{c.get('fixed')} 蓋住 {c.get('target')}「{c.get('text')}」{c.get('cover')}%")
    for r in rows:
        for c in (r.get("coveredTop") or []):
            reds.append(f"{r['route']}：{c.get('fixed')} 蓋住 {c.get('target')}「{c.get('text')}」{c.get('cover')}%")
        for c in (r.get("loneTop") or []):
            reds.append(f"{r['route']}：統計卡「{c.get('text')}」獨佔一列（§2.6 ① 手機兩張一列）")
    if base and tot["clipped"] > int(base.get("clipped", 0)):
        reds.append(f"截字 {tot['clipped']} > 基線 {base.get('clipped')}——新增的截字：")
        for r in rows:
            for c in (r.get("clippedTop") or [])[:2]:
                reds.append(f"    {r['route']}：{c.get('sel')}「{c.get('text')}」超出 {c.get('over')}px")
    # 容忍 +5：這兩個數字隨資料量（分頁頁數、列數）微幅浮動，09-05 晚同一版程式量到 262／265
    if base and tot["tinyFont"] > int(base.get("tinyFont", 0)) + 5:
        yels.append(f"字級<11px {tot['tinyFont']} > 基線 {base.get('tinyFont')}")
    if base and tot["smallTap"] > int(base.get("smallTap", 0)) + 5:
        yels.append(f"點擊目標<28px {tot['smallTap']} > 基線 {base.get('smallTap')}")
    if blocked:
        yels.append(f"{blocked} 頁被導回登入頁（未驗）")
    if not base:
        yels.append("沒有基線檔——首跑；請以本次結果建立 .rwd_quality_baseline.json（存量不判紅、新增才紅）")

    for m in reds[:20]:
        print(f"  [RED] {m}")
    for m in yels[:10]:
        print(f"  [YELLOW] {m}")
    if reds:
        print(f"[RED] {len(reds)} 項——下拉塌陷／遮蔽／統計卡獨列／新增截字")
        return 2
    if yels:
        print("[YELLOW] 見上")
        return 1
    print("[GREEN] 五項手機品質指標未惡化、無遮蔽、統計卡皆兩張一列")
    return 0


if __name__ == "__main__":
    _rc = main()
    # 統一結果契約（2026-09-06）：每層跑完寫同一種形狀，weekly 113 只讀契約就畫得出機制圖
    write_result("rwd_mobile_quality", _rc, "手機品質五指標：rc={}".format(_rc))
    sys.exit(_rc)
