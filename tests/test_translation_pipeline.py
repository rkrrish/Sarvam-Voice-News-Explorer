import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from fastapi.testclient import TestClient
from app.main import app
from app.services.translation_service import translation_service
from app.services.news_service import news_service

client = TestClient(app)

def test_translation_service_isolated():
    print("\n--- 1. Testing Translation Service Isolated (Sarvam Server Model) ---")
    hindi_query = "क्या हगिंग फेस हैक हुआ था?"
    to_en = translation_service.translate_to_english(hindi_query, source_language_code="hi-IN")
    assert to_en["success"] is True
    assert to_en["was_translated"] is True
    assert "hack" in to_en["translated_text"].lower() or "hugging" in to_en["translated_text"].lower()
    print(f"[Original Hindi]: {hindi_query}")
    print(f"[Translated English]: {to_en['translated_text']}")
    print(f"[Model Used]: {to_en['model']}")

    # Back-translation
    sample_answer = "No evidence was found that Hugging Face was hacked by OpenAI."
    to_hi = translation_service.translate_from_english(sample_answer, target_language_code="hi-IN")
    assert to_hi["success"] is True
    assert to_hi["was_translated"] is True
    assert len(to_hi["translated_text"]) > 10
    print(f"[Back-translated to Hindi]: {to_hi['translated_text']}")

def test_end_to_end_multilingual_pipeline():
    print("\n--- 2. Testing End-to-End Pipeline with Hindi Query ---")
    payload = {
        "query": "क्या हगिंग फेस और ओपनएआई के बीच कुछ हुआ था?",
        "language_code": "hi-IN"
    }
    resp = client.post("/api/process-text", json=payload)
    assert resp.status_code == 200
    res = resp.json()

    assert res["success"] is True
    assert "translation" in res
    assert res["translation"]["was_translated"] is True
    assert res["translation"]["source_language"] == "hi-IN"
    assert res["translation"]["translated_english_query"] != ""
    assert len(res["translation"]["related_terms_used"]) > 0
    assert res["translation"]["translation_model"] is not None
    assert "llm_analysis" in res
    assert "user_intent" in res["llm_analysis"]
    assert "search_query" in res["llm_analysis"]
    assert "keywords" in res["llm_analysis"]

    print(f"[User Query (Hindi)]: {res['transcript']}")
    print(f"[LLM Analyzed Intent]: {res['llm_analysis']['user_intent']}")
    print(f"[LLM Generated Search Sentence]: {res['llm_analysis']['search_query']}")
    print(f"[LLM Keywords]: {res['llm_analysis']['keywords']}")
    print(f"[News Articles Found]: {res['news']['total_found']}")
    print(f"[Question Answered]: {res['question_answered']}")
    print(f"[Final Native Answer (Hindi)]:\n{res['answer']}")
    print(f"[Audio Base64 Available]: {bool(res['audio_base64'])}")
    print(f"[Ledger Transaction ID]: {res['transaction_id']}")

def test_english_query_skips_translation():
    print("\n--- 3. Testing English Query (Should skip translation) ---")
    payload = {
        "query": "What are the latest updates on quantum computing?",
        "language_code": "en-IN"
    }
    resp = client.post("/api/process-text", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["translation"]["was_translated"] is False
    print(f"[English Query translation skipped as expected: was_translated = False]")

if __name__ == "__main__":
    test_translation_service_isolated()
    test_end_to_end_multilingual_pipeline()
    test_english_query_skips_translation()
    print("\n>>> ALL MULTILINGUAL TRANSLATION TESTS PASSED! <<<")
