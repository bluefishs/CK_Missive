#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""Hook 有沒有機會被觸發（不是「它存不存在」，也不是「它跑不跑得動」）。

## 為什麼需要這一支

2026-08-30 一天之內查出三種「機制在，但那不是它真正的觸發路徑」：

| 發現 | 形狀 |
|---|---|
| 我 08-29「修好」的 secret guard 修在 `.git/hooks/pre-commit` | `core.hooksPath = frontend/.husky/_` ⇒ **那個檔 git 從不執行**。實測：`.pem` 私鑰加進暫存 → **exit 0 並印「全部檢查通過」** |
| `pre-push`（7,787 B、3 階段守門包） | `.git/hooks/` 那份被旁路，而 husky 底下**沒有實作** ⇒ shim 遇檔案不存在就 `exit 0` ⇒ **從來沒有跑過一次** |
| `link-id-check.ps1` 等三支 | 檔案在、文件寫著「手動執行」，**沒有任何 runner／settings 在叫** |

⚠️ 既有的 `spec_executor_audit`（weekly 39）**問的是相反方向**：
「規範宣告的腳本 → 有沒有執行者」。它的執行者來源是
`run_*.sh` ＋ `backend/app/**` ＋ Windows 排程 —— **不含 git hook 與
`.claude/settings.json`**。所以它在上述三件事全部成立時仍回 GREEN。
本支補的是**反方向**：**執行者存在 → 它有沒有機會被觸發。**

## 四條判準（都是機械式的，沒有推測成分）

1. **`.git/hooks/` 被旁路** —— `core.hooksPath` 指向別處時，該目錄下
   所有非 `.sample` 檔案永遠不會執行。
2. **husky shim 有、實作缺席，且 `.git/hooks/` 有一份被擱置** ——
   代表「有人寫了這個 hook，而它沒有接上」。
   （shim 有、兩邊都沒實作 = 沒人用這個 hook 型別，**不判**。）
3. **`.claude/hooks/*.ps1` 沒有被 `.claude/settings.json` 引用。**
4. **被引用、含中文，卻沒有明示 UTF-8 輸出編碼**（2026-08-30 追加）。

## 為什麼第 4 條也是「可觸達性」

它看起來像編碼細節，實際上是同一種失效：**hook 跑了，而它說的話沒有抵達。**

當日實測：`validate-file-location` 擋下一個 Write，我收到的是

    ?ɮצ?m?H?W: D:/... - 請參考 .claude/rules/architecture.md

—— **擋對了，但看不懂為什麼**，於是那次攔截等同沒有發生。根因是
Windows 主控台預設 cp950，PowerShell 用它編碼 stdout/stderr，
中文被替換成 `?`（有損），而 hook 自己的退出碼完全正常 ⇒ 不會有人發現。

⚠️ **BOM 與輸出編碼是兩件事，都要**：BOM 決定 PowerShell 怎麼**讀**這個檔
（沒有 BOM ⇒ 檔內中文字面量就已經錯了，本 repo 2026-08-27 為 `careful-guard`
付過這個學費）；`[Console]::OutputEncoding` 決定它怎麼**寫**出去。
修好其中一個，另一個照樣讓訊息變成亂碼。

判準只看「有沒有設 UTF-8 輸出編碼」這個機械事實，不試圖執行它 ——
執行需要真實 payload，而不同 hook 的 payload 形狀不同。

## 基線制（刻意不讓它第一天就滿江紅）

上述三類目前共 11 筆，全部是**待 owner 決定**的存量（A42／A45／A46）。
若一律判紅，weekly 會永遠是紅的 —— 而本 repo 記過
「**永遠是紅的訊號與沒有訊號是同一個下場**」。
⇒ 存量寫進 `.hook_reachability_baseline.json`（**帶理由**），
**新增一筆才判紅**。基線筆數每次執行都印出來，數字不動就代表沒有人在清。

## 誰跑它

weekly step 91（`run_fitness_weekly.sh`）。
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.paths import repo_root  # noqa: E402

ROOT = repo_root()
BASELINE = Path(__file__).resolve().parent / ".hook_reachability_baseline.json"

# 檔案內含這段字樣 = 已知且已標註「不會被執行」，不重複報
ACKNOWLEDGED_MARK = "不會被 git 執行"

# 判準 ④：中文訊息要抵達，這兩件事缺一不可
#
# ⚠️ 字樣必須是 `[Console]::OutputEncoding`，**不能只寫 `OutputEncoding`**。
#    PowerShell 另有一個 `$OutputEncoding` 自動變數，它管的是「管線送給
#    原生命令（native exe）時用什麼編碼」，**與 console 輸出無關** ——
#    只設它，中文照樣以 cp950 有損輸出。
#    首版判準寫成寬字樣，負向對照當場證明它不會紅：我抽掉了真正有效的那行，
#    而下一行的 `$OutputEncoding` 仍讓字樣命中 ⇒ 判準等於裝飾。
_UTF8_OUT_MARK = "[Console]::OutputEncoding"
_CJK = range(0x4E00, 0xA000)


def _has_cjk(text: str) -> bool:
    return any(ord(ch) in _CJK for ch in text)


def _hooks_path() -> tuple[str, Path]:
    try:
        r = subprocess.run(["git", "config", "core.hooksPath"], cwd=ROOT,
                           capture_output=True, text=True, timeout=30)
        hp = r.stdout.strip()
    except Exception:
        hp = ""
    active = (ROOT / hp).resolve() if hp else (ROOT / ".git" / "hooks").resolve()
    return hp, active


