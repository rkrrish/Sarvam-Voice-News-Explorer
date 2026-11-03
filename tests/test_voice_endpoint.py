import io
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
from app.services.tts_service import tts_service
import base64

client = TestClient(app)

def test_process_voice_multipart():
    print("\n--- 1. Generating synthetic test voice sample using Sarvam TTS ---")
    synth = tts_service.synthesize(
        text="What are the latest updates on artificial intelligence in technology?",
        language_code="en-IN",
        speaker="kavya"
    )
    assert synth["success"] is True
    audio_base64 = synth["audio_base64"].split(",")[1]
    audio_bytes = base64.b64decode(audio_base64)
    print(f"Synthesized voice sample: {len(audio_bytes)} bytes.")

    print("\n--- 2. Sending voice audio to POST /api/process-voice ---")
    files = {
        "audio": ("query.wav", io.BytesIO(audio_bytes), "audio/wav")
    }
    data = {
        "language_code": "en-IN"
    }
    resp = client.post("/api/process-voice", files=files, data=data)
    assert resp.status_code == 200
    res = resp.json()
    assert res["success"] is True
    assert "transcript" in res
    assert len(res["transcript"]) > 0
    assert "news" in res
    assert "answer" in res
    assert "ledger_entry" in res
    
    print(f"[STT Transcript]: '{res['transcript']}'")
    print(f"[Detected Lang]: {res['detected_language']} (Confidence: {res['confidence']})")
    print(f"[News Articles Found]: {res['news']['total_found']}")
    print(f"[Question Answered]: {res['question_answered']}")
    print(f"[Cited Articles]: {res['cited_article_indices']}")
    print(f"[TTS Audio generated]: {bool(res['audio_base64'])}")
    print(f"[Ledger Transaction ID]: {res['transaction_id']}")
    print("\n>>> VOICE PIPELINE VERIFICATION PASSED SUCCESSFULLY! <<<")

if __name__ == "__main__":
    test_process_voice_multipart()
