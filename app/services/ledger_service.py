import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from app.config import LEDGER_FILE, LEDGER_DIR, IS_VERCEL

logger = logging.getLogger(__name__)

class LedgerService:
    def __init__(self):
        self._in_memory_records: List[Dict[str, Any]] = []
        self._load_existing()

    def _load_existing(self):
        """Load initial records from disk if available."""
        try:
            if LEDGER_FILE.exists():
                with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        self._in_memory_records = json.loads(content)
        except Exception as e:
            logger.info(f"Ledger file read note ({e}). Initializing empty in-memory ledger.")

    def record_entry(
        self,
        input_type: str,
        transcript: str,
        detected_language: str,
        confidence: float,
        news_data: Dict[str, Any],
        llm_data: Dict[str, Any],
        tts_data: Dict[str, Any],
        audio_filename: Optional[str] = None,
        duration_ms: Optional[float] = None,
        translation_data: Optional[Dict[str, Any]] = None,
        llm_analysis: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record an immutable provenance transaction linking raw query, LLM query analysis,
        translation, fetched news, cited articles, generated answer, and audio.
        """
        transaction_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()

        record = {
            "id": transaction_id,
            "timestamp": timestamp,
            "input": {
                "type": input_type,
                "transcript": transcript,
                "detected_language": detected_language,
                "confidence": confidence,
                "audio_filename": audio_filename
            },
            "llm_query_analysis": llm_analysis or {},
            "translation_audit": translation_data or {
                "was_translated": False,
                "source_language": detected_language,
                "target_language": "en-IN",
                "translated_english_query": transcript,
                "related_terms_used": news_data.get("extracted_keywords", []),
                "translation_model": None
            },
            "news_retrieval": {
                "query_used": news_data.get("query_used", ""),
                "original_query": news_data.get("original_query", ""),
                "extracted_keywords": news_data.get("extracted_keywords", []),
                "total_found": news_data.get("total_found", 0),
                "fallback_used": news_data.get("fallback_used", False),
                "retrieved_articles": news_data.get("articles", [])
            },
            "answer_synthesis": {
                "model": llm_data.get("prompt_payload", {}).get("model", "sarvam-105b-conversations"),
                "question_answered": llm_data.get("answered", False),
                "answer_text": llm_data.get("answer", ""),
                "audio_script": llm_data.get("audio_script", ""),
                "cited_article_indices": llm_data.get("cited_article_indices", []),
                "cited_articles": llm_data.get("cited_articles", []),
                "reasoning": llm_data.get("reasoning", ""),
                "language_code": llm_data.get("language_code", detected_language),
                "prompt_snapshot": llm_data.get("prompt_payload", {})
            },
            "audio_synthesis": {
                "tts_model": tts_data.get("tts_model", "bulbul:v3"),
                "speaker": tts_data.get("speaker", ""),
                "audio_url": tts_data.get("audio_url", ""),
                "audio_base64_available": bool(tts_data.get("audio_base64"))
            },
            "audit_metadata": {
                "environment": "vercel" if IS_VERCEL else "container/local",
                "duration_ms": duration_ms
            }
        }

        # Store in-memory (most recent first)
        self._in_memory_records.insert(0, record)

        # Persist to disk if writable
        self._persist_to_disk(record)

        return record

    def _persist_to_disk(self, record: Dict[str, Any]):
        try:
            LEDGER_DIR.mkdir(parents=True, exist_ok=True)
            # Individual immutable transaction file
            single_file = LEDGER_DIR / f"{record['id']}.json"
            with open(single_file, "w", encoding="utf-8") as f:
                json.dump(record, f, indent=2, ensure_ascii=False)

            # Master ledger file
            with open(LEDGER_FILE, "w", encoding="utf-8") as f:
                json.dump(self._in_memory_records, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Could not persist ledger to filesystem ({e}). Data remains safe in memory.")

    def get_all(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Return paginated records."""
        return self._in_memory_records[offset:offset + limit]

    def get_by_id(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Find a specific record by transaction ID."""
        for rec in self._in_memory_records:
            if rec.get("id") == record_id:
                return rec

        # Check disk if not in memory
        try:
            single_file = LEDGER_DIR / f"{record_id}.json"
            if single_file.exists():
                with open(single_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return None

ledger_service = LedgerService()
