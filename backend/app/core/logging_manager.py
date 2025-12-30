# -*- coding: utf-8 -*-
"""
統一日誌管理系統
處理系統錯誤LOG整合、分級和監控
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum
from pathlib import Path

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class LogLevel(str, Enum):
    """日誌級別枚舉"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class ErrorCategory(str, Enum):
    """錯誤類別枚舉"""
    SYSTEM = "SYSTEM"           # 系統層級錯誤
    DATABASE = "DATABASE"       # 資料庫錯誤
    API = "API"                # API相關錯誤
    AUTH = "AUTH"              # 認證授權錯誤
    VALIDATION = "VALIDATION"   # 資料驗證錯誤
    EXTERNAL = "EXTERNAL"       # 外部服務錯誤
    UNICODE = "UNICODE"         # Unicode編碼錯誤


class LogEntry:
    """統一日誌記錄格式"""
    
    def __init__(
        self,
        level: LogLevel,
        message: str,
        category: ErrorCategory = ErrorCategory.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.timestamp = timestamp or datetime.now()
        self.level = level
        self.category = category
        self.message = message
        self.details = details or {}
        self.request_id = request_id
        self.user_id = user_id
    
    def to_dict(self) -> Dict[str, Any]:
        """轉換為字典格式"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level.value,
            "category": self.category.value,
            "message": self.message,
            "details": self.details,
            "request_id": self.request_id,
            "user_id": self.user_id
        }
    
    def to_json(self) -> str:
        """轉換為JSON格式"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class SystemLogManager:
    """系統日誌管理器"""
    
    def __init__(self, log_dir: str = "logs", max_file_size: int = 10 * 1024 * 1024):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.max_file_size = max_file_size
        
        # 初始化不同類型的日誌記錄器
        self._setup_loggers()
        
        # 錯誤統計
        self.error_stats = {
            "total_errors": 0,
            "by_category": {cat.value: 0 for cat in ErrorCategory},
            "by_level": {level.value: 0 for level in LogLevel},
            "recent_errors": []
        }
    
    def _setup_loggers(self):
        """設置不同的日誌記錄器"""
        # 系統主要日誌
        self.main_logger = self._create_logger("main", "system.log")
        
        # 錯誤專用日誌
        self.error_logger = self._create_logger("error", "errors.log")
        
        # API請求日誌
        self.api_logger = self._create_logger("api", "api.log")
        
        # 資料庫操作日誌
        self.db_logger = self._create_logger("database", "database.log")
    
    def _create_logger(self, name: str, filename: str) -> logging.Logger:
        """創建日誌記錄器"""
        logger = logging.getLogger(f"ck_missive.{name}")
        logger.setLevel(logging.DEBUG)
        
        # 避免重複添加handler
        if not logger.handlers:
            # 文件處理器
            file_handler = logging.FileHandler(
                self.log_dir / filename, 
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)
            
            # 控制台處理器（僅錯誤級別）
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.ERROR)
            
            # 日誌格式
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            logger.addHandler(file_handler)
            logger.addHandler(console_handler)
        
        return logger
    
    def log(self, entry: LogEntry):
        """記錄日誌條目"""
        try:
            # 選擇適當的記錄器
            logger = self._get_logger_for_category(entry.category)
            
            # 構建日誌消息
            log_message = self._format_log_message(entry)
            
            # 記錄到適當級別
            if entry.level == LogLevel.DEBUG:
                logger.debug(log_message)
            elif entry.level == LogLevel.INFO:
                logger.info(log_message)
            elif entry.level == LogLevel.WARNING:
                logger.warning(log_message)
            elif entry.level == LogLevel.ERROR:
                logger.error(log_message)
            elif entry.level == LogLevel.CRITICAL:
                logger.critical(log_message)
            
            # 更新統計
            self._update_stats(entry)
            
        except Exception as e:
            # 日誌系統自身的錯誤處理
            print(f"LOGGING_ERROR: {e}")
    
    def _get_logger_for_category(self, category: ErrorCategory) -> logging.Logger:
        """根據錯誤類別選擇日誌記錄器"""
        if category == ErrorCategory.DATABASE:
            return self.db_logger
        elif category in [ErrorCategory.API, ErrorCategory.AUTH]:
            return self.api_logger
        elif category in [ErrorCategory.SYSTEM]:
            return self.error_logger
        else:
            return self.main_logger
    
    def _format_log_message(self, entry: LogEntry) -> str:
        """格式化日誌消息"""
        parts = [entry.message]
        
        if entry.request_id:
            parts.append(f"[ReqID:{entry.request_id}]")
        
        if entry.user_id:
            parts.append(f"[UserID:{entry.user_id}]")
        
        if entry.details:
            # 避免Unicode問題，僅包含關鍵信息
            safe_details = self._make_safe_details(entry.details)
            if safe_details:
                parts.append(f"Details: {safe_details}")
        
        return " ".join(parts)
    
    def _make_safe_details(self, details: Dict[str, Any]) -> str:
        """創建安全的詳細信息字符串（支援中文字符）"""
        try:
            safe_details = {}
            for key, value in details.items():
                if isinstance(value, str):
                    # 保留中文字符，只處理控制字符和特殊字符
                    try:
                        # 嘗試使用原始字符串
                        safe_value = value.replace('\r', '').replace('\n', ' ').replace('\t', ' ')
                        if safe_value.strip():
                            safe_details[key] = safe_value
                    except UnicodeError:
                        # 如果出現編碼錯誤，則使用 UTF-8 編碼處理
                        try:
                            safe_value = value.encode('utf-8', errors='ignore').decode('utf-8')
                            safe_details[key] = safe_value
                        except:
                            safe_details[key] = "[encoding_issue]"
                else:
                    safe_details[key] = str(value)
            
            return json.dumps(safe_details, ensure_ascii=False, indent=None)
        except Exception:
            return "Details: [encoding_error]"
    
    def _update_stats(self, entry: LogEntry):
        """更新錯誤統計"""
        self.error_stats["total_errors"] += 1
        self.error_stats["by_category"][entry.category.value] += 1
        self.error_stats["by_level"][entry.level.value] += 1
        
        # 保留最近的錯誤記錄
        if entry.level in [LogLevel.ERROR, LogLevel.CRITICAL]:
            self.error_stats["recent_errors"].append({
                "timestamp": entry.timestamp.isoformat(),
                "category": entry.category.value,
                "message": entry.message
            })
            
            # 只保留最近100條錯誤
            if len(self.error_stats["recent_errors"]) > 100:
                self.error_stats["recent_errors"] = self.error_stats["recent_errors"][-100:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """獲取錯誤摘要"""
        return {
            "summary": self.error_stats,
            "log_files": {
                "main": str(self.log_dir / "system.log"),
                "errors": str(self.log_dir / "errors.log"),
                "api": str(self.log_dir / "api.log"),
                "database": str(self.log_dir / "database.log")
            },
            "generated_at": datetime.now().isoformat()
        }


class LoggingMiddleware(BaseHTTPMiddleware):
    """HTTP請求日誌中介軟體"""
    
    def __init__(self, app, log_manager: SystemLogManager):
        super().__init__(app)
        self.log_manager = log_manager
    
    async def dispatch(self, request: Request, call_next):
        """處理HTTP請求日誌"""
        start_time = time.time()
        request_id = f"{int(time.time() * 1000)}"  # 簡單的請求ID
        
        # 記錄請求開始
        entry = LogEntry(
            level=LogLevel.INFO,
            category=ErrorCategory.API,
            message=f"REQUEST_START {request.method} {request.url.path}",
            request_id=request_id,
            details={
                "method": request.method,
                "url": str(request.url),
                "headers": dict(request.headers)
            }
        )
        self.log_manager.log(entry)
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # 記錄請求完成
            entry = LogEntry(
                level=LogLevel.INFO,
                category=ErrorCategory.API,
                message=f"REQUEST_END {request.method} {request.url.path} - {response.status_code}",
                request_id=request_id,
                details={
                    "status_code": response.status_code,
                    "process_time": round(process_time, 4)
                }
            )
            self.log_manager.log(entry)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # 記錄請求錯誤
            entry = LogEntry(
                level=LogLevel.ERROR,
                category=ErrorCategory.API,
                message=f"REQUEST_ERROR {request.method} {request.url.path}",
                request_id=request_id,
                details={
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": round(process_time, 4)
                }
            )
            self.log_manager.log(entry)
            
            raise


# 全局日誌管理器實例
log_manager = SystemLogManager()


# 便捷函數
def log_error(message: str, category: ErrorCategory = ErrorCategory.SYSTEM, 
              details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
    """記錄錯誤日誌"""
    entry = LogEntry(LogLevel.ERROR, message, category, details, request_id)
    log_manager.log(entry)


def log_warning(message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
                details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
    """記錄警告日誌"""
    entry = LogEntry(LogLevel.WARNING, message, category, details, request_id)
    log_manager.log(entry)


def log_info(message: str, category: ErrorCategory = ErrorCategory.SYSTEM,
             details: Optional[Dict[str, Any]] = None, request_id: Optional[str] = None):
    """記錄信息日誌"""
    entry = LogEntry(LogLevel.INFO, message, category, details, request_id)
    log_manager.log(entry)


def log_unicode_error(original_message: str, error: Exception, context: str = ""):
    """專門處理Unicode編碼錯誤"""
    safe_message = original_message.encode('ascii', errors='ignore').decode('ascii')
    entry = LogEntry(
        level=LogLevel.ERROR,
        category=ErrorCategory.UNICODE,
        message=f"UNICODE_ERROR in {context}: {safe_message}",
        details={
            "original_error": str(error),
            "context": context,
            "error_type": type(error).__name__
        }
    )
    log_manager.log(entry)