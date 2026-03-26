"""
LINE Flex Message Builder — Flex Message 模板建構器

提供：
- 公文截止提醒 Flex 卡片
- Agent 回覆 Flex 卡片
- Quick Reply 按鈕列表

Version: 1.0.0
Created: 2026-03-26
Extracted from: line_bot_service.py
"""


def build_deadline_flex(doc_subject: str, deadline: str) -> dict:
    """公文截止提醒 Flex Message"""
    return {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical",
            "contents": [{"type": "text", "text": "\U0001f4cb 公文截止提醒", "weight": "bold", "size": "lg"}],
            "backgroundColor": "#FF6B6B",
            "paddingAll": "12px",
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "md",
            "contents": [
                {"type": "text", "text": doc_subject[:60], "weight": "bold", "wrap": True},
                {"type": "separator"},
                {
                    "type": "box", "layout": "horizontal",
                    "contents": [
                        {"type": "text", "text": "截止日", "color": "#888888", "size": "sm", "flex": 2},
                        {"type": "text", "text": deadline, "weight": "bold", "size": "sm", "flex": 3},
                    ],
                },
            ],
        },
        "footer": {
            "type": "box", "layout": "vertical",
            "contents": [
                {
                    "type": "button", "style": "primary", "color": "#1890FF",
                    "action": {"type": "message", "label": "查詢此公文", "text": f"查詢公文 {doc_subject[:20]}"},
                },
            ],
        },
    }


def build_agent_reply_flex(question: str, answer: str, tools_used: list = None) -> dict:
    """Agent 回覆 Flex Message"""
    body_contents = [
        {"type": "text", "text": answer[:800], "wrap": True, "size": "sm"},
    ]
    if tools_used:
        body_contents.append({"type": "separator"})
        body_contents.append({
            "type": "text", "text": f"\U0001f527 {', '.join(tools_used[:3])}",
            "size": "xs", "color": "#888888",
        })

    return {
        "type": "bubble",
        "header": {
            "type": "box", "layout": "vertical",
            "contents": [{"type": "text", "text": f"\U0001f50d {question[:40]}", "weight": "bold", "size": "md", "wrap": True}],
            "backgroundColor": "#E8F4FD",
            "paddingAll": "12px",
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": body_contents,
        },
    }


def build_quick_reply_items(suggestions: list) -> list:
    """建構 Quick Reply 按鈕列表"""
    items = []
    for text in suggestions[:13]:  # LINE 上限 13 個
        items.append({
            "type": "action",
            "action": {"type": "message", "label": text[:20], "text": text[:300]},
        })
    return items
