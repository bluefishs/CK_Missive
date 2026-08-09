# -*- coding: utf-8 -*-
"""跨 repo／跨 session 工作連續性稽核（2026-08-09）。

## 為什麼需要這一支

owner 2026-08-09：「跨專案 repo 或 session 導致紀錄或待辦事項遺失，
是否也應導入自我檢核修復與自我進化等程序，避免反覆遺忘重工」。

同一輪裡就有六個實例，全是同一個形狀 ——
**在某個 repo/session 完成的事沒有傳播出去，而且沒有任何機制會發現**：

| 事件 | 形態 | 潛伏 |
|---|---|---|
| lvrland 推送被 baseline 閘門擋 | 別人未提交的工作卡住整個 repo | 數週 |
| DT `frontend/dist` 落後 21 個 commit | 寫好了但從未部署（L79 的大規模版） | 3.5 週 |
| `sso_ttl_ssot_audit.py` 寫於 07-21 | 寫好但從沒接進任何 runner | 2 週+ |
| lvrland 原有 6 支檢核腳本 | 同上，沒有任何東西會跑它們 | 不明 |
| pile 的 `db_transaction_health_check` | 同上，**現在仍是** | 進行中 |
| 我的 shared-modules commit | hook 擋下卻回報成已推送 | 當日 |

這些都不是「程式壞了」，所以沒有任何既有檢核會紅。
它們是**工作停在半途而沒有人知道**。

## 判準（全部可機器判定，不做語意猜測）

| 檢查 | RED | YELLOW |
|---|---|---|
| 未推送 commit | 逾 `PUSH_STALE_DAYS` | 有但還新 |
| 孤兒檢核腳本（沒有任何 runner 引用） | — | 任一 |
| 工作區未提交檔逾 `WIP_STALE_DAYS` | — | 任一 |

**孤兒腳本刻意只判 YELLOW**：可能是刻意的一次性工具。但「存在卻沒人跑」
必須被看見 —— 那正是 `arch_pattern_script_existence_not_enforcement` 記的事。

**未推送刻意分兩級**：剛提交還沒推是正常工作節奏；**逾期**才是「卡住了」。

## 用法

    python scripts/checks/cross_repo_work_continuity_audit.py
    python scripts/checks/cross_repo_work_continuity_audit.py --self-test
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

PORTFOLIO = Path("D:/CKProject")
SYNC_SCRIPT = PORTFOLIO / "shared-modules" / "sync-vendored.sh"

PUSH_STALE_DAYS = 3      # 未推送超過這麼久＝卡住了，不是還在寫
WIP_STALE_DAYS = 14      # 未提交檔案放這麼久＝多半被忘了

# 自動產物：這些路徑的未提交是 cron 寫的，不是「有人忘了提交」
AUTO_PRODUCT_RE = re.compile(
    r"(wiki/memory/|wiki/SOUL\.md|docs/health/|"
    r"integration-health/|\.json$)"
)


def _git(repo: Path, *args: str) -> str:
    try:
        r = subprocess.run(["git", "-C", str(repo), *args],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=60)
        return r.stdout if r.returncode == 0 else ""
    except Exception:
        return ""


def consumer_repos() -> list[str]:
    """repo 清單取自 sync-vendored.sh —— 不自建第二份會漂移的清單。"""
    if not SYNC_SCRIPT.exists():
        print(f"✗ 找不到 {SYNC_SCRIPT} —— 無法取得 repo 清單，不視為通過")
        raise SystemExit(2)
    txt = SYNC_SCRIPT.read_text(encoding="utf-8", errors="replace")
    m = re.search(r'"selfaudit\|[^|]+\|([^"]+)"', txt)
    if not m:
        print("✗ sync-vendored.sh 內找不到 selfaudit 消費者清單")
        raise SystemExit(2)
    repos = m.group(1).split()
    if not repos:
        print("✗ 消費者清單為空 —— 解析失敗而非真的沒有")
        raise SystemExit(2)
    return repos


def check_unpushed(repo: Path, name: str) -> tuple[list[str], list[str]]:
    reds, yellows = [], []
    out = _git(repo, "log", "@{u}..HEAD", "--format=%H|%ct|%s")
    lines = [l for l in out.splitlines() if l.strip()]
    if not lines:
        return reds, yellows
    oldest_ts = min(int(l.split("|")[1]) for l in lines)
    age = (datetime.now() - datetime.fromtimestamp(oldest_ts)).days
    subj = lines[-1].split("|", 2)[2][:44]
    # 只看年齡判不出「被擋住」：commit 可能是今天的，但推不上去。
    # lvrland 2026-08-09 實例：5 筆未推送、最舊 0 天（看起來正常），
    # 實際是 pre-push 閘門因**別人未提交的變更**擋住整個 repo 數週 ——
    # 每次有人提交就把「最舊」重置，年齡永遠不會逾期。
    # 故直接問一次 `git push --dry-run`：擋住就是擋住，不必等它變老。
    blocked = ""
    try:
        r = subprocess.run(["git", "-C", str(repo), "push", "--dry-run"],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=300)
        if r.returncode != 0:
            tail = [l for l in (r.stderr or "").splitlines() if l.strip()]
            blocked = tail[-1][:80] if tail else f"exit={r.returncode}"
    except Exception as e:  # noqa: BLE001
        blocked = f"無法判定（{type(e).__name__}）"

    if blocked:
        reds.append(f"{name}: {len(lines)} 筆推不上去 —— {blocked}")
    elif age >= PUSH_STALE_DAYS:
        reds.append(f"{name}: {len(lines)} 筆未推送，最舊已 {age} 天（「{subj}」）")
    else:
        yellows.append(f"{name}: {len(lines)} 筆未推送（{age} 天，仍在正常節奏）")
    return reds, yellows


def check_stale_wip(repo: Path, name: str) -> list[str]:
    """未提交且**不是自動產物**的檔案，放太久多半是被忘了。"""
    out = _git(repo, "status", "--porcelain")
    stale = []
    cutoff = datetime.now() - timedelta(days=WIP_STALE_DAYS)
    for line in out.splitlines():
        if len(line) < 4:
            continue
        rel = line[3:].strip().strip('"')
        if AUTO_PRODUCT_RE.search(rel):
            continue
        f = repo / rel
        try:
            if not f.is_file():
                continue
            if datetime.fromtimestamp(f.stat().st_mtime) < cutoff:
                stale.append(rel)
        except OSError:
            continue
    if stale:
        return [f"{name}: {len(stale)} 個未提交檔逾 {WIP_STALE_DAYS} 天"
                f"（{'、'.join(stale[:3])}{'…' if len(stale) > 3 else ''}）"]
    return []


# 明確表態的腳本：**不是豁免清單，是決策紀錄**。
#
# 借 CK_PileMgmt 的作法（`test_ops_scripts_auto_discovery_indexed`）——
# 它的 docstring 寫得最好：「沒有『我忘了』這個 failure mode」。
# 差別在 pile 是**寫入當下**強制表態（push 閘門），本檔是事後掃描；
# 兩者互補，但表態的形式一致：**必須寫理由，不能只放一個名字**。
#
# 加進來之前先問：它是不是該接線？「一次性工具」與「壞掉所以被拿掉」
# 在目錄裡長得一模一樣 —— 2026-08-09 實測這 6 支就有 3 支是後者。
DECLARED_STANDALONE: dict[str, dict[str, str]] = {
    "CK_Missive": {
        "jwt_debug.py": "除錯工具（容器內簽/驗 JWT），非檢核",
        "verify_ai_stubs.py": "DDD 遷移期的一次性驗證（AI re-export stub），遷移已完成",
        "check_consistency.py": "早期前後端一致性腳本；已被 api_contract_alignment_audit（weekly 25）"
                                "的三方對照涵蓋，保留供對照",
        "frontend_backend_endpoint_audit.py": "**已被取代**（api_contract_alignment_audit 涵蓋更廣的三方對照），"
                                              "且自身 cp950 崩潰無法在 host 執行 → 待 owner 決定刪除",
        "cron_liveness_snapshot.py": "**已被取代**（scheduler_liveness_audit 已在 run_fitness）；"
                                     "自身需容器內 app 模組，host 跑不了 → 待 owner 決定刪除",
        "manifest_drift_audit.py": "檢查 CK_Missive/shared-modules/*/manifest.yml 的中繼資料完整性。"
                                   "**唯一讀 manifest.yml 的就是它自己** —— 補齊那些欄位沒有消費者，"
                                   "故不接線；若日後有人真的消費 manifest，再復活",
    },
}


def check_orphan_checks(repo: Path, name: str) -> list[str]:
    """檢核腳本存在，卻沒有任何 runner／排程引用它。

    「腳本存在 ≠ 生效」在本專案已是反覆出現的形態
    （lvrland 曾有 6 支沒人跑、`sso_ttl_ssot_audit.py` 寫了 2 週沒接線）。
    """
    cdir = repo / "scripts" / "checks"
    if not cdir.is_dir():
        return []
    scripts = [p for p in cdir.glob("*.py")
               if not p.name.startswith("_") and p.name != "producer_registry.py"]
    if not scripts:
        return []
    # 誰可能引用：repo 內所有 .sh/.py/.yml/.json + scheduler
    haystack = []
    for pat in ("scripts/**/*.sh", "scripts/**/*.py", "backend/**/*.py",
                "*.json", "docs/**/*.md", ".github/**/*.yml"):
        for f in repo.glob(pat):
            if f.is_file() and f.suffix in (".sh", ".py", ".json", ".md", ".yml"):
                try:
                    haystack.append(f.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    pass
    blob = "\n".join(haystack)
    orphans = []
    for sc in scripts:
        # 扣掉**它自己檔案裡**的出現次數，而不是固定扣 1。
        #
        # 初版寫 `blob.count(name) - 1  # 自己那份` —— 那假設每支腳本都會在內容裡
        # 寫自己的檔名（docstring 用法示範）。不寫的那些就被扣成 0，
        # 於是 `doc_reference_integrity_audit.py`（明明是 weekly step 23）
        # 被誤報成孤兒。**新加的檢核最不該被信任**，這條是驗出來的。
        try:
            own = sc.read_text(encoding="utf-8", errors="ignore").count(sc.name)
        except OSError:
            own = 0
        if blob.count(sc.name) - own <= 0:
            orphans.append(sc.name)
    declared = DECLARED_STANDALONE.get(name, {})
    undeclared = [o for o in orphans if o not in declared]
    # 已表態的**不再報**，但也不是消失：理由寫在 DECLARED_STANDALONE 裡，
    # 而那份是程式碼、會進 code review、改動看得見。
    # 只報沒表態的 —— 「新出現的孤兒」才是需要有人做決定的東西。
    if undeclared:
        return [f"{name}: {len(undeclared)} 支檢核腳本沒有任何 runner 引用**且未表態**"
                f"（{'、'.join(undeclared[:3])}{'…' if len(undeclared) > 3 else ''}）"
                " —— 接線、刪除、或加進 DECLARED_STANDALONE 並寫明理由"]
    return []


def judge(reds: list[str], yellows: list[str]) -> int:
    if reds:
        return 2
    if yellows:
        return 1
    return 0


def self_test() -> int:
    cases = [
        ("有逾期未推送", ["a"], [], 2),
        ("只有警示", [], ["b"], 1),
        ("全部正常", [], [], 0),
        ("紅黃並存取最嚴重", ["a"], ["b"], 2),
    ]
    bad = []
    for name, r, y, expect in cases:
        got = judge(r, y)
        ok = got == expect
        print(f"  {'✓' if ok else '✗'} {name:18s} 預期 exit={expect} 實際={got}")
        if not ok:
            bad.append(name)
    if bad:
        print(f"\n✗ 判準無鑑別力：{bad}")
        return 2
    print("\n✓ 判準有鑑別力（正向 3 例、負向 1 例）")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    print("=== 跨 repo／跨 session 工作連續性稽核 ===")
    print("  問的是：有沒有工作停在半途而沒有人知道\n")

    reds: list[str] = []
    yellows: list[str] = []
    for name in consumer_repos():
        repo = PORTFOLIO / name
        if not (repo / ".git").exists():
            continue
        r, y = check_unpushed(repo, name)
        reds += r
        yellows += y
        yellows += check_stale_wip(repo, name)
        yellows += check_orphan_checks(repo, name)

    if reds:
        print("🔴 卡住的工作：")
        for m in reds:
            print(f"    {m}")
    if yellows:
        print("🟡 需要看一眼：")
        for m in yellows:
            print(f"    {m}")
    if not reds and not yellows:
        print("  沒有停在半途的工作")

    code = judge(reds, yellows)
    print()
    print(f"Status: [{'RED' if code >= 2 else 'YELLOW' if code == 1 else 'GREEN'}]")
    if reds:
        print("  處置：未推送逾期多半不是忘了推，是**被閘門擋住而沒有人在看**。")
        print("  先跑一次 `git push` 看它說什麼 —— 擋住的理由常常是別人未提交的變更。")
    return code


if __name__ == "__main__":
    sys.exit(main())
