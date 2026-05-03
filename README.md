# Blind Navigation Demo

A web application for blind navigation using camera, voice commands, and sensor data.

## Project Structure

```
visualNavigator/
├── backend/          # FastAPI backend
│   ├── main.py       # API endpoints
│   ├── session.py    # Session storage
│   └── requirements.txt
├── frontend/         # Single-page web app
│   └── index.html
└── plans/            # Design documents
```

## Quick Start

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Backend runs on `http://localhost:8000`

### Frontend

Open `frontend/index.html` in Chrome, or serve it:

```bash
cd frontend
python3 -m http.server 3000
```

Then open `http://localhost:3000`

**Note**: For camera access on mobile, you need HTTPS. See [TESTING.md](TESTING.md) and [DEPLOYMENT.md](DEPLOYMENT.md) for options.

## Documentation

- [TESTING.md](TESTING.md) - Complete testing guide for local and mobile testing
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide with HTTPS
- [plans/plan2.md](plans/plan2.md) - Original development plan

## Development Status

- [x] Day 1: Frontend skeleton with camera + 2 buttons + sensors
- [x] Day 2: Backend core with /capture and /command endpoints
- [x] Day 3: API integration (Whisper, Vision LLM)
- [x] Day 4: Sensor integration in vision prompts
- [ ] Day 5: Deployment

## Features

- **Camera capture**: Take photos with rear camera
- **Voice commands**: Speak to set destination and ask for guidance
- **Sensor data**: Collects device orientation (gyroscope) and motion (accelerometer)
- **Phone angle detection**: Warns user if phone is tilted incorrectly (saves API costs)
- **Vision analysis**: Uses multimodal LLM to analyze scene and provide navigation instructions
- **Speech synthesis**: Reads instructions aloud using browser TTS
- **Session management**: Maintains context across multiple captures and commands

## API Keys Setup

The backend uses external APIs for speech and vision processing. Create a `.env` file in the `backend/` directory:

```bash
cd backend
cp .env.example .env
# Edit .env and add your API keys
```

**Minimal setup (recommended):**
- `SPEECH_TO_TEXT_API_KEY` - OpenAI API key for Whisper
- `GEMINI_API_KEY` - Google Gemini API key for vision
- `VISION_PROVIDER=gemini`

See [API_CONFIG.md](API_CONFIG.md) for detailed configuration options, including:
- Custom base URLs (国内中转 API)
- Different model selections
- Cost optimization tips

**Without API keys**, the system runs with mock responses for testing the flow.

## Testing Locally

1. Start backend: `cd backend && python main.py`
2. Open `frontend/index.html` in Chrome
3. Click "CAPTURE PHOTO" to initialize camera
4. Click "CAPTURE PHOTO" again to take a photo
5. Click "SPEAK" to start recording, click again to stop
6. Check browser console and backend logs for debug info

## API Endpoints

### POST /capture
- Receives: image (multipart), sensors (JSON string)
- Returns: `{"status": "ok", "spoken_text": "Photo captured!"}`
- Stores image + sensors in session

### POST /command
- Receives: audio (multipart), sensors (JSON string)
- Returns: `{"status": "ok", "spoken_text": "..."}`
- Transcribes voice, reasons about navigation, returns instruction

## Next Steps

See `plans/plan2.md` for the full development plan.
