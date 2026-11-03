// Sarvam Voice News Explorer & Audit Ledger Frontend Script

let mediaRecorder = null;
let audioChunks = [];
let isRecording = false;
let recordStartTime = 0;
let timerInterval = null;
let audioContext = null;
let analyser = null;
let animFrameId = null;

let currentLedgerRecords = [];
let currentModalRecord = null;

// Initialization
document.addEventListener("DOMContentLoaded", () => {
  checkSystemHealth();
  loadLedgerRecords();
  initDarkMode();

  // Show welcome modal only on first visit (tracked via localStorage)
  const hasSeenWelcome = localStorage.getItem("sarvam_welcome_seen");
  if (!hasSeenWelcome) {
    showWelcomeModal();
  }

  // Enter key in text input triggers search
  const textInput = document.getElementById("textQueryInput");
  if (textInput) {
    textInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        submitTextQuery();
      }
    });
  }

  // Close welcome modal on Escape key
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      closeWelcomeModal();
    }
  });
});

// ==========================================
// WELCOME MODAL
// ==========================================

function showWelcomeModal() {
  const modal = document.getElementById("welcomeModal");
  if (modal) modal.style.display = "flex";
}

function closeWelcomeModal() {
  const modal = document.getElementById("welcomeModal");
  if (modal) {
    modal.style.display = "none";
    // Mark as seen so it doesn't show again until localStorage is cleared
    try {
      localStorage.setItem("sarvam_welcome_seen", "1");
    } catch (e) {
      console.warn("localStorage unavailable:", e);
    }
  }
}

// ==========================================
// DARK MODE TOGGLE
// ==========================================

function initDarkMode() {
  const saved = localStorage.getItem("sarvam_dark_mode");
  if (saved === "1") {
    document.body.classList.add("dark");
    updateDarkModeBtn(true);
  }
}

function toggleDarkMode() {
  const isDark = document.body.classList.toggle("dark");
  updateDarkModeBtn(isDark);
  try {
    localStorage.setItem("sarvam_dark_mode", isDark ? "1" : "0");
  } catch (e) {
    console.warn("localStorage unavailable:", e);
  }
}

function updateDarkModeBtn(isDark) {
  const icon = document.getElementById("darkModeIcon");
  const label = document.getElementById("darkModeLabel");
  if (icon) icon.textContent = isDark ? "☀️" : "🌙";
  if (label) label.textContent = isDark ? "Light" : "Dark";
}

// ==========================================
// LANGUAGE COMING SOON TOAST
// ==========================================

let langToastTimer = null;

function showLangComingSoon() {
  const toast = document.getElementById("langToast");
  if (!toast) return;
  toast.style.display = "block";
  clearTimeout(langToastTimer);
  langToastTimer = setTimeout(() => {
    toast.style.display = "none";
  }, 3200);
}


// Check API Health
async function checkSystemHealth() {
  const badge = document.getElementById("systemStatus");
  try {
    const res = await fetch("/api/health");
    const data = await res.json();
    if (data.sarvam_configured && data.newsapi_configured) {
      badge.className = "status-badge connected";
      badge.innerHTML = '<span class="status-dot"></span> News Desk: Online';
    } else {
      badge.className = "status-badge warning";
      badge.innerHTML = '<span class="status-dot" style="background:#f59e0b;"></span> Missing API Keys';
    }
  } catch (e) {
    badge.className = "status-badge disconnected";
    badge.innerHTML = '<span class="status-dot" style="background:#ef4444;"></span> Server Offline';
  }
}

// Switch between Explorer and Ledger tabs
function switchTab(tabName) {
  const explorerTab = document.getElementById("explorerTab");
  const ledgerTab = document.getElementById("ledgerTab");
  const explorerBtn = document.getElementById("tabExplorerBtn");
  const ledgerBtn = document.getElementById("tabLedgerBtn");

  if (tabName === "explorer") {
    explorerTab.style.display = "block";
    ledgerTab.style.display = "none";
    explorerBtn.classList.add("active");
    ledgerBtn.classList.remove("active");
  } else {
    explorerTab.style.display = "none";
    ledgerTab.style.display = "block";
    ledgerBtn.classList.add("active");
    explorerBtn.classList.remove("active");
    loadLedgerRecords();
  }
}

// Quick scenario helper
function useQuery(text) {
  document.getElementById("textQueryInput").value = text;
  submitTextQuery();
}

// ==========================================
// VOICE RECORDING LOGIC (Web Audio / MediaRecorder)
// ==========================================

