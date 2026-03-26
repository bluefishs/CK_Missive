#!/usr/bin/env python3
"""
LINE Rich Menu 建立腳本

建立 CK Missive 的 LINE Rich Menu（底部選單）。
僅需執行一次（或需要更新選單時）。

Usage:
    python scripts/init/setup-line-rich-menu.py
    python scripts/init/setup-line-rich-menu.py --delete  # 刪除現有 Rich Menu

Requires:
    LINE_CHANNEL_ACCESS_TOKEN in .env

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

TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
API = "https://api.line.me/v2/bot"

RICH_MENU = {
    "size": {"width": 2500, "height": 843},
    "selected": True,
    "name": "CK Missive 快捷選單",
    "chatBarText": "開啟選單",
    "areas": [
        {
            "bounds": {"x": 0, "y": 0, "width": 833, "height": 843},
            "action": {"type": "message", "text": "查詢最近的公文"},
        },
        {
            "bounds": {"x": 833, "y": 0, "width": 834, "height": 843},
            "action": {"type": "message", "text": "查詢案件進度"},
        },
        {
            "bounds": {"x": 1667, "y": 0, "width": 833, "height": 843},
            "action": {"type": "message", "text": "系統健康狀態"},
        },
    ],
}


def create_rich_menu():
    if not TOKEN:
        print("ERROR: LINE_CHANNEL_ACCESS_TOKEN 必須設定在 .env")
        sys.exit(1)

    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }

    with httpx.Client() as client:
        # 1. 建立 Rich Menu
        resp = client.post(f"{API}/richmenu", json=RICH_MENU, headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"ERROR: 建立 Rich Menu 失敗: {resp.status_code} {resp.text}")
            sys.exit(1)

        menu_id = resp.json().get("richMenuId")
        print(f"Rich Menu 建立成功: {menu_id}")

        # 2. 設為預設 Rich Menu
        resp2 = client.post(
            f"{API}/user/all/richmenu/{menu_id}",
            headers={"Authorization": f"Bearer {TOKEN}"},
            timeout=10,
        )
        if resp2.status_code == 200:
            print("已設為預設 Rich Menu")
        else:
            print(f"WARNING: 設為預設失敗: {resp2.status_code}")

        print()
        print("Rich Menu 區域:")
        print("  [查詢公文] [查詢案件] [系統狀態]")
        print()
        print("提示: 需上傳背景圖片 (2500x843px):")
        print(f"  curl -X POST {API}/richmenu/{menu_id}/content \\")
        print(f'    -H "Authorization: Bearer $TOKEN" \\')
        print(f'    -H "Content-Type: image/png" \\')
        print("    --data-binary @rich-menu-bg.png")


def delete_rich_menu():
    headers = {"Authorization": f"Bearer {TOKEN}"}
    with httpx.Client() as client:
        resp = client.get(f"{API}/richmenu/list", headers=headers, timeout=10)
        if resp.status_code != 200:
            print(f"ERROR: {resp.status_code}")
            return
        menus = resp.json().get("richmenus", [])
        print(f"刪除 {len(menus)} 個 Rich Menu...")
        for menu in menus:
            client.delete(f"{API}/richmenu/{menu['richMenuId']}", headers=headers, timeout=10)
            print(f"  ✓ {menu['richMenuId']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LINE Rich Menu 管理")
    parser.add_argument("--delete", action="store_true", help="刪除所有 Rich Menu")
    args = parser.parse_args()

    if args.delete:
        delete_rich_menu()
    else:
        create_rich_menu()
