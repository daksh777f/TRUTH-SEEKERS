# How to Load the Browser Extension

## Chrome / Edge / Brave

1. **Open Extensions Page**
   - Chrome: Go to `chrome://extensions/`
   - Edge: Go to `edge://extensions/`
   - Brave: Go to `brave://extensions/`

2. **Enable Developer Mode**
   - Look for "Developer mode" toggle in the top-right corner
   - Turn it **ON**

3. **Load the Extension**
   - Click the "Load unpacked" button
   - Navigate to your project folder
   - Select the `extension` folder
   - Click "Select Folder"

4. **Pin the Extension**
   - Click the puzzle icon (🧩) in your browser toolbar
   - Find "Verique - AI Content Verifier"
   - Click the pin icon to keep it visible

## Usage

### Method 1: Right-Click Menu
1. Select any text on a webpage
2. Right-click → "Verify with Verique"
3. Results will appear in a sidebar

### Method 2: Extension Popup
1. Click the Verique icon in toolbar
2. Paste or type content
3. Click "Verify"

### Method 3: Keyboard Shortcut
1. Select text on any page
2. Press `Alt + Shift + V`
3. Verification starts automatically

## Important Prerequisites

**Make sure the backend is running!**

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**And you have a Groq API key configured in `backend/.env`:**
```env
GROQ_API_KEY=gsk_your_key_here
```

Without the backend running or API key configured, the extension won't work!

## Troubleshooting

### Extension not appearing after loading
- Make sure you selected the `extension` folder (not the root project folder)
- Check browser console for errors (F12 → Console tab)

### "Connection failed" error
- Ensure backend is running on port 8000
- Visit http://127.0.0.1:8000/health to test

### Verification returns empty results
- Check that `GROQ_API_KEY` is set in `backend/.env`
- Restart the backend server after adding the key

### Extension icon grayed out
- Try refreshing the webpage
- Check that you're on a regular webpage (extensions don't work on browser settings pages)
