// ── State ──────────────────────────────────────────────────────────────────
const state = {
  token: localStorage.getItem('token') || null,
  userEmail: localStorage.getItem('userEmail') || null,
  documents: [],
  currentDoc: null,
  flashcards: [],
  quiz: [],
  quizAnswers: {},
  quizSubmitted: false,
  currentCard: 0,
  activeTab: 'flashcards',
};

// ── API ────────────────────────────────────────────────────────────────────
const api = {
  base: '/api',

  headers() {
    const h = { 'Content-Type': 'application/json' };
    if (state.token) h['Authorization'] = `Bearer ${state.token}`;
    return h;
  },

  async request(method, path, body = null, isFile = false) {
    const opts = { method, headers: state.token ? { Authorization: `Bearer ${state.token}` } : {} };
    if (body && !isFile) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    } else if (isFile) {
      opts.body = body; // FormData
    }

    const res = await fetch(this.base + path, opts);
    if (res.status === 204) return null;

    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || `Error ${res.status}`);
    return data;
  },

  register: (email, password) => api.request('POST', '/auth/register', { email, password }),
  login:    (email, password) => api.request('POST', '/auth/login',    { email, password }),
  getDocs:  ()        => api.request('GET',    '/documents'),
  uploadDoc:(form)    => api.request('POST',   '/documents', form, true),
  deleteDoc:(id)      => api.request('DELETE', `/documents/${id}`),
  getDoc:   (id)      => api.request('GET',    `/documents/${id}`),
  generate: (id)      => api.request('POST',   `/documents/${id}/generate`),
  getFlashcards: (id) => api.request('GET',    `/documents/${id}/flashcards`),
  getQuiz:       (id) => api.request('GET',    `/documents/${id}/quiz`),
};

// ── Toast ──────────────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const el = document.createElement('div');
  el.className = `toast ${type === 'error' ? 'toast-error' : type === 'success' ? 'toast-success' : ''}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => el.remove(), 4000);
}

// ── Auth ───────────────────────────────────────────────────────────────────
function showAuth()    { document.getElementById('auth-page').classList.remove('hidden');  document.getElementById('main-app').classList.add('hidden'); }
function showApp()     { document.getElementById('auth-page').classList.add('hidden');     document.getElementById('main-app').classList.remove('hidden'); }
function showDashboard(){ document.getElementById('dashboard-view').classList.remove('hidden'); document.getElementById('doc-view').classList.add('hidden'); }
function showDocView() { document.getElementById('dashboard-view').classList.add('hidden'); document.getElementById('doc-view').classList.remove('hidden'); }

function saveSession(token, email) {
  state.token = token;
  state.userEmail = email;
  localStorage.setItem('token', token);
  localStorage.setItem('userEmail', email);
  document.getElementById('user-email-display').textContent = email;
}

function logout() {
  state.token = null;
  state.userEmail = null;
  localStorage.removeItem('token');
  localStorage.removeItem('userEmail');
  showAuth();
}

function setAuthTab(tab) {
  document.querySelectorAll('.auth-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
  document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
}

function setError(id, msg) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.className = 'msg msg-error show';
}
function clearMsg(id) { const el = document.getElementById(id); el.className = 'msg'; el.textContent = ''; }

async function handleLogin(e) {
  e.preventDefault();
  clearMsg('login-msg');
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const btn = document.getElementById('login-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Logging in…';
  try {
    const data = await api.login(email, password);
    saveSession(data.access_token, data.user_email);
    showApp();
    loadDashboard();
  } catch (err) {
    setError('login-msg', err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Log In';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  clearMsg('register-msg');
  const email = document.getElementById('reg-email').value.trim();
  const password = document.getElementById('reg-password').value;
  if (password.length < 8) { setError('register-msg', 'Password must be at least 8 characters.'); return; }
  const btn = document.getElementById('register-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner"></span> Creating account…';
  try {
    const data = await api.register(email, password);
    saveSession(data.access_token, data.user_email);
    showApp();
    loadDashboard();
    toast('Welcome! Your account is ready.', 'success');
  } catch (err) {
    setError('register-msg', err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = 'Create Account';
  }
}

// ── Dashboard ──────────────────────────────────────────────────────────────
async function loadDashboard() {
  showDashboard();
  const grid = document.getElementById('doc-grid');
  grid.innerHTML = '<div class="empty-state"><div class="empty-icon">⏳</div><p>Loading your documents…</p></div>';
  try {
    state.documents = await api.getDocs();
    renderDocGrid();
  } catch (err) {
    grid.innerHTML = `<div class="empty-state"><div class="empty-icon">⚠️</div><p>${err.message}</p></div>`;
  }
}

function renderDocGrid() {
  const grid = document.getElementById('doc-grid');
  if (!state.documents.length) {
    grid.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">📚</div>
        <p>No documents yet.<br>Upload a PDF or text file to get started.</p>
      </div>`;
    return;
  }

  grid.innerHTML = state.documents.map(doc => {
    const date = new Date(doc.upload_timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    const fcBadge = doc.flashcard_count > 0
      ? `<span class="badge badge-purple">✦ ${doc.flashcard_count} flashcards</span>` : '';
    const qBadge = doc.quiz_question_count > 0
      ? `<span class="badge badge-cyan">? ${doc.quiz_question_count} quiz Qs</span>` : '';
    const newBadge = !doc.flashcard_count && !doc.quiz_question_count
      ? `<span class="badge badge-gray">Not generated</span>` : '';
    return `
      <div class="doc-card" id="doc-card-${doc.id}">
        <span class="doc-icon">${doc.filename.endsWith('.pdf') ? '📄' : '📝'}</span>
        <div class="doc-info" onclick="openDoc(${doc.id})">
          <div class="doc-name">${escHtml(doc.filename)}</div>
          <div class="doc-meta">Uploaded ${date}</div>
          <div class="doc-badges">${fcBadge}${qBadge}${newBadge}</div>
        </div>
        <div class="doc-actions">
          <button class="btn btn-sm btn-secondary" onclick="openDoc(${doc.id})">Open</button>
          <button class="btn btn-sm btn-danger btn-icon" onclick="deleteDoc(event,${doc.id})" title="Delete">🗑</button>
        </div>
      </div>`;
  }).join('');
}

