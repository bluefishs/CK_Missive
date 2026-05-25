# -*- coding: utf-8 -*-
"""集中專案路徑常數 — v6.10 P1-E SSOT（2026-05-18 律定）

起因：5/18 揭發 backup_scheduler path bug（Wave 8 遷子包後 Path.parents[N]
未同步），導致 5/13-5/16 backup 寫到錯位置 + audit/log 跨層遷移風險。

律定（規約 E）：禁止 service / repository / script 自算 Path(__file__).parents[N]，
必須 from app.core.paths import ... 統一取用。

加 fitness step 30 `paths_sloppy_calc_guard.py` 偵測新代碼用 `parents\[`。
"""
from __future__ import annotations

from pathlib import Path

# 本檔位於 backend/app/core/paths.py
# parents[0]=core / parents[1]=app / parents[2]=backend / parents[3]=PROJECT_ROOT
PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

# === 一級資料夾 ===
BACKEND_DIR: Path = PROJECT_ROOT / "backend"
FRONTEND_DIR: Path = PROJECT_ROOT / "frontend"
DOCS_DIR: Path = PROJECT_ROOT / "docs"
SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"
WIKI_DIR: Path = PROJECT_ROOT / "wiki"
CONFIGS_DIR: Path = PROJECT_ROOT / "configs"
TESTS_DIR: Path = PROJECT_ROOT / "tests"

# === Runtime（全 .gitignore）===
LOGS_DIR: Path = PROJECT_ROOT / "logs"
BACKUPS_DIR: Path = PROJECT_ROOT / "backups"
UPLOADS_DIR: Path = PROJECT_ROOT / "uploads"
SECRETS_DIR: Path = PROJECT_ROOT / "secrets"
DATA_DIR: Path = PROJECT_ROOT / "data"

# === 子資料夾常數（避免散落計算）===
BACKUP_DB_DIR: Path = BACKUPS_DIR / "database"
BACKUP_ATTACH_DIR: Path = BACKUPS_DIR / "attachments"
BACKUP_LOG_DIR: Path = LOGS_DIR / "backup"

WIKI_ENTITIES_DIR: Path = WIKI_DIR / "entities"
WIKI_TOPICS_DIR: Path = WIKI_DIR / "topics"
WIKI_MEMORY_DIR: Path = WIKI_DIR / "memory"
WIKI_SYNTHESIS_DIR: Path = WIKI_DIR / "synthesis"

# memory wiki 子資料夾（v6.10 P1 memory/ 8 檔批次接通 SSOT 用）
WIKI_MEMORY_DIARY_DIR: Path = WIKI_MEMORY_DIR / "diary"
WIKI_MEMORY_FAILURES_DIR: Path = WIKI_MEMORY_DIR / "failures"
WIKI_MEMORY_PATTERNS_DIR: Path = WIKI_MEMORY_DIR / "patterns"
WIKI_MEMORY_PROPOSALS_DIR: Path = WIKI_MEMORY_DIR / "proposals"
WIKI_MEMORY_CRYSTALS_DIR: Path = WIKI_MEMORY_DIR / "crystals"
WIKI_SOUL_PATH: Path = WIKI_DIR / "SOUL.md"

DOCS_ADR_DIR: Path = DOCS_DIR / "adr"
DOCS_ARCH_DIR: Path = DOCS_DIR / "architecture"
DOCS_RUNBOOKS_DIR: Path = DOCS_DIR / "runbooks"
DOCS_ARCHIVED_DIR: Path = DOCS_DIR / "archived"

# === 配置 ===
ENV_FILE: Path = PROJECT_ROOT / ".env"
REMOTE_BACKUP_CONFIG: Path = CONFIGS_DIR / "remote_backup.json"

# === 跨 repo 相關（cross-repo path discovery）===
CKPROJECT_ROOT: Path = PROJECT_ROOT.parent  # D:/CKProject (CK_AaaP, hermes-agent 等同層)


def ensure_runtime_dirs() -> None:
    """確保 runtime 目錄存在（idempotent，由 main.py startup 呼叫）"""
    for d in (LOGS_DIR, BACKUPS_DIR, UPLOADS_DIR, BACKUP_DB_DIR,
              BACKUP_ATTACH_DIR, BACKUP_LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


__all__ = [
    "PROJECT_ROOT",
    "BACKEND_DIR", "FRONTEND_DIR", "DOCS_DIR", "SCRIPTS_DIR",
    "WIKI_DIR", "CONFIGS_DIR", "TESTS_DIR",
    "LOGS_DIR", "BACKUPS_DIR", "UPLOADS_DIR", "SECRETS_DIR", "DATA_DIR",
    "BACKUP_DB_DIR", "BACKUP_ATTACH_DIR", "BACKUP_LOG_DIR",
    "WIKI_ENTITIES_DIR", "WIKI_TOPICS_DIR", "WIKI_MEMORY_DIR", "WIKI_SYNTHESIS_DIR",
    "WIKI_MEMORY_DIARY_DIR", "WIKI_MEMORY_FAILURES_DIR",
    "WIKI_MEMORY_PATTERNS_DIR", "WIKI_MEMORY_PROPOSALS_DIR",
    "WIKI_MEMORY_CRYSTALS_DIR", "WIKI_SOUL_PATH",
    "DOCS_ADR_DIR", "DOCS_ARCH_DIR", "DOCS_RUNBOOKS_DIR", "DOCS_ARCHIVED_DIR",
    "ENV_FILE", "REMOTE_BACKUP_CONFIG",
    "CKPROJECT_ROOT", "ensure_runtime_dirs",
]
