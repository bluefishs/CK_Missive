# -*- coding: utf-8 -*-
"""集中專案路徑常數 — v6.10 P1-E SSOT（2026-05-18 律定）

起因：5/18 揭發 backup_scheduler path bug（Wave 8 遷子包後 Path.parents[N]
未同步），導致 5/13-5/16 backup 寫到錯位置 + audit/log 跨層遷移風險。

律定（規約 E）：禁止 service / repository / script 自算 Path(__file__).parents[N]，
必須 from app.core.paths import ... 統一取用。

加 fitness step 30 `paths_sloppy_calc_guard.py` 偵測新代碼用 `parents\[`。
"""
from __future__ import annotations

import os
from pathlib import Path

# 本檔位於 backend/app/core/paths.py
# parents[0]=core / parents[1]=app / parents[2]=backend / parents[3]=PROJECT_ROOT
#
# v6.12 (2026-05-30) Pipeline silent dormant 修法：
#   Docker container 內 main.py 在 /app/main.py，paths.py 在 /app/app/core/paths.py
#   parents[3] = / (root) → PROJECT_ROOT 計算錯誤，導致 WIKI_DIR=/wiki 但實際 mount 在 /app/wiki
#   揭發：5/28-5/30 optimization_pipeline silent 寫 /wiki Permission denied
#   修法：環境變數 CK_PROJECT_ROOT override，container 內 docker-compose 注入 = /app
#
# ⚠️ L52 (2026-05-30) 警示：若改動 PROJECT_ROOT 邏輯（含 CK_PROJECT_ROOT env），
#    必須同步檢查所有 docker-compose.*.yml mount target prefix 是否對齊。
#    違反 → cron 找 PROJECT_ROOT/scripts 不存在 → silent dormant（同 L52 教訓）
#    Audit: scripts/checks/paths_compose_mount_audit.py (fitness step 62)
_env_root = os.getenv("CK_PROJECT_ROOT")
if _env_root and Path(_env_root).exists():
    PROJECT_ROOT: Path = Path(_env_root).resolve()
else:
    PROJECT_ROOT: Path = Path(__file__).resolve().parents[3]

# === 一級資料夾 ===
# v6.13 (2026-05-31) L52 family 第 8 案修法：
# bug: container 內 PROJECT_ROOT=/app 但 host 的 backend/* 內容已 flatten 到 /app/
#      → /app/backend 不存在 / /app/frontend 不存在 (frontend dist 在 /frontend/dist)
# 修法: 加 fallback — 若 PROJECT_ROOT/backend 不存在則 BACKEND_DIR=PROJECT_ROOT 自己
#       對齊 docker container 結構 (WORKDIR=/app, host backend/* flatten 入)
_default_backend = PROJECT_ROOT / "backend"
BACKEND_DIR: Path = _default_backend if _default_backend.exists() else PROJECT_ROOT
_default_frontend = PROJECT_ROOT / "frontend"
if _default_frontend.exists():
    FRONTEND_DIR: Path = _default_frontend
elif Path("/frontend").exists():
    # container 內 dist mount 在根目錄 /frontend/dist
    FRONTEND_DIR: Path = Path("/frontend")
else:
    FRONTEND_DIR: Path = _default_frontend
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
