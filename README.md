# 🧠 AI Study Assistant

> **Live URL:** `https://your-app-name.onrender.com` ← update after deployment

Upload lecture notes or textbook chapters (PDF or TXT) and receive AI-generated flashcards and quiz questions — all from a secure, multi-user web application.

---

## Features

- **User auth** — Register, login, JWT access tokens (24hr expiry), bcrypt password hashing
- **Document upload** — PDF and plain text, text extracted and stored in SQLite
- **AI generation** — ≥5 flashcards + 5 multiple-choice quiz questions per document via OpenRouter LLM
- **Flashcard viewer** — 3D flip animation, navigate through cards
- **Quiz** — Select answers, submit, see score and correct answers highlighted
- **Data isolation** — Users can only access their own documents and generated content

---

## Local Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/your-username/ai-study-assistant.git
cd ai-study-assistant
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in:
#   OPENROUTER_API_KEY — from https://openrouter.ai
#   JWT_SECRET_KEY     — any long random string (openssl rand -hex 32)
```

### 3. Run the development server

```bash
uvicorn backend.main:app --reload
```

Open **http://localhost:8000** in your browser.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | ✅ | Get free at https://openrouter.ai |
| `JWT_SECRET_KEY` | ✅ | Any long random string — keep it secret |
| `JWT_EXPIRE_HOURS` | Optional | Token expiry in hours (default: 24) |
| `DATABASE_URL` | Optional | SQLite path (default: `sqlite:///./study_assistant.db`) |

See `.env.example` for a template.

---

## Deploying to Render

1. Push this repo to GitHub (public)
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click **Apply**
5. In **Environment**, add:
   - `OPENROUTER_API_KEY` → your key
   - `JWT_SECRET_KEY` → a random secret (`openssl rand -hex 32`)
6. Click **Deploy**

Your app will be live at `https://your-service-name.onrender.com`.

---

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI app + static file serving
│   ├── database.py      # SQLAlchemy engine + session
│   ├── models.py        # ORM models (User, Document, Flashcard, QuizQuestion)
│   ├── schemas.py       # Pydantic request/response schemas
│   ├── auth.py          # JWT + bcrypt utilities + get_current_user
│   ├── llm.py           # OpenRouter API integration
│   └── routers/
│       ├── auth.py      # /api/auth/register, /api/auth/login
│       ├── documents.py # /api/documents (CRUD)
│       └── generation.py# /api/documents/{id}/generate
├── frontend/
│   ├── index.html       # Single-page app
│   ├── style.css        # Premium dark-mode design
│   └── app.js           # Vanilla JS SPA logic
├── requirements.txt
├── render.yaml
├── .env.example
└── README.md
```

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/register` | ❌ | Register new user |
| POST | `/api/auth/login` | ❌ | Login, receive JWT |
| GET | `/api/documents` | ✅ | List user's documents |
| POST | `/api/documents` | ✅ | Upload PDF/TXT |
| GET | `/api/documents/{id}` | ✅ | Get document detail |
| DELETE | `/api/documents/{id}` | ✅ | Delete document + cascade |
| POST | `/api/documents/{id}/generate` | ✅ | Generate flashcards + quiz |
| GET | `/api/documents/{id}/flashcards` | ✅ | Get saved flashcards |
| GET | `/api/documents/{id}/quiz` | ✅ | Get saved quiz questions |

---

## LLM Model

Pinned model: `mistralai/mistral-7b-instruct:free` via OpenRouter  
The prompt instructs the model to return **strict JSON only** — parsed and validated before being stored in the database.

---

## Security Notes

- Passwords are hashed with bcrypt — never stored in plain text
- JWT tokens expire after 24 hours (configurable)
- All document/generation endpoints return `401 Unauthorized` with no valid token
- Database queries are scoped to `current_user.id` — users cannot access each other's data
