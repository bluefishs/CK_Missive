"""
桃園查估派工 - 常數定義
"""
from typing import Literal


# 關聯類型：機關來函 / 乾坤發文
LinkTypeEnum = Literal['agency_incoming', 'company_outgoing']


# 作業類別常數
WORK_TYPES = [
    "#0.專案行政作業",
    "00.專案會議",
    "01.地上物查估作業",
    "02.土地協議市價查估作業",
    "03.土地徵收市價查估作業",
    "04.相關計畫書製作",
    "05.測量作業",
    "06.樁位測釘作業",
    "07.辦理教育訓練",
    "08.作業提繳事項",
]
