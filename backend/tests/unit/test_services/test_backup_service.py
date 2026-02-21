# -*- coding: utf-8 -*-
"""
BackupService 單元測試

測試範圍:
- Docker 偵測: _find_docker_path, _check_docker_available
- 備份建立: create_backup (mock subprocess)
- 備份列表: list_backups
- 備份刪除: delete_backup
- 還原邏輯: restore_database
- 環境狀態: get_environment_status
- 配置取得: get_backup_config
- 清理功能: cleanup_orphan_files

測試策略: Mock subprocess、os.path、shutil，不使用真實 Docker 與檔案系統。

v1.0.0 - 2026-02-21
"""
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest

from app.services.backup import utils as backup_utils


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def mock_settings():
    """建立 mock settings"""
    with patch("app.services.backup.utils.settings") as mock_s:
        mock_s.POSTGRES_USER = "test_user"
        mock_s.POSTGRES_PASSWORD = "test_pass"
        mock_s.POSTGRES_DB = "test_db"
        yield mock_s


@pytest.fixture
def service(mock_settings, tmp_path):
    """建立 BackupService 實例，使用 tmp_path 避免操作真實檔案系統"""
    with patch("app.services.backup.utils.BackupUtilsMixin._find_docker_path", return_value="docker"), \
         patch("app.services.backup.utils.BackupUtilsMixin._check_docker_available", return_value=True), \
         patch("app.services.backup.utils.BackupUtilsMixin._load_remote_config", return_value={}), \
         patch("app.services.backup.utils.BackupUtilsMixin._load_backup_logs", return_value=[]), \
         patch("app.services.backup.utils.BackupUtilsMixin._ensure_directories"):

        from app.services.backup import BackupService

        svc = BackupService.__new__(BackupService)
        svc.project_root = tmp_path
        svc.backup_dir = tmp_path / "backups" / "database"
        svc.attachment_backup_dir = tmp_path / "backups" / "attachments"
        svc.uploads_dir = tmp_path / "backend" / "uploads"
        svc.log_dir = tmp_path / "logs" / "backup"
        svc.backup_script = tmp_path / "scripts" / "backup" / "db_backup.ps1"
        svc.restore_script = tmp_path / "scripts" / "backup" / "db_restore.ps1"
        svc.db_user = "test_user"
        svc.db_password = "test_pass"
        svc.db_name = "test_db"
        svc.container_name = "test_postgres"
        svc._docker_path = "docker"
        svc._docker_available = True
        svc.remote_config_file = tmp_path / "config" / "remote_backup.json"
        svc._remote_config = {}
        svc.backup_log_file = tmp_path / "logs" / "backup" / "backup_operations.json"
        svc._backup_logs = []

        # 建立必要目錄
        svc.backup_dir.mkdir(parents=True, exist_ok=True)
        svc.attachment_backup_dir.mkdir(parents=True, exist_ok=True)
        svc.log_dir.mkdir(parents=True, exist_ok=True)

        yield svc


# ============================================================
# Docker 偵測測試
# ============================================================

class TestFindDockerPath:
    """_find_docker_path 方法測試"""

    def test_find_docker_via_which(self, mock_settings):
        """測試透過 shutil.which 找到 Docker"""
        with patch("shutil.which", return_value="/usr/bin/docker"), \
             patch("app.services.backup.utils.BackupUtilsMixin._check_docker_available", return_value=True), \
             patch("app.services.backup.utils.BackupUtilsMixin._load_remote_config", return_value={}), \
             patch("app.services.backup.utils.BackupUtilsMixin._load_backup_logs", return_value=[]), \
             patch("app.services.backup.utils.BackupUtilsMixin._ensure_directories"), \
             patch("app.services.backup.utils.BackupUtilsMixin._load_env_config"):

            from app.services.backup import BackupService
            svc = BackupService.__new__(BackupService)
            result = svc._find_docker_path()

            assert result == "/usr/bin/docker"

    def test_find_docker_fallback(self, mock_settings):
        """測試 shutil.which 找不到時回退到 "docker" """
        with patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):

            from app.services.backup import BackupService
            svc = BackupService.__new__(BackupService)
            result = svc._find_docker_path()

            assert result == "docker"


