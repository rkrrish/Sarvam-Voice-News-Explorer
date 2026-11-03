import time
import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import (
    BASE_DIR,
    AUDIO_DIR,
    SARVAM_API_KEY,
    NEWSAPI_KEY
)
from app.services.stt_service import stt_service
from app.services.news_service import news_service
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.services.translation_service import translation_service
from app.services.ledger_service import ledger_service

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("sarvam-news-assistant")

app = FastAPI(
    title="Sarvam Voice News Assistant & Provenance Ledger",
    description="Voice-driven news exploration, multilingual answering, and audit tracking.",
    version="1.0.0"
)

# CORS configuration for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"

# Serve static assets if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

class TextQueryRequest(BaseModel):
    query: str
    language_code: Optional[str] = None
    speaker: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h2>Sarvam Voice News Assistant API is running.</h2><p>Visit /docs for API documentation.</p>")

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "sarvam_configured": bool(SARVAM_API_KEY),
        "newsapi_configured": bool(NEWSAPI_KEY),
        "timestamp": time.time()
    }

async def _execute_pipeline(
    query: str,
    input_type: str,
    detected_lang: str,
    confidence: float,
    audio_filename: Optional[str] = None,
    speaker: Optional[str] = None,
    transaction_id: Optional[str] = None,
    start_time: Optional[float] = None
):
    start_time = start_time or time.time()
    transaction_id = transaction_id or str(uuid.uuid4())

    is_non_english = detected_lang not in ("en-IN", "en")

    # 1. Send voice input prompt to Sarvam LLM to analyze intent & create keywords/sentences for NewsAPI
    llm_analysis = llm_service.analyze_query_and_extract_search(
        prompt=query,
        input_language=detected_lang
    )
    search_sentence = llm_analysis.get("search_query") or query
    search_keywords = llm_analysis.get("keywords") or []
    user_intent = llm_analysis.get("user_intent", "")
    logger.info(f"LLM Query Analysis -> Intent: '{user_intent}', Search: '{search_sentence}', Keywords: {search_keywords}")

    # 2. Search NewsAPI based on the LLM output (search sentence & keywords)
    news_result = news_service.search_news(
        query=search_sentence,
        keywords=search_keywords
    )

    # 3. Send search results back to LLM to analyze headlines and content to form grounded answer
    llm_result_en = llm_service.generate_answer(
        query=query,
        articles=news_result.get("articles", []),
        language_code="en-IN"
    )

    # 4. Translate answer into the user's native language if non-English
    if is_non_english:
        back_answer = translation_service.translate_from_english(
            llm_result_en.get("answer", ""),
            target_language_code=detected_lang
        )
        back_script = translation_service.translate_from_english(
            llm_result_en.get("audio_script", ""),
            target_language_code=detected_lang
        )

        final_answer = back_answer.get("translated_text") or llm_result_en.get("answer")
        final_script = back_script.get("translated_text") or llm_result_en.get("audio_script")

        llm_result = {
            **llm_result_en,
            "answer": final_answer,
            "audio_script": final_script,
            "language_code": detected_lang
        }

        translation_audit = {
            "was_translated": True,
            "source_language": detected_lang,
            "target_language": "en-IN",
            "original_query": query,
            "translated_english_query": search_sentence,
            "llm_search_query": search_sentence,
            "related_terms_used": news_result.get("extracted_keywords", search_keywords),
            "translation_model": "sarvam-translate:v1",
            "intermediate_english_answer": llm_result_en.get("answer"),
            "native_translated_answer": final_answer
        }
    else:
        final_answer = llm_result_en.get("answer")
        final_script = llm_result_en.get("audio_script")
        llm_result = {
            **llm_result_en,
            "answer": final_answer,
            "audio_script": final_script,
            "language_code": "en-IN"
        }
        translation_audit = {
            "was_translated": False,
            "source_language": "en-IN",
            "target_language": "en-IN",
            "original_query": query,
            "translated_english_query": query,
            "llm_search_query": search_sentence,
            "related_terms_used": news_result.get("extracted_keywords", search_keywords),
            "translation_model": None,
            "intermediate_english_answer": final_answer,
            "native_translated_answer": final_answer
        }

    # 5. Text-to-Speech Output in user's native language
    tts_result = tts_service.synthesize(
        text=llm_result.get("audio_script") or llm_result.get("answer", ""),
        language_code=detected_lang,
        speaker=speaker,
        transaction_id=transaction_id
    )

    duration_ms = round((time.time() - start_time) * 1000, 2)

    # 6. Provenance Ledger Storage
    ledger_entry = ledger_service.record_entry(
        input_type=input_type,
        transcript=query,
        detected_language=detected_lang,
        confidence=confidence,
        news_data=news_result,
        llm_data=llm_result,
        tts_data=tts_result,
        audio_filename=audio_filename,
        duration_ms=duration_ms,
        translation_data=translation_audit,
        llm_analysis=llm_analysis
    )

    return {
        "success": True,
        "transaction_id": ledger_entry["id"],
        "transcript": query,
        "detected_language": detected_lang,
        "confidence": confidence,
        "llm_analysis": llm_analysis,
        "translation": translation_audit,
        "news": news_result,
        "answer": llm_result.get("answer"),
        "audio_script": llm_result.get("audio_script"),
        "question_answered": llm_result.get("answered", False),
        "cited_articles": llm_result.get("cited_articles", []),
        "cited_article_indices": llm_result.get("cited_article_indices", []),
        "reasoning": llm_result.get("reasoning"),
        "audio_base64": tts_result.get("audio_base64"),
        "audio_url": tts_result.get("audio_url"),
        "speaker": tts_result.get("speaker"),
        "duration_ms": duration_ms,
        "ledger_entry": ledger_entry
    }