async function toggleRecording() {
  if (isRecording) {
    stopRecording();
  } else {
    startRecording();
  }
}

async function startRecording() {
  audioChunks = [];
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    
    // Setup AudioContext for waveform visualization
    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(stream);
    source.connect(analyser);
    analyser.fftSize = 64;

    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        audioChunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/wav" });
      stream.getTracks().forEach(track => track.stop());
      cancelAnimationFrame(animFrameId);
      if (audioContext && audioContext.state !== "closed") {
        audioContext.close();
      }
      processVoiceAudio(audioBlob);
    };

    mediaRecorder.start();
    isRecording = true;

    // UI Updates
    document.getElementById("recordBtn").classList.add("recording");
    const onAirTag = document.getElementById("micOnAirTag");
    if (onAirTag) {
      onAirTag.textContent = "🔴 LISTENING...";
      onAirTag.style.background = "#dc2626";
      onAirTag.style.color = "#ffffff";
    }
    document.getElementById("recordingStatus").textContent = "Listening... speak your question clearly";
    document.getElementById("recordingTimer").style.display = "block";
    document.getElementById("waveformCanvas").style.display = "block";
    
    recordStartTime = Date.now();
    timerInterval = setInterval(updateTimer, 1000);
    drawWaveform();

  } catch (err) {
    console.error("Microphone access error:", err);
    alert("Microphone access was denied or not supported. You can still type your question or upload an audio file.");
  }
}

function stopRecording() {
  if (!mediaRecorder || !isRecording) return;
  mediaRecorder.stop();
  isRecording = false;

  clearInterval(timerInterval);
  document.getElementById("recordBtn").classList.remove("recording");
  const onAirTag = document.getElementById("micOnAirTag");
  if (onAirTag) {
    onAirTag.textContent = "MIC READY";
    onAirTag.style.background = "#e2e8f0";
    onAirTag.style.color = "#64748b";
  }
  document.getElementById("recordingStatus").textContent = "Processing audio and searching news...";
  document.getElementById("recordingTimer").style.display = "none";
  document.getElementById("waveformCanvas").style.display = "none";
}

function updateTimer() {
  const elapsed = Math.floor((Date.now() - recordStartTime) / 1000);
  const mins = String(Math.floor(elapsed / 60)).padStart(2, '0');
  const secs = String(elapsed % 60).padStart(2, '0');
  document.getElementById("recordingTimer").textContent = `${mins}:${secs}`;
}

function drawWaveform() {
  if (!isRecording || !analyser) return;
  const canvas = document.getElementById("waveformCanvas");
  const ctx = canvas.getContext("2d");
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  
  analyser.getByteFrequencyData(dataArray);

  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const barWidth = (canvas.width / bufferLength) * 2;
  let x = 0;

  for (let i = 0; i < bufferLength; i++) {
    const barHeight = (dataArray[i] / 255) * canvas.height;
    ctx.fillStyle = `rgba(220, 38, 38, ${0.45 + (dataArray[i] / 255) * 0.55})`;
    ctx.fillRect(x, canvas.height - barHeight, barWidth - 1, barHeight);
    x += barWidth;
  }

  animFrameId = requestAnimationFrame(drawWaveform);
}

// Upload Pre-recorded Audio
function handleFileUpload(event) {
  const file = event.target.files[0];
  if (!file) return;
  document.getElementById("uploadedFileName").textContent = `Selected: ${file.name}`;
  processVoiceAudio(file);
}

// ==========================================
// API CLIENT & PROCESSING
// ==========================================

async function processVoiceAudio(blobOrFile) {
  showProcessingState("Transcribing your audio with Sarvam Saaras STT...");
  updateStepper("stepSTT");

  const formData = new FormData();
  formData.append("audio", blobOrFile, "question.wav");
  
  const selectedLang = document.getElementById("languageSelect").value;
  if (selectedLang) {
    formData.append("language_code", selectedLang);
  }

  try {
    const res = await fetch("/api/process-voice", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Error processing your voice question");
    }

    const data = await res.json();
    renderResponse(data);
    saveRecordLocally(data.ledger_entry);
    loadLedgerRecords();

  } catch (err) {
    alert(`Voice Query Error: ${err.message}`);
    hideProcessingState();
  }
}