class TestCheckDockerAvailable:
    """_check_docker_available 方法測試

    注意: service fixture 內部 patch 了 _check_docker_available，
    因此這裡直接建立新實例來測試真實方法邏輯。
    """

    def test_docker_available(self, mock_settings):
        """測試 Docker 可用"""
        from app.services.backup import BackupService

        svc = BackupService.__new__(BackupService)
        svc._docker_path = "docker"

        with patch.object(backup_utils, "subprocess") as mock_sub:
            mock_sub.run.return_value = MagicMock(returncode=0)
            result = svc._check_docker_available()
            assert result is True

    def test_docker_not_available(self, mock_settings):
        """測試 Docker 不可用"""
        from app.services.backup import BackupService

        svc = BackupService.__new__(BackupService)
        svc._docker_path = "docker"

        with patch.object(backup_utils, "subprocess") as mock_sub:
            mock_sub.run.side_effect = FileNotFoundError
            result = svc._check_docker_available()
            assert result is False


# ============================================================
# 備份列表測試
# ============================================================

class TestListBackups:
    """list_backups 方法測試"""

    @pytest.mark.asyncio
    async def test_list_backups_empty(self, service):
        """測試列出備份 - 空目錄"""
        result = await service.list_backups()

        assert "database_backups" in result
        assert "attachment_backups" in result
        assert "statistics" in result
        assert result["statistics"]["database_backup_count"] == 0

    @pytest.mark.asyncio
    async def test_list_backups_with_files(self, service):
        """測試列出備份 - 有備份檔案"""
        # 建立模擬備份檔案
        backup_file = service.backup_dir / "ck_missive_backup_20260101_120000.sql"
        backup_file.write_text("-- PostgreSQL database dump\n-- PostgreSQL database dump complete")

        result = await service.list_backups()

        assert result["statistics"]["database_backup_count"] == 1
        assert result["database_backups"][0]["filename"] == "ck_missive_backup_20260101_120000.sql"

    @pytest.mark.asyncio
    async def test_list_backups_skips_zero_byte(self, service):
        """測試列出備份 - 跳過 0-byte 檔案"""
        # 建立 0-byte 備份（失敗的備份）
        zero_file = service.backup_dir / "ck_missive_backup_20260101_000000.sql"
        zero_file.write_text("")

        result = await service.list_backups()

        assert result["statistics"]["database_backup_count"] == 0


# ============================================================
# 備份建立測試
# ============================================================

class TestCreateBackup:
    """create_backup 方法測試"""

    @pytest.mark.asyncio
    async def test_create_backup_docker_unavailable(self, service):
        """測試 Docker 不可用時備份失敗"""
        service._docker_available = False

        result = await service.create_backup(
            include_database=True,
            include_attachments=False,
        )

        assert result["success"] is False
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_create_backup_attachments_no_uploads(self, service):
        """測試附件備份 - 無 uploads 目錄"""
        result = await service.create_backup(
            include_database=False,
            include_attachments=True,
        )

        # uploads 目錄不存在時應仍然成功（無檔案可備份）
        att = result.get("attachments_backup")
        assert att is not None
        assert att["success"] is True


# ============================================================
# 備份刪除測試
# ============================================================

