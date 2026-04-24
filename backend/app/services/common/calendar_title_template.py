# -*- coding: utf-8 -*-
"""Calendar Event Title Template (ADR-0026 v5.8.1).

集中化日曆事件標題規則，讓公文事件、派工事件、手動事件走同一模板。

**標準格式**：
```
【{category}】{verb}派工單號{no3}({team_abbr})_{project_name}_{item}
```

**範例**：
```
【成果】提交派工單號020(全國)_中壢區南園二路延伸中豐北路道路新闢工程_徵收市價報告
【會議通知】召開派工單號003(全國)_中壢區龍岡路4-1-10M計畫道路路口瓶頸打通工程_協議價購市價審查會議
【會勘通知】辦理派工單號021(乾坤)_中壢區大華路(內定一街至大華路350巷)道路拓寬工程_現勘會勘
【派工通知】接收派工單號006(冠誠)_桃園區鹽庫西街至春日路_土地協議市價查估作業
```

使用：
```python
from app.services.common.calendar_title_template import build_calendar_event_title
title = build_calendar_event_title(
    category='work_result',
    dispatch=dispatch,
    user_description=None,  # 用戶未填時自動推導
    item_override=None,     # 具體項目可覆寫
)
```
"""
from __future__ import annotations

from typing import Optional


# 作業類別 → 中文標籤（表格/過濾等非標題場景用）
CATEGORY_LABELS = {
    "admin_notice": "行政",
    "dispatch_notice": "派工通知",
    "work_result": "成果",
    "meeting_notice": "會議通知",
    "meeting_record": "會議紀錄",
    "survey_notice": "會勘通知",
    "survey_record": "會勘紀錄",
    "other": "其他",
}

# 作業類別 → 動詞
CATEGORY_VERBS = {
    "admin_notice": "發布",
    "dispatch_notice": "接收",
    "work_result": "提交",
    "meeting_notice": "召開",
    "meeting_record": "提交",
    "survey_notice": "辦理",
    "survey_record": "提交",
    "other": "辦理",
}

# 「動詞+類別」組合標籤（title 開頭用）
# 例：【提交成果】、【召開會議】...
CATEGORY_ACTION_LABELS = {
    "admin_notice": "發布行政",
    "dispatch_notice": "接收派工",
    "work_result": "提交成果",
    "meeting_notice": "召開會議",
    "meeting_record": "提交會議紀錄",
    "survey_notice": "辦理會勘",
    "survey_record": "提交會勘紀錄",
    "other": "辦理事項",
}

# 作業類別 × 查估類別代碼 → 預設項目名稱
# 類別代碼來自 sub_case_name 第二段（例：02.土地協議市價查估作業 → "02"）
WORK_CODE_ITEM_MAP = {
    # 成果 (work_result)
    ("work_result", "01"): "地上物查估成果",
    ("work_result", "02"): "協議價購報告",
    ("work_result", "03"): "徵收市價報告",
    ("work_result", "04"): "提存款案成果",
    ("work_result", "05"): "測量成果",
    ("work_result", "06"): "地上物補查報告",
    ("work_result", "07"): "教育訓練紀錄",
    # 會議通知
    ("meeting_notice", "02"): "協議價購市價審查會議",
    ("meeting_notice", "03"): "徵收市價審查會議",
    # 會議紀錄
    ("meeting_record", "02"): "協議價購市價審查會議紀錄",
    ("meeting_record", "03"): "徵收市價審查會議紀錄",
    # 會勘
    ("survey_notice", "01"): "地上物現勘",
    ("survey_notice", "02"): "土地協議現勘",
    ("survey_notice", "03"): "土地徵收現勘",
    ("survey_notice", "05"): "測量現勘",
    ("survey_record", "01"): "地上物現勘紀錄",
    ("survey_record", "02"): "土地協議現勘紀錄",
    ("survey_record", "03"): "土地徵收現勘紀錄",
    ("survey_record", "05"): "測量現勘紀錄",
    # 派工通知（類別本身就是名稱）
    ("dispatch_notice", "01"): "地上物查估作業",
    ("dispatch_notice", "02"): "土地協議市價查估作業",
    ("dispatch_notice", "03"): "土地徵收市價查估作業",
    ("dispatch_notice", "04"): "提存款案件",
    ("dispatch_notice", "05"): "測量作業",
    ("dispatch_notice", "06"): "地上物補查作業",
    ("dispatch_notice", "07"): "教育訓練",
}

# 查估團隊縮寫 — 依實際 DB 樣本提供映射
SURVEY_UNIT_ABBR = {
    "乾坤不動產估價團隊": "乾坤",
    "全國不動產估價師事務所": "全國",
    "冠誠不動產估價師事務所": "冠誠",
    "昇揚不動產估價師聯合事務所": "昇揚",
    "大有國際不動產估價師聯合事務所": "大有",
    "上升空間資訊股份有限公司": "上升",
    "竣吉不動產估價師事務所": "竣吉",
    "威名不動產估價師事務所": "威名",
    "勤典測量工程行": "勤典",
}


