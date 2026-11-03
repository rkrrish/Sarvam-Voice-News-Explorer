import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import pytest
from app.services.news_service import news_service
from app.services.llm_service import llm_service
from app.services.tts_service import tts_service
from app.services.stt_service import stt_service
from app.services.ledger_service import ledger_service
import base64

def test_news_retrieval_scenario():
    """Verify NewsAPI retrieval with the example scenario."""
    query = "What happened between Hugging Face and OpenAI? Was Hugging Face hacked?"
    result = news_service.search_news(query, page_size=5)
    
    assert "articles" in result
    assert "query_used" in result
    print(f"\n[News] Extracted keywords: {result['extracted_keywords']}")
    print(f"[News] Query used: '{result['query_used']}'")
    print(f"[News] Articles found: {len(result['articles'])}")

def test_llm_answer_and_grounding():
    """Verify Sarvam LLM can process articles, ground answers, and cite sources."""
    query = "What happened between Hugging Face and OpenAI? Was Hugging Face hacked?"
    news_result = news_service.search_news(query, page_size=5)
    
    llm_result = llm_service.generate_answer(
        query=query,
        articles=news_result["articles"],
        language_code="en-IN"
    )
    
    assert llm_result["success"] is True
    assert "answer" in llm_result
    assert "audio_script" in llm_result
    print(f"\n[LLM] Answer:\n{llm_result['answer']}")
    print(f"[LLM] Question Answered: {llm_result['answered']}")
    print(f"[LLM] Cited Articles: {llm_result['cited_article_indices']}")

def test_multilingual_hindi_answering():
    """Verify Sarvam LLM generates answer in Hindi when Hindi is requested."""
    query = "आर्टिफिशियल इंटेलिजेंस में क्या नया हो रहा है?"
    news_result = news_service.search_news("artificial intelligence", page_size=3)
    
    llm_result = llm_service.generate_answer(
        query=query,
        articles=news_result["articles"],
        language_code="hi-IN"
    )
    
    assert llm_result["success"] is True
    assert len(llm_result["answer"]) > 10
    print(f"\n[Hindi Answer]:\n{llm_result['answer'][:150]}...")

def test_tts_synthesis():
    """Verify Sarvam TTS converts answer script to audio."""
    sample_text = "Here is the latest update regarding artificial intelligence and Hugging Face."
    tts_result = tts_service.synthesize(
        text=sample_text,
        language_code="en-IN",
        transaction_id="test_run_01"
    )
    
    assert tts_result["success"] is True
    assert tts_result["audio_base64"].startswith("data:audio/wav;base64,")
    print(f"\n[TTS] Synthesized successfully. Base64 len: {len(tts_result['audio_base64'])}")

def test_ledger_provenance():
    """Verify end-to-end ledger recording and auditing."""
    news_data = {
        "query_used": "Hugging Face OpenAI",
        "original_query": "Was Hugging Face hacked?",
        "extracted_keywords": ["Hugging Face", "hacked"],
        "total_found": 1,
        "articles": [{
            "id": "art_1",
            "index": 1,
            "title": "Security Notice from Hugging Face",
            "source": "TechCrunch",
            "author": "Reporter",
            "description": "Hugging Face detected suspicious activity on Spaces.",
            "url": "https://example.com/hf-notice",
            "published_at": "2024-06-01T00:00:00Z",
            "content": "Full article content snippet..."
        }]
    }
    llm_data = {
        "answered": True,
        "answer": "Yes, Hugging Face detected unauthorized access to Spaces [Article 1].",
        "audio_script": "Yes, Hugging Face detected unauthorized access to Spaces.",
        "cited_article_indices": [1],
        "cited_articles": [{"id": "art_1", "index": 1, "title": "Security Notice from Hugging Face"}],
        "reasoning": "Confirmed via Article 1.",
        "language_code": "en-IN",
        "prompt_payload": {"model": "sarvam-105b-conversations"}
    }
    tts_data = {
        "tts_model": "bulbul:v3",
        "speaker": "aditi_en_stories",
        "audio_url": "/api/audio/test.wav",
        "audio_base64": "data:audio/wav;base64,UklGR..."
    }

    record = ledger_service.record_entry(
        input_type="text",
        transcript="Was Hugging Face hacked?",
        detected_language="en-IN",
        confidence=1.0,
        news_data=news_data,
        llm_data=llm_data,
        tts_data=tts_data,
        duration_ms=1200.0
    )

    assert record["id"] is not None
    assert record["answer_synthesis"]["question_answered"] is True
    assert len(record["news_retrieval"]["retrieved_articles"]) == 1
    
    # Verify retrieval from ledger service
    retrieved = ledger_service.get_by_id(record["id"])
    assert retrieved is not None
    assert retrieved["id"] == record["id"]
    print(f"\n[Ledger] Provenance transaction stored and audited: {record['id']}")

if __name__ == "__main__":
    print("=== 1. Testing News Retrieval ===")
    test_news_retrieval_scenario()
    
    print("\n=== 2. Testing Sarvam LLM Answer & Grounding ===")
    test_llm_answer_and_grounding()
    
    print("\n=== 3. Testing Multilingual (Hindi) Response ===")
    test_multilingual_hindi_answering()
    
    print("\n=== 4. Testing Sarvam TTS Voice Output ===")
    test_tts_synthesis()
    
    print("\n=== 5. Testing Provenance Ledger Storage ===")
    test_ledger_provenance()

    print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")