async function deleteDoc(e, id) {
  e.stopPropagation();
  if (!confirm('Delete this document and all its flashcards and quiz questions?')) return;
  try {
    await api.deleteDoc(id);
    state.documents = state.documents.filter(d => d.id !== id);
    renderDocGrid();
    toast('Document deleted.', 'success');
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ── Upload ─────────────────────────────────────────────────────────────────
function setupUpload() {
  const zone = document.getElementById('upload-zone');
  const input = document.getElementById('file-input');

  zone.addEventListener('click', () => input.click());
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (file) uploadFile(file);
  });
  input.addEventListener('change', () => { if (input.files[0]) uploadFile(input.files[0]); });
}

async function uploadFile(file) {
  const ext = file.name.split('.').pop().toLowerCase();
  if (!['pdf', 'txt'].includes(ext)) { toast('Only .pdf and .txt files are supported.', 'error'); return; }

  const zone = document.getElementById('upload-zone');
  zone.innerHTML = '<span class="spinner"></span> Uploading and extracting text…';
  zone.style.pointerEvents = 'none';

  const form = new FormData();
  form.append('file', file);

  try {
    const doc = await api.uploadDoc(form);
    state.documents.unshift(doc);
    renderDocGrid();
    toast(`"${file.name}" uploaded successfully.`, 'success');
    openDoc(doc.id);
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    zone.style.pointerEvents = '';
    zone.innerHTML = `
      <span class="upload-icon">☁️</span>
      <p><strong>Click to upload</strong> or drag and drop</p>
      <p>PDF or TXT · Max 20 MB</p>`;
  }
}

// ── Document View ──────────────────────────────────────────────────────────
async function openDoc(id) {
  showDocView();
  document.getElementById('doc-view').innerHTML = `
    <div class="empty-state" style="margin-top:4rem">
      <div class="empty-icon">⏳</div><p>Loading document…</p>
    </div>`;

  try {
    const doc = await api.getDoc(id);
    state.currentDoc = doc;
    state.flashcards = doc.flashcards || [];
    state.quiz = doc.quiz_questions || [];
    state.currentCard = 0;
    state.quizAnswers = {};
    state.quizSubmitted = false;
    renderDocView();
  } catch (err) {
    toast(err.message, 'error');
    loadDashboard();
  }
}