def collect() -> list[dict]:
    hp, active = _hooks_path()
    git_hooks = ROOT / ".git" / "hooks"
    found: list[dict] = []

    bypassed = hp and active != git_hooks.resolve()
    stranded_names: set[str] = set()

    # ① .git/hooks 被旁路
    if bypassed and git_hooks.is_dir():
        for p in sorted(git_hooks.glob("*")):
            if p.is_dir() or p.suffix == ".sample":
                continue
            try:
                txt = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                txt = ""
            if ACKNOWLEDGED_MARK in txt:
                # 已標註「不會被執行」⇒ 這一份不報，**且配對的 shim 也不報**。
                # （首版把它加進 stranded_names，於是判準 ② 仍為它判紅 ——
                #  豁免只擋住一半，另一半照樣吵。負向對照的第三段抓到的。）
                continue
            stranded_names.add(p.name)
            found.append({"kind": "git-hooks-bypassed", "id": f".git/hooks/{p.name}",
                          "size": p.stat().st_size})

    # ② shim 有、實作缺席，且 .git/hooks 有一份被擱置
    if bypassed and active.is_dir():
        impl_dir = active.parent
        for p in sorted(active.glob("*")):
            if p.name in ("h", "husky.sh") or p.name.startswith("."):
                continue
            if (impl_dir / p.name).exists():
                continue
            if p.name in stranded_names:
                found.append({"kind": "shim-noop-with-stranded-impl",
                              "id": f"{impl_dir.name}/{p.name}"})

    # ③ .claude/hooks/*.ps1 未被 settings.json 引用
    cfg = ROOT / ".claude" / "settings.json"
    hooks_dir = ROOT / ".claude" / "hooks"
    if cfg.is_file() and hooks_dir.is_dir():
        blob = cfg.read_text(encoding="utf-8-sig", errors="replace")
        for p in sorted(hooks_dir.glob("*.ps1")):
            if p.name not in blob:
                found.append({"kind": "claude-hook-unreferenced",
                              "id": f".claude/hooks/{p.name}"})
                continue

            # ④ 被引用、含中文 → 訊息要抵達，BOM 與輸出編碼缺一不可
            try:
                raw = p.read_bytes()
            except OSError:
                continue
            txt = raw.decode("utf-8-sig", errors="replace")
            if not _has_cjk(txt):
                continue
            miss = []
            if raw[:3] != b"\xef\xbb\xbf":
                miss.append("BOM")
            if _UTF8_OUT_MARK not in txt:
                miss.append("UTF-8 輸出編碼")
            if miss:
                found.append({"kind": "claude-hook-mojibake",
                              "id": f".claude/hooks/{p.name}",
                              "missing": "／".join(miss)})
    return found


def main() -> int:
    hp, active = _hooks_path()
    print("=" * 74)
    print("Hook 可觸達性：它有沒有機會被觸發（weekly 91）")
    print("=" * 74)
    print(f"\n  core.hooksPath = {hp or '（未設，用 .git/hooks）'}")
    print(f"  git 實際執行的目錄：{active}")

    if not (ROOT / ".git").exists():
        print("\n✗ 不在 git 工作區 —— 無法判定（不視為通過）")
        return 2

    found = collect()
    base = {}
    if BASELINE.is_file():
        base = json.loads(BASELINE.read_text(encoding="utf-8"))
    known = set(base.get("known", {}).keys())

    new = [f for f in found if f["id"] not in known]
    still = [f for f in found if f["id"] in known]

    print(f"\n  偵測到不可觸達 {len(found)} 筆｜基線內 {len(still)}｜**新增 {len(new)}**")
    # 基線數字必須印出來 —— 數字不動就代表沒有人在清
    print(f"  基線筆數：{len(known)}（每次都印；不動＝沒有人在清）")

    if still:
        print("\n  ── 基線內（待 owner 決定，不判紅）──")
        for f in still:
            print(f"    · {f['id']:<44} {base['known'][f['id']][:52]}")

    for f in new:
        print(f"\n  [RED  ] {f['id']}")
        if f["kind"] == "git-hooks-bypassed":
            print(f"           `.git/hooks/` 被 core.hooksPath 旁路 ⇒ **永遠不會執行**"
                  f"（{f.get('size', 0)} bytes）")
            print(f"           要嘛改到 {active.parent}，要嘛在檔頭寫明「{ACKNOWLEDGED_MARK}」")
        elif f["kind"] == "shim-noop-with-stranded-impl":
            print("           husky shim 存在但**沒有實作** ⇒ 靜靜 exit 0；"
                  "而 `.git/hooks/` 有一份被擱置")
        elif f["kind"] == "claude-hook-mojibake":
            print(f"           含中文卻缺：**{f['missing']}** ⇒ 訊息以亂碼抵達")
            print("           退出碼會完全正常 —— 它擋對了，而看不懂為什麼，")
            print("           那次攔截等同沒有發生。修法：檔案存成 UTF-8 with BOM，")
            print("           並在開頭加 `[Console]::OutputEncoding = "
                  "[System.Text.Encoding]::UTF8`。")
        else:
            print("           `.claude/settings.json` 沒有引用它 ⇒ 沒有任何事件會觸發")

    if new:
        print(f"\n⚠️ 新增的不可觸達 hook 不會報錯、不會留痕，只是**安靜地什麼都不做**。")
        print(f"\nStatus: [RED] 新增 {len(new)} 筆")
        return 1

    print("\nStatus: [GREEN] 沒有新增的不可觸達 hook")
    return 0


if __name__ == "__main__":
    sys.exit(main())
