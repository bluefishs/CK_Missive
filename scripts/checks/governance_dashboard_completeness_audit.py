"""Governance Dashboard Completeness Audit (fitness step, 2026-06-12)

防回退守衛：治理 SSOT 儀表板自身的「整合缺口」。

背景（2026-06-12 覆盤揭發）：
  GOVERNANCE_INTEGRATED_DASHBOARD.md 由 in-container scheduler(cwd=/app) 每日
  regenerate，但生成器一度寫死 host 佈局(backend/logs, backend/app, ~/.claude)
  → §5 facade caller 顯 `?`、§9.6 誤報「cron_events.jsonl 不存在」(實有 11k 筆)、
  §3/§4 silent 空白。這是 L52/L57「host vs container 路徑漂移」家族在 meta-治理
  工具上的重演，也正是 dashboard 設計初衷(消滅整合缺口)要防的事 → 機制化驗證(L62)。

檢查（掃 dashboard 輸出，非掃生成器原始碼）：
  R1  §5 facade 表出現 `| ? |`            → RED（生成器路徑解析壞了）
  R2  §9.6 報「不存在」但 cron_events 實存  → RED（LOGS_DIR 漂移）
  R3  §3 commits 空白且本機為 git repo     → YELLOW（host 端該有 commit）
  R4  dashboard freshness > 36h            → YELLOW（cron 沒在重生）

Usage:
  python scripts/checks/governance_dashboard_completeness_audit.py
  python scripts/checks/governance_dashboard_completeness_audit.py --strict
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DASHBOARD = ROOT / "docs" / "architecture" / "GOVERNANCE_INTEGRATED_DASHBOARD.md"


def _first_dir(*cands: Path) -> Path:
    for c in cands:
        if c.exists():
            return c
    return cands[0]


# 與 generate_governance_dashboard.py 同款 host/container 佈局解析
LOGS_DIR = _first_dir(ROOT / "backend" / "logs", ROOT / "logs")
IS_GIT_REPO = (ROOT / ".git").exists()


def _section(text: str, header: str, next_header: str) -> str:
    m = re.search(re.escape(header) + r"(.*?)" + re.escape(next_header), text, re.DOTALL)
    return m.group(1) if m else ""


def main(strict: bool = False) -> int:
    print("=== Governance Dashboard Completeness Audit ===")
    if not DASHBOARD.exists():
        print(f"  [RED] dashboard 不存在: {DASHBOARD}")
        return 1 if strict else 0

    text = DASHBOARD.read_text(encoding="utf-8", errors="ignore")
    reds: list[str] = []
    yellows: list[str] = []

    # R1: §5 facade caller 顯 `?`（生成器 PKG_DIR 解析壞）
    sec5 = _section(text, "## 5. Facade", "## 6.")
    if re.search(r"\|\s*\?\s*\|", sec5):
        reds.append("R1 §5 facade caller=`?` → 生成器 PKG_DIR 路徑漂移(host/container)")

    # R2: §9.6 報「不存在」但 cron_events 實際存在
    sec96 = _section(text, "## 9.6", "## 10.")
    events_exists = (LOGS_DIR / "cron_events.jsonl").exists()
    if "不存在" in sec96 and events_exists:
        reds.append("R2 §9.6 報 cron_events「不存在」但實存 → LOGS_DIR 路徑漂移")

    # R3: §3 commits 空白 + host 為 git repo（容器內無 git 屬合理，不算）
    sec3 = _section(text, "## 3. 最近", "## 4.")
    has_commit = bool(re.search(r"^- `[0-9a-f]{7,}", sec3, re.MULTILINE))
    if IS_GIT_REPO and not has_commit:
        yellows.append("R3 §3 commits 空白但本機為 git repo → 應於 host regenerate")

    # R4: freshness > 36h
    m = re.search(r"\*\*Generated\*\*:\s*([0-9: \-]+)", text)
    if m:
        try:
            gen = datetime.strptime(m.group(1).strip()[:19], "%Y-%m-%d %H:%M:%S")
            age_h = (datetime.now() - gen).total_seconds() / 3600
            print(f"  freshness: {age_h:.1f}h")
            if age_h > 36:
                yellows.append(f"R4 dashboard {age_h:.0f}h 未重生 → cron regenerate 可能斷")
        except ValueError:
            pass

    print(f"  layout: LOGS_DIR={LOGS_DIR.name} git_repo={IS_GIT_REPO} cron_events={events_exists}")
    print()

    for r in reds:
        print(f"  [RED]    {r}")
    for y in yellows:
        print(f"  [YELLOW] {y}")

    if reds:
        level = "RED"
    elif yellows:
        level = "YELLOW"
    else:
        level = "GREEN"
    print()
    print(f"Status: [{level}] {'儀表板區段完整' if level == 'GREEN' else '見上方'}")
    if level != "GREEN":
        print("修法: python scripts/checks/generate_governance_dashboard.py（檢查 PKG_DIR/LOGS_DIR 解析）")

    if strict and level == "RED":
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    sys.exit(main(strict=args.strict))
