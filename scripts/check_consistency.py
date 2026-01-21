#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""前後端一致性檢查腳本"""
import sys
import os

# 設定編碼
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, r"C:\GeminiCli\CK_Missive\backend")

def check_models():
    """檢查 ORM 模型載入"""
    try:
        from app.extended.models import (
            PartnerVendor, ContractProject, OfficialDocument,
            GovernmentAgency, User, DocumentCalendarEvent,
            DocumentAttachment, EventReminder, SystemNotification,
            UserSession, SiteNavigationItem, SiteConfiguration,
            ProjectAgencyContact, StaffCertification,
            TaoyuanProject, TaoyuanDispatchOrder
        )
        print("[OK] ORM models loaded (16 core models)")
        return True
    except Exception as e:
        print(f"[FAIL] ORM models failed: {e}")
        return False

def check_main_app():
    """檢查主應用載入"""
    try:
        from main import app  # main.py 在 backend/ 根目錄
        print("[OK] FastAPI main app loaded")
        return True
    except Exception as e:
        print(f"[FAIL] Main app failed: {e}")
        return False

def check_schemas():
    """檢查 Pydantic Schema 載入"""
    try:
        from app.schemas import document, agency, project, user
        print("[OK] Pydantic schemas loaded")
        return True
    except Exception as e:
        print(f"[FAIL] Schemas failed: {e}")
        return False

def check_api_endpoints():
    """檢查 API 端點模組"""
    try:
        from app.api.endpoints import (
            agencies, projects, vendors, users,
            site_management, document_calendar, taoyuan_dispatch
        )
        print("[OK] API endpoints loaded")
        return True
    except Exception as e:
        print(f"[FAIL] API endpoints failed: {e}")
        return False

def check_documents_api():
    """檢查公文 API 模組"""
    try:
        from app.api.endpoints.documents import list as doc_list
        from app.api.endpoints.documents import crud as doc_crud
        print("[OK] Documents API modules loaded")
        return True
    except Exception as e:
        print(f"[FAIL] Documents API failed: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Backend Service Consistency Check")
    print("=" * 50)

    results = []
    results.append(check_models())
    results.append(check_schemas())
    results.append(check_api_endpoints())
    results.append(check_documents_api())
    results.append(check_main_app())

    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} checks passed")

    if all(results):
        print("[SUCCESS] All checks passed")
        sys.exit(0)
    else:
        print("[WARNING] Some checks failed")
        sys.exit(1)