async function submitTextQuery() {
  const input = document.getElementById("textQueryInput");
  const query = input.value.trim();
  if (!query) {
    alert("Please enter a question or topic to search.");
    return;
  }

  showProcessingState("Searching the news and preparing the ground report...");
  updateStepper("stepNews");

  const selectedLang = document.getElementById("languageSelect").value || "en-IN";

  try {
    const res = await fetch("/api/process-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: query,
        language_code: selectedLang
      })
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Error searching news");
    }

    const data = await res.json();
    renderResponse(data);
    saveRecordLocally(data.ledger_entry);
    loadLedgerRecords();

  } catch (err) {
    alert(`Search Error: ${err.message}`);
    hideProcessingState();
  }
}

function showProcessingState(text) {
  document.getElementById("processingCard").style.display = "flex";
  document.getElementById("responseSection").style.display = "none";
  document.getElementById("processingDetail").textContent = text;
}

function hideProcessingState() {
  document.getElementById("processingCard").style.display = "none";
}

function updateStepper(activeId) {
  ["stepSTT", "stepLLMAnalysis", "stepNews", "stepLLMAnswer", "stepTranslateNative", "stepTTS"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.remove("active");
  });
  const target = document.getElementById(activeId);
  if (target) target.classList.add("active");
}

// ==========================================
// RENDER RESPONSE & AUDIO
// ==========================================

function renderResponse(data) {
  hideProcessingState();
  document.getElementById("responseSection").style.display = "block";

  // Query Summary Banner
  document.getElementById("displayTranscript").textContent = data.transcript || "N/A";
  document.getElementById("langBadge").textContent = `Language: ${data.detected_language || 'en-IN'}`;
  document.getElementById("confidenceBadge").textContent = `Match: ${Math.round((data.confidence || 1) * 100)}%`;
  document.getElementById("durationBadge").textContent = `⚡ ${(data.duration_ms / 1000).toFixed(2)}s`;

  // Sarvam LLM Query Analysis Card
  const llmBox = document.getElementById("llmAnalysisBox");
  if (data.llm_analysis && data.llm_analysis.search_query) {
    llmBox.style.display = "block";
    document.getElementById("llmUserIntent").textContent = data.llm_analysis.user_intent || "General question";
    document.getElementById("llmSearchQuery").textContent = `"${data.llm_analysis.search_query}"`;
    const kwContainer = document.getElementById("llmKeywordsList");
    kwContainer.innerHTML = "";
    const kws = data.llm_analysis.keywords || [];
    if (kws.length > 0) {
      kws.forEach(kw => {
        const pill = document.createElement("span");
        pill.className = "kw-pill";
        pill.textContent = kw;
        kwContainer.appendChild(pill);
      });
    } else {
      kwContainer.innerHTML = '<span class="kw-pill">Key topics</span>';
    }
  } else {
    llmBox.style.display = "none";
  }

  // Translation Info Banner
  const transBox = document.getElementById("translationInfoBox");
  if (data.translation && data.translation.was_translated) {
    transBox.style.display = "block";
    document.getElementById("transOriginalQuery").textContent = `"${data.translation.original_query || ''}"`;
    document.getElementById("transNativeLang").textContent = `${data.detected_language} (via ${data.translation.translation_model || 'sarvam-translate:v1'})`;
    document.getElementById("translationModelBadge").textContent = data.translation.translation_model || "sarvam-translate:v1";
  } else {
    transBox.style.display = "none";
  }

  // Answer Status Pill
  const pill = document.getElementById("answerStatusPill");
  const pillIcon = document.getElementById("answerStatusIcon");
  const pillText = document.getElementById("answerStatusText");

  if (data.question_answered) {
    pill.className = "answer-status-pill";
    pillIcon.textContent = "✓";
    pillText.textContent = "Answer Found in the News";
  } else {
    pill.className = "answer-status-pill warning";
    pillIcon.textContent = "⚠️";
    pillText.textContent = "Limited News Coverage Found";
  }

  // Answer Body
  document.getElementById("answerText").textContent = data.answer || "No answer generated.";

  // Audio Playback
  const player = document.getElementById("ttsAudioPlayer");
  const downloadBtn = document.getElementById("downloadAudioBtn");
  const speakerInfo = document.getElementById("speakerInfo");

  const audioSrc = data.audio_base64 || data.audio_url;
  if (audioSrc) {
    player.src = audioSrc;
    downloadBtn.href = audioSrc;
    downloadBtn.style.display = "inline-flex";
    speakerInfo.textContent = `Anchor: ${data.speaker || 'Aditi (Sarvam Bulbul)'} • ${data.detected_language}`;

    const autoplay = document.getElementById("autoplayToggle").checked;
    if (autoplay) {
      player.play().catch(e => console.log("Autoplay prevented:", e));
    }
  } else {
    player.src = "";
    downloadBtn.style.display = "none";
    speakerInfo.textContent = "Voice audio unavailable.";
  }

  // Model Reasoning & Citations Details
  document.getElementById("modelReasoningText").textContent = data.reasoning || "Direct answer based on news articles found.";
  const citedList = document.getElementById("citedSourcesList");
  citedList.innerHTML = "";

  const citedArticles = data.cited_articles || [];
  if (citedArticles.length > 0) {
    citedArticles.forEach(art => {
      const li = document.createElement("li");
      li.innerHTML = `<strong>[Article ${art.index}]</strong> ${escapeHtml(art.title)} — <em>${escapeHtml(art.source)}</em> (<a href="${art.url}" target="_blank" rel="noopener">Read Article ↗</a>)`;
      citedList.appendChild(li);
    });
  } else {
    citedList.innerHTML = "<li>No specific articles cited directly.</li>";
  }

  // News Articles Grid
  const articles = data.news ? data.news.articles : [];
  document.getElementById("articlesCount").textContent = articles.length;
  document.getElementById("searchQueryUsed").textContent = `Search query: "${data.news ? data.news.query_used : ''}"`;

  const grid = document.getElementById("articlesGrid");
  grid.innerHTML = "";

  const citedIndices = new Set(data.cited_article_indices || []);

  if (articles.length === 0) {
    grid.innerHTML = '<p class="empty-state">No news articles found for this topic.</p>';
  } else {
    articles.forEach(art => {
      const isCited = citedIndices.has(art.index);
      const card = document.createElement("div");
      card.className = `article-card ${isCited ? 'cited' : ''}`;
      
      const pubDate = art.published_at ? new Date(art.published_at).toLocaleDateString() : '';

      card.innerHTML = `
        ${isCited ? '<span class="cited-badge">⭐ Used in Answer</span>' : ''}
        <div>
          <div class="article-source">[Source #${art.index}] ${escapeHtml(art.source)}</div>
          <h4 class="article-title">${escapeHtml(art.title)}</h4>
          <p class="article-snippet">${escapeHtml(art.description || art.content || '')}</p>
        </div>
        <div class="article-footer">
          <span class="article-date">${pubDate}</span>
          <a href="${art.url}" target="_blank" rel="noopener" class="article-link">Read full story ↗</a>
        </div>
      `;
      grid.appendChild(card);
    });
  }

  // Scroll smoothly to response
  document.getElementById("responseSection").scrollIntoView({ behavior: 'smooth' });
}

