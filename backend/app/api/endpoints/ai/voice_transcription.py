"""
語音轉文字 API 端點

接收前端 MediaRecorder 錄製的音訊（webm/wav），
透過 Groq Whisper API 轉為文字。

Version: 1.0.0
Created: 2026-03-20
"""

from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/voice/transcribe")
async def transcribe_voice(
    audio: UploadFile = File(...),
    language: str = Form("zh"),
):
    """語音轉文字

    接受 webm/wav/m4a/mp3 格式，回傳辨識文字。
    """
    from app.services.ai.voice_transcriber import get_voice_transcriber

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
