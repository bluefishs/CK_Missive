#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""weekly 的每一步都必須能紅，否則要在步驟名裡講明它只是報告。

## 為什麼有這一支

2026-08-29 同日連續兩次踩到同一個形狀 **「檢查做了、記錄了，但不影響判定」**：

  · `/api/health/detailed` 六項檢查**只有兩項會改頂層 status**，
    AI 服務整個 exception 而訊息字面上寫著「All systems operational」
  · CK_AaaP 同日回報他們的 `all_healthy: True` 是寫死的初始值

⇒ 一般化的問題是：**weekly 的 88 個步驟裡，有沒有哪一步永遠不可能紅？**

實查：193 支檢核腳本中 20 支沒有任何非 0 退出路徑，
而其中**只有 1 支**（`facade_adoption_audit`）被 runner 當成 `run_step`。
它的檔頭明文寫著「informational only — 不入 strict fail」⇒ **那是有意的設計**。

**問題不在腳本，在顯示**：它的綠燈與其他 87 個真守門長得一模一樣，
讀輸出的人會合理地以為「這件事被檢查了而且沒問題」。
⇒ 修法是把它標成「（僅報告·不判紅）」，而不是逼它去紅。

## ⚠️ 判準的窄度是這支的全部價值

我的第一版判準是**掃檔頭有沒有 informational／不判紅／never fails 等字樣**，
命中 7 支 —— **其中 6 支是誤報**。那些字樣出現在「存量列 baseline 不判紅」
這類**局部豁免的散文**裡，而腳本整體是會紅的（step 61 與 64 在同日的
weekly 裡確實是紅的）。

⇒ 判準改為**看程式碼有沒有非 0 退出路徑**，不看它怎麼描述自己。
這與本 repo 反覆記過的「判準命中的是散文不是程式碼」是同一件事。

## 判準

對 `run_fitness_weekly.sh` 的每一個 `run_step`：

  RED  腳本**沒有任何非 0 退出路徑**（＝永遠不可能紅），
       而步驟名裡**沒有**標明它只是報告
  ok   能紅的步驟；或已標明「僅報告」的步驟

⚠️ 剝掉註解再判：`# return 1` 不算一條退出路徑。

## 誰跑它

weekly step 89（`run_fitness_weekly.sh`）。
"""
import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts" / "checks" / "run_fitness_weekly.sh"

#: 步驟名裡出現任一個就視為已標明「這只是報告」
_MARKED = re.compile(r"僅報告|不判紅|informational|report[- ]only", re.I)

#: 非 0 退出路徑（剝掉註解後才比對）
_NONZERO = re.compile(r"(?:sys\.exit|SystemExit)\s*\(\s*[1-9]|return\s+[1-9]\d*\b|exit\s+[1-9]")

_STEP = re.compile(r'run_step\s+"(\d+)"\s+"([^"]*)"\s+"([^"]+)"')


def _strip_comments(text: str, is_py: bool) -> str:
    """去掉註解與 docstring —— 判準要看程式碼，不看它怎麼描述自己。"""
    if is_py:
        # 去掉三引號區塊（docstring）
        text = re.sub(r'"""[\s\S]*?"""', "", text)
        text = re.sub(r"'''[\s\S]*?'''", "", text)
    return "\n".join(ln.split("#", 1)[0] for ln in text.splitlines())


def main() -> int:
    if not RUNNER.is_file():
        print(f"✗ 找不到 {RUNNER} —— 無法判定（不視為通過）")
        return 2

    steps = _STEP.findall(RUNNER.read_text(encoding="utf-8", errors="replace"))
    if not steps:
        print("✗ 解析不到任何 run_step —— 判定不可信，不視為通過")
        return 2

    reds, marked, missing = [], [], []
    for no, label, path in steps:
        script = ROOT / path.split()[0]
        if not script.is_file():
            missing.append((no, label, path))
            continue
        code = _strip_comments(
            script.read_text(encoding="utf-8", errors="replace"),
            script.suffix == ".py")
        can_fail = bool(_NONZERO.search(code))
        is_marked = bool(_MARKED.search(label))
        if can_fail:
            continue
        (marked if is_marked else reds).append((no, label, script.name))

    print(f"weekly 共 {len(steps)} 步｜永遠不可能紅但**已標明**的 {len(marked)} 步")
    for no, label, name in marked:
        print(f"    step {no}: {label}  ({name})")

    if missing:
        print(f"\n✗ {len(missing)} 步的腳本檔不存在：")
        for no, label, path in missing:
            print(f"    step {no}: {label} → {path}")
        return 2

    if not reds:
        print("✓ 每一步不是能紅、就是已標明只是報告")
        return 0

    print(f"\n✗ {len(reds)} 步**永遠不可能紅，而步驟名沒有說**")
    for no, label, name in reds:
        print(f"    step {no}: {label}  ({name})")
    print("\n  它的綠燈與真守門長得一樣，讀輸出的人會以為這件事被檢查過了。")
    print("  二選一：讓它在該紅的時候回非 0，或在步驟名加「（僅報告·不判紅）」。")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
