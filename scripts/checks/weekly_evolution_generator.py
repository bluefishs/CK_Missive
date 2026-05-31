"""Weekly Evolution Generator (v6.13, 2026-05-31)

對齊 owner「日誌與周報成為實質平臺靈魂」訴求。

揭發背景:
- 5/31 三層覆盤 (KG_HERMES_KUNGE_THREE_LAYER_RETRO) 揭發 W22 缺檔
- 真因: 既有 kunge_weekly_learning_summary 只 LINE 推摘要，沒產出 W*.md 檔
- 修法: 本檔 — 每週日 02:00 真實產出 wiki/memory/evolutions/W{NN}.md

對齊 owner 安全:
- 不覆寫已存在 (W22 手寫保留)
- 純 INSERT/APPEND，無 DELETE
- frontmatter 標 generator: auto vs manual 區分

執行:
  python scripts/checks/weekly_evolution_generator.py
  python scripts/checks/weekly_evolution_generator.py --force-week 2026-W22  # 補回特定週
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path


WIKI_MEMORY = Path(os.getenv("CK_WIKI_DIR", "/app/wiki")) / "memory"
EVOLUTIONS_DIR = WIKI_MEMORY / "evolutions"


def get_iso_week(dt: datetime) -> str:
    """ISO 8601 week: 2026-W22"""
    year, week, _ = dt.isocalendar()
    return f"{year}-W{week:02d}"


def get_week_range(week_str: str) -> tuple[datetime, datetime]:
    """2026-W22 → (Mon 2026-05-25, Sun 2026-05-31)"""
    year, week_num = week_str.split("-W")
    year, week_num = int(year), int(week_num)
    # ISO 8601: week 1 = first week with Thursday
    jan4 = datetime(year, 1, 4)
    week1_mon = jan4 - timedelta(days=jan4.isoweekday() - 1)
    monday = week1_mon + timedelta(weeks=week_num - 1)
    sunday = monday + timedelta(days=6, hours=23, minutes=59)
    return monday, sunday


def count_files_in_range(dir_path: Path, start: datetime, end: datetime, pattern: str = "*.md") -> list[str]:
    if not dir_path.is_dir():
        return []
    out = []
    start_ts, end_ts = start.timestamp(), end.timestamp()
    for f in dir_path.glob(pattern):
        try:
            mt = f.stat().st_mtime
            if start_ts <= mt <= end_ts:
                out.append(f.name)
        except Exception:
            continue
    return out


def get_git_commits(start: datetime, end: datetime) -> list[dict]:
    """git log 撈本週 commit (short oneline)"""
    try:
        repo_root = Path(os.getenv("CK_PROJECT_ROOT", "/app")).parent
        since = start.strftime("%Y-%m-%d")
        until = (end + timedelta(days=1)).strftime("%Y-%m-%d")
        r = subprocess.run(
            ["git", "log", f"--since={since}", f"--until={until}",
             "--pretty=format:%h|%s", "--no-merges"],
            cwd=str(repo_root), capture_output=True, timeout=15,
        )
        lines = r.stdout.decode("utf-8", errors="replace").strip().split("\n")
        commits = []
        for line in lines:
            if "|" in line:
                sha, msg = line.split("|", 1)
                commits.append({"sha": sha, "msg": msg[:80]})
        return commits
    except Exception:
        return []


def render_weekly(week_str: str) -> str:
    monday, sunday = get_week_range(week_str)
    date_range = f"{monday.strftime('%Y-%m-%d')} → {sunday.strftime('%Y-%m-%d')}"

    diary_files = count_files_in_range(WIKI_MEMORY / "diary", monday, sunday)
    pattern_files = count_files_in_range(WIKI_MEMORY / "patterns", monday, sunday)
    failure_files = count_files_in_range(WIKI_MEMORY / "failures", monday, sunday)
    lesson_files = count_files_in_range(WIKI_MEMORY / "lessons", monday, sunday)
    critique_files = count_files_in_range(WIKI_MEMORY / "critiques", monday, sunday)
    retro_files = count_files_in_range(WIKI_MEMORY / "self-retrospective-reports", monday, sunday)
    commits = get_git_commits(monday, sunday)

    now = datetime.now()
    lines = [
        "---",
        f"title: 進化週報 {week_str}",
        "type: evolution_weekly",
        f"week: {week_str}",
        f"date_range: {date_range}",
        f"created_at: {now.isoformat(timespec='seconds')}",
        "generator: auto",
        "tags: [memory, evolution, weekly]",
        "---",
        "",
        f"# {week_str} 進化週報",
        "",
        f"> **日期範圍**：{date_range}",
        f"> **產生方式**：auto (weekly_evolution_generator cron)",
        f"> **產生時間**：{now.strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 1. 本週量化指標",
        "",
        "| 項目 | 本週 count |",
        "|---|---|",
        f"| commits | {len(commits)} |",
        f"| diary 日數 | {len(diary_files)} |",
        f"| 新 patterns | {len(pattern_files)} |",
        f"| 新 failures | {len(failure_files)} |",
        f"| 新 lessons | {len(lesson_files)} |",
        f"| 新 critiques | {len(critique_files)} |",
        f"| self-retrospective | {len(retro_files)} |",
        "",
    ]

    # 自我意識真活訊號 (對齊三層覆盤檢查項)
    lines.extend([
        "## 2. 自我意識真活訊號",
        "",
        f"- **diary 連續性**: {'✅ 真活' if len(diary_files) >= 5 else '⚠️ 不足'} ({len(diary_files)} 日)",
        f"- **質性反省 (critique)**: {'✅ 有' if len(critique_files) > 0 else '❌ 0 條 (停滯訊號)'}",
        f"- **學習結晶 (lessons)**: {'✅' if len(lesson_files) > 0 else '⚠️ 0 新'}",
        f"- **行動量 (commits)**: {len(commits)}",
        "",
    ])

    if commits:
        lines.extend(["## 3. 本週 commits (top 20)", ""])
        for c in commits[:20]:
            lines.append(f"- `{c['sha']}` {c['msg']}")
        if len(commits) > 20:
            lines.append(f"- ... 還有 {len(commits) - 20} 個")
        lines.append("")

    if lesson_files:
        lines.extend(["## 4. 本週新 lessons", ""])
        for fn in lesson_files[:10]:
            lines.append(f"- {fn}")
        lines.append("")

    if failure_files:
        lines.extend(["## 5. 本週新 failures", ""])
        for fn in failure_files[:10]:
            lines.append(f"- {fn}")
        lines.append("")

    if critique_files:
        lines.extend(["## 6. 本週 critiques (質性反省)", ""])
        for fn in critique_files[:5]:
            lines.append(f"- {fn}")
        lines.append("")
    else:
        lines.extend([
            "## 6. 本週 critiques",
            "",
            "❌ **本週 0 條 critique** — 質性反省斷層訊號",
            "可能原因：critic 鏈未被呼叫 / query 都太「好答」",
            "建議：check agent_critic.py call path + verdict trigger 條件",
            "",
        ])

    lines.extend([
        "## 7. 元洞察 (auto-generated stub)",
        "",
        "> 本檔為自動產生，可由 agent 後續手寫補充 retro 觀察。",
        f"> 對應 cron: weekly_evolution_generator (每週日 02:00)",
        "",
        "---",
        "",
        f"> 對齊 owner: 「日誌與周報成為實質平臺靈魂」訴求",
        f"> 防 W22 重演: 不再依賴手寫補寫",
    ])

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force-week", help="補回特定週，例: 2026-W21")
    parser.add_argument("--force", action="store_true", help="覆寫已存在 (預設不覆寫)")
    parser.add_argument("--dry-run", action="store_true", help="只印不寫")
    args = parser.parse_args()

    # 本週 = 上週日為止（avoid 本週尚未結束就 generate）
    # cron 排在週日 02:00 → 此時 monday 算法應指向 last full week
    now = datetime.now()
    if args.force_week:
        week_str = args.force_week
    else:
        # 週日 02:00 跑時 → ISO week 仍是本週，但實際我們要 generate 的是本週
        # 因為週日 = 本週最後一天，跑時已過大部分工作日
        week_str = get_iso_week(now)

    EVOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
    target = EVOLUTIONS_DIR / f"{week_str}.md"

    if target.exists() and not args.force:
        print(f"SKIP: {target.name} 已存在 (--force 覆寫)")
        # 不報錯 — 對齊「不覆寫手寫」原則
        return 0

    content = render_weekly(week_str)

    if args.dry_run:
        print(content[:500])
        print(f"\n[DRY-RUN] 預計寫入 {target}")
        return 0

    target.write_text(content, encoding="utf-8")
    print(f"GENERATED: {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
