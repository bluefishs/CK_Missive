#!/usr/bin/env python
"""治理強制覆蓋 —— ADR 與教訓，有多少是「有人在強制」的。

## 為什麼需要這一支

`docs/adr/` 23 篇、`LESSONS_REGISTRY` 80 條，都是為了**不要再犯**而寫的。
但一條決策或教訓若沒有任何機制在強制它，它就只是一段文字 ——
而文字不會在有人違反時出聲。

2026-08-13 量測：**ADR 23 篇裡只有 12 篇提到強制檢核**，
80 條教訓總共只提到 23 支不重複的檢核腳本。剩下的那些，
違反了不會有人知道 —— 這正是 L01「SSOT 聲明 vs 實作斷鏈」的家族。

## 它刻意不做的事

**不判斷「這條該不該有檢核」。** 2026-08-03（v6.39）評估過自動分類並正確否決：
多數教訓是行為準則（如 L77「先做 spike 驗」），本質上無法用檢核防範，
而區分需要語意判斷 → 會產出無法採信的清單。

所以本支只回答一個**可機器驗證**的問題：**這條有沒有指向任何檢核腳本**。
「該不該有」交給人在新增時宣告（見 `declaration_gate` 的同型設計）。

## 判準

- 只**報數字與清單**，不因「未提到檢核」判紅 —— 那會是一個永遠亮著的燈，
  而永遠亮著的燈等於沒有燈（本專案反覆記過這件事）。
- 真正該紅的是**倒退**：本支輸出 JSON 由 producer registry 納管，
  覆蓋數往下掉才是訊號。
- 引用了**不存在的腳本**才是硬錯誤（那是斷鏈，L01 本體）→ 判 RED。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

ROOT = Path(__file__).resolve().parents[2]
CHECKS = ROOT / "scripts" / "checks"
OUT = ROOT / "wiki" / "memory" / "integration-health" / "enforcement-coverage.json"

# 2026-08-13：初版寫成 `scripts/checks/(...)`，於是 L86/L87/L89 引用的
# `CK_lvrland_Webmap/scripts/checks/run_checks.sh` 這種**跨 repo 路徑**
# 也被當成本 repo 的腳本，然後報「不存在」—— 本支上線第一次跑就自己產生 3 個假紅。
# （§3 第 15/19 條的同型：新機制上線當下最該懷疑的就是它自己。）
# 前面不得有 `/`，才算本 repo 的相對路徑。
_SCRIPT_RE = re.compile(r"(?<![\w/])scripts/checks/([A-Za-z0-9_]+\.(?:py|cjs|sh))")
_FITNESS_RE = re.compile(r"(?:fitness|weekly|daily)\s*(?:step)?\s*#?\s*\d+", re.I)


def _existing_scripts() -> set[str]:
    return {p.name for p in CHECKS.glob("*") if p.is_file()}


def scan_adrs(known: set[str]) -> tuple[list[dict], list[str]]:
    rows, broken = [], []
    for p in sorted((ROOT / "docs" / "adr").glob("[0-9]*.md")):
        text = p.read_text(encoding="utf-8", errors="ignore")
        scripts = sorted(set(_SCRIPT_RE.findall(text)))
        for s in scripts:
            if s not in known:
                broken.append(f"{p.name} → scripts/checks/{s}（不存在）")
        rows.append({
            "id": p.name.split("-")[0],
            "file": p.name,
            "scripts": scripts,
            "mentions_fitness": bool(_FITNESS_RE.search(text)),
        })
    return rows, broken


def scan_lessons(known: set[str]) -> tuple[list[dict], list[str]]:
    reg = ROOT / "docs" / "architecture" / "LESSONS_REGISTRY.md"
    lines = reg.read_text(encoding="utf-8", errors="ignore").splitlines()
    heads = [(i, l) for i, l in enumerate(lines) if re.match(r"^## L\d+", l)]
    rows, broken = [], []
    for idx, (start, head) in enumerate(heads):
        end = heads[idx + 1][0] if idx + 1 < len(heads) else len(lines)
        block = "\n".join(lines[start:end])
        scripts = sorted(set(_SCRIPT_RE.findall(block)))
        for s in scripts:
            if s not in known:
                broken.append(f"{head[:40]} → scripts/checks/{s}（不存在）")
        rows.append({
            "id": re.match(r"^## (L\d+)", head).group(1),
            "title": head.lstrip("# ").strip()[:80],
            "scripts": scripts,
            "mentions_fitness": bool(_FITNESS_RE.search(block)),
        })
    return rows, broken


BASELINE = ROOT / "docs" / "architecture" / ".governance_declaration_baseline.txt"

# 明確表態的標記。沿用 doc_baseline_claim_audit 已踩過的兩個取捨：
# 用 HTML 註解不用中文字（行文提到就誤觸）、只認行首。
_DECL_RE = re.compile(r"^<!--\s*(enforced-by|not-enforceable)\s*:\s*(.+?)\s*-->", re.M)


def _load_baseline() -> set[str]:
    if not BASELINE.exists():
        return set()
    return {l.strip() for l in BASELINE.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")}


def _declared(text: str) -> bool:
    return bool(_DECL_RE.search(text))


def run_gate(adrs: list[dict], lessons: list[dict]) -> int:
    """閘門：**新增**的 ADR／教訓沒有表態就擋下。

    存量走 baseline 逐步清，理由與 `declaration_gate`（腳本表態）完全相同 ——
    一次要求 14 篇 ADR + 56 條教訓全部補齊，結果會是一個天天紅的閘門，
    而天天紅的閘門三天後就沒有人看了。只擋新增，存量寫進 baseline 慢慢消。

    「有表態」認兩種：
      · 內文已指向某支檢核腳本（覆蓋掃描既有的判準，不必為此再補一個標記）
      · 行首明確宣告 `<!--enforced-by: …-->` 或 `<!--not-enforceable: 理由-->`

    ⚠️ `not-enforceable` 是**正當答案**，不是逃生口。多數教訓是行為準則
    （L77「先做 spike 驗」），本來就無法用檢核防範 ——
    v6.39 正是因為想自動分類這件事而正確地否決了整個做法。
    這裡把判斷交還給寫的人，機器只驗「有沒有表態」。
    """
    base = _load_baseline()
    naked: list[str] = []
    for r in adrs:
        ident = f"adr:{r['file']}"
        if r["scripts"] or r["mentions_fitness"] or ident in base:
            continue
        text = (ROOT / "docs" / "adr" / r["file"]).read_text(encoding="utf-8", errors="ignore")
        if not _declared(text):
            naked.append(ident)
    reg = (ROOT / "docs" / "architecture" / "LESSONS_REGISTRY.md").read_text(
        encoding="utf-8", errors="ignore")
    blocks = re.split(r"(?=^## L\d+)", reg, flags=re.M)
    by_id = {re.match(r"## (L\d+)", b).group(1): b for b in blocks if re.match(r"## L\d+", b)}
    for r in lessons:
        ident = f"lesson:{r['id']}"
        if r["scripts"] or r["mentions_fitness"] or ident in base:
            continue
        if not _declared(by_id.get(r["id"], "")):
            naked.append(ident)

    print("\n" + "-" * 70)
    print(f"宣告制閘門：baseline {len(base)} 項存量｜未表態的新增 {len(naked)} 項")
    if not naked:
        print("Status: [GREEN] 沒有未表態的新增 ADR／教訓")
        return 0
    print("Status: [RED] 以下新增項目沒有表態：")
    for n in naked:
        print(f"  - {n}")
    print("  → 在該檔行首加一行：")
    print("       <!--enforced-by: scripts/checks/xxx.py-->")
    print("     或（本質上無法用檢核防範時，這是正當答案）：")
    print("       <!--not-enforceable: 這是行為準則，靠 review 不靠檢核-->")
    return 2


def main() -> int:
    gate_mode = "--gate" in sys.argv
    write_baseline = "--write-baseline" in sys.argv
    print("=" * 70)
    print("治理強制覆蓋（ADR／教訓 有沒有人在強制）")
    print("=" * 70)

    known = _existing_scripts()
    adrs, adr_broken = scan_adrs(known)
    lessons, lesson_broken = scan_lessons(known)

    def covered(rows):
        return [r for r in rows if r["scripts"] or r["mentions_fitness"]]

    a_cov, l_cov = covered(adrs), covered(lessons)
    all_scripts = {s for r in adrs + lessons for s in r["scripts"]}

    print(f"\n  ADR      {len(a_cov):>3}/{len(adrs):<3} 有指向強制機制"
          f"（{len(a_cov)/max(1,len(adrs)):.0%}）")
    print(f"  教訓     {len(l_cov):>3}/{len(lessons):<3} 有指向強制機制"
          f"（{len(l_cov)/max(1,len(lessons)):.0%}）")
    print(f"  被引用的檢核腳本（去重）：{len(all_scripts)} 支 / 現有 "
          f"{len([n for n in known if n.endswith(('.py','.cjs','.sh'))])} 支")

    naked_adr = [r["file"] for r in adrs if r not in a_cov]
    if naked_adr:
        print(f"\n  沒有指向任何強制機制的 ADR（{len(naked_adr)} 篇）：")
        for f in naked_adr[:12]:
            print(f"     - {f}")
        print("     → 不判紅：有些 ADR 本來就是決策紀錄而非可強制的規則。")
        print("       該不該補，由人在 Phase 4 的宣告制閘門表態，不由這裡猜。")

    broken = adr_broken + lesson_broken
    result = {
        "checked_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "adr_total": len(adrs), "adr_covered": len(a_cov),
        "lesson_total": len(lessons), "lesson_covered": len(l_cov),
        "scripts_referenced": len(all_scripts),
        "fail": len(broken),
        "broken_refs": broken,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  已寫入 {OUT.relative_to(ROOT)}")

    if broken:
        # 引用了不存在的腳本＝斷鏈，那是硬錯誤（L01 本體），不是「還沒補」
        print(f"\nStatus: [RED] {len(broken)} 處引用了不存在的檢核腳本")
        for b in broken:
            print(f"  - {b}")
        return 2

    if write_baseline:
        items = ([f"adr:{r['file']}" for r in adrs if not (r["scripts"] or r["mentions_fitness"])]
                 + [f"lesson:{r['id']}" for r in lessons
                    if not (r["scripts"] or r["mentions_fitness"])])
        BASELINE.write_text(
            "# 治理宣告閘門 —— 存量清單（2026-08-13 建立）\n"
            "# 這些 ADR／教訓在閘門上線時尚未表態，逐項清掉即從本檔移除一行。\n"
            "# 閘門每次執行都印剩餘數量 —— 數字不動就代表沒有人在清。\n"
            "# 新增的項目不在此列，會被真的擋下。\n"
            + "\n".join(sorted(items)) + "\n", encoding="utf-8")
        print(f"\n  已寫入 baseline：{len(items)} 項存量 → {BASELINE.name}")

    print("\nStatus: [GREEN] 引用的檢核腳本全部存在")
    print("  註：覆蓋率本身不判紅（永遠亮著的燈等於沒有燈）——")
    print("      由 producer registry 追蹤，數字往下掉才是訊號。")

    if gate_mode:
        return run_gate(adrs, lessons)
    return 0


if __name__ == "__main__":
    sys.exit(main())
