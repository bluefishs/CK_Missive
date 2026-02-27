"""
Agent 閒聊模組 — 非文件查詢走輕量 LLM 對話

偵測閒聊意圖，跳過工具規劃 + RAG 向量檢索，
僅使用 1 次 LLM 呼叫產生自然對話回應。

Extracted from agent_orchestrator.py v1.8.0
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)

# ============================================================================
# 閒聊偵測 — 非文件查詢走輕量 LLM 對話，跳過工具規劃 + RAG 向量檢索
# ============================================================================

# 高信心閒聊模式：精確匹配的問候詞 / 短語
_CHITCHAT_EXACT: set[str] = {
    "早安", "午安", "晚安", "你好", "您好", "嗨", "哈囉",
    "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
    "早", "安安", "哈嘍", "嗨嗨", "謝謝", "感謝", "掰掰", "再見",
    "bye", "thanks", "thank you",
}

# 閒聊前綴模式：以這些開頭的短句視為閒聊
_CHITCHAT_PREFIXES = (
    "你是誰", "你叫什麼", "你會什麼", "你能做什麼", "可以幫我什麼",
    "介紹一下", "自我介紹", "怎麼使用", "如何使用", "使用說明",
    "今天天氣", "講個笑話", "心情不好",
)

CHAT_SYSTEM_PROMPT = """你是「乾坤助理」，乾坤測繪公文管理系統的 AI 助理。

你只能做這些事：搜尋公文、查詢派工單、探索知識圖譜、統計公文資料。
除此之外的事情你都做不到，包括但不限於：影片、音樂、電影、訂餐、天氣、新聞、翻譯、寫程式。

