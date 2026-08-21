"""
語音轉文字 API 端點

接收前端 MediaRecorder 錄製的音訊（webm/wav），
透過 Groq Whisper API 轉為文字。

Version: 1.0.0
Created: 2026-03-20
"""

from fastapi import Depends
from app.core.dependencies import require_auth
from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

# 2026-08-21：router 層要求登入。
#
# 本檔端點**全部會消耗 GPU／LLM 額度**（摘要／分類／關鍵字／自然語言搜尋／
# 意圖解析／機關比對／語音轉錄／圖表與視覺分析）。實測公網未登入、
# 只要先從公開的 /api/secure-site-management/csrf-token 取一枚 token，
# 就能打到 200 —— `ai/config` 甚至吐出 provider 清單與
# `host.docker.internal:11434` 內網位址。
#
# ⚠️ **CSRF 不是認證**：那支 token 端點是刻意公開的（L68 自癒需要），
# 任何人都取得到。第一次實測「全部 403」是 CSRF 擋掉沒帶 token 的請求而已，
# 帶了就過 —— 那是假的安全感。
#
# owner 2026-08-21：「規範不得要新增額外費用之設計」——
# 對外開放的推論端點就是**別人用、我們付費**。
router = APIRouter(dependencies=[Depends(require_auth())])


@router.post("/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    language: str = Form("zh"),
):
    """語音轉文字

    接受 webm/wav/m4a/mp3 格式，回傳辨識文字。
    """
    from app.services.ai.misc.voice_transcriber import get_voice_transcriber

    # 驗證格式
    filename = audio.filename or "audio.webm"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"

    transcriber = get_voice_transcriber()

    audio_data = await audio.read()
    if not audio_data:
        return JSONResponse(
            status_code=400,
            content={"error": "音訊資料為空"},
        )

    result = await transcriber.transcribe(
        audio_data=audio_data,
        audio_format=ext,
        language=language,
    )

    if result["source"] == "error":
        return JSONResponse(
            status_code=422,
            content={"error": result["text"]},
        )

    return {
        "text": result["text"],
        "language": result["language"],
        "duration_ms": result["duration_ms"],
        "source": result["source"],
    }