class TestDeleteBackup:
    """delete_backup 方法測試"""

    @pytest.mark.asyncio
    async def test_delete_database_backup(self, service):
        """測試刪除資料庫備份"""
        backup_file = service.backup_dir / "ck_missive_backup_20260101_120000.sql"
        backup_file.write_text("test")

        result = await service.delete_backup(
            "ck_missive_backup_20260101_120000.sql", "database"
        )

        assert result["success"] is True
        assert not backup_file.exists()

    @pytest.mark.asyncio
    async def test_delete_backup_not_found(self, service):
        """測試刪除不存在的備份"""
        result = await service.delete_backup("nonexistent.sql", "database")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_delete_incremental_backup_forbidden(self, service):
        """測試禁止刪除增量備份主目錄"""
        result = await service.delete_backup(
            "attachments_latest", "attachments"
        )

        assert result["success"] is False
        assert "Cannot delete" in result["error"]


# ============================================================
# 還原測試
# ============================================================

class TestRestoreDatabase:
    """restore_database 方法測試"""

    @pytest.mark.asyncio
    async def test_restore_database_file_not_found(self, service):
        """測試還原不存在的備份檔案"""
        result = await service.restore_database("nonexistent.sql")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_restore_database_success(self, service):
        """測試成功還原資料庫"""
        backup_file = service.backup_dir / "ck_missive_backup_restore.sql"
        backup_file.write_text("-- PostgreSQL dump")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")

            result = await service.restore_database(
                "ck_missive_backup_restore.sql"
            )

        assert result["success"] is True
        assert "restored" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_restore_database_psql_failure(self, service):
        """測試 psql 還原失敗"""
        backup_file = service.backup_dir / "ck_missive_backup_fail.sql"
        backup_file.write_text("-- PostgreSQL dump")

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stderr="psql: error"
            )

            result = await service.restore_database(
                "ck_missive_backup_fail.sql"
            )

        assert result["success"] is False


# ============================================================
# 環境狀態測試
# ============================================================

class TestGetEnvironmentStatus:
    """get_environment_status 方法測試"""

    def test_get_environment_status(self, service):
        """測試取得環境狀態"""
        with patch.object(service, "_check_docker_available", return_value=True):
            result = service.get_environment_status()

        assert "docker_available" in result
        assert "docker_path" in result
        assert "backup_dir_exists" in result
        assert result["docker_available"] is True


# ============================================================
# 配置取得測試
# ============================================================

class TestGetBackupConfig:
    """get_backup_config 方法測試"""

    @pytest.mark.asyncio
    async def test_get_backup_config(self, service):
        """測試取得備份配置"""
        result = await service.get_backup_config()

        assert "backup_directory" in result
        assert "database_name" in result
        assert "database_user" in result
        assert result["database_name"] == "test_db"
        assert result["database_user"] == "test_user"


# ============================================================
# 清理功能測試
# ============================================================

class TestCleanupOrphanFiles:
    """cleanup_orphan_files 方法測試"""

    @pytest.mark.asyncio
    async def test_cleanup_orphan_files_cleans_zero_byte(self, service):
        """測試清理 0-byte 孤立檔案"""
        # 建立 0-byte 孤立檔案
        orphan = service.backup_dir / "ck_missive_backup_orphan.sql"
        orphan.write_text("")

        with patch.object(service, "_log_backup_operation", new_callable=AsyncMock):
            result = await service.cleanup_orphan_files()

        assert result["cleaned_count"] == 1
        assert "ck_missive_backup_orphan.sql" in result["files"]
        assert not orphan.exists()

    @pytest.mark.asyncio
    async def test_cleanup_orphan_files_keeps_valid(self, service):
        """測試清理不會刪除有效備份"""
        # 建立有內容的備份檔案
        valid = service.backup_dir / "ck_missive_backup_valid.sql"
        valid.write_text("-- PostgreSQL dump content")

        with patch.object(service, "_log_backup_operation", new_callable=AsyncMock):
            result = await service.cleanup_orphan_files()

        assert result["cleaned_count"] == 0
        assert valid.exists()

    @pytest.mark.asyncio
    async def test_cleanup_orphan_files_empty(self, service):
        """測試清理空目錄"""
        result = await service.cleanup_orphan_files()

        assert result["cleaned_count"] == 0
        assert result["files"] == []
