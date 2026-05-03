# Blind Navigation Demo — Simplified Plan (plan2)

> **Goal**: A minimal web app for navigating from any point in a classroom to the podium while blindfolded. User speaks the destination, captures photos with sensor data, and receives spoken navigation instructions.

---

## 1. System Overview

```
┌─────────── iPhone Chrome ───────────┐
│  • Camera preview (debug only)      │
│  • Two buttons: CAPTURE | SPEAK     │
│  • Collects: image + gyro + accel   │
└──────────────┬──────────────────────┘
               │ HTTPS
               ▼
┌─────────── Backend (FastAPI) ───────┐
│  /capture  → store image + sensors  │
│  /command  → transcribe voice       │
│            → call vision LLM        │
│            → generate instruction   │
│            → call TTS               │
└──────────────┬──────────────────────┘
               │
               ▼
         Vision LLM + TTS APIs
```

**No Redis, no database, no GPS routing, no complex dependencies.** Session state lives in-memory (or SQLite if you need persistence across restarts).

---

## 2. Core Rules

1. **Two separate endpoints**:
   - `/capture` — receives image + sensors, stores them, returns "Photo captured!"
   - `/command` — receives voice + sensors, transcribes, reasons, returns spoken instruction + audio

2. **Frontend never does reasoning** — no destination parsing, no obstacle detection, no navigation logic

3. **Backend owns all intelligence** — transcription, vision analysis, instruction generation, safety checks

4. **Simple scope** — classroom to podium only; no campus-wide routing

---

## 3. Frontend Design

### 3.1 Mobile Layout (Portrait)

```text
+------------------------------------------------+
|                                                |
|              CAMERA PREVIEW                    |
|              developer debug only              |
|                                                |
|              height: 40vh                      |
|                                                |
+------------------------------------------------+
| Debug log, 3 lines only                        |
| Capture: 3                                     |
| Last upload: image + sensors                   |
| State: ready                                   |
|              height: 10vh                      |
+------------------------------------------------+
|                      |                         |
|          BUTTON      | BUTTON                  |
|                      |                         |
|        CAPTURE PHOTO | SPEAK                   |
|        Once: capture | Once: start recording   |
|                      | Again: stop & send      |
|         height: 50vh | height: 50vh            |
|                      |                         |
+------------------------------------------------+
```

### 3.2 Button Behaviors

**CAPTURE PHOTO button**:
- Tap once → capture image + read sensors → upload to `/capture`
- On success → speak "Photo captured!" via `speechSynthesis`

**SPEAK button**:
- First tap → start recording → speak "Recording started!"
- Second tap → stop recording → upload audio + sensors to `/command` → speak "Recording stopped!"
- Backend returns spoken instruction → play via `speechSynthesis` or returned audio

### 3.3 Sensors to Collect

Capture on every photo/voice upload:

```json
{
  "orientation": {
    "alpha": 45.2,    // compass heading (0–360°)
    "beta": 10.5,     // front-back tilt (-180 to 180°)
    "gamma": -5.3     // left-right tilt (-90 to 90°)
  },
  "motion": {
    "acceleration": {"x": 0.1, "y": 0.05, "z": 9.8},
    "rotationRate": {"alpha": 0, "beta": 0, "gamma": 0}
  },
  "screen": {
    "orientation": "portrait-primary",
    "angle": 0
  }
}
```

**No GPS needed** — classroom navigation relies on vision + sensors, not geolocation.

On iOS 13+, request `DeviceOrientationEvent.requestPermission()` on first user interaction.

---

## 4. Backend Design

### 4.1 Tech Stack

- **Python + FastAPI** (or Node + Express)
- **In-memory session dict** (or SQLite if you want persistence)
- **Vision API**: Gemini 2.5 Flash / GPT-4o-mini / Qwen-VL
- **Speech-to-text**: OpenAI Whisper API / Google Speech-to-Text
- **Text-to-speech**: Return text for browser `speechSynthesis` (free), or OpenAI TTS / Google TTS (paid)

