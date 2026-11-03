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

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["sarvam_configured"] is True
    assert data["newsapi_configured"] is True
    print("\n[API] Health check passed.")

def test_root_html_endpoint():
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Sarvam Voice News Explorer" in resp.text
    print("[API] Root HTML served properly.")

def test_process_text_endpoint():
    payload = {
        "query": "What is the latest status of OpenAI and artificial intelligence?",
        "language_code": "en-IN"
    }
    resp = client.post("/api/process-text", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert "transaction_id" in data
    assert "answer" in data
    assert "audio_base64" in data
    assert "ledger_entry" in data
    print(f"[API] Process text passed. Transaction ID: {data['transaction_id']}")

def test_ledger_list_endpoint():
    resp = client.get("/api/ledger")
    assert resp.status_code == 200
    data = resp.json()
    assert "records" in data
    assert len(data["records"]) > 0
    record_id = data["records"][0]["id"]
    print(f"[API] Ledger list returned {len(data['records'])} records. First: {record_id}")

    # Test single ledger retrieval
    detail_resp = client.get(f"/api/ledger/{record_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["id"] == record_id
    assert "news_retrieval" in detail
    assert "answer_synthesis" in detail
    print(f"[API] Single ledger detail verified for {record_id}.")

if __name__ == "__main__":
    test_health_endpoint()
    test_root_html_endpoint()
    test_process_text_endpoint()
    test_ledger_list_endpoint()
    print("\n>>> ALL API ENDPOINT TESTS PASSED! <<<")
