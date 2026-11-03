import base64
import logging
from typing import Dict, Any, Optional
from sarvamai import SarvamAI
from app.config import (
    SARVAM_API_KEY,
    SARVAM_TTS_MODEL,
    LANGUAGE_SPEAKER_MAP,
    AUDIO_DIR
)

logger = logging.getLogger(__name__)

SUPPORTED_TTS_LANGUAGES = {
    "bn-IN", "en-IN", "gu-IN", "hi-IN", "kn-IN",
    "ml-IN", "mr-IN", "od-IN", "pa-IN", "ta-IN", "te-IN"
}

class TTSService:
    def __init__(self, api_key: Optional[str] = None):
        key = api_key or SARVAM_API_KEY
        if not key:
            raise ValueError("SARVAM_API_KEY is not set.")
        self.client = SarvamAI(api_subscription_key=key)

    def synthesize(
        self,
        text: str,
        language_code: str = "en-IN",
        speaker: Optional[str] = None,
        transaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Convert text to speech using Sarvam TTS (bulbul:v3).
        Returns base64 audio and writes to disk if writable.
        """
        try:
            # Normalize language code for TTS
            tts_lang = language_code if language_code in SUPPORTED_TTS_LANGUAGES else "en-IN"
            chosen_speaker = speaker or LANGUAGE_SPEAKER_MAP.get(tts_lang, "kavya")

            # Clean and limit text length for natural voice delivery (under ~500 chars)
            clean_text = text.strip()
            if len(clean_text) > 480:
                # Find punctuation near 480
                truncated = clean_text[:480]
                last_punct = max(truncated.rfind("."), truncated.rfind("।"), truncated.rfind("?"))
                if last_punct > 200:
                    clean_text = truncated[:last_punct + 1]
                else:
                    clean_text = truncated + "..."

            response = self.client.text_to_speech.convert(
                text=clean_text,
                language_code=tts_lang,
                speaker=chosen_speaker,
                model=SARVAM_TTS_MODEL
            )

            audios = getattr(response, "audios", [])
            if not audios:
                raise ValueError("No audio returned from Sarvam TTS.")

            raw_base64 = audios[0]
            data_uri = f"data:audio/wav;base64,{raw_base64}"

            # Save to disk if writable
            filename = f"{transaction_id or 'speech'}.wav"
            audio_url = f"/api/audio/{filename}"
            try:
                AUDIO_DIR.mkdir(parents=True, exist_ok=True)
                audio_path = AUDIO_DIR / filename
                with open(audio_path, "wb") as f:
                    f.write(base64.b64decode(raw_base64))
            except Exception as io_err:
                # In serverless/read-only environments, audio_url falls back to data URI
                logger.info(f"Filesystem write skipped ({io_err}), using data URI.")
                audio_url = data_uri

            return {
                "success": True,
                "audio_base64": data_uri,
                "audio_url": audio_url,
                "speaker": chosen_speaker,
                "language_code": tts_lang,
                "tts_model": SARVAM_TTS_MODEL
            }

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}", exc_info=True)
            return {
                "success": False,
                "audio_base64": None,
                "audio_url": None,
                "speaker": speaker,
                "language_code": language_code,
                "error": str(e)
            }

tts_service = TTSService()