def abbreviate_survey_unit(survey_unit: Optional[str]) -> str:
    """查估單位名稱 → 縮寫（2-3 字）。

    優先查明確映射表，fallback 到前 2 字。
    """
    if not survey_unit:
        return ""
    s = survey_unit.strip()
    if s in SURVEY_UNIT_ABBR:
        return SURVEY_UNIT_ABBR[s]
    # Fallback：前 2 字
    return s[:2]


def extract_dispatch_no_3digit(dispatch_no: Optional[str]) -> str:
    """`115年_派工單號020` → `020`；若無則空字串。"""
    if not dispatch_no:
        return ""
    import re
    m = re.search(r"(\d{3})$", dispatch_no.strip())
    return m.group(1) if m else ""


def extract_project_name(sub_case_name: Optional[str], fallback: Optional[str] = None) -> str:
    """從 sub_case_name 抽出工程名稱（切 `_` 前段）。

    `桃園區鹽庫西街至春日路_02.土地協議市價查估作業` → `桃園區鹽庫西街至春日路`
    """
    if sub_case_name and "_" in sub_case_name:
        return sub_case_name.split("_", 1)[0].strip()
    if sub_case_name:
        return sub_case_name.strip()
    return (fallback or "").strip()


def extract_work_code(sub_case_name: Optional[str]) -> Optional[str]:
    """抽出查估類別代碼 `02`、`03`... 從 sub_case_name 第二段。

    `桃園區..._02.土地協議市價查估作業` → `02`
    多類別支援：`..._01.地上物查估作業、03.土地徵收市價查估作業` → `01`（取第一個）
    """
    if not sub_case_name or "_" not in sub_case_name:
        return None
    import re
    m = re.search(r"(\d{2})\.", sub_case_name.split("_", 1)[1])
    return m.group(1) if m else None


def derive_item(
    category: str,
    sub_case_name: Optional[str] = None,
    user_description: Optional[str] = None,   # 保留參數但**不**作為 item 來源
    override: Optional[str] = None,
) -> str:
    """推導「項目」（模板最後一段）。

    優先序：
    1. override（呼叫方明確指定，如 API 帶 item 參數）
    2. (category, work_code) 映射表（標準化項目名稱）
    3. category label（兜底）

    **注意**：user_description 不作為 item — 實際資料中 description 常是公文
    全文 copy，塞入 title 會造成過長混亂。description 保留在 event.description
    欄位顯示，title 要乾淨統一。
    """
    if override and override.strip():
        return override.strip()
    code = extract_work_code(sub_case_name)
    if code and (category, code) in WORK_CODE_ITEM_MAP:
        return WORK_CODE_ITEM_MAP[(category, code)]
    return CATEGORY_LABELS.get(category, "事項")


def build_calendar_event_title(
    *,
    category: str,
    dispatch=None,                          # TaoyuanDispatchOrder 物件 or None
    doc_subject: Optional[str] = None,     # 公文主旨（dispatch 無法提供時用）
    user_description: Optional[str] = None, # 用戶填的 description
    item_override: Optional[str] = None,   # 明確項目
) -> str:
    """組合標題：`【動詞+類別】派工單號{no3}({team})_{project_name}_{item}`

    範例：
      【提交成果】派工單號010(昇揚)_平鎮區..._協議價購報告
      【召開會議】派工單號003(全國)_中壢區..._協議價購市價審查會議
      【接收派工】派工單號008(全國)_大溪區..._土地徵收市價查估作業

    若無 dispatch → fallback 用 doc_subject + user_description 組合最小化標題。
    """
    action_label = CATEGORY_ACTION_LABELS.get(category, "辦理事項")

    # 若用戶 description 以 `[` 或 `【` 開頭視為完整標題，直接回（用戶自訂）
    if user_description and user_description.strip() and user_description.strip()[0] in ("[", "【"):
        return user_description.strip()

    if dispatch is None:
        # 無派工 — 用公文主旨 fallback
        if doc_subject and doc_subject.strip():
            return f"【{action_label}】{doc_subject.strip()}"
        if user_description and user_description.strip():
            return f"【{action_label}】{user_description.strip()}"
        return f"【{action_label}】"

    no3 = extract_dispatch_no_3digit(getattr(dispatch, "dispatch_no", None))
    team = abbreviate_survey_unit(getattr(dispatch, "survey_unit", None))
    project_name = extract_project_name(
        getattr(dispatch, "sub_case_name", None),
        fallback=getattr(dispatch, "project_name", None),
    )
    item = derive_item(
        category,
        sub_case_name=getattr(dispatch, "sub_case_name", None),
        user_description=user_description,
        override=item_override,
    )

    # 組合
    no_team = ""
    if no3:
        no_team = f"派工單號{no3}"
    if team:
        no_team = no_team + f"({team})" if no_team else f"({team})"

    # 【動詞+類別】派工單號020(全國)_工程名稱_項目
    prefix = f"【{action_label}】"
    suffix_parts = []
    if no_team:
        suffix_parts.append(no_team)
    if project_name:
        suffix_parts.append(project_name)
    if item:
        suffix_parts.append(item)

    if not suffix_parts:
        return prefix
    return prefix + suffix_parts[0] + ("_" + "_".join(suffix_parts[1:]) if len(suffix_parts) > 1 else "")
