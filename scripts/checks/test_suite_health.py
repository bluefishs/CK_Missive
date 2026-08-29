#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""測試套件健康檢核 — 「它跑不跑得起來」也要有人問。

## 為什麼需要這一支（2026-08-03）

測試套件長期不能安全執行（打生產庫 + 連線耗盡），**沒有任何機制在問這件事** ——
是 owner 記在待辦裡，不是系統發現的。同期還有一個症狀相同的案例：
08-02 因站台改版重寫 ezbid parser，10 個測試當場全紅，但因為全套跑不起來，
那次修改**兩天內都沒有回歸保護**，直到套件修好才浮出來。

對照六階階梯（`SELF_AUDIT_EVOLUTION_STANDARD.md`）：測試是最底層的網，
而「網本身破了」沒有任何一階在看。這支補的就是那個洞。

## 為什麼是「基線比對」而不是「必須全綠」

現況有 44 個既有失敗（mock 耗盡、過時斷言等測試債）。要求全綠會讓這支
天天紅 → 變成第 4709 筆沒人看的告警，正是我們一路在治的告警疲勞。

所以比對的是**測試 id 集合**，不是數字：
  - 出現基線裡沒有的失敗 → RED（新引入的回歸，這才是要擋的）
  - 基線裡的失敗被修好   → YELLOW 提示更新基線（好消息也要看得到，
                            否則基線只會膨脹、永遠不收斂）
  - 只用數字比對會漏掉「修好一個、同時弄壞另一個」——總數不變但實際有回歸。

## 三態
  0 = GREEN（無新增失敗）
  1 = YELLOW（有失敗被修好，基線該更新）
  2 = RED（新增失敗／套件跑不起來／測試庫不存在）

