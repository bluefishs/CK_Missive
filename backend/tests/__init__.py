# -*- coding: utf-8 -*-
"""
CK_Missive 後端測試套件
Backend Test Suite

目錄結構:
    tests/
    ├── __init__.py          # 本檔案
    ├── conftest.py          # 共用 fixtures
    ├── test_schema_consistency.py  # Schema 一致性測試
    ├── unit/                # 單元測試
    │   ├── __init__.py
    │   └── test_validators.py
    ├── integration/         # 整合測試
    │   ├── __init__.py
    │   └── test_documents_api.py
    └── factories/           # 測試資料工廠
        ├── __init__.py
        └── document_factory.py
"""
