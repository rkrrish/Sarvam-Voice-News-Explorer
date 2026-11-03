# 🎙️ Sarvam Daily Chronicle — Multilingual Voice News Explorer & Audit Ledger

An AI-powered voice agent that lets users ask news questions **in any Indian language**, fetches real-time news from [NewsAPI.org](https://newsapi.org), synthesizes a grounded answer using the **Sarvam AI** model stack, plays the spoken response in the user's native language via Sarvam TTS, and records every step in an immutable **Data Provenance Ledger**.


### Demo deployed at Vercel: https://sarvam-voice-news-explorer.vercel.app/

---

## 🌊 End-to-End Pipeline Flow

Below is the full journey of a user's voice query, from spoken word to native-language audio response:

```
 🎤 Voice Input (any Indian language)
         │
         ▼
 ┌───────────────────────────────────────────┐
 │  STAGE 1 — TRANSCRIPTION                 │
 │  Sarvam saaras:v3 (STT)                  │
 │  Voice → Text in detected language       │
 └───────────────────────────────────────────┘
         │ e.g. "क्या AI में कोई नया अपडेट है?"
         ▼
 ┌───────────────────────────────────────────┐
 │  STAGE 2 — TRANSLATION (if non-English)  │
 │  Sarvam sarvam-translate:v1              │
 │  Native language → English               │
 │  (NewsAPI.org supports English only)     │
 └───────────────────────────────────────────┘
         │ e.g. "Is there any new update in AI?"
         ▼
 ┌───────────────────────────────────────────┐
 │  STAGE 3 — INTENT ANALYSIS               │
 │  Sarvam sarvam-105b-conversations (LLM)  │
 │  Understands what the user wants →       │
 │  Generates optimized English search      │
 │  query + keywords for NewsAPI            │
 └───────────────────────────────────────────┘
         │ e.g. query: "AI breakthroughs 2024"
         │      keywords: ["artificial intelligence", "update"]
         ▼
 ┌───────────────────────────────────────────┐
 │  STAGE 4 — NEWS RETRIEVAL                │
 │  NewsAPI.org /everything endpoint        │
 │  Smart multi-attempt search with         │
 │  keyword fallbacks & OR queries          │
 └───────────────────────────────────────────┘
         │ Returns up to 8 relevant articles
         ▼
 ┌───────────────────────────────────────────┐
 │  STAGE 5 — GROUNDED ANSWER GENERATION    │
 │  Sarvam sarvam-105b-conversations (LLM)  │
 │  Reads articles → drafts cited answer    │
 │  with [Article N] provenance citations   │
 └───────────────────────────────────────────┘
         │ Answer in English with citations
         ▼
 ┌───────────────────────────────────────────┐
 │  STAGE 6 — BACK-TRANSLATION              │
 │  Sarvam sarvam-translate:v1              │
 │  English answer → User's native language │
 └───────────────────────────────────────────┘
         │ e.g. Answer now in Hindi
         ▼
 ┌───────────────────────────────────────────┐
 │  STAGE 7 — VOICE SYNTHESIS               │
 │  Sarvam bulbul:v3 (TTS)                  │
 │  Native-language text → WAV audio        │
 │  Language-matched speaker voice          │
 └───────────────────────────────────────────┘
         │
         ▼
 🔊 Spoken answer in user's native language
    + 📜 Full audit ledger entry saved
```

> **If the user speaks English**, stages 2 and 6 are automatically skipped — the query goes directly to intent analysis and the answer is synthesized in English.

---

## 🧩 Stage Name Meanings

| Stage | Name | What It Means |
|---|---|---|
| 1 | **Transcription** | Converting the spoken audio into written text (Speech-to-Text) |
| 2 | **Translation** | Rendering the text from one human language to another (native → English) |
| 3 | **Intent Analysis** | Understanding *what* the user actually wants to know, then crafting an optimal search query |
| 4 | **News Retrieval** | Fetching real-time news articles from the NewsAPI wire feed based on the LLM-crafted query |
| 5 | **Grounded Answer Generation** | Using retrieved articles as the only source of truth to compose a factual, cited answer |
| 6 | **Back-Translation** | Translating the English answer back into the user's original language |
| 7 | **Voice Synthesis** | Converting the native-language text answer into spoken audio (Text-to-Speech) |

---

## 🤖 Models Used

| Stage | Sarvam Model | Role |
|---|---|---|
| Speech-to-Text | `saaras:v3` | Multilingual ASR — transcribes audio and auto-detects the spoken Indian language |
| Translation | `sarvam-translate:v1` | Bidirectional translation between 23+ Indian languages and English |
| Intent Analysis & Answer | `sarvam-105b-conversations` | 105B-parameter LLM — extracts search intent, generates grounded cited news answers |
| Text-to-Speech | `bulbul:v3` | Multilingual TTS — synthesizes natural-sounding speech in 11 Indian languages with language-matched speakers |

---

## 🌟 Key Features

1. **Multilingual Voice-First UX**: Speak in any of 10+ Indian languages — the system auto-detects your language (via `saaras:v3`) and responds in kind.

2. **English-Bridged Search**: Because NewsAPI.org only supports English queries, all Indian-language inputs are first translated to English (`sarvam-translate:v1`) before the LLM crafts the search query. The final answer is then translated back.

3. **LLM-Optimized News Search**: `sarvam-105b-conversations` doesn't just pass raw text to NewsAPI — it first understands the user's *intent*, then generates a precise English search phrase and keywords. This means a question like *"Modi ne kya kiya aaj?"* becomes a clean search like `"Modi India news today"`.

4. **Smart Search Fallbacks**: The news service attempts up to 5 retrieval strategies — exact LLM query → keyword phrases → OR query → individual terms → top headlines — ensuring an answer is always found.

5. **Grounded Answering with Citations**: The LLM is only allowed to answer using the retrieved articles, and must cite `[Article N]` for every claim. No hallucinations.

6. **Native-Language TTS with Matched Voices**: `bulbul:v3` selects a language-appropriate speaker voice automatically (e.g., `vijay` for Tamil, `kavitha` for Telugu, `kavya` for English, `aayan` for Hindi).

7. **Data Provenance & Audit Ledger**: Every query is stored with full lineage in `data/ledger.json` and `data/ledgers/{id}.json` — raw audio filename, transcription, translation audit, search query used, retrieved articles, LLM prompt & response, citations, and final outcome. Exportable as JSON.

8. **Dual Deployment Ready**:
   - 🐳 **Docker & Docker Compose**: One-command containerized deployment with volume persistence.
   - ☁️ **Vercel Serverless**: Pre-configured with `api/index.py` and `vercel.json` for one-click cloud deployment.

---

## 🖥️ Frontend Highlights

The web UI (`static/`) is styled as a **broadsheet newspaper newsroom** — "The Sarvam Daily Chronicle":

- **📰 Broadsheet Masthead**: Full newspaper-style header with live ticker bar showing real-time system status.
- **🎙️ Studio Mic Centerpiece**: Large animated microphone button with real-time waveform visualization and recording timer.
- **⌨️ Text + Audio Upload Fallback**: Users can also type a question or upload an audio file (`.wav`, `.mp3`, `.m4a`, `.webm`) if they don't want to use live mic.
- **🌐 Language Picker**: Dropdown to manually set input language or use "Auto-Detect (Sarvam Saaras)" for hands-free operation.
- **💡 Suggested Queries**: Quick-tap chip buttons for trying sample questions (including Hindi examples).
- **📋 Live Processing Stepper**: 6-step animated progress bar (`Saaras STT → Editor Analysis → News Wires → Drafting → Regional Translation → News Anchor Voice`) visible while the pipeline runs.
- **🧠 AI Analysis Reveal Card**: Shows how the LLM interpreted the question — user intent summary, the exact search query sent to NewsAPI, and the key topics extracted.
- **🌐 Translation Info Box**: Appears for non-English queries, showing original question and the target language used for the answer.
- **🔊 Audio Player with Autoplay**: Inline audio player with autoplay toggle and downloadable `.wav` output. Speaker info shown (e.g., "Anchor: Vijay (Sarvam Bulbul) • Tamil").
- **🗞️ News Articles Grid**: All retrieved articles displayed as newspaper-style cards with source, date, and link.
- **🔍 Collapsible Fact-Check Panel**: "See sources & fact-check notes" toggle reveals the LLM's reasoning and all cited article links.
- **📜 History & Ledger Tab**: Full query history table (time, input type, language, articles found, outcome) with modal deep-dive showing raw JSON audit record and a one-click JSON export.
- **📱 Responsive Design**: Works on mobile and desktop with modern Inter + Newsreader typography.

---

## 📂 Project Structure

```
sarvam/
├── app/
│   ├── config.py              # Configuration & environment loading, model names, speaker map
│   ├── main.py                # FastAPI endpoints & pipeline orchestration
│   └── services/
│       ├── stt_service.py     # Stage 1: Sarvam saaras:v3 Speech-to-Text
│       ├── translation_service.py # Stages 2 & 6: Sarvam sarvam-translate:v1
│       ├── llm_service.py     # Stages 3 & 5: Sarvam sarvam-105b-conversations
│       ├── news_service.py    # Stage 4: NewsAPI.org search with smart fallbacks
│       ├── tts_service.py     # Stage 7: Sarvam bulbul:v3 Text-to-Speech
│       └── ledger_service.py  # Audit ledger — records full data provenance
├── static/
│   ├── index.html             # Broadsheet-style web UI
│   ├── style.css              # Modern responsive styling (newspaper theme)
│   └── app.js                 # MediaRecorder, waveform, stepper, ledger client
├── api/
│   └── index.py               # Vercel Serverless entrypoint
├── data/
│   ├── ledger.json            # Master JSON audit ledger (gitignored)
│   ├── ledgers/               # Per-transaction JSON records (gitignored)
│   └── audio/                 # Generated audio WAV cache (gitignored)
├── tests/
│   ├── test_api_endpoints.py  # Endpoint integration tests
│   ├── test_scenario.py       # End-to-end scenario tests
│   ├── test_translation_pipeline.py # Translation pipeline tests
│   └── test_voice_endpoint.py # Voice upload tests
├── Dockerfile                 # Python 3.10-slim container with ffmpeg
├── docker-compose.yml         # Docker orchestration with data volume mount
├── vercel.json                # Vercel deployment configuration
├── requirements.txt           # Python dependencies
├── .env.example               # Environment variable template
└── .env                       # Your API credentials (gitignored — never commit this)
```

---

## 🚀 Quickstart: Running Locally

### 1. Prerequisites

Python 3.10+ is required. Using conda:
```bash
conda activate <env name>
```
Or create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate    # Windows
source venv/bin/activate # macOS/Linux
```

### 2. Configure Environment

Copy the example and fill in your API keys:
```bash
cp .env.example .env
```

Edit `.env`:
```env
SARVAM_API_KEY=your_sarvam_api_key_here
NEWSAPI_KEY=your_newsapi_key_here
```

- Get a Sarvam AI key: https://sarvam.ai
- Get a NewsAPI key: https://newsapi.org

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Application

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser at **http://localhost:8000**

---

## 🧪 Testing

### Run the Test Suite

```bash
# Run all tests
pytest tests/ -v

# Run specific test files
pytest tests/test_api_endpoints.py -v
pytest tests/test_translation_pipeline.py -v
pytest tests/test_scenario.py -v
pytest tests/test_voice_endpoint.py -v
```

### Manual Testing via the UI

1. Open **http://localhost:8000**
2. Try the suggested queries using the quick-tap chip buttons, e.g.:
   - **"Hugging Face & OpenAI Hack"** — English query test
   - **"हिंदी: AI Updates"** — Non-English pipeline test (exercises translation stages)
   - **"ISRO Space News"** — Topic entity test
3. Click the microphone, speak your question, and click again to stop. The 6-step stepper will animate as the pipeline runs.
4. Check the **History & Ledger** tab to inspect the full audit record for your query.

### Test via API (curl)

**Text query (English):**
```bash
curl -X POST http://localhost:8000/api/process-text \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the latest AI breakthroughs?", "language_code": "en-IN"}'
```

**Text query (Hindi — exercises full translation pipeline):**
```bash
curl -X POST http://localhost:8000/api/process-text \
  -H "Content-Type: application/json" \
  -d '{"query": "आर्टिफिशियल इंटेलिजेंस में क्या नया हुआ है?", "language_code": "hi-IN"}'
```

**Voice query:**
```bash
curl -X POST http://localhost:8000/api/process-voice \
  -F "audio=@your_recording.wav" \
  -F "language_code=hi-IN"
```

**Health check:**
```bash
curl http://localhost:8000/api/health
```

---

## 🐳 Running with Docker

Build and launch the complete stack with Docker Compose:

```bash
# Build and run in detached mode
docker compose up --build -d

# Check running status
docker compose ps

# View live container logs
docker compose logs -f

# Stop container
docker compose down
```

> The container mounts `./data` from your host to persist the provenance ledger and audio cache across container rebuilds.

---

## ☁️ Deploying to Vercel

The repository is pre-configured with `vercel.json` and `api/index.py` for seamless Vercel deployment.

### Method 1: Vercel CLI

```bash
# Install Vercel CLI if needed
npm install -g vercel

# Deploy
vercel
```

### Method 2: Git Repository Import

1. Push this repository to GitHub / GitLab / Bitbucket.
2. In the Vercel Dashboard, click **Add New Project** and select this repo.
3. Under **Environment Variables**, add:
   - `SARVAM_API_KEY` — Your Sarvam AI key
   - `NEWSAPI_KEY` — Your NewsAPI key
4. Click **Deploy**.

> **Note on Vercel Serverless**: Because Vercel has an ephemeral filesystem, audio is returned as base64 data URIs and ledger records are backed up in `/tmp` and client-side `localStorage` to ensure audio playback and history tracking work reliably across cold starts.

---

## 📊 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/process-voice` | Upload audio (`multipart/form-data`) → Full pipeline (STT → Translate → LLM → News → LLM → Translate → TTS → Ledger) |
| `POST` | `/api/process-text` | JSON text query `{"query": "...", "language_code": "hi-IN"}` → Pipeline (skip STT) |
| `GET` | `/api/ledger` | Fetch all historical provenance transactions |
| `GET` | `/api/ledger/{id}` | Fetch full audit record for a specific query |
| `GET` | `/api/audio/{filename}` | Stream synthesized WAV audio file |
| `GET` | `/api/health` | Health check verifying Sarvam & NewsAPI configuration |

---

## 🌍 Supported Languages

| Language | Code | TTS Speaker |
|---|---|---|
| English (India) | `en-IN` | kavya |
| Hindi (हिंदी) | `hi-IN` | aayan |
| Bengali (বাংলা) | `bn-IN` | anand |
| Tamil (தமிழ்) | `ta-IN` | vijay |
| Telugu (తెలుగు) | `te-IN` | kavitha |
| Kannada (ಕನ್ನಡ) | `kn-IN` | rohan |
| Gujarati (ગુજરાતી) | `gu-IN` | pooja |
| Marathi (मराठी) | `mr-IN` | ishita |
| Punjabi (ਪੰਜਾਬੀ) | `pa-IN` | anand |
| Malayalam (മലയാളം) | `ml-IN` | shreya |
| Odia (ଓଡ଼ିଆ) | `od-IN` | priya |

> Translation via `sarvam-translate:v1` supports an extended set including Assamese, Bodo, Dogri, Kashmiri, Konkani, Maithili, Manipuri, Nepali, Sanskrit, Santali, Sindhi, and Urdu.

---

## 🔒 Security & Git Hygiene

- `.env` is **gitignored** — your API keys are never committed.
- `data/ledger.json` and `data/ledgers/` are **gitignored** — session query history is not committed.
- `data/audio/` is **gitignored** — generated audio files are not committed.
- Use `.env.example` as a template; fill `.env` locally with real keys.
- For production, set `SARVAM_API_KEY` and `NEWSAPI_KEY` as environment variables in your deployment platform (Vercel, Docker, etc.) — never hardcode them.

---

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Backend API | FastAPI + Uvicorn |
| AI Models | Sarvam AI (`saaras:v3`, `sarvam-105b-conversations`, `bulbul:v3`, `sarvam-translate:v1`) |
| News Data | NewsAPI.org |
| Frontend | Vanilla HTML/CSS/JS (broadsheet newspaper theme) |
| Containerization | Docker + Docker Compose |
| Cloud Deployment | Vercel Serverless |
| Audit Persistence | JSON flat-file ledger (`data/ledger.json`) |

---

*Powered by **Sarvam AI** (Saaras STT • Sarvam-105B • Bulbul TTS • Sarvam-Translate) and **NewsAPI.org**. All ground reports are grounded in real media coverage with full source citations.*
