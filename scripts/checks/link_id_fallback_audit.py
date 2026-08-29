#!/usr/bin/env python
# -*- coding: utf-8 -*-
r"""link_id 不得用 `??` / `||` 回退到別的 id（development-rules §7）。

## 這條規範在防什麼

關聯記錄的操作對象必須是 `link_id`（那一條關聯本身），不是被關聯實體的 id：

    // ❌ 危險 —— link_id 缺席時會拿 project id 去解除關聯
    const linkId = proj.link_id ?? proj.id;

    // ✅ 嚴格要求存在
    if (item.link_id === undefined) {
      message.error('關聯資料缺少 link_id，請重新整理頁面');
      return;
    }

失效的代價是**對錯的紀錄執行操作**，而畫面上不會有任何異狀。

## 為什麼重寫（原本那支的三個缺陷，2026-08-30 實測）

`.claude/hooks/link-id-check.ps1`（2026-01-21）**存在但沒有任何 runner
在叫它**，而且真的跑起來會給錯的答案：

| 它的檢查 | 實際狀況 |
|---|---|
| Check 1／2 `link_id ??` `\|\|` | `Select-String -Path "src\**\*.tsx"` —— **PowerShell 的 `**` 不是遞迴 glob**，等同於 `*`。實測掃得到 **119/604** 個 `.tsx`（20%）⇒ 對 80% 的前端是瞎的，而它印 `[PASS]` |
| Check 4 BaseLink 必須在 `types/api.ts` | 型別實際在 `types/taoyuan.ts:53` ⇒ **永久假紅** |
| Check 5 防禦性檢查計數 | 同 glob 盲區 ⇒ 報「0 個」而 `DispatchLinksTab` 就有 |

⇒ 淨效果：誰把它接進 runner，拿到的是**一個永久紅燈加兩個假綠**。
這正是本 repo 記過兩次的「腳本存在 ≠ 有在強制」，外加一層
「**就算你去跑它，它給的也是錯的**」。

## 判準

在剝除註解／字串後的 TS/TSX 原始碼裡找 `link_id` 後接 `??` 或 `||`。

**豁免 React `key={...}`**：`key` 只決定渲染身分、不決定操作對象，
拿它回退不會操作到錯的紀錄。現況唯一命中就是這一種
（`DispatchLinksTab.tsx:102`），而同檔 120 行對真正的操作
（`unlinkDispatchMutation`）有正確的 undefined/null 守衛 —— 判它紅是誤報。

⚠️ 刻意**不**檢查「有沒有防禦性 if」：那需要追資料流，而
「有幾個 if」是個會鼓勵人寫無意義 if 的代理指標。

## 誰跑它

weekly step 90（`run_fitness_weekly.sh`）。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "frontend" / "src"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.ts_source import code_only, TsToolUnavailable  # noqa: E402

FALLBACK = re.compile(r"\blink_id\s*(\?\?|\|\|)")
# React key 的回退不決定操作對象 —— 見檔頭「判準」
KEY_ATTR = re.compile(r"key\s*=\s*\{[^{}]*\blink_id\s*(?:\?\?|\|\|)")


def main() -> int:
    if not SRC.is_dir():
        print(f"✗ 找不到 {SRC} —— 無法判定（不視為通過）")
        return 2

    files = [p for p in sorted(SRC.rglob("*.ts")) + sorted(SRC.rglob("*.tsx"))
             if "__tests__" not in p.as_posix() and ".test." not in p.name]
    if not files:
        print("✗ 一個前端原始檔都沒掃到 —— 目錄結構可能變了，本檢核已失效")
        return 2

    try:
        sources = code_only(files)
    except TsToolUnavailable as e:
        # 不退回較弱的判準 —— 「判準變弱」與「沒有違規」在輸出上一樣（ADR-0028）
        print(f"✗ 無法可靠剝除註解／字串：{e}")
        return 2

    reds, exempt, scanned = [], [], 0
    for p in files:
        t = sources.get(str(p.resolve()), "")
        if not t:
            continue
        scanned += 1
        for m in FALLBACK.finditer(t):
            line_no = t[: m.start()].count("\n") + 1
            line = t.splitlines()[line_no - 1] if line_no <= t.count("\n") + 1 else ""
            rel = p.relative_to(SRC).as_posix()
            if KEY_ATTR.search(line):
                exempt.append((rel, line_no))
            else:
                reds.append((rel, line_no, line.strip()[:88]))

    print("=" * 74)
    print("link_id 不得回退到別的 id（development-rules §7，weekly 90）")
    print("=" * 74)
    print(f"\n  掃描 {scanned} 個前端原始檔")
    # ⚠️ 這一行是給人看的解析度證據：原本那支 PowerShell 版只掃得到 119/604，
    #    而它照樣印 [PASS]。掃了幾個檔必須說出來。
    if scanned < 400:
        print(f"\n✗ 只掃到 {scanned} 個檔（預期 600+）—— 讀取範圍可能又縮了，不視為通過")
        return 2

    for rel, line_no in exempt:
        print(f"\n  [豁免  ] {rel}:{line_no}")
        print("           用在 React key= ⇒ 只決定渲染身分，不決定操作對象")

    for rel, line_no, frag in reds:
        print(f"\n  [RED  ] {rel}:{line_no}")
        print(f"           {frag}")
        print("           link_id 缺席時會拿別的 id 去操作 ⇒ 動到錯的紀錄，畫面無異狀。")
        print("           改法：`if (x.link_id == null) { message.error(...); return; }`")

    if reds:
        print(f"\nStatus: [RED] {len(reds)} 處 link_id 回退")
        return 1

    print(f"\nStatus: [GREEN] 無 link_id 回退（{len(exempt)} 處 key= 豁免）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