@app.post("/api/process-voice")
async def process_voice(
    audio: UploadFile = File(...),
    language_code: Optional[str] = Form(None),
    speaker: Optional[str] = Form(None)
):
    """
    Capture user voice input, transcribe via Sarvam STT.
    If non-English: translate to English, search NewsAPI, synthesize,
    translate back to native language, generate native speech TTS,
    and save full provenance in JSON ledger.
    """
    start_time = time.time()
    transaction_id = str(uuid.uuid4())

    try:
        audio_bytes = await audio.read()
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Audio file is empty.")

        # Speech-to-Text
        stt_result = stt_service.transcribe(
            audio_bytes=audio_bytes,
            filename=audio.filename or "recording.wav",
            language_code=language_code
        )

        if not stt_result.get("success") or not stt_result.get("transcript"):
            error_msg = stt_result.get("error", "Could not transcribe audio. Please speak clearly and try again.")
            raise HTTPException(status_code=422, detail=error_msg)

        transcript = stt_result["transcript"]
        detected_lang = language_code or stt_result.get("detected_language") or "en-IN"
        confidence = stt_result.get("confidence", 1.0)

        return await _execute_pipeline(
            query=transcript,
            input_type="voice",
            detected_lang=detected_lang,
            confidence=confidence,
            audio_filename=audio.filename,
            speaker=speaker,
            transaction_id=transaction_id,
            start_time=start_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice processing failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/process-text")
async def process_text(request: TextQueryRequest):
    """
    Process text query directly: translate if non-English, retrieve news,
    synthesize answer, translate back, generate TTS, and audit in ledger.
    """
    query = request.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    target_lang = request.language_code or "en-IN"

    try:
        return await _execute_pipeline(
            query=query,
            input_type="text",
            detected_lang=target_lang,
            confidence=1.0,
            speaker=request.speaker
        )
    except Exception as e:
        logger.error(f"Text query processing failure: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/ledger")
async def list_ledger(limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    """List historical provenance transactions."""
    records = ledger_service.get_all(limit=limit, offset=offset)
    return {"total": len(records), "records": records}

@app.get("/api/ledger/{record_id}")
async def get_ledger_record(record_id: str):
    """Retrieve full audit detail for a specific transaction."""
    record = ledger_service.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="Ledger record not found.")
    return record

@app.get("/api/audio/{filename}")
async def get_audio_file(filename: str):
    """Stream generated WAV audio."""
    file_path = AUDIO_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found.")
    return FileResponse(file_path, media_type="audio/wav")
