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


def build_progress_report_flex(summary: dict) -> dict:
    """派工進度彙整 Flex Message（對標 OpenClaw 進度彙整格式）

    Args:
        summary: DispatchProgressSynthesizer.to_dict() 的回傳值
    """
    completed = summary.get('completed', [])
    in_progress = summary.get('in_progress', [])
    overdue = summary.get('overdue', [])
    alerts = summary.get('key_alerts', [])

    body_contents = []

    # 統計摘要
    body_contents.append({
        "type": "box", "layout": "horizontal", "spacing": "md",
        "contents": [
            {"type": "text", "text": f"✅ {len(completed)}", "size": "sm", "color": "#27AE60", "align": "center"},
            {"type": "text", "text": f"🔄 {len(in_progress)}", "size": "sm", "color": "#F39C12", "align": "center"},
            {"type": "text", "text": f"🔴 {len(overdue)}", "size": "sm", "color": "#E74C3C", "align": "center"},
        ],
    })
    body_contents.append({"type": "separator", "margin": "md"})

    # 逾期項目（最重要，最多顯示 5 筆）
    if overdue:
        body_contents.append({
            "type": "text", "text": "逾期派工單", "weight": "bold",
            "size": "sm", "color": "#E74C3C", "margin": "md",
        })
        for item in overdue[:5]:
            no = item.get('dispatch_no', '').replace('115年_', '')
            handler = item.get('case_handler', '未指派')
            days = item.get('overdue_days', 0)
            body_contents.append({
                "type": "text", "size": "xs", "wrap": True,
                "text": f"⚠️ {no} ({handler}) 逾期{days}天",
            })

    # 關鍵提醒
    if alerts:
        body_contents.append({"type": "separator", "margin": "md"})
        for alert in alerts[:3]:
            body_contents.append({
                "type": "text", "size": "xs", "wrap": True,
                "color": "#E67E22", "text": f"・{alert}",
            })

    return {
        "type": "bubble",
        "size": "mega",
        "header": {
            "type": "box", "layout": "vertical",
            "contents": [{"type": "text", "text": "📊 派工進度彙整", "weight": "bold", "size": "lg", "color": "#FFFFFF"}],
            "backgroundColor": "#1890FF",
            "paddingAll": "14px",
        },
        "body": {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": body_contents,
            "paddingAll": "14px",
        },
        "footer": {
            "type": "box", "layout": "vertical",
            "contents": [
                {
                    "type": "button", "style": "primary", "color": "#1890FF", "height": "sm",
                    "action": {"type": "message", "label": "查看完整報告", "text": "派工進度彙整"},
                },
            ],
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