用法：
  python scripts/checks/test_suite_health.py            # 檢核
  python scripts/checks/test_suite_health.py --update   # 重錄基線（修完債之後跑）
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"
BASELINE = REPO / "backend" / "tests" / "known_failures.json"

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run_suite() -> tuple[set[str], str, int, dict]:
    """跑全套，回傳 (失敗的 test id 集合, 摘要行, pytest returncode, 未執行統計)。

    ⚠️ 2026-08-29 擴充：原本**只解析 `failed`**，而 `skipped` 與 `xfailed`
    完全不看 —— 那讓 `test_agent_evolution_loop.py` 的 **11 支 xfail**
    自 2026-04-14 起 4.5 個月沒被執行過，而基線一直是綠的。

    `xfail` 比 `skip` 更隱蔽：`pytest.xfail()` 寫在測試主體內，
    報告顯示 `N xfailed`，**既不算通過也不算失敗，連 `-rs` 都不列**。

    ⇒ 「沒有失敗」與「沒有執行」不是同一件事，而基線原本只看得見前者。
    這是 CK_AaaP 2026-08-29 指出的「好機制只套在一條路徑上」的本地實例。
    """
    proc = subprocess.run(
        # `-rfEs`：failed + error + skipped。
        #
        # ⚠️ **必須是 `fEs` 不能只寫 `s`** —— pytest 的 `-r` 是**取代**不是附加。
        # 我首版寫 `-rs`，把預設的 `fE` 換掉 ⇒ **FAILED 行整批不印** ⇒
        # 解析到 0 個失敗 ⇒ **基線被寫成 0 項**（而該次實際有 36 failed）。
        # 那會讓下一次執行把 36 個既有失敗全報成「新增」。
        # 一個為了看見 skip 而加的旗標，差點讓失敗偵測整個失效。
        [sys.executable, "-m", "pytest", "tests", "-q", "--no-header", "-rfEs",
         "-p", "no:cacheprovider"],
        cwd=BACKEND, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=3600,
    )
    out = proc.stdout + proc.stderr
    # 注意過濾空字串：pytest 的 error summary 有時會有一行光禿禿的 "ERROR"，
    # 收進來會變成一個空的 test id 混在基線裡（首次建基線時就踩到了）。
    failed = {
        line[len(prefix):].split(" ")[0].strip()
        for line in out.splitlines()
        for prefix in ("FAILED ", "ERROR ")
        if line.startswith(prefix)
    }
    failed = {t for t in failed if t and "::" in t}
    summary = next(
        (l for l in reversed(out.splitlines()) if re.search(r"\d+ (passed|failed|error)", l)),
        "(無法解析 pytest 摘要)",
    )
    # collection 階段炸掉時 pytest 不會印 FAILED，只有 errors —— 那是最嚴重的情況
    if "error" in summary.lower() and not failed:
        failed.add("<collection-error>")
    # 未執行的測試：skip 有理由可列，xfail 只有數字（pytest 不逐條印）
    skipped = [
        line.split(": ", 1)[-1].strip()
        for line in out.splitlines() if line.startswith("SKIPPED ")
    ]
    m_x = re.search(r"(\d+) xfailed", summary)
    m_s = re.search(r"(\d+) skipped", summary)
    not_run = {
        "skipped": int(m_s.group(1)) if m_s else 0,
        "xfailed": int(m_x.group(1)) if m_x else 0,
        "skip_reasons": sorted(set(skipped))[:20],
    }
    return failed, summary.strip(), proc.returncode, not_run


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update", action="store_true", help="以本次結果重錄基線")
    ap.add_argument("--force", action="store_true",
                    help="允許把基線歸零（僅在確認全部真的修好時用）")
    args = ap.parse_args()

    print("=" * 66)
    print(" 測試套件健康檢核（跑全套，約 10 分鐘）")
    print("=" * 66)

    if not BACKEND.exists():
        print(f"  ✗ 找不到 backend 目錄: {BACKEND}")
        return 2

    try:
        failed, summary, rc, not_run = run_suite()
    except subprocess.TimeoutExpired:
        print("  ✗ RED：測試套件逾時未完成（>60 分鐘）")
        return 2

    print(f"  pytest: {summary}")

    # 套件根本跑不起來 —— 這比「有幾個測試紅」嚴重得多，要能區分開來
    if "<collection-error>" in failed:
        print("  ✗ RED：collection 階段即失敗，整套無法執行")
        print("    常見原因：測試資料庫不存在（跑 bash scripts/dev/setup-test-db.sh）")
        return 2
    if rc not in (0, 1):
        print(f"  ✗ RED：pytest 以非預期狀態結束（exit={rc}）")
        print("    exit=3 通常代表 conftest 護欄擋下了（測試庫與生產庫同名）")
        return 2

    if args.update:
        # ── 寫入前的自洽檢查 ────────────────────────────────────────
        #
        # ⚠️ 2026-08-30 事故：我為了印出 skip 理由而加 `-rs`，
        # 而 pytest 的 `-r` 是**取代**不是附加 ⇒ 預設的 `fE` 被換掉
        # ⇒ **FAILED 行整批不印** ⇒ 解析到 0 個失敗
        # ⇒ **基線被寫成 0 項，而該次實際有 36 failed**。
        #
        # collection-error 與異常退出碼兩道守衛**都通過了** ——
        # pytest 正常結束，只是我沒解析到。⇒ 需要第三道：
        # **拿解析結果去對 pytest 自己的摘要**。
        #
        # 形狀由 CK_AaaP 同日提出：他們的快照寫入在 live 不可達時拒絕，
        # 理由是「基準只有一半，會讓下次比對永遠對不上」。
        #
        # ⚠️ 同日複查時發現本 repo 早有更強的形式 ——
        # `http_method_convention_audit` 的註解：
        #   「找不到東西不得回綠 —— 740 個端點不可能一條 GET 都沒有
        #     （/api/health 一定在）」
        # 那是**用領域知識定下限**，比「與摘要對得上」更強：
        # 它連「掃描壞了而摘要也一起壞了」都擋得住。
        # 這裡的對應下限是 `passed` —— 4000+ 支測試不可能一支都沒跑。
        m_passed = re.search(r"(\d+) passed", summary)
        passed_n = int(m_passed.group(1)) if m_passed else 0
        if passed_n < 100:
            print(f"  ✗ RED：只有 {passed_n} 支通過 —— **不寫入**")
            print("    本套件有 4000+ 支測試，個位數／零通過代表它根本沒跑完，")
            print("    而不是「測試都壞了」。基線不該記錄一次沒跑起來的結果。")
            return 2

        m_failed = re.search(r"(\d+) failed", summary)
        said = int(m_failed.group(1)) if m_failed else 0
        if said != len(failed):
            print(f"  ✗ RED：pytest 說 {said} failed，而解析到 {len(failed)} 項 —— **不寫入**")
            print("    兩者不一致代表輸出解析壞了（例如 `-r` 旗標把 FAILED 行關掉）。")
            print("    寫進去會讓下次比對把既有失敗全報成新增，")
            print("    而慣常處置是「重錄基線」⇒ **真正的新增回歸會一起被吸收**。")
            return 2

        prev = {}
        if BASELINE.exists():
            try:
                prev = json.loads(BASELINE.read_text(encoding="utf-8"))
            except Exception:
                prev = {}
        prev_n = len(prev.get("known_failures") or [])
        if prev_n and len(failed) == 0 and not args.force:
            print(f"  ✗ RED：基線原有 {prev_n} 項，本次解析到 **0** 項 —— **不寫入**")
            print("    全部修好是可能的，但更常見的是解析壞了。")
            print("    確定要歸零請加 --force。")
            return 2

        BASELINE.write_text(
            json.dumps({
                "known_failures": sorted(failed),
                # 未執行的測試也納入棘輪 —— 「沒有失敗」不等於「有被執行」
                "not_run": {"skipped": not_run["skipped"], "xfailed": not_run["xfailed"]},
            }, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"  基線已更新：{len(failed)} 項（與 pytest 摘要一致）"
              f" → {BASELINE.relative_to(REPO)}")
        return 0

    if not BASELINE.exists():
        print(f"  ✗ RED：找不到基線檔 {BASELINE.relative_to(REPO)}")
        print("    首次建立請跑：python scripts/checks/test_suite_health.py --update")
        return 2

    _baseline = json.loads(BASELINE.read_text(encoding="utf-8"))
    known = set(_baseline["known_failures"])
    new = sorted(failed - known)
    fixed = sorted(known - failed)

    print(f"  已知失敗 {len(known)} 項｜本次失敗 {len(failed)} 項"
          f"｜新增 {len(new)}｜已修好 {len(fixed)}")

    # ── 未執行的測試（skip / xfail）──────────────────────────────────
    #
    # 「沒有失敗」不等於「有被執行」。本檢核原本只看 failed，於是
    # `test_agent_evolution_loop.py` 的 11 支 xfail 從 2026-04-14 起
    # **4.5 個月沒被執行過而基線一直是綠的**（待辦 A35）。
    #
    # 存量列基線不判紅（要不要補實作是業務決定），**新增即紅** ——
    # 棘輪只准往下轉。
    _base_nr = _baseline.get("not_run") or {}
    base_skip = int(_base_nr.get("skipped", 0))
    base_xf = int(_base_nr.get("xfailed", 0))
    cur_skip, cur_xf = not_run["skipped"], not_run["xfailed"]

    print(f"  未執行：skipped {cur_skip}（基線 {base_skip}）"
          f"｜xfailed {cur_xf}（基線 {base_xf}）")
    if not_run["skip_reasons"]:
        print("    skip 理由（前 6）：")
        for r in not_run["skip_reasons"][:6]:
            print(f"      · {r[:88]}")

    not_run_red = []
    if cur_skip > base_skip:
        not_run_red.append(f"skipped {base_skip} → {cur_skip}")
    if cur_xf > base_xf:
        not_run_red.append(f"xfailed {base_xf} → {cur_xf}")
    if not_run_red:
        print("")
        print(f"  ✗ RED：未執行的測試變多了（{'、'.join(not_run_red)}）")
        print("    ⚠️ 它們不會讓套件變紅 —— skip 與 xfail 都不算失敗，")
        print("       而 xfail 連 `-rs` 都不會列出來。新增一支等於少一支覆蓋，")
        print("       而報告上看不出差別。")
        print("    修法：讓它真的能跑；或若確為 scaffold，記入待辦並在此更新基線")
        print(f"          （python {Path(__file__).name} --update）")
        return 2

    if new:
        print(f"\n  ✗ RED：新增 {len(new)} 項失敗（基線裡沒有＝這次弄壞的）")
        for t in new[:15]:
            print(f"     {t}")
        if len(new) > 15:
            print(f"     …另 {len(new) - 15} 項")
        return 2

    if fixed:
        print(f"\n  ⚠ YELLOW：{len(fixed)} 項既有失敗已修好，請重錄基線")
        for t in fixed[:10]:
            print(f"     {t}")
        print("     指令：python scripts/checks/test_suite_health.py --update")
        return 1

    print("\n  ✓ GREEN：無新增失敗（既有測試債維持在基線）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
