# -*- coding: utf-8 -*-
"""
CORS (Cross-Origin Resource Sharing) 設定

此模組集中管理 CORS 來源，確保應用程式各部分（主應用程式、異常處理器）使用一致的設定。
支援動態 IP 偵測和環境變數擴展。

版本: 1.1.0
更新: 2026-01-15
"""
import logging
import socket
from typing import List, Set
from app.core.config import settings

logger = logging.getLogger(__name__)

# --- 常用端口配置 ---
FRONTEND_PORTS = [3000, 3001, 3002, 3003, 3004, 3005]


def get_local_ips() -> Set[str]:
    """
    自動獲取本機所有網路介面的 IP 地址

    Returns:
        Set[str]: 本機 IP 地址集合
    """
    ips = {"127.0.0.1", "localhost"}

    try:
        # 方法1: 通過 hostname 獲取
        hostname = socket.gethostname()
        host_ips = socket.gethostbyname_ex(hostname)[2]
        ips.update(host_ips)

        # 方法2: 通過連接外部地址獲取本機 IP (不實際發送數據)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            ips.add(local_ip)
            s.close()
        except Exception:
            pass

    except Exception as e:
        logger.warning(f"獲取本機 IP 時發生錯誤: {e}")

    return ips


def generate_origins_for_ips(ips: Set[str], ports: List[int]) -> List[str]:
    """
    為指定的 IP 和端口組合生成 CORS 來源

    Args:
        ips: IP 地址集合
        ports: 端口列表

    Returns:
        List[str]: CORS 來源列表
    """
    origins = []
    for ip in ips:
        for port in ports:
            origins.append(f"http://{ip}:{port}")
    return origins


# --- CORS 允許來源 ---
# 基礎來源清單
cors_origins: List[str] = []

# 1. 動態獲取本機 IP 並生成來源
local_ips = get_local_ips()
cors_origins.extend(generate_origins_for_ips(local_ips, FRONTEND_PORTS))
logger.info(f"動態偵測到 {len(local_ips)} 個本機 IP: {local_ips}")

# 2. 靜態配置的區域網路 IP (確保向後兼容)
static_ips = {
    "192.168.50.35",
    "192.168.50.38",
    "192.168.50.210",
    "192.168.1.1",
    "192.168.0.1",
}
cors_origins.extend(generate_origins_for_ips(static_ips, FRONTEND_PORTS))

# 3. 從環境變數擴展 CORS 來源
if settings.CORS_ORIGINS:
    env_origins = [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
    if env_origins:
        cors_origins.extend(env_origins)
        logger.info(f"從環境變數加載了 {len(env_origins)} 個額外的 CORS 來源。")

# 4. 去除重複，確保清單唯一性
allowed_origins: List[str] = list(set(cors_origins))

# 5. 記錄最終配置
logger.info(f"最終的 CORS 允許來源數量: {len(allowed_origins)}")
logger.debug(f"CORS 允許的來源: {sorted(allowed_origins)}")


def is_origin_allowed(origin: str) -> bool:
    """
    檢查指定的 origin 是否在允許列表中

    Args:
        origin: 要檢查的來源

    Returns:
        bool: 是否允許
    """
    return origin in allowed_origins


def add_origin(origin: str) -> bool:
    """
    動態添加新的 CORS 來源 (運行時)

    Args:
        origin: 要添加的來源

    Returns:
        bool: 是否成功添加 (False 表示已存在)
    """
    global allowed_origins
    if origin not in allowed_origins:
        allowed_origins.append(origin)
        logger.info(f"動態添加 CORS 來源: {origin}")
        return True
    return False
