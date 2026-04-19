# -*- coding: utf-8 -*-
"""Morning Report Narrative — 把結構化晨報升級為「副手備忘錄」風格 narrative。

2026-04-19 新建。解決「AI 晨報像表格，沒有 AI 的感覺」問題。

設計原則：
- **副手口吻**：不是報表機器人，是懂業務的副手
- **重點先講**：跳過「今日有 X 筆…」的統計開場
- **跨事件聯繫**：同機關、同承辦、相似模式要點出來
- **給判斷**：「這個很急」「那個先不用理」
- **給建議**：結尾指出 1-2 個該先做的事
- **失敗安全**：LLM 失敗 → 回傳 None，caller 自動回退原結構化格式

使用方式：
    from app.services.ai.domain.morning_report_narrative import narrate_report
    narrative = await narrate_report(structured_data, fallback_text)
    # narrative 為 None 代表失敗，caller 用 fallback_text

env 控制：
    MORNING_REPORT_NARRATIVE_ENABLED=true  # 預設 true
    MORNING_REPORT_NARRATIVE_TIMEOUT=20    # 秒
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

TZ_TAIPEI = ZoneInfo("Asia/Taipei")

# ── 系統 prompt — 定義副手人格 ──
_SYSTEM_PROMPT = """你是乾坤測繪的 AI 助理「阿榮的副手」。每天早上你會寫一份簡短的 morning memo 給老闆（阿榮）。

**寫作風格（必須遵守）**：
- 繁體中文
- 200-350 字（以 Telegram 單訊息為度）
- 開頭直呼「阿榮，早」或「早，阿榮」
- 口吻像熟練的資深副手：專業、簡潔、有溫度、不囉嗦
- **重點在前**：跳過「今日有 X 件 Y 件」的報表式開場
- **跨事件聯繫**：發現同機關、同承辦、相似模式主動點出
- **給判斷、給建議**：結尾留 1-2 個你認為該先處理的事
- 用自然段落，不要純列點；**少用**表格、標題、emoji（最多 1-2 個關鍵 emoji）

**禁止**：
- 純數字堆疊（如「派工 3 筆、會議 2 筆、現勘 1 筆」）
- 空泛結論（如「請留意相關事項」）
- 官話客套（如「敬請指示」「順頌時祺」）
- 發明資料中沒有的事實；若資料為空就如實說「今天沒特別急的事」

**範例**（僅供風格參考，勿抄襲）**：
> 阿榮，早。
> 今天 114-055 應該交件但承辦老蕭上週請假三天，可能卡住；方便的話可以 call 他確認進度。
> 桃園市政府那三份新公文剛好都是預算變更，模式跟去年 06 月的 5 筆一樣，建議走同批流程處理就好。
> 另外 ERP 有 2 筆費用還沒審（都是 5 萬以內小額），趁上午空檔就可以批掉。
> 先處理派工卡關那件，其他都不急。
"""


_USER_PROMPT_TEMPLATE = """今天是 {date_str}。以下是從系統自動彙整的原始資料（結構化清單）：

---
{structured_text}
---

請依據上述資料，寫一段 memo 給阿榮。記得：
1. 重點在前、有判斷
2. 跨事件關聯（機關、承辦、模式）
3. 結尾 1-2 個建議行動
4. 200-350 字，自然段落"""


async def narrate_report(
    structured_data: Dict[str, Any],
    structured_text: str,
    *,
    channel: str = "telegram",
) -> Optional[str]:
    """把結構化晨報轉為 narrative 備忘錄。

    Args:
        structured_data: morning_report_service.generate_report() 的 sections dict
        structured_text: formatter 已生成的格式化文字（作為 LLM input）
        channel: 目標頻道（影響字數長度 hint，telegram 較短、email 較長）

    Returns:
        narrative 文字；失敗或 env 關閉時回 None（caller 用原文字）
    """
    if os.getenv("MORNING_REPORT_NARRATIVE_ENABLED", "true").lower() not in ("1", "true", "yes"):
        return None

    # 資料太空就不 narrate（沒什麼可寫的）
    if not structured_text or len(structured_text.strip()) < 30:
        logger.info("Morning narrative skipped: source text too short")
        return None

    # 45s 為實測穩定值（Groq 429 時 fallback NVIDIA 需 30-40s）
    timeout_s = int(os.getenv("MORNING_REPORT_NARRATIVE_TIMEOUT", "45"))
    date_str = datetime.now(TZ_TAIPEI).strftime("%Y-%m-%d %A")

    user_prompt = _USER_PROMPT_TEMPLATE.format(
        date_str=date_str,
        structured_text=structured_text[:4000],  # 保護 context window
    )

    try:
        from app.core.ai_connector import get_ai_connector
        ai = get_ai_connector()

        result = await asyncio.wait_for(
            ai.chat_completion(
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,  # 稍有創意但不失準
                max_tokens=700,
                task_type="summary",
            ),
            timeout=timeout_s,
        )

        if not result or len(result.strip()) < 50:
            logger.warning("Morning narrative returned empty/too short, fallback")
            return None

        # 最小後處理：剪尾、去多餘空行
        narrative = result.strip()
        # 移除可能的 </think> 殘餘（已有 _strip_think_tags 保護但雙重防）
        if "<think>" in narrative or "<start_of_thinking>" in narrative:
            logger.warning("Morning narrative contains thinking tags; using fallback")
            return None

        logger.info(
            "Morning narrative generated: %d chars (from %d source chars)",
            len(narrative), len(structured_text),
        )
        return narrative

    except asyncio.TimeoutError:
        logger.warning("Morning narrative timed out after %ds — using fallback", timeout_s)
        return None
    except Exception as e:
        logger.warning("Morning narrative failed (%s) — using fallback", e)
        return None


def compose_final_report(
    narrative: Optional[str],
    structured_text: str,
    *,
    include_appendix: bool = True,
) -> str:
    """組合最終推送內容。

    Args:
        narrative: LLM 產出的 narrative（可能為 None）
        structured_text: 原始結構化格式
        include_appendix: narrative 成功時是否附加結構化作為 appendix

    Returns:
        最終推送字串
    """
    if not narrative:
        # narrative 失敗：回退原格式
        return structured_text

    if not include_appendix:
        return narrative

    # narrative + structured as appendix（使用者仍可查表格細節）
    return f"{narrative}\n\n───── 詳細清單 ─────\n{structured_text}"