function renderDocView() {
  const doc = state.currentDoc;
  document.getElementById('doc-view').innerHTML = `
    <div class="doc-detail-header">
      <button class="btn btn-secondary btn-sm" onclick="loadDashboard()">← Back</button>
      <div class="doc-detail-title">${escHtml(doc.filename)}</div>
    </div>

    <div class="generate-bar">
      <div>
        <strong>AI Generation</strong>
        <p>${state.flashcards.length ? `${state.flashcards.length} flashcards · ${state.quiz.length} quiz questions generated` : 'No content generated yet. Click Generate to create flashcards and a quiz.'}</p>
      </div>
      <button class="btn btn-generate" id="gen-btn" onclick="generateContent(${doc.id})">
        ${state.flashcards.length ? '🔄 Regenerate' : '✨ Generate Study Material'}
      </button>
    </div>

    ${state.flashcards.length || state.quiz.length ? `
    <div class="content-tabs">
      <button class="content-tab ${state.activeTab === 'flashcards' ? 'active' : ''}" onclick="switchTab('flashcards')">
        ✦ Flashcards (${state.flashcards.length})
      </button>
      <button class="content-tab ${state.activeTab === 'quiz' ? 'active' : ''}" onclick="switchTab('quiz')">
        ? Quiz (${state.quiz.length})
      </button>
    </div>
    <div id="tab-content"></div>
    ` : ''}
  `;

  if (state.flashcards.length || state.quiz.length) renderTabContent();
}

function switchTab(tab) {
  state.activeTab = tab;
  document.querySelectorAll('.content-tab').forEach(t => {
    t.classList.toggle('active', t.textContent.toLowerCase().includes(tab.substring(0,4)));
  });
  renderTabContent();
}

function renderTabContent() {
  const el = document.getElementById('tab-content');
  if (!el) return;
  if (state.activeTab === 'flashcards') renderFlashcards(el);
  else renderQuiz(el);
}

// ── Flashcards ─────────────────────────────────────────────────────────────
function renderFlashcards(container) {
  if (!state.flashcards.length) { container.innerHTML = '<div class="empty-state"><p>No flashcards yet.</p></div>'; return; }
  const i = state.currentCard;
  const card = state.flashcards[i];
  container.innerHTML = `
    <div class="flashcard-container">
      <div class="flashcard-counter">Card ${i + 1} of ${state.flashcards.length}</div>
      <div class="flashcard-scene" onclick="flipCard()">
        <div class="flashcard" id="fc-card">
          <div class="flashcard-face flashcard-front">
            <div class="flashcard-label">Question</div>
            <div class="flashcard-text">${escHtml(card.front)}</div>
            <div class="flashcard-hint">Click to reveal answer</div>
          </div>
          <div class="flashcard-face flashcard-back">
            <div class="flashcard-label">Answer</div>
            <div class="flashcard-text">${escHtml(card.back)}</div>
            <div class="flashcard-hint">Click to flip back</div>
          </div>
        </div>
      </div>
      <div class="flashcard-nav">
        <button class="btn btn-secondary" onclick="prevCard()" ${i === 0 ? 'disabled' : ''}>← Prev</button>
        <button class="btn btn-secondary" onclick="nextCard()" ${i === state.flashcards.length - 1 ? 'disabled' : ''}>Next →</button>
      </div>
    </div>`;
}

function flipCard() { document.getElementById('fc-card')?.classList.toggle('flipped'); }

function nextCard() {
  if (state.currentCard < state.flashcards.length - 1) {
    state.currentCard++;
    renderTabContent();
  }
}

function prevCard() {
  if (state.currentCard > 0) {
    state.currentCard--;
    renderTabContent();
  }
}

