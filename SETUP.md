# Verique Setup Guide

## Prerequisites
- Python 3.11+
- Node.js 18+
- Chrome/Edge browser (for extension)

## Quick Start

### 1. Backend Setup

```powershell
cd backend

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install dependencies (if not already done)
pip install -r requirements.txt

# Get FREE Groq API Key
# Visit: https://console.groq.com/keys
# Create account and generate API key

# Edit .env file and add your key
# GROQ_API_KEY=gsk_your_key_here

# Start backend server
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**Backend will run on:** http://127.0.0.1:8000

### 2. Frontend Setup

```powershell
cd frontend

# Install dependencies (if needed)
npm install

# Start frontend
npm run dev
```

**Frontend will run on:** http://localhost:3000 (or 3001 if 3000 is busy)

### 3. Browser Extension Setup

1. Open Chrome/Edge
2. Go to `chrome://extensions/` or `edge://extensions/`
3. Enable "Developer mode" (toggle in top right)
4. Click "Load unpacked"
5. Select the `extension` folder from this project
6. Pin the extension to your toolbar

**Usage:**
- Click the extension icon to open popup
- Right-click any text → "Verify with Verique"
- Use keyboard shortcut: `Alt+Shift+V`

## Important Notes

### GROQ API Key (Required!)
The backend **REQUIRES** a Groq API key to work properly. Without it:
- All verifications will return empty results
- Page scores will always be neutral (50)
- No actual AI analysis will happen

**Get your FREE key here:** https://console.groq.com/keys

Add it to `backend/.env`:
```env
GROQ_API_KEY=gsk_your_actual_key_here
```

Then restart the backend server.

### Database
The app uses SQLite by default (no Docker needed). Database file: `backend/trustlens.db`

To use PostgreSQL with Docker (optional):
```powershell
docker compose up -d postgres redis
```

Then update `backend/.env`:
```env
DATABASE_URL=postgresql://trustlens:trustlens@localhost:5432/trustlens
```

## Testing

### Test Backend
Visit: http://127.0.0.1:8000/docs

Try the `/v1/verify` endpoint with sample text.

### Test Frontend
Open: http://localhost:3000

Paste some text with factual claims (e.g., from a news article) and click "Verify".

### Test Extension
1. Load extension in browser
2. Visit any webpage
3. Right-click text → "Verify with Verique"
4. Or click extension icon and paste text

## Troubleshooting

### "Same safe score" issue
**Cause:** No GROQ_API_KEY configured
**Fix:** Add your Groq API key to `backend/.env` and restart backend

### Extension shows 404 error
**Cause:** Backend not running or wrong URL
**Fix:** 
1. Ensure backend is running on port 8000
2. Check extension `background.js` has `API_BASE = 'http://127.0.0.1:8000'`

### Frontend shows 404
**Cause:** API endpoint mismatch
**Fix:** Endpoints should be `/v1/verify` (not `/api/v1/verify`)

## Architecture

```
┌─────────────────┐
│   Browser       │
│   Extension     │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
    ┌────▼─────┐     ┌────▼─────┐
    │ Frontend │     │ Backend  │
    │ Next.js  │────▶│ FastAPI  │
    │ :3000    │     │ :8000    │
    └──────────┘     └────┬─────┘
                          │
                     ┌────▼─────┐
                     │ Groq LLM │
                     │ (FREE)   │
                     └──────────┘
```

## Next Steps

1. ✅ Get Groq API key
2. ✅ Add to `.env` file
3. ✅ Restart backend
4. ✅ Test verification with real content
5. ✅ Load extension in browser
6. ✅ Start verifying web content!
