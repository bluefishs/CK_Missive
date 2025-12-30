#!/usr/bin/env python3
"""
行事曆整合系統評估與設定腳本
基於前述架構進行公文事件轉行事曆任務管理的整合實作
"""

import os
import json
import shutil
from pathlib import Path
from datetime import datetime
import sys

class CalendarIntegrationSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.backend_root = self.project_root / "backend"
        self.frontend_root = self.project_root / "frontend"
        self.evaluation_results = {}

    def print_header(self, title):
        """印出標題"""
        print(f"\n{'='*60}")
        print(f" {title}")
        print(f"{'='*60}")

    def print_section(self, title):
        """印出區段標題"""
        print(f"\n{'-'*40}")
        print(f" {title}")
        print(f"{'-'*40}")

    def evaluate_current_system(self):
        """評估現有系統架構"""
        self.print_header("系統架構評估")

        # 檢查後端API端點
        self.print_section("後端API端點分析")
        backend_endpoints = self.backend_root / "app" / "api" / "endpoints"
        calendar_files = {
            "calendar.py": "基本行事曆API",
            "document_calendar.py": "公文行事曆整合API",
            "pure_calendar.py": "純粹行事曆API"
        }

        for file, desc in calendar_files.items():
            file_path = backend_endpoints / file
            exists = "[YES]" if file_path.exists() else "[NO]"
            size = f"({file_path.stat().st_size} bytes)" if file_path.exists() else ""
            print(f"  {exists} {file} - {desc} {size}")

        # 檢查前端頁面
        self.print_section("前端頁面分析")
        frontend_pages = self.frontend_root / "src" / "pages"
        calendar_pages = {
            "CalendarPage.tsx": "主要行事曆頁面（公文整合）",
            "PureCalendarPage.tsx": "純粹行事曆頁面（獨立功能）"
        }

        for file, desc in calendar_pages.items():
            file_path = frontend_pages / file
            exists = "[YES]" if file_path.exists() else "[NO]"
            size = f"({file_path.stat().st_size} bytes)" if file_path.exists() else ""
            print(f"  {exists} {file} - {desc} {size}")

        # 檢查服務層
        self.print_section("服務層分析")
        services = {
            "backend/app/services/document_calendar_service.py": "公文行事曆服務",
            "frontend/src/services/pureCalendarService.ts": "前端純粹行事曆服務"
        }

        for path, desc in services.items():
            file_path = self.project_root / path
            exists = "[YES]" if file_path.exists() else "[NO]"
            print(f"  {exists} {desc}")

        self.evaluation_results["architecture"] = "evaluated"

    def analyze_integration_requirements(self):
        """分析整合需求"""
        self.print_header("[TARGET] 整合需求分析")

        requirements = [
            {
                "title": "公文事件轉換機制",
                "description": "將公文重要日期自動轉為行事曆事件",
                "priority": "高",
                "components": ["Document API", "Calendar Event Creator", "Date Parser"]
            },
            {
                "title": "專案同仁通知系統",
                "description": "向指定專案團隊成員發送行事曆通知",
                "priority": "高",
                "components": ["User Management", "Notification Service", "Project Groups"]
            },
            {
                "title": "Google Calendar雙向同步",
                "description": "本地行事曆與Google Calendar保持同步",
                "priority": "中",
                "components": ["Google API Integration", "Sync Service", "Conflict Resolution"]
            },
            {
                "title": "多層級提醒機制",
                "description": "支援不同優先級和時間的提醒設定",
                "priority": "中",
                "components": ["Reminder Scheduler", "Notification Templates", "Priority Manager"]
            }
        ]

        for i, req in enumerate(requirements, 1):
            print(f"\n{i}. {req['title']} (優先級: {req['priority']})")
            print(f"   描述: {req['description']}")
            print(f"   需要組件: {', '.join(req['components'])}")

        self.evaluation_results["requirements"] = requirements

    def check_current_implementation_gaps(self):
        """檢查現有實作的不足之處"""
        self.print_header("[SEARCH] 實作缺口分析")

        gaps = [
            {
                "area": "公文頁面整合",
                "issue": "公文詳細頁面缺少「加入行事曆」按鈕",
                "impact": "用戶無法直接從公文創建行事曆事件",
                "solution": "在DocumentDetailPage新增CalendarEventCreator組件"
            },
            {
                "area": "通知系統",
                "issue": "缺少專案群組管理和批量通知功能",
                "impact": "無法向專案同仁發送統一通知",
                "solution": "實作ProjectNotificationService和用戶群組管理"
            },
            {
                "area": "同步機制",
                "issue": "Google Calendar整合僅為單向推送",
                "impact": "外部Google Calendar變更無法同步回系統",
                "solution": "實作雙向同步和衝突解決機制"
            },
            {
                "area": "提醒設定",
                "issue": "提醒機制過於簡單，缺少彈性設定",
                "impact": "無法滿足不同使用情境的提醒需求",
                "solution": "實作多層級提醒設定和排程系統"
            }
        ]

        for i, gap in enumerate(gaps, 1):
            print(f"\n{i}. {gap['area']}")
            print(f"   問題: {gap['issue']}")
            print(f"   影響: {gap['impact']}")
            print(f"   解決方案: {gap['solution']}")

        self.evaluation_results["gaps"] = gaps

    def propose_integration_architecture(self):
        """提出整合架構建議"""
        self.print_header("[BUILD] 整合架構設計")

        architecture = {
            "前端層": {
                "DocumentDetailPage": "新增「轉為行事曆事件」功能",
                "CalendarPage": "作為主要行事曆管理中心",
                "NotificationCenter": "統一通知管理界面",
                "ProjectTeamManager": "專案團隊成員管理"
            },
            "服務層": {
                "DocumentCalendarIntegrator": "公文事件轉換服務",
                "ProjectNotificationService": "專案通知服務",
                "CalendarSyncService": "行事曆同步服務",
                "ReminderScheduler": "提醒排程服務"
            },
            "後端API": {
                "/api/document-calendar/convert": "公文轉行事曆事件",
                "/api/notifications/project": "專案通知API",
                "/api/calendar/sync": "行事曆同步API",
                "/api/reminders/schedule": "提醒排程API"
            },
            "資料模型": {
                "DocumentCalendarEvent": "公文行事曆事件",
                "ProjectNotification": "專案通知記錄",
                "CalendarSyncStatus": "同步狀態追蹤",
                "ReminderRule": "提醒規則設定"
            }
        }

        for layer, components in architecture.items():
            print(f"\n[LIST] {layer}:")
            for comp, desc in components.items():
                print(f"   - {comp}: {desc}")

        self.evaluation_results["architecture_design"] = architecture

    def create_implementation_plan(self):
        """建立實作計畫"""
        self.print_header("[CALENDAR] 實作計畫")

        phases = [
            {
                "phase": "第一階段：公文行事曆轉換",
                "duration": "1-2週",
                "tasks": [
                    "在DocumentDetailPage新增「加入行事曆」按鈕",
                    "實作DocumentCalendarIntegrator服務",
                    "建立公文日期解析邏輯",
                    "新增API端點 /api/document-calendar/convert"
                ]
            },
            {
                "phase": "第二階段：專案通知系統",
                "duration": "2-3週",
                "tasks": [
                    "設計專案群組管理界面",
                    "實作ProjectNotificationService",
                    "建立通知模板系統",
                    "整合Email和系統內通知"
                ]
            },
            {
                "phase": "第三階段：Google Calendar強化",
                "duration": "2週",
                "tasks": [
                    "實作雙向同步機制",
                    "建立衝突解決邏輯",
                    "優化現有Google API整合",
                    "新增同步狀態監控"
                ]
            },
            {
                "phase": "第四階段：多層級提醒",
                "duration": "1-2週",
                "tasks": [
                    "設計提醒規則配置界面",
                    "實作ReminderScheduler服務",
                    "建立提醒通知管道",
                    "新增提醒歷史追蹤"
                ]
            }
        ]

        for i, phase in enumerate(phases, 1):
            print(f"\n{i}. {phase['phase']} ({phase['duration']})")
            for task in phase['tasks']:
                print(f"   [DONE] {task}")

        self.evaluation_results["implementation_plan"] = phases

    def generate_setup_files(self):
        """生成設定檔案"""
        self.print_header("[FILE] 生成設定檔案")

        # 建立設定目錄
        config_dir = self.project_root / "calendar_integration_config"
        config_dir.mkdir(exist_ok=True)

        # 生成評估報告
        report_file = config_dir / "evaluation_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "evaluation_results": self.evaluation_results
            }, f, ensure_ascii=False, indent=2)
        print(f"[OK] 評估報告已生成: {report_file}")

        # 生成API規格檔案
        api_spec = {
            "document_calendar_convert": {
                "endpoint": "/api/document-calendar/convert",
                "method": "POST",
                "description": "將公文轉換為行事曆事件",
                "request_body": {
                    "document_id": "公文ID",
                    "event_type": "事件類型 (deadline/meeting/review)",
                    "notification_recipients": "通知收件人列表",
                    "reminder_settings": "提醒設定"
                }
            },
            "project_notification": {
                "endpoint": "/api/notifications/project/{project_id}",
                "method": "POST",
                "description": "發送專案通知",
                "request_body": {
                    "message": "通知訊息",
                    "recipients": "收件人列表",
                    "channels": "通知管道 (email/system/calendar)"
                }
            }
        }

        api_file = config_dir / "api_specifications.json"
        with open(api_file, 'w', encoding='utf-8') as f:
            json.dump(api_spec, f, ensure_ascii=False, indent=2)
        print(f"[OK] API規格檔案已生成: {api_file}")

        # 生成資料庫遷移腳本模板
        migration_sql = """
-- 行事曆整合相關資料表

-- 專案通知設定表
CREATE TABLE IF NOT EXISTS project_notifications (
    id SERIAL PRIMARY KEY,
    project_id INTEGER REFERENCES projects(id),
    user_id INTEGER REFERENCES users(id),
    notification_type VARCHAR(50),
    is_enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 提醒規則表
CREATE TABLE IF NOT EXISTS reminder_rules (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES document_calendar_events(id),
    reminder_type VARCHAR(50),
    trigger_minutes_before INTEGER,
    notification_channels TEXT[], -- email, system, calendar
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 同步狀態追蹤表
CREATE TABLE IF NOT EXISTS calendar_sync_status (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES document_calendar_events(id),
    sync_provider VARCHAR(50), -- google, outlook等
    external_event_id VARCHAR(255),
    last_sync_at TIMESTAMP,
    sync_status VARCHAR(50), -- synced, pending, failed
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

        migration_file = config_dir / "migration_template.sql"
        with open(migration_file, 'w', encoding='utf-8') as f:
            f.write(migration_sql)
        print(f"[OK] 資料庫遷移模板已生成: {migration_file}")

    def run_evaluation(self):
        """執行完整評估"""
        print("[START] 行事曆整合系統評估開始...")

        try:
            self.evaluate_current_system()
            self.analyze_integration_requirements()
            self.check_current_implementation_gaps()
            self.propose_integration_architecture()
            self.create_implementation_plan()
            self.generate_setup_files()

            self.print_header("[OK] 評估完成")
            print(f"[STATS] 評估結果已保存至: calendar_integration_config/")
            print(f"[LIST] 建議立即開始第一階段實作：公文行事曆轉換功能")
            print(f"[TARGET] 預期整體完成時間：6-9週")

        except Exception as e:
            print(f"[ERROR] 評估過程中發生錯誤: {e}")
            return False

        return True

def main():
    """主函數"""
    setup = CalendarIntegrationSetup()
    success = setup.run_evaluation()

    if success:
        print(f"\n[SUCCESS] 設定完成！可以開始進行整合實作。")
        print(f"[IDEA] 建議下一步：執行第一階段實作計畫")
    else:
        print(f"\n[ERROR] 設定失敗，請檢查錯誤訊息。")
        sys.exit(1)

if __name__ == "__main__":
    main()