// ── Quiz ───────────────────────────────────────────────────────────────────
function renderQuiz(container) {
  if (!state.quiz.length) { container.innerHTML = '<div class="empty-state"><p>No quiz questions yet.</p></div>'; return; }

  const letters = ['A','B','C','D'];
  const optKeys = ['option_a','option_b','option_c','option_d'];

  let scoreHtml = '';
  if (state.quizSubmitted) {
    const correct = state.quiz.filter((q,i) => state.quizAnswers[i] === q.correct_answer_index).length;
    const pct = Math.round((correct / state.quiz.length) * 100);
    scoreHtml = `
      <div class="quiz-score-card">
        <div class="score-big">${pct}%</div>
        <div class="score-label">You got ${correct} of ${state.quiz.length} correct</div>
        <button class="btn btn-secondary" style="margin-top:1rem" onclick="resetQuiz()">Retake Quiz</button>
      </div>`;
  }

  const questionsHtml = state.quiz.map((q, qi) => {
    const opts = optKeys.map((k,oi) => {
      let cls = 'quiz-option';
      if (state.quizSubmitted) {
        cls += ' disabled';
        if (oi === q.correct_answer_index) cls += ' correct';
        else if (state.quizAnswers[qi] === oi) cls += ' incorrect';
      } else if (state.quizAnswers[qi] === oi) {
        cls += ' selected';
      }
      return `<div class="${cls}" onclick="selectAnswer(${qi},${oi})">
        <span class="option-letter">${letters[oi]}</span>
        <span>${escHtml(q[k])}</span>
      </div>`;
    }).join('');

    return `<div class="quiz-question-card">
      <div class="quiz-q-num">Question ${qi + 1}</div>
      <div class="quiz-q-text">${escHtml(q.question)}</div>
      <div class="quiz-options">${opts}</div>
    </div>`;
  }).join('');

  const allAnswered = state.quiz.every((_,i) => state.quizAnswers[i] !== undefined);
  const submitHtml = !state.quizSubmitted ? `
    <div class="quiz-submit-bar">
      <button class="btn btn-primary" style="max-width:200px" onclick="submitQuiz()" ${!allAnswered ? 'disabled' : ''}>
        Submit Quiz
      </button>
    </div>` : '';

  container.innerHTML = `
    <div class="quiz-container">
      ${scoreHtml}
      ${questionsHtml}
      ${submitHtml}
    </div>`;
}

function selectAnswer(qi, oi) {
  if (state.quizSubmitted) return;
  state.quizAnswers[qi] = oi;
  renderTabContent();
}

function submitQuiz() {
  state.quizSubmitted = true;
  renderTabContent();
}

function resetQuiz() {
  state.quizAnswers = {};
  state.quizSubmitted = false;
  renderTabContent();
}

// ── Generate ───────────────────────────────────────────────────────────────
async function generateContent(docId) {
  const overlay = document.getElementById('generating-overlay');
  overlay.classList.remove('hidden');

  try {
    const data = await api.generate(docId);
    state.flashcards = data.flashcards;
    state.quiz = data.quiz_questions;
    state.currentCard = 0;
    state.quizAnswers = {};
    state.quizSubmitted = false;
    state.activeTab = 'flashcards';

    // Update doc list counts
    const docInList = state.documents.find(d => d.id === docId);
    if (docInList) {
      docInList.flashcard_count = data.flashcards.length;
      docInList.quiz_question_count = data.quiz_questions.length;
    }

    renderDocView();
    toast('Study material generated!', 'success');
  } catch (err) {
    toast(err.message, 'error');
  } finally {
    overlay.classList.add('hidden');
  }
}

// ── Utils ──────────────────────────────────────────────────────────────────
function escHtml(str) {
  return String(str)
    .replace(/&/g,'&amp;')
    .replace(/</g,'&lt;')
    .replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;');
}

// ── Init ───────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Auth tab switching
  document.querySelectorAll('.auth-tab').forEach(t =>
    t.addEventListener('click', () => setAuthTab(t.dataset.tab))
  );

  // Auth forms
  document.getElementById('login-form').addEventListener('submit', handleLogin);
  document.getElementById('register-form').addEventListener('submit', handleRegister);

  // Logout
  document.getElementById('logout-btn').addEventListener('click', logout);

  // Brand click → dashboard
  document.getElementById('brand-btn').addEventListener('click', loadDashboard);

  // Upload
  setupUpload();

  // Check session
  if (state.token) {
    showApp();
    document.getElementById('user-email-display').textContent = state.userEmail || '';
    loadDashboard();
  } else {
    showAuth();
  }
});