### 4.2 Endpoints

#### POST `/capture`

**Request**:
```
multipart/form-data:
  - image: file
  - sensors: JSON string
```

**Action**:
1. Save image to session memory (keep last 3–5 frames)
2. Store sensor snapshot
3. Return `{"status": "ok", "spoken_text": "Photo captured!"}`

**Never returns navigation instructions.**

#### POST `/command`

**Request**:
```
multipart/form-data:
  - audio: file (webm/ogg/wav)
  - sensors: JSON string
```

**Action**:
1. Transcribe audio via Whisper API
2. Classify intent:
   - Setting destination? → confirm and store
   - Asking for guidance? → call vision LLM with latest image + sensors
   - Asking "where am I?" → describe environment
3. Generate spoken response
4. Return `{"spoken_text": "...", "audio_base64": null}`

Frontend plays `spoken_text` via `speechSynthesis`.

### 4.3 Session State (In-Memory)

```python
sessions = {
    "session_id": {
        "destination": "podium",
        "images": [<last 3 images>],
        "sensors": [<last 3 sensor snapshots>],
        "last_instruction": "Move forward 2 meters"
    }
}
```

Use a simple dict keyed by session ID (generated on first `/capture` or `/command`). No Redis, no database required for MVP. If you need persistence, use SQLite with one table.

### 4.4 Vision LLM Prompt Template

```text
You are a navigation assistant for a blind user in a classroom.

Destination: {destination}
Last instruction: {last_instruction}

The user is holding a phone. Attached is the camera view and sensor data:
- Orientation: alpha={alpha}°, beta={beta}°, gamma={gamma}°
- Motion: acceleration={acc}, rotation={rot}

Based on the image and sensors:
1. If the phone is tilted down (beta < -30°), say: "Raise your phone to chest level"
2. If the image is blurry or dark, say: "Image unclear, please capture again"
3. If you see the destination, estimate distance and direction
4. If there's an obstacle, say: "Stop. Obstacle ahead."
5. Otherwise, give a short movement instruction (≤ 20 words)

Return JSON only:
{
  "instruction": "Move forward 3 steps",
  "arrived": false,
  "needs_recapture": false
}
```

Keep instructions **short and actionable** — blind users need quick, clear commands.

### 4.5 Safety Rules

- If vision LLM detects a hazard → instruction must start with "Stop."
- If phone orientation is bad (facing down, extreme tilt) → ask user to adjust before moving
- If image quality is poor → request another capture
- Never give movement instructions without a recent image

---

## 5. Development Plan (5 Days)

### Day 1 — Frontend Skeleton
- [ ] Single HTML page with camera preview + 2 buttons
- [ ] Implement CAPTURE button → capture image + read sensors → POST to `/capture`
- [ ] Implement SPEAK button → record audio → POST to `/command`
- [ ] Use `speechSynthesis` to speak responses
- [ ] Test on localhost with mock backend responses

### Day 2 — Backend Core
- [ ] FastAPI with `/capture` and `/command` endpoints
- [ ] In-memory session storage
- [ ] `/capture` stores image + sensors, returns "Photo captured!"
- [ ] `/command` receives audio, returns mock instruction
- [ ] Test full loop: capture → speak → get response

### Day 3 — Integrate APIs
- [ ] Add Whisper API for speech-to-text
- [ ] Add Gemini/GPT-4o-mini for vision analysis
- [ ] Implement prompt template with sensor data
- [ ] Parse destination from transcribed voice
- [ ] Generate navigation instructions from vision + sensors

### Day 4 — Sensor Integration
- [ ] Frontend: request iOS orientation permission
- [ ] Frontend: collect orientation + motion on every upload
- [ ] Backend: use sensor data in vision prompt
- [ ] Detect bad phone angles and warn user

