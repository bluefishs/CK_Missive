# -*- coding: utf-8 -*-
"""
異地備份設定 UTF-8 BOM 讀取 Regression（2026-07-29）

事故（owner 多次回報「異地備份無法正常運作」）：
  `/admin/backup` → 異地備份分頁顯示路徑空白、開關關閉、最後同步時間「尚未同步」，
  但 NAS 上實際每日都有新的 dump（實測 30 份、最新當日 493MB），
  Windows 排程 `CK-Missive-Offsite-Backup` LastTaskResult=0。

根因（跨語言 writer/reader 編碼契約）：
  `backend/config/remote_backup.json` 的寫入者是 **Windows PowerShell** 排程腳本，
  PS 5.1 `Set-Content -Encoding UTF8` 會寫入 **UTF-8 BOM**（實測檔頭 `EF BB BF`）；
  Python 端以 `encoding="utf-8"` + `json.load` 讀取 → 拋
  `Unexpected UTF-8 BOM (decode using utf-8-sig)` → 被 except 吞成 warning →
  **整份設定 silent 退回預設值** → UI 顯示「尚未同步」＝看起來像備份壞掉。

  註：此症狀曾被判為「UI 誤解」而只加了說明 Alert（2026-07-03 `ab01ef3e`），
  屬未穿透診斷；真因是本編碼契約。

修法：改用 `utf-8-sig`（對有/無 BOM 皆正確），並把讀取失敗從 warning 升為 error。
"""
import json

import pytest

from app.services.backup import BackupService


def _make_svc(tmp_path):
    svc = BackupService.__new__(BackupService)
    svc.remote_config_file = tmp_path / "remote_backup.json"
    return svc


CONFIG = {
    "remote_path": "\\\\CKNAS\\CK_Project\\#Project_data\\missive_databsae",
    "sync_enabled": False,
    "sync_interval_hours": 24,
    "last_sync_time": "2026-07-29T03:00:08.709112",
    "sync_status": "idle",
    "remote_file_count": 30,
    "latest_remote_file": "ck_missive_backup_20260729_015958.sql",
}


class TestRemoteConfigEncoding:
    def test_reads_utf8_with_bom(self, tmp_path):
        """PowerShell 寫出的 BOM 檔必須能讀（修法前這裡會退回預設值）。"""
        svc = _make_svc(tmp_path)
        # utf-8-sig 寫入 = PS 5.1 Set-Content -Encoding UTF8 的實際位元組
        svc.remote_config_file.write_text(
            json.dumps(CONFIG, ensure_ascii=False), encoding="utf-8-sig"
        )
        assert svc.remote_config_file.read_bytes()[:3] == b"\xef\xbb\xbf", "前置條件：檔案應含 BOM"

        cfg = svc._load_remote_config()
        assert cfg["last_sync_time"] == CONFIG["last_sync_time"], (
            "BOM 檔讀取失敗會 silent 退回預設 None → UI 顯示「尚未同步」"
        )
        assert cfg["remote_path"] == CONFIG["remote_path"]
        assert cfg["remote_file_count"] == 30, "PS 寫入的 NAS 狀態欄位須完整帶出"

    def test_reads_utf8_without_bom(self, tmp_path):
        """容器自身寫出的無 BOM 檔行為不得回歸。"""
        svc = _make_svc(tmp_path)
        svc.remote_config_file.write_text(
            json.dumps(CONFIG, ensure_ascii=False), encoding="utf-8"
        )
        cfg = svc._load_remote_config()
        assert cfg["last_sync_time"] == CONFIG["last_sync_time"]

    def test_missing_file_falls_back_to_defaults(self, tmp_path):
        svc = _make_svc(tmp_path)
        cfg = svc._load_remote_config()
        assert cfg["last_sync_time"] is None and cfg["sync_enabled"] is False

    def test_save_does_not_clobber_scheduler_written_fields(self, tmp_path):
        """容器儲存設定時，不得覆蓋排程（容器外 writer）剛寫入的 NAS 狀態欄位。"""
        svc = _make_svc(tmp_path)
        svc.remote_config_file.write_text(
            json.dumps(CONFIG, ensure_ascii=False), encoding="utf-8-sig"
        )
        # 模擬容器啟動時載入的舊快照（缺 NAS 欄位、時間較舊）
        svc._remote_config = {
            "remote_path": "\\\\CKNAS\\new-path",
            "sync_enabled": True,
            "sync_interval_hours": 12,
            "last_sync_time": "2026-07-09T03:00:00",
        }
        svc._save_remote_config()

        saved = json.loads(svc.remote_config_file.read_text(encoding="utf-8-sig"))
        assert saved["sync_interval_hours"] == 12, "容器擁有的設定欄位應被寫入"
        assert saved["remote_path"] == "\\\\CKNAS\\new-path"
        assert saved["last_sync_time"] == CONFIG["last_sync_time"], "排程寫入的時間不得被舊快照覆蓋"
        assert saved["remote_file_count"] == 30, "排程寫入的 NAS 狀態不得遺失"


@pytest.mark.parametrize("encoding", ["utf-8-sig", "utf-8"])
def test_reload_picks_up_external_changes(tmp_path, encoding):
    """排程每日更新檔案後，不重啟後端也要讀得到（原本只在建構時讀一次）。"""
    svc = _make_svc(tmp_path)
    svc.remote_config_file.write_text(json.dumps(CONFIG, ensure_ascii=False), encoding=encoding)
    svc._remote_config = svc._load_remote_config()

    updated = {**CONFIG, "last_sync_time": "2026-07-30T03:00:01"}
    svc.remote_config_file.write_text(json.dumps(updated, ensure_ascii=False), encoding=encoding)

    assert svc.reload_remote_config()["last_sync_time"] == "2026-07-30T03:00:01"
