#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系統重啟後配置持久化檢查工具
確保配置不會意外變動
"""

import os
import sys
import json
import hashlib
import shutil
from pathlib import Path
from datetime import datetime

class ConfigPersistenceChecker:
    def __init__(self):
        self.project_root = Path.cwd()
        self.config_snapshot_file = self.project_root / "config-snapshot.json"
        self.critical_files = [
            ".env",
            ".env.master",
            "docker-compose.unified.yml",
            "configs/docker-compose.yml",
            "port-config.json",
            "backend/Dockerfile.unified",
            "frontend/Dockerfile.unified"
        ]

    def calculate_file_hash(self, file_path):
        """計算檔案的 MD5 雜湊值"""
        if not os.path.exists(file_path):
            return None

        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    def create_config_snapshot(self):
        """創建配置檔案快照"""
        print("=== 創建配置檔案快照 ===")

        snapshot = {
            "timestamp": datetime.now().isoformat(),
            "files": {}
        }

        for file_path in self.critical_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                file_hash = self.calculate_file_hash(full_path)
                file_size = full_path.stat().st_size
                snapshot["files"][file_path] = {
                    "hash": file_hash,
                    "size": file_size,
                    "exists": True
                }
                print(f"[SNAPSHOT] {file_path} - {file_hash[:8]}...")
            else:
                snapshot["files"][file_path] = {
                    "exists": False
                }
                print(f"[MISSING] {file_path}")

        # 保存快照
        with open(self.config_snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, indent=2, ensure_ascii=False)

        print(f"[OK] 配置快照已保存: {self.config_snapshot_file}")
        return snapshot

    def verify_config_integrity(self):
        """驗證配置完整性"""
        print("\n=== 驗證配置檔案完整性 ===")

        if not self.config_snapshot_file.exists():
            print("[ERROR] 配置快照不存在，請先執行 --create-snapshot")
            return False

        # 載入快照
        with open(self.config_snapshot_file, 'r', encoding='utf-8') as f:
            snapshot = json.load(f)

        print(f"[INFO] 快照時間: {snapshot['timestamp']}")

        integrity_ok = True
        changed_files = []

        for file_path, snapshot_data in snapshot["files"].items():
            full_path = self.project_root / file_path
            current_exists = full_path.exists()

            if snapshot_data["exists"] != current_exists:
                print(f"[CHANGED] {file_path} - 存在狀態改變")
                changed_files.append(file_path)
                integrity_ok = False
                continue

            if current_exists:
                current_hash = self.calculate_file_hash(full_path)
                current_size = full_path.stat().st_size

                if current_hash != snapshot_data["hash"]:
                    print(f"[CHANGED] {file_path} - 檔案內容已變更")
                    print(f"  快照雜湊: {snapshot_data['hash'][:8]}...")
                    print(f"  目前雜湊: {current_hash[:8]}...")
                    changed_files.append(file_path)
                    integrity_ok = False
                elif current_size != snapshot_data["size"]:
                    print(f"[CHANGED] {file_path} - 檔案大小改變")
                    changed_files.append(file_path)
                    integrity_ok = False
                else:
                    print(f"[OK] {file_path} - 未變更")

        if integrity_ok:
            print("\n[SUCCESS] 所有配置檔案完整性驗證通過")
        else:
            print(f"\n[WARNING] 發現 {len(changed_files)} 個檔案有變更")
            print("變更的檔案：")
            for file_path in changed_files:
                print(f"  - {file_path}")

        return integrity_ok

    def restore_from_backup(self):
        """從備份還原配置"""
        print("\n=== 從備份還原配置 ===")

        backup_dir = self.project_root / "config-backups"
        if not backup_dir.exists():
            print("[ERROR] 備份目錄不存在")
            return False

        # 尋找最新備份
        backup_files = list(backup_dir.glob("backup-*.tar.gz"))
        if not backup_files:
            print("[ERROR] 沒有找到備份檔案")
            return False

        latest_backup = max(backup_files, key=lambda x: x.stat().st_mtime)
        print(f"[INFO] 使用備份: {latest_backup.name}")

        # 還原檔案（這裡只是示範邏輯）
        print("[INFO] 還原功能需要手動實施")
        print(f"[INFO] 備份位置: {latest_backup}")

        return True

    def create_backup(self):
        """創建配置備份"""
        print("\n=== 創建配置備份 ===")

        backup_dir = self.project_root / "config-backups"
        backup_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup-{timestamp}"
        backup_path = backup_dir / f"{backup_name}.tar.gz"

        # 複製關鍵檔案到臨時目錄
        temp_dir = backup_dir / backup_name
        temp_dir.mkdir(exist_ok=True)

        backed_up_files = []
        for file_path in self.critical_files:
            source = self.project_root / file_path
            if source.exists():
                # 創建目標目錄結構
                target = temp_dir / file_path
                target.parent.mkdir(parents=True, exist_ok=True)

                # 複製檔案
                shutil.copy2(source, target)
                backed_up_files.append(file_path)
                print(f"[BACKUP] {file_path}")

        # 壓縮備份（簡化版本）
        print(f"[OK] 備份完成: {len(backed_up_files)} 個檔案")
        print(f"[INFO] 備份位置: {temp_dir}")

        return True

    def setup_autostart_validation(self):
        """設定系統重啟後自動驗證"""
        print("\n=== 設定系統重啟後自動驗證 ===")

        # 創建自動驗證腳本
        autocheck_script = self.project_root / "auto-config-check.bat"

        script_content = f"""@echo off
