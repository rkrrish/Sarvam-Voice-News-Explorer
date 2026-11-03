import logging
from typing import Dict, Any, Optional
from sarvamai import SarvamAI
from app.config import SARVAM_API_KEY, SARVAM_TRANSLATION_MODEL

logger = logging.getLogger(__name__)

# Languages supported by Sarvam translation models
SUPPORTED_TRANSLATION_LANGUAGES = {
    "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN", "ml-IN",
    "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN", "as-IN",
    "brx-IN", "doi-IN", "kok-IN", "ks-IN", "mai-IN", "mni-IN",
    "ne-IN", "sa-IN", "sat-IN", "sd-IN", "ur-IN"
}

class TranslationService:
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or SARVAM_API_KEY
        if not key:
            raise ValueError("SARVAM_API_KEY is not set.")
        self.client = SarvamAI(api_subscription_key=key)

    def translate_to_english(self, text: str, source_language_code: str) -> Dict[str, Any]:
        """
        Translate input text from a native language to English using the Sarvam server model.
        If already English, returns the input unchanged.
        """
        clean_text = text.strip()
        if not clean_text:
            return {"success": True, "translated_text": "", "was_translated": False}

        # If already English, skip translation
        if source_language_code in ("en-IN", "en"):
            return {
                "success": True,
                "translated_text": clean_text,
                "source_language": source_language_code,
                "target_language": "en-IN",
                "was_translated": False,
                "model": None
            }

        source_code = source_language_code if source_language_code in SUPPORTED_TRANSLATION_LANGUAGES else "auto"

        try:
            logger.info(f"Translating native input to English with {SARVAM_TRANSLATION_MODEL}: '{clean_text}'")
            resp = self.client.text.translate(
                input=clean_text,
                source_language_code=source_code,
                target_language_code="en-IN",
                model=SARVAM_TRANSLATION_MODEL
            )
            translated = getattr(resp, "translated_text", clean_text) or clean_text
            return {
                "success": True,
                "translated_text": translated.strip(),
                "original_text": clean_text,
                "source_language": source_language_code,
                "target_language": "en-IN",
                "was_translated": True,
                "model": SARVAM_TRANSLATION_MODEL,
                "request_id": getattr(resp, "request_id", "")
            }
        except Exception as e:
            logger.error(f"Translation to English error: {e}", exc_info=True)
            return {
                "success": False,
                "translated_text": clean_text,
                "original_text": clean_text,
                "source_language": source_language_code,
                "target_language": "en-IN",
                "was_translated": False,
                "error": str(e)
            }

    def translate_from_english(self, text: str, target_language_code: str) -> Dict[str, Any]:
        """
        Translate English text back to the user's native language using the Sarvam server model.
        If target is English, returns input unchanged.
        """
        clean_text = text.strip()
        if not clean_text:
            return {"success": True, "translated_text": "", "was_translated": False}

        if target_language_code in ("en-IN", "en"):
            return {
                "success": True,
                "translated_text": clean_text,
                "source_language": "en-IN",
                "target_language": target_language_code,
                "was_translated": False,
                "model": None
            }

        target_code = target_language_code if target_language_code in SUPPORTED_TRANSLATION_LANGUAGES else "hi-IN"

        try:
            logger.info(f"Translating English response to {target_code} with {SARVAM_TRANSLATION_MODEL}")
            
            # If text is very long, Sarvam translate handles up to 1000 characters per call cleanly
            if len(clean_text) > 950:
                chunks = self._chunk_text(clean_text, max_len=900)
                translated_chunks = []
                for chunk in chunks:
                    resp = self.client.text.translate(
                        input=chunk,
                        source_language_code="en-IN",
                        target_language_code=target_code,
                        model=SARVAM_TRANSLATION_MODEL
                    )
                    translated_chunks.append(getattr(resp, "translated_text", chunk) or chunk)
                translated = " ".join(translated_chunks)
            else:
                resp = self.client.text.translate(
                    input=clean_text,
                    source_language_code="en-IN",
                    target_language_code=target_code,
                    model=SARVAM_TRANSLATION_MODEL
                )
                translated = getattr(resp, "translated_text", clean_text) or clean_text

            return {
                "success": True,
                "translated_text": translated.strip(),
                "original_text": clean_text,
                "source_language": "en-IN",
                "target_language": target_code,
                "was_translated": True,
                "model": SARVAM_TRANSLATION_MODEL
            }
        except Exception as e:
            logger.error(f"Translation from English error: {e}", exc_info=True)
            return {
                "success": False,
                "translated_text": clean_text,
                "original_text": clean_text,
                "source_language": "en-IN",
                "target_language": target_code,
                "was_translated": False,
                "error": str(e)
            }

    def _chunk_text(self, text: str, max_len: int = 900) -> list:
        """Split text by sentences to keep within length bounds."""
        sentences = text.replace("\n", " ").split(". ")
        chunks = []
        current = ""
        for s in sentences:
            piece = s.strip() + ". "
            if len(current) + len(piece) > max_len and current:
                chunks.append(current.strip())
                current = piece
            else:
                current += piece
        if current:
            chunks.append(current.strip())
        return chunks

translation_service = TranslationService()
