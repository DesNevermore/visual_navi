# Testing Guide

## Local Testing (without deployment)

### 1. Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Optional: Add API keys for real testing
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and GEMINI_API_KEY

# Start backend
python main.py
```

Backend runs on `http://localhost:8000`

### 2. Frontend Testing

**Option A: Direct file access (Chrome only, localhost)**
```bash
# Open frontend/index.html directly in Chrome
open frontend/index.html  # macOS
# or just drag the file into Chrome
```

**Option B: Local server (recommended)**
```bash
cd frontend
python3 -m http.server 3000
# Open http://localhost:3000 in browser
```

### 3. Testing Flow

#### Step 1: Initialize
1. Open the frontend in Chrome
2. Click **CAPTURE PHOTO** button
3. Grant camera and microphone permissions
4. Wait for "Ready" message

#### Step 2: Set Destination
1. Click **SPEAK** button
2. Say: "Go to the podium" (or any destination)
3. Click **SPEAK** again to stop recording
4. Listen for confirmation: "Destination set to podium..."

#### Step 3: Navigate
1. Point camera at the scene
2. Click **CAPTURE PHOTO** to take a picture
3. Click **SPEAK** to ask for guidance
4. Say: "Where should I go?" or just make any sound
5. Click **SPEAK** again to stop
6. Listen for navigation instruction

#### Step 4: Test Phone Angles
1. Tilt phone down (looking at floor)
2. Click **CAPTURE PHOTO**
3. Click **SPEAK** twice to ask for guidance
4. Should hear: "Raise your phone to chest level..."

5. Tilt phone sideways
6. Repeat capture and speak
7. Should hear: "Hold your phone upright..."

### 4. Testing with Mock Responses (No API Keys)

Without API keys, the system uses mock responses:
- Transcription: always returns "go to the podium"
- Vision: returns generic navigation instructions
- This is perfect for testing the UI flow and sensor integration

### 5. Testing with Real APIs

Add API keys to `backend/.env`:

```bash
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
VISION_PROVIDER=gemini
```

Restart backend, then:
1. Record real voice commands
2. System will transcribe actual speech
3. Vision LLM will analyze real camera images
4. Get context-aware navigation instructions

### 6. Debug Information

Check the debug log (3 lines below camera preview):
- Line 1: Capture count
- Line 2: Last upload type (image/audio + sensors)
- Line 3: Current state (boot/ready/recording/busy)

Backend logs show:
```
[CAPTURE] Session xxx: stored image #N
[COMMAND] Session xxx: received audio
[COMMAND] Transcription: ...
```

### 7. Common Issues

**Camera not working:**
- Check browser console for errors
- Ensure you're on HTTPS or localhost
- Try Chrome instead of Safari
- Check camera permissions in browser settings

**Microphone not working:**
- Grant microphone permission when prompted
- Check browser console for errors
- Ensure no other app is using the microphone

**Backend connection failed:**
- Check backend is running: `curl http://localhost:8000/`
- Check CORS errors in browser console
- Ensure frontend is accessing `http://localhost:8000` (check index.html line 88)

**Speech not playing:**
- Check browser console for speechSynthesis errors
- Try clicking the page first (some browsers require user interaction)
- Check system volume

## Mobile Testing (Android Chrome)

### Option 1: Chrome Insecure Origin Flag (Your Phone Only)

1. On Android phone, open Chrome
2. Go to: `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
3. Enable it
4. Add: `http://YOUR_COMPUTER_IP:8000`
5. Restart Chrome
6. Update `frontend/index.html` line 88:
   ```javascript
   const BACKEND_URL = 'http://YOUR_COMPUTER_IP:8000';
   ```
7. Serve frontend: `cd frontend && python3 -m http.server 3000`
8. On phone, visit: `http://YOUR_COMPUTER_IP:3000`

### Option 2: Cloudflare Tunnel (Free HTTPS)

1. Install cloudflared:
   ```bash
   brew install cloudflared  # macOS
   # or download from https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation/
   ```

2. Start tunnel:
   ```bash
   cd backend
   cloudflared tunnel --url http://localhost:8000
   ```

3. Copy the `https://xxx.trycloudflare.com` URL

4. Update `frontend/index.html` line 88:
   ```javascript
   const BACKEND_URL = 'https://xxx.trycloudflare.com';
   ```

5. Serve frontend with another tunnel:
   ```bash
   cd frontend
   python3 -m http.server 3000 &
   cloudflared tunnel --url http://localhost:3000
   ```

6. Open the frontend tunnel URL on your phone

## iOS Testing

**iOS requires HTTPS** - use Cloudflare Tunnel (Option 2 above) or deploy with a domain.

The Chrome insecure origin flag does NOT work on iOS.

## Automated Testing

```bash
# Test backend endpoints
cd backend

# Health check
curl http://localhost:8000/

# Test capture
curl -X POST http://localhost:8000/capture \
  -F "image=@test_image.jpg" \
  -F 'sensors={"orientation":{"alpha":45,"beta":10,"gamma":0}}'

# Test command
curl -X POST http://localhost:8000/command \
  -F "audio=@test_audio.webm" \
  -F 'sensors={"orientation":{"alpha":45,"beta":10,"gamma":0}}'
```

## Performance Testing

Monitor backend logs for timing:
- Image upload: should be < 1s
- Transcription: 1-3s (with API) or instant (mock)
- Vision analysis: 2-5s (with API) or instant (mock)
- Total round-trip: 3-8s

## Next Steps

Once local testing is complete, see `plans/plan2.md` §6 for deployment options.