// ==========================================
// PROVENANCE LEDGER TAB LOGIC (The Papertrail)
// ==========================================

async function loadLedgerRecords() {
  try {
    const res = await fetch("/api/ledger");
    if (res.ok) {
      const data = await res.json();
      currentLedgerRecords = data.records || [];
    }
  } catch (err) {
    console.warn("Could not fetch server ledger, using local cache:", err);
  }

  // Merge with localStorage records
  const localRecords = getLocalRecords();
  const existingIds = new Set(currentLedgerRecords.map(r => r.id));
  localRecords.forEach(r => {
    if (!existingIds.has(r.id)) {
      currentLedgerRecords.push(r);
    }
  });

  // Sort newest first
  currentLedgerRecords.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  // Update badge
  document.getElementById("ledgerCountBadge").textContent = currentLedgerRecords.length;

  renderLedgerTable(currentLedgerRecords);
}

function renderLedgerTable(records) {
  const tbody = document.getElementById("ledgerTableBody");
  tbody.innerHTML = "";

  if (records.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="8" class="empty-state">No questions recorded yet. Ask a question above to start your history log.</td>
      </tr>
    `;
    return;
  }

  records.forEach(rec => {
    const tr = document.createElement("tr");
    const dateStr = new Date(rec.timestamp).toLocaleString();
    const isAnswered = rec.answer_synthesis?.question_answered;
    const citedCount = rec.answer_synthesis?.cited_articles?.length || rec.answer_synthesis?.cited_article_indices?.length || 0;
    const totalFound = rec.news_retrieval?.total_found || 0;
    const channelName = rec.input.type === 'voice' ? 'Voice' : 'Text';

    tr.innerHTML = `
      <td>${dateStr}</td>
      <td><span class="badge ${rec.input.type === 'voice' ? 'lang-badge' : 'time-badge'}">${channelName}</span></td>
      <td><strong>${escapeHtml(rec.input.transcript || '')}</strong></td>
      <td>${rec.input.detected_language}</td>
      <td>${totalFound}</td>
      <td>${citedCount}</td>
      <td>
        <span class="badge ${isAnswered ? 'conf-badge' : 'time-badge'}">
          ${isAnswered ? 'Answered' : 'Inconclusive'}
        </span>
      </td>
      <td>
        <button class="btn secondary-btn" style="padding:4px 10px; font-size:12px;" onclick="inspectLedgerRecord('${rec.id}')">View Details</button>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function inspectLedgerRecord(recordId) {
  const record = currentLedgerRecords.find(r => r.id === recordId);
  if (!record) return;

  currentModalRecord = record;
  document.getElementById("modalTitle").textContent = `Question Details: ${record.id}`;
  
  const llmAnalysis = record.llm_query_analysis;
  const llmAnalysisHtml = (llmAnalysis && llmAnalysis.search_query) ? `
    <div style="margin-top:8px; margin-bottom:8px; padding:10px 14px; background:#f0fdf4; border:1px solid #bbf7d0; border-radius:6px; font-size:12px;">
      <p><strong>🧠 AI Search Analysis:</strong> ${escapeHtml(llmAnalysis.user_intent || '')}</p>
      <p><strong>Search Query:</strong> "${escapeHtml(llmAnalysis.search_query)}"</p>
      <p><strong>Keywords:</strong> ${escapeHtml((llmAnalysis.keywords || []).join(', '))}</p>
    </div>
  ` : '';

  const trans = record.translation_audit;
  const transHtml = (trans && trans.was_translated) ? `
    <div style="margin-top:8px; margin-bottom:8px; padding:10px 14px; background:#eff6ff; border:1px solid #bfdbfe; border-radius:6px; font-size:12px;">
      <p><strong>🌐 Translation Details:</strong> Translated from <em>${trans.source_language}</em> to <em>English</em> (Model: ${trans.translation_model || 'sarvam-translate:v1'})</p>
      <p><strong>Original Question:</strong> "${escapeHtml(trans.original_query || '')}"</p>
      <p><strong>Related Terms:</strong> ${escapeHtml((trans.related_terms_used || []).join(', '))}</p>
    </div>
  ` : '';

  const summary = `
    <p><strong>Question:</strong> "${escapeHtml(record.input.transcript)}"</p>
    <p><strong>Language:</strong> ${record.input.detected_language} • <strong>Input Method:</strong> ${record.input.type === 'voice' ? 'Voice' : 'Text'}</p>
    ${llmAnalysisHtml}
    ${transHtml}
    <p><strong>News Search:</strong> "${escapeHtml(record.news_retrieval.query_used)}" (${record.news_retrieval.total_found} articles found)</p>
    <p><strong>Articles Cited:</strong> ${record.answer_synthesis.cited_article_indices.length > 0 ? record.answer_synthesis.cited_article_indices.map(i => '#' + i).join(', ') : 'None'}</p>
    <p><strong>Result:</strong> ${record.answer_synthesis.question_answered ? 'Answered' : 'Inconclusive'}</p>
  `;
  document.getElementById("modalSummary").innerHTML = summary;
  document.getElementById("modalJson").textContent = JSON.stringify(record, null, 2);

  document.getElementById("ledgerModal").style.display = "flex";
}

function closeModal(event) {
  document.getElementById("ledgerModal").style.display = "none";
}

function copyModalJson() {
  if (!currentModalRecord) return;
  navigator.clipboard.writeText(JSON.stringify(currentModalRecord, null, 2));
  alert("Technical log copied to clipboard!");
}

function exportLedgerJSON() {
  if (currentLedgerRecords.length === 0) {
    alert("Query history log is currently empty.");
    return;
  }
  const blob = new Blob([JSON.stringify(currentLedgerRecords, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `sarvam_news_history_${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

// Client-side Local Storage Backup (resilient on Serverless / Vercel restarts)
function saveRecordLocally(record) {
  if (!record) return;
  const records = getLocalRecords();
  records.unshift(record);
  if (records.length > 50) records.pop();
  try {
    localStorage.setItem("sarvam_news_ledger", JSON.stringify(records));
  } catch (e) {
    console.warn("localStorage quota exceeded:", e);
  }
}

function getLocalRecords() {
  try {
    const raw = localStorage.getItem("sarvam_news_ledger");
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function escapeHtml(str) {
  if (!str) return '';
  return str.replace(/[&<>"']/g, (m) => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#039;'
  }[m]));
}
