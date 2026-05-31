"""Skill KG ingest 加入 (2026-05-31, v6.13)

對齊 GRAPH_ECOSYSTEM 建議 #5:
.claude/skills/ 108 SKILL.md 完全不在 KG (silo)
→ AI agent 無法查「有哪些 skill 可用」

對齊 owner 備份安全:
- 純 INSERT 完全可逆
- 預設 dry-run / --apply 真執行
- 回滾: DELETE WHERE entity_type='skill'
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / ".claude" / "skills"


def list_skills() -> list[dict]:
    """掃 .claude/skills/**/SKILL.md 或 *.md (取頂層描述)"""
    skills = []
    if not SKILLS_DIR.is_dir():
        return skills

    for f in SKILLS_DIR.rglob("*.md"):
        if "node_modules" in f.parts:
            continue
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        # 抓 frontmatter (---  ... ---)
        name = f.stem
        description = ""
        m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
        if m:
            fm = m.group(1)
            name_m = re.search(r"^name:\s*(.+)$", fm, re.MULTILINE)
            desc_m = re.search(r"^description:\s*(.+)$", fm, re.MULTILINE)
            if name_m:
                name = name_m.group(1).strip()
            if desc_m:
                description = desc_m.group(1).strip()[:500]

        # 若無 frontmatter，取第一行 # heading 或前 200 字
        if not description:
            lines = text.splitlines()
            for line in lines:
                if line.strip().startswith("#"):
                    description = line.strip("# ")[:200]
                    break

        # 相對路徑作為 external_id 唯一
        rel = f.relative_to(SKILLS_DIR)
        external_id = f"skill-{rel.as_posix().replace('/', '_').replace('.md', '')}"
        skills.append({
            "name": name,
            "description": description or f"skill from {rel}",
            "external_id": external_id,
            "rel_path": str(rel),
        })
    return skills


def run_in_container(code: str) -> str:
    try:
        env = os.environ.copy()
        env["MSYS_NO_PATHCONV"] = "1"
        r = subprocess.run(
            ["docker", "exec", "ck_missive_backend", "python", "-c", code],
            capture_output=True, timeout=180, env=env,
        )
        return r.stdout.decode("utf-8", errors="replace").strip()
    except Exception as e:
        return f"ERROR: {e}"


def apply_ingest(skills: list[dict], dry_run: bool = True) -> int:
    """INSERT skill 列表 to canonical_entities"""
    import json as _json
    if dry_run:
        return len(skills)

    # 用 JSON 傳給 container 內 python
    skills_json = _json.dumps(skills, ensure_ascii=False)
    # 寫 temp 檔避免 shell escape
    tmp_file = ROOT / "scripts" / "sync" / "_skill_tmp.json"
    tmp_file.write_text(skills_json, encoding="utf-8")
    code = """
import asyncio, json
from app.db.database import AsyncSessionLocal
from sqlalchemy import text
async def main():
    with open('/app/scripts/sync/_skill_tmp.json', encoding='utf-8') as f:
        skills = json.load(f)
    async with AsyncSessionLocal() as db:
        cnt = 0
        for s in skills:
            # canonical_name 加 external_id suffix 避 unique conflict
            canonical = f"{s['name']} ({s['external_id'][:30]})"[:200]
            try:
                await db.execute(text('''
                    INSERT INTO canonical_entities
                    (canonical_name, entity_type, description, graph_domain, external_id,
                     first_seen_at, last_seen_at)
                    VALUES (:name, 'skill', :desc, 'knowledge', :ext, NOW(), NOW())
                    ON CONFLICT DO NOTHING
                '''), {'name': canonical, 'desc': s['description'][:500], 'ext': s['external_id']})
                cnt += 1
            except Exception as e:
                print(f'ERR {s.get(\"name\")}: {str(e)[:80]}')
        await db.commit()
        print(f'INGESTED: {cnt}')
asyncio.run(main())
"""
    out = run_in_container(code)
    print(out)
    tmp_file.unlink(missing_ok=True)
    return len(skills)


def main() -> int:
    apply = "--apply" in sys.argv
    print("=== Skill KG ingest 加入 (對齊 owner 安全 純加可逆) ===")
    print()

    skills = list_skills()
    print(f"Skills 盤點: {len(skills)} SKILL.md/*.md from .claude/skills/")

    # 顯示 sample 5
    for s in skills[:5]:
        print(f"  - {s['name']} ({s['rel_path']})")
    if len(skills) > 5:
        print(f"  ... 還有 {len(skills) - 5} 個")
    print()

    if not apply:
        print("🟡 DRY-RUN MODE")
        print(f"DRY-RUN: 預估 {len(skills)} entity 待 INSERT")
        print()
        print("執行真實: python scripts/sync/skill_kg_ingest.py --apply")
        print("回滾: DELETE FROM canonical_entities WHERE entity_type='skill';")
        return 0

    print("🟢 APPLY MODE — 真實 INSERT")
    apply_ingest(skills, dry_run=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
