"""
Skill 自動掃描器 — NemoClaw Stage 3

掃描 .claude/skills/*.md 檔案，提取 frontmatter metadata，
轉換為 ToolDefinition 格式供 ToolRegistry 自動註冊。

Version: 1.0.0
Created: 2026-03-19
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# PROJECT_ROOT: backend/app/services/ai/ → parents[4] = CK_Missive/
PROJECT_ROOT = Path(__file__).resolve().parents[5]

# 排除的檔案名稱（非 skill 內容）
_EXCLUDED_FILES = {"README.md", "SKILLS_INVENTORY.md", "SKILL-TEMPLATE.md"}


def _parse_frontmatter(content: str) -> Dict[str, Any]:
    """
    解析 YAML frontmatter（--- 標記之間的內容）。

    僅解析 name, description, triggers 三個欄位，
    使用簡單正則而非完整 YAML parser 以減少依賴。
    """
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return {}

    fm_text = match.group(1)
    result: Dict[str, Any] = {}

    # name
    name_match = re.search(r"^name:\s*(.+)$", fm_text, re.MULTILINE)
    if name_match:
        result["name"] = name_match.group(1).strip().strip("'\"")

    # description (支援多行 > 格式和單行)
    desc_match = re.search(
        r"^description:\s*>\s*\n((?:\s+.+\n?)+)", fm_text, re.MULTILINE
    )
    if desc_match:
        # 多行 > 格式：合併為單行
        lines = desc_match.group(1).strip().splitlines()
        result["description"] = " ".join(line.strip() for line in lines)
    else:
        desc_match = re.search(r"^description:\s*(.+)$", fm_text, re.MULTILINE)
        if desc_match:
            result["description"] = desc_match.group(1).strip().strip("'\"")

    # triggers (YAML list)
    triggers_match = re.search(
        r"^triggers:\s*\n((?:\s+-\s+.+\n?)+)", fm_text, re.MULTILINE
    )
    if triggers_match:
        trigger_lines = triggers_match.group(1).strip().splitlines()
        result["triggers"] = [
            line.strip().lstrip("- ").strip().strip("'\"")
            for line in trigger_lines
            if line.strip().startswith("-")
        ]

    return result


def _extract_from_heading(content: str) -> Dict[str, Any]:
    """
    從 Markdown 的第一個標題和第一段文字提取 metadata。
    用於沒有 frontmatter 的 skill 檔案。
    """
    result: Dict[str, Any] = {}

    # 跳過可能的 frontmatter 區塊
    text = content
    if text.startswith("---"):
        end = text.find("---", 3)
        if end > 0:
            text = text[end + 3:].strip()

    # 提取第一個標題
    heading_match = re.search(r"^#+\s+(.+)$", text, re.MULTILINE)
    if heading_match:
        title = heading_match.group(1).strip()
        # 從標題生成 name (kebab-case)
        name = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", title).strip("-").lower()
        result["name"] = name
        result["description"] = title

    # 提取第一段非空文字作為描述
    lines = text.splitlines()
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("```"):
            result["description"] = stripped[:200]
            break

    return result


def scan_skills() -> List[Dict[str, Any]]:
    """
    掃描所有 skills，返回 metadata 列表。

    掃描目錄：
    - .claude/skills/*.md (專案 skills)
    - .claude/skills/_shared/shared/*.md (共享 skills)
    - .claude/skills/_shared/shared/superpowers/*/SKILL.md (superpowers)
    - .claude/skills/_shared/react/*.md (React skills)

    Returns:
        [
            {
                "name": "document-management",
                "description": "公文管理領域知識",
                "triggers": ["公文", "document", "收文", "發文"],
                "file_path": ".claude/skills/document-management.md",
            },
            ...
        ]
    """
    skills: List[Dict[str, Any]] = []
    skills_root = PROJECT_ROOT / ".claude" / "skills"

    if not skills_root.is_dir():
        logger.warning("Skills directory not found: %s", skills_root)
        return skills

    # Collect all skill files
    skill_files: List[Path] = []

    # 1. Project-level skills
    for f in sorted(skills_root.glob("*.md")):
        if f.name not in _EXCLUDED_FILES:
            skill_files.append(f)

    # 2. Shared skills
    shared_dir = skills_root / "_shared" / "shared"
    if shared_dir.is_dir():
        for f in sorted(shared_dir.glob("*.md")):
            if f.name not in _EXCLUDED_FILES:
                skill_files.append(f)

    # 3. Superpowers (each in its own directory with SKILL.md)
    superpowers_dir = shared_dir / "superpowers"
    if superpowers_dir.is_dir():
        for subdir in sorted(superpowers_dir.iterdir()):
            if subdir.is_dir():
                skill_file = subdir / "SKILL.md"
                if skill_file.exists():
                    skill_files.append(skill_file)

    # 4. React shared skills
    react_dir = skills_root / "_shared" / "react"
    if react_dir.is_dir():
        for f in sorted(react_dir.glob("*.md")):
            if f.name not in _EXCLUDED_FILES:
                skill_files.append(f)

    # Parse each file
    seen_names: set = set()
    for file_path in skill_files:
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.debug("Failed to read skill file %s: %s", file_path, e)
            continue

        # Try frontmatter first, then heading extraction
        metadata = _parse_frontmatter(content)
        if not metadata.get("name"):
            metadata = _extract_from_heading(content)

        name = metadata.get("name")
        if not name:
            # Derive from filename
            name = file_path.stem

        # Sanitize name: must be ASCII-safe for tool registration
        # If name contains non-ASCII, fall back to filename stem
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            name = file_path.stem
        # If still non-ASCII (e.g. Chinese filename), skip
        if not re.match(r"^[a-zA-Z0-9_-]+$", name):
            logger.debug("Skipping skill with non-ASCII name: %s", file_path)
            continue

        # Deduplicate
        if name in seen_names:
            continue
        seen_names.add(name)

        description = metadata.get("description", name.replace("-", " ").title())
        triggers = metadata.get("triggers", [])
        rel_path = str(file_path.relative_to(PROJECT_ROOT)).replace("\\", "/")

        skills.append({
            "name": name,
            "description": description,
            "triggers": triggers,
            "file_path": rel_path,
        })

    logger.info("Scanned %d skills from %s", len(skills), skills_root)
    return skills
