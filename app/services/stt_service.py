import io
import logging
from typing import Dict, Any, Optional
from sarvamai import SarvamAI
from app.config import SARVAM_API_KEY, SARVAM_STT_MODEL

logger = logging.getLogger(__name__)

class STTService:
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or SARVAM_API_KEY
        if not key:
            raise ValueError("SARVAM_API_KEY is not set.")
        self.client = SarvamAI(api_subscription_key=key)

    def transcribe(self, audio_bytes: bytes, filename: str = "query.wav", language_code: Optional[str] = None) -> Dict[str, Any]:
        """
        Transcribe audio using Sarvam STT API (saaras:v3).
        Returns transcript, detected language_code, and confidence.
        """
        try:
            audio_io = io.BytesIO(audio_bytes)
            audio_io.name = filename

            kwargs = {
                "file": audio_io,
                "model": SARVAM_STT_MODEL
            }
            if language_code and language_code != "unknown":
                kwargs["language_code"] = language_code

            response = self.client.speech_to_text.transcribe(**kwargs)

            transcript = getattr(response, "transcript", "") or ""
            detected_lang = getattr(response, "language_code", None) or "en-IN"
            confidence = getattr(response, "language_probability", 1.0)
            request_id = getattr(response, "request_id", "")

            return {
                "success": True,
                "transcript": transcript.strip(),
                "detected_language": detected_lang,
                "confidence": confidence,
                "request_id": request_id,
            }
        except Exception as e:
            logger.error(f"STT Error: {str(e)}", exc_info=True)
            return {
                "success": False,
                "transcript": "",
                "detected_language": "en-IN",
                "confidence": 0.0,
                "error": str(e)
            }

stt_service = STTService()
