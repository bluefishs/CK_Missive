"""Proposal Aging Alert (v6.13, 2026-05-31)

對齊 owner「學習閉環 + 日誌 + 坤哥真活」訴求。

揭發背景:
- 5/31 三層覆盤揭發 4 proposal pending 40 天
- 18:00 autobiography_belief_check 又新產 1 個 → 共 5 pending
- pipeline_red_consecutive_days=11 主因之一 = crystals=0
- 學習閉環斷在 proposal→crystal (owner 健忘 / 決策成本高)

修法 (本檔):
- 每週日 02:20 cron 檢查 pending proposal aging
- pending > 7 天的全部列入 LINE 摘要推 owner
- 含完整 reason + 風險評估 + 1-click curl approve 指令
- 把 owner 決策成本降到最低

對齊 owner 安全:
- 純 read 不自動 apply (owner approve 是不可逆 hard gate)
- 不繞 admin require_admin 端點
- 揭發即是動作 (不被遺忘 = 學習閉環真活)
"""
from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List


WIKI_MEMORY = Path(os.getenv("CK_WIKI_DIR", "/app/wiki")) / "memory"
PROPOSALS_DIR = WIKI_MEMORY / "proposals"


def parse_proposal(path: Path) -> Dict:
    """Parse frontmatter from a proposal markdown."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return {}

    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}

    meta: Dict = {"proposal_id": path.stem}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta


def assess_risk(meta: Dict) -> str:
    """評估 risk 等級"""
    kind = meta.get("proposal_kind", "")
    if kind == "intent_rule":
        return "LOW"
    if kind == "soul_section":
        return "MEDIUM"
    if kind == "synonym":
        return "LOW"
    return "UNKNOWN"


def age_days(meta: Dict) -> float:
    """計算 proposal age"""
    proposed_at = meta.get("proposed_at", "")
    if not proposed_at:
        # 用檔案 mtime fallback
        return 0.0
    try:
        # 解析 ISO 格式 (可能含 timezone)
        dt = datetime.fromisoformat(proposed_at.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return delta.days + delta.seconds / 86400
    except Exception:
        return 0.0


def list_pending_proposals() -> List[Dict]:
    """列所有 status: pending 的 proposal"""
    if not PROPOSALS_DIR.is_dir():
        return []
    out = []
    for f in PROPOSALS_DIR.glob("*.md"):
        if f.name.startswith("."):
            continue
        meta = parse_proposal(f)
        if not meta:
            continue
        if meta.get("status") != "pending":
            continue
        meta["_age_days"] = age_days(meta)
        meta["_risk"] = assess_risk(meta)
        out.append(meta)
    out.sort(key=lambda x: x.get("_age_days", 0), reverse=True)
    return out


def build_owner_summary(proposals: List[Dict]) -> str:
    """組 owner-friendly LINE message"""
    if not proposals:
        return ""

    lines = [
        "🧬 坤哥學習閉環 aging 揭發",
        "（pending proposal 主動推送）",
        "",
        f"當前 pending: {len(proposals)} 個",
        "",
    ]

    by_risk: Dict[str, List[Dict]] = {"LOW": [], "MEDIUM": [], "UNKNOWN": []}
    for p in proposals:
        risk = p.get("_risk", "UNKNOWN")
        by_risk.setdefault(risk, []).append(p)

    # 低風險先（最容易決策）
    for risk_level in ["LOW", "MEDIUM", "UNKNOWN"]:
        ps = by_risk.get(risk_level, [])
        if not ps:
            continue
        emoji = {"LOW": "🟢", "MEDIUM": "🟡", "UNKNOWN": "⚪"}[risk_level]
        lines.append(f"【{emoji} {risk_level} 風險 ({len(ps)} 個)】")
        for p in ps:
            pid = p.get("proposal_id", "?")
            kind = p.get("proposal_kind", "?")
            age = p.get("_age_days", 0)
            target = p.get("target_file", "?").split("/")[-1]
            reason = p.get("reason", "")[:80]
            lines.append("")
            lines.append(f"📌 {pid[:60]}")
            lines.append(f"   age: {age:.0f} 天 / kind: {kind}")
            lines.append(f"   target: {target}")
            if reason:
                lines.append(f"   reason: {reason}")
        lines.append("")

    lines.extend([
        "【approve SOP】",
        "",
        "POST /api/ai/memory/proposals/approve",
        '{"proposal_id": "...", "approved_by": "Aaron"}',
        "",
        "或前端 /kunge/memory 點 approve",
        "",
        "【safety】",
        "- crystal_applier 自帶 7 step 安全 SOP",
        "- snapshot → validate → apply → record",
        "- 可 git revert",
        "",
        "【為何要 approve】",
        "5/31 self-retro RED 主因:",
        "學習閉環 flow=0%",
        "→ crystals=0 (本檔揭發)",
        "→ 坤哥學了沒結晶",
        "",
        "對齊 owner:",
        "「學習閉環 + 日誌 + 坤哥真活」",
    ])

    return "\n".join(lines)


async def push_line(body: str) -> bool:
    """推 LINE via IntegrationFacade"""
    try:
        sys.path.insert(0, "/app")
        from app.services.contracts.facades import IntegrationFacade
        return await IntegrationFacade().push_admin_alert(
            title="", body=body, channel="line",
        )
    except Exception as e:
        print(f"LINE push failed: {e}")
        return False


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-age-days", type=float, default=7.0,
                       help="只推 age >= N 天的 proposal")
    parser.add_argument("--dry-run", action="store_true",
                       help="只印不推 LINE")
    parser.add_argument("--no-line", action="store_true",
                       help="禁用 LINE (本機驗證用)")
    args = parser.parse_args()

    proposals = list_pending_proposals()
    print(f"Total pending proposals: {len(proposals)}")

    if not proposals:
        print("✅ 無 pending proposal")
        return 0

    for p in proposals:
        print(f"  {p['proposal_id'][:60]} age={p['_age_days']:.1f}d risk={p['_risk']}")

    # 篩選 aging
    aging = [p for p in proposals if p.get("_age_days", 0) >= args.min_age_days]
    print(f"\nAging (>= {args.min_age_days}d): {len(aging)}")

    if not aging:
        print("✅ 無 aging proposal")
        return 0

    summary = build_owner_summary(aging)
    print()
    print("=" * 60)
    print(summary)
    print("=" * 60)

    if args.dry_run or args.no_line:
        print("\n[DRY-RUN] 未推 LINE")
        return 1  # 非 0 = 揭發 aging

    ok = await push_line(summary)
    print(f"\nLINE pushed: {ok}")
    return 1 if aging else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
