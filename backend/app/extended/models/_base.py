"""
共享基礎 - ORM 模型共用匯入

所有子模組從此檔案匯入 Base, Vector, func 等共用依賴。
"""
from sqlalchemy import (
    Column, Integer, String, Float, Date, DateTime,
    ForeignKey, Text, Boolean, Table, func,
    UniqueConstraint, Index, JSON,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, deferred
from datetime import datetime

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    Vector = None

# pgvector 需要 Python 套件 AND PostgreSQL 擴展同時可用
import os
if Vector is not None and os.environ.get("PGVECTOR_ENABLED", "false").lower() != "true":
    Vector = None

from app.db.database import Base

__all__ = [
    "Base", "Vector",
    "Column", "Integer", "String", "Float", "Date", "DateTime",
    "ForeignKey", "Text", "Boolean", "Table", "func",
    "UniqueConstraint", "Index", "JSON", "JSONB",
    "relationship", "deferred", "datetime",
]