### Day 5 — Deploy & Test
- [ ] Deploy to VPS with Caddy (auto HTTPS)
- [ ] Or use Cloudflare Tunnel for temporary HTTPS
- [ ] Or use Chrome flag `edge://flags/#unsafely-treat-insecure-origin-as-secure` for Android testing
- [ ] Test blindfolded walk from classroom corner to podium
- [ ] Tune prompt based on real-world results

---

## 6. Deployment Options

### Option A: Domain + Caddy (Recommended for sharing)
- Buy cheap domain (~¥10/yr)
- Install Caddy on VPS
- One-line `Caddyfile`: `nav.yourdomain.top { reverse_proxy 127.0.0.1:8000 }`
- Auto HTTPS via Let's Encrypt

### Option B: Cloudflare Tunnel (Free, temporary)
```bash
cloudflared tunnel --url http://localhost:8000
```
Returns `https://random-words.trycloudflare.com` — works on any device

### Option C: Android Chrome Flag (Your phone only)
- Open `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
- Add `http://191.x.x.x:8000`
- Restart Chrome
- Camera works on plain HTTP

**iOS requires HTTPS** — use Option A or B.

---

## 7. Cost Estimate (100 captures/day)

| Item | Cost |
|---|---|
| VPS (2 vCPU / 2 GB) | ¥40/month |
| Domain | ¥10/year ≈ ¥1/month |
| Gemini 2.5 Flash (3000 images/month) | < ¥5/month |
| Whisper API (100 voice commands/month, ~1 min each) | < ¥3/month |
| Browser `speechSynthesis` TTS | Free |
| **Total** | **≈ ¥50/month** |

---

## 8. Key Simplifications from design.md

| Removed | Why |
|---|---|
| Redis | Use in-memory dict or SQLite |
| GPS / HKUST Path Advisor | Classroom demo doesn't need campus routing |
| Complex state machine | Two buttons, simple states: ready / recording / busy |
| Separate capture/command pipelines | Keep them separate but simpler |
| Long-press gestures | Use separate buttons instead |
| Audio base64 return | Use browser TTS for MVP |

---

## 9. File Structure

```
visualNavigator/
├── backend/
│   ├── main.py              # FastAPI app
│   ├── session.py           # In-memory session storage
│   ├── vision.py            # Vision LLM client
│   ├── speech.py            # Whisper + TTS clients
│   └── requirements.txt
├── frontend/
│   └── index.html           # Single-file app
├── deploy/
│   └── Caddyfile
└── plans/
    ├── plan1.md
    └── plan2.md             # This file
```

---

## 10. Testing Checklist

Before blindfolded testing:

- [ ] Camera preview shows rear camera feed
- [ ] CAPTURE button uploads image + sensors
- [ ] SPEAK button records and uploads audio
- [ ] Backend transcribes voice correctly
- [ ] Backend detects destination from voice
- [ ] Backend generates reasonable instructions from images
- [ ] Sensor data (orientation) is included in vision prompt
- [ ] Bad phone angles trigger "raise your phone" warnings
- [ ] `speechSynthesis` speaks all responses clearly
- [ ] HTTPS works on iPhone (via domain or Cloudflare Tunnel)

Blindfolded test:

- [ ] Start from random classroom position
- [ ] Speak destination: "Go to the podium"
- [ ] Follow spoken instructions
- [ ] Capture photos when instructed
- [ ] Reach podium without removing blindfold

---

## 11. Next Steps

Ready to start Day 1? I need three decisions:

1. **Backend language**: Python (FastAPI) or Node (Express)?
2. **VPS location**: China or overseas? (affects API choice)
3. **Deployment**: Do you have a domain, or should we start with Cloudflare Tunnel / Chrome flag?

Once you confirm, I'll build the Day 1 skeleton: frontend with 2 buttons + camera + sensors, and backend with mock endpoints.
