#!/usr/bin/env python3
"""
Discord Slash Commands 註冊腳本

向 Discord API 註冊 CK Missive 的 Slash Commands。
僅需執行一次（或 commands 定義變更時）。

Usage:
    python scripts/init/register-discord-commands.py
    python scripts/init/register-discord-commands.py --guild 123456789  # 測試用（僅特定伺服器）
    python scripts/init/register-discord-commands.py --delete           # 刪除所有命令

Requires:
    DISCORD_BOT_TOKEN in .env
    DISCORD_APPLICATION_ID in .env

Version: 1.0.0
Created: 2026-03-25
"""

import argparse
import os
import sys
import httpx

# 載入 .env
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
env_path = os.path.join(project_root, ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
APP_ID = os.getenv("DISCORD_APPLICATION_ID", "")
API_BASE = "https://discord.com/api/v10"

COMMANDS = [
    {
        "name": "ck-ask",
        "description": "向乾坤智能體提問 (公文/案件/派工/財務)",
        "options": [
            {
                "name": "question",
                "description": "你的問題",
                "type": 3,  # STRING
                "required": True,
            }
        ],
    },
    {
        "name": "ck-doc",
        "description": "查詢公文 (依文號)",
        "options": [
            {
                "name": "doc_number",
                "description": "公文文號",
                "type": 3,
                "required": True,
            }
        ],
    },
    {
        "name": "ck-case",
        "description": "查詢案件 (依案號)",
        "options": [
            {
                "name": "case_code",
                "description": "案件代碼 (例: CK115_PM_01_001)",
                "type": 3,
                "required": True,
            }
        ],
    },
]


def register_commands(guild_id: str = ""):
    """註冊 Slash Commands"""
    if not BOT_TOKEN or not APP_ID:
        print("ERROR: DISCORD_BOT_TOKEN 和 DISCORD_APPLICATION_ID 必須設定在 .env")
        sys.exit(1)

    if guild_id:
        url = f"{API_BASE}/applications/{APP_ID}/guilds/{guild_id}/commands"
        scope = f"guild {guild_id}"
    else:
        url = f"{API_BASE}/applications/{APP_ID}/commands"
        scope = "global"

    headers = {"Authorization": f"Bot {BOT_TOKEN}"}

    print(f"註冊 {len(COMMANDS)} 個 Slash Commands ({scope})...")
    print()

    with httpx.Client() as client:
        for cmd in COMMANDS:
            resp = client.post(url, json=cmd, headers=headers, timeout=10)
            if resp.status_code in (200, 201):
                data = resp.json()
                print(f"  ✓ /{cmd['name']} — ID: {data.get('id')}")
            else:
                print(f"  ✗ /{cmd['name']} — {resp.status_code}: {resp.text}")

    print()
    print("完成！命令可能需要最多 1 小時才能在所有伺服器生效。")
    if guild_id:
        print("(Guild-scoped 命令會立即生效)")


def delete_commands(guild_id: str = ""):
    """刪除所有 Slash Commands"""
    if guild_id:
        url = f"{API_BASE}/applications/{APP_ID}/guilds/{guild_id}/commands"
    else:
        url = f"{API_BASE}/applications/{APP_ID}/commands"

    headers = {"Authorization": f"Bot {BOT_TOKEN}"}

    with httpx.Client() as client:
        resp = client.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"ERROR: {resp.status_code}: {resp.text}")
            return

        commands = resp.json()
        print(f"刪除 {len(commands)} 個命令...")
        for cmd in commands:
            del_resp = client.delete(f"{url}/{cmd['id']}", headers=headers, timeout=10)
            status = "✓" if del_resp.status_code == 204 else f"✗ {del_resp.status_code}"
            print(f"  {status} /{cmd['name']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Discord Slash Commands 管理")
    parser.add_argument("--guild", default="", help="僅註冊到指定 Guild (測試用)")
    parser.add_argument("--delete", action="store_true", help="刪除所有命令")
    args = parser.parse_args()

    if args.delete:
        delete_commands(args.guild)
    else:
        register_commands(args.guild)