echo === 系統啟動後配置自動檢查 ===
cd /d "{self.project_root}"

python config-persistence-check.py --verify
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] 配置檔案完整性檢查失敗
    echo 請檢查配置是否被意外修改
    pause
)

echo === 啟動服務健康檢查 ===
python quick_health_check.py
"""

        with open(autocheck_script, 'w', encoding='utf-8') as f:
            f.write(script_content)

        print(f"[OK] 自動檢查腳本已創建: {autocheck_script}")

        # 創建 Linux/Mac 版本
        autocheck_sh = self.project_root / "auto-config-check.sh"

        sh_content = f"""#!/bin/bash
echo "=== 系統啟動後配置自動檢查 ==="
cd "{self.project_root}"

python3 config-persistence-check.py --verify
if [ $? -ne 0 ]; then
    echo "[WARNING] 配置檔案完整性檢查失敗"
    echo "請檢查配置是否被意外修改"
    read -p "按 Enter 鍵繼續..."
fi

echo "=== 啟動服務健康檢查 ==="
python3 quick_health_check.py
"""

        with open(autocheck_sh, 'w', encoding='utf-8') as f:
            f.write(sh_content)

        # 設定執行權限
        try:
            os.chmod(autocheck_sh, 0o755)
        except:
            pass

        print(f"[OK] Linux/Mac 自動檢查腳本已創建: {autocheck_sh}")
        print("\n[INFO] 使用方式：")
        print("  Windows: 雙擊執行 auto-config-check.bat")
        print("  Linux/Mac: ./auto-config-check.sh")

        return True

    def protect_config_files(self):
        """保護配置檔案不被意外修改"""
        print("\n=== 保護配置檔案 ===")

        protected_count = 0

        for file_path in self.critical_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    # Windows: 設定檔案為唯讀
                    if os.name == 'nt':
                        os.system(f'attrib +R "{full_path}"')
                    else:
                        # Linux/Mac: 設定檔案權限為唯讀
                        os.chmod(full_path, 0o444)

                    print(f"[PROTECTED] {file_path}")
                    protected_count += 1
                except Exception as e:
                    print(f"[ERROR] 無法保護 {file_path}: {e}")

        print(f"[OK] 已保護 {protected_count} 個配置檔案")
        print("\n[WARNING] 如需修改配置，請先執行：")
        print("  python config-persistence-check.py --unprotect")

        return True

    def unprotect_config_files(self):
        """解除配置檔案保護"""
        print("\n=== 解除配置檔案保護 ===")

        unprotected_count = 0

        for file_path in self.critical_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    # Windows: 移除唯讀屬性
                    if os.name == 'nt':
                        os.system(f'attrib -R "{full_path}"')
                    else:
                        # Linux/Mac: 恢復寫入權限
                        os.chmod(full_path, 0o644)

                    print(f"[UNPROTECTED] {file_path}")
                    unprotected_count += 1
                except Exception as e:
                    print(f"[ERROR] 無法解除保護 {file_path}: {e}")

        print(f"[OK] 已解除保護 {unprotected_count} 個配置檔案")

        return True

def main():
    checker = ConfigPersistenceChecker()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "--create-snapshot":
            checker.create_config_snapshot()
        elif command == "--verify":
            result = checker.verify_config_integrity()
            sys.exit(0 if result else 1)
        elif command == "--backup":
            checker.create_backup()
        elif command == "--restore":
            checker.restore_from_backup()
        elif command == "--setup-autostart":
            checker.setup_autostart_validation()
        elif command == "--protect":
            checker.protect_config_files()
        elif command == "--unprotect":
            checker.unprotect_config_files()
        elif command == "--help":
            print("配置持久化檢查工具")
            print()
            print("用法:")
            print("  python config-persistence-check.py --create-snapshot  # 創建配置快照")
            print("  python config-persistence-check.py --verify          # 驗證配置完整性")
            print("  python config-persistence-check.py --backup          # 創建配置備份")
            print("  python config-persistence-check.py --restore         # 從備份還原")
            print("  python config-persistence-check.py --setup-autostart # 設定自動驗證")
            print("  python config-persistence-check.py --protect         # 保護配置檔案")
            print("  python config-persistence-check.py --unprotect       # 解除檔案保護")
        else:
            print(f"未知命令: {command}")
            print("使用 --help 查看用法")
    else:
        # 預設：創建快照並驗證
        print("=== 配置持久化檢查工具 ===")
        checker.create_config_snapshot()
        checker.verify_config_integrity()
        checker.setup_autostart_validation()

if __name__ == "__main__":
    main()