規則：
1. 只用繁體中文，直接回覆，不要輸出推理過程
2. 回覆最多 2-3 句話，簡潔親切
3. 如果使用者問你能力範圍以外的事，坦白說「這個我幫不上忙」，然後友善地提醒你能做什麼
4. 問候和閒聊正常回應，但適時引導回公文相關功能"""

# 問題類型 → 智慧回覆（Ollama 回退時使用）
_SMART_FALLBACKS: List[tuple] = [
    # (關鍵字集合, 回覆)
    ({"早安", "早", "good morning"}, "早安！新的一天開始了，有什麼公文需要我幫忙查詢的嗎？"),
    ({"午安", "good afternoon"}, "午安！下午工作加油，需要我幫忙找什麼資料嗎？"),
    ({"晚安", "good evening"}, "晚安！辛苦了，還有什麼公文需要我幫忙處理的嗎？"),
    ({"你好", "您好", "嗨", "哈囉", "嗨嗨", "安安", "哈嘍", "hi", "hello", "hey"},
     "你好！我是乾坤助理，可以幫你搜尋公文、查詢派工單、探索相關單位之間的關係，問我就對了！"),
    ({"你是誰", "你叫什麼", "自我介紹", "介紹一下"},
     "我是乾坤助理！專門幫你在公文系統裡找資料，不管是查公文、看派工紀錄、還是分析單位關係都難不倒我。"),
    ({"你能做什麼", "可以幫我什麼", "你會什麼", "使用說明", "怎麼使用", "如何使用"},
     "你可以直接用自然語言問我，像是「工務局上個月的函」或「派工單號 014」，我會幫你從系統裡撈出來！"),
    ({"謝謝", "感謝", "thanks", "thank you"},
     "不客氣！隨時需要查詢公文或派工單，跟我說一聲就好。"),
    ({"掰掰", "再見", "bye"},
     "掰掰！下次需要找公文記得來找我。"),
    ({"笑話", "開心", "心情"},
     "公文雖然嚴肅，但我會盡量讓查詢過程輕鬆一點！有什麼需要幫忙的嗎？"),
    ({"天氣"},
     "天氣我不太擅長，但公文查詢可是我的強項！需要幫忙嗎？"),
]


# 公文業務關鍵字 — 只要命中任一，就走 Agent 工具流程
_BUSINESS_KEYWORDS = (
    # 公文相關
    "公文", "函", "令", "公告", "書函", "簽", "通知", "開會",
    "收文", "發文", "字號", "文號", "主旨", "附件",
    # 派工相關
    "派工", "工單", "測量", "測釘", "放樣", "測繪", "作業",
    # 機關 / 單位
    "市政府", "工務局", "地政", "水利", "交通", "都發",
    "鄉公所", "區公所", "縣政府", "國土", "營建署",
    "乾坤", "上升空間",
    # 專案 / 工程
    "工程", "專案", "標案", "契約", "計畫", "委託",
    # 查詢動作
    "查詢", "搜尋", "找", "有哪些", "列出", "統計", "多少",
    # 知識圖譜
    "實體", "關係", "圖譜", "相似",
    # 日期篩選
    "上個月", "這個月", "今年", "去年", "本週", "最近",
    "月", "年",
)


def is_chitchat(text: str) -> bool:
    """
    判斷是否為閒聊/非文件查詢

    策略：反向偵測 — 檢查是否包含公文業務關鍵字
    - 有業務關鍵字 → 不是閒聊 → 走 Agent 工具流程
    - 沒有業務關鍵字 → 視為閒聊 → 走輕量 LLM 對話
    """
    normalized = text.strip().lower()

    # 1. 精確匹配已知問候（最快路徑）
    if normalized in _CHITCHAT_EXACT:
        return True

    # 2. 前綴匹配（「你是誰」「怎麼使用」等）
    if len(normalized) <= 30 and any(normalized.startswith(p) for p in _CHITCHAT_PREFIXES):
        return True

    # 3. 反向偵測：含任何業務關鍵字 → 不是閒聊
    if any(kw in normalized for kw in _BUSINESS_KEYWORDS):
        return False

    # 4. 短句且無業務關鍵字 → 閒聊
    #    （超過 40 字的長句可能是複雜查詢描述，保守走 Agent）
    if len(normalized) <= 40:
        return True

    return False


def get_smart_fallback(question: str) -> str:
    """根據問題類型取得合適的預設回覆"""
    q = question.strip().lower()
    for keywords, response in _SMART_FALLBACKS:
        if q in keywords or any(kw in q for kw in keywords):
            return response
    return "你好！有什麼公文相關的事情需要幫忙嗎？"


def clean_chitchat_response(raw: str, question: str) -> str:
    """
    過濾 qwen3:4b 洩漏的思考鏈，提取真正的回覆內容

    qwen3 小模型即使設定 think=false，仍會在 content 中混入推理分析。
    策略：偵測思考洩漏 → 嘗試提取有效回覆 → 回退到智慧預設。
    """
    if not raw:
        return get_smart_fallback(question)

    # 移除 <think> 標記（標準格式）
    cleaned = re.sub(r"<think>.*?</think>\s*", "", raw, flags=re.DOTALL).strip()

    # 偵測思考洩漏特徵
    _THINKING_MARKERS = (
        "首先", "我需要", "根据", "根據", "用户", "用戶",
        "回覆結構", "回复结构", "腦力", "脑力",
        "可能的回覆", "核心能力", "對話風格", "作為", "作为",
        "/no_think", "規則說", "規則", "分析",
    )

    has_thinking = any(m in cleaned for m in _THINKING_MARKERS)
    if not has_thinking:
        # 額外檢查：是否包含大量簡體中文（qwen3 傾向用簡體推理）
        simplified_chars = sum(1 for c in cleaned if '\u4e00' <= c <= '\u9fff')
        if simplified_chars > 0:
            # 簡體比例檢測（粗略：若含「这」「们」「还」等常見簡體字）
            _SIMPLIFIED = set("这们还个么没对说从关让给应该怎样为什呢吗了吧")
            simplified_count = sum(1 for c in cleaned if c in _SIMPLIFIED)
            if simplified_count > 3:
                has_thinking = True

        if not has_thinking:
            return cleaned

    # ── 思考洩漏 → 嘗試提取有效回覆 ──

    # 策略 1: 找引號包裹的對話回覆（「...」或 "..."）
    quoted = re.findall(r'[「""]([^」""]{5,100})[」""]', cleaned)
    if quoted:
        best = max(quoted, key=len)
        # 確認提取的內容不是推理（不含 meta 詞）
        if not any(m in best for m in ("用戶", "用户", "我需要", "首先")):
            return best

    # 策略 2: 取最後一個以常見回覆開頭的句子
    _REPLY_STARTERS = (
        "你好", "早安", "午安", "晚安", "嗨", "哈囉",
        "不客氣", "沒問題", "好的", "哈哈", "掰掰", "再見",
    )
    lines = [ln.strip() for ln in cleaned.split("\n") if ln.strip()]
    for line in reversed(lines):
        if any(line.startswith(s) for s in _REPLY_STARTERS):
            return line[:150]

    # 策略 3: 智慧型預設回覆
    return get_smart_fallback(question)
