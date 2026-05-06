"""
FastAPI backend for blind navigation demo.
Handles /capture and /command endpoints.
"""

from fastapi import FastAPI, File, UploadFile, Form, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import base64
import json
from typing import Optional
import io
from PIL import Image
import os
import re
from dotenv import load_dotenv

load_dotenv()

from session import session_store
from speech import SpeechClient
from vision import VisionClient

app = FastAPI(title="Blind Navigation API")

DEFAULT_CORS_ORIGINS = [
    "http://localhost:1200",
    "http://127.0.0.1:1200",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://oc.rustapp.uk:1201",
    "https://oc.rustapp.uk:1201",
]

cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", ",".join(DEFAULT_CORS_ORIGINS)).split(",")
    if origin.strip()
]

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize API clients
# Set environment variables in .env file
speech_client = SpeechClient()
vision_client = VisionClient()


def build_response(status: str, spoken_text: str, synthesize_audio: bool = True, **extra):
    """Build an API response with optional backend-generated speech audio."""
    audio_data = speech_client.synthesize(spoken_text) if synthesize_audio and spoken_text else None
    payload = {
        "status": status,
        "spoken_text": spoken_text,
        "audio_base64": None,
        "audio_content_type": None,
        **extra,
    }

    if audio_data:
        payload["audio_base64"] = base64.b64encode(audio_data).decode("ascii")
        payload["audio_content_type"] = speech_client.tts_content_type

    return payload


def extract_destination(transcription: str) -> Optional[str]:
    """Return a destination only when the user actually appears to set one."""
    text = transcription.strip()
    normalized = text.lower().strip(" .!?")

    if normalized in {"hello", "hi", "hey", "testing", "test", "hello testing"}:
        return None

    if any(phrase in normalized for phrase in ["what is", "what's", "in front", "around me", "where am i"]):
        return None

    if "podium" in normalized or "讲台" in normalized:
        return "podium"
    if "door" in normalized or "门" in normalized:
        return "door"
    if "window" in normalized or "窗" in normalized:
        return "window"

    patterns = [
        r"(?:go|walk|take me|guide me|navigate me)\s+to\s+(.+)",
        r"(?:set\s+)?destination\s+(?:to|as)\s+(.+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            destination = match.group(1).strip(" .!?")
            return destination or None

    return None


def is_scene_question(transcription: str) -> bool:
    normalized = transcription.lower()
    return any(
        phrase in normalized
        for phrase in ["what is in front", "what's in front", "what is around", "describe", "where am i"]
    )


def destination_is_invalid(destination: Optional[str]) -> bool:
    if destination is None:
        return True
    normalized = destination.lower().strip(" .!?")
    return normalized in {"hello", "hi", "hey", "testing", "test", "hello testing"}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {"status": "ok", "message": "Blind Navigation API"}


@app.post("/capture")
async def capture(
    image: UploadFile = File(...),
    sensors: str = Form(...),
    session_id: Optional[str] = Cookie(None),
    response: Response = None
):
    """
    Receive image + sensor data.
    Store in session memory.
    Return acknowledgment only - no navigation logic here.
    """
    # Parse sensors
    try:
        sensor_data = json.loads(sensors)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "spoken_text": "Invalid sensor data"}
        )

    # Get or create session
    session_id, session = session_store.get_or_create_session(session_id)

    # Read and store image
    image_data = await image.read()

    # Optionally compress image to save memory
    try:
        img = Image.open(io.BytesIO(image_data))
        # Resize if too large (max 1024px on longest side)
        max_size = 1024
        if max(img.size) > max_size:
            ratio = max_size / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)

        # Convert back to bytes
        buffer = io.BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        image_data = buffer.getvalue()
    except Exception as e:
        print(f"Image processing error: {e}")
        # Use original if processing fails

    # Store in session
    session.add_image(image_data, sensor_data)

    # Set session cookie
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    print(f"[CAPTURE] Session {session_id[:8]}: stored image #{len(session.images)}, sensors: {sensor_data.keys()}")

    return build_response(
        "ok",
        "Photo captured!",
        synthesize_audio=False,
        capture_count=len(session.images),
    )


@app.post("/command")
async def command(
    audio: UploadFile = File(...),
    sensors: str = Form(...),
    session_id: Optional[str] = Cookie(None),
    response: Response = None
):
    """
    Receive voice command + sensor data.
    Transcribe, reason, and return spoken instruction.
    This is where all the intelligence happens.
    """
    # Parse sensors
    try:
        sensor_data = json.loads(sensors)
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "spoken_text": "Invalid sensor data"}
        )

    # Get or create session
    session_id, session = session_store.get_or_create_session(session_id)

    # Read audio
    audio_data = await audio.read()

    # Set session cookie
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    print(f"[COMMAND] Session {session_id[:8]}: received audio ({len(audio_data)} bytes), sensors: {sensor_data.keys()}")

    # Transcribe audio
    transcription = speech_client.transcribe(audio_data, audio.filename)
    print(f"[COMMAND] Transcription: {transcription}")

    if not transcription:
        return build_response(
            "error",
            "Could not understand audio. Please try again.",
        )

    destination = extract_destination(transcription)
    if destination:
        session.set_destination(destination)
        spoken_response = f"Destination set to {destination}. Tap capture to take photos as you walk."

    elif destination_is_invalid(session.destination):
        session.destination = None
        latest_image = session.get_latest_image()
        if is_scene_question(transcription) and latest_image:
            result = vision_client.analyze_navigation(
                image_data=latest_image['data'],
                destination="safe path forward",
                last_instruction=session.last_instruction,
                sensors=sensor_data
            )
            spoken_response = result.get("instruction", "Unable to analyze. Please try again.")
            session.set_last_instruction(spoken_response)
        elif is_scene_question(transcription):
            spoken_response = "Please capture a photo first, then ask again."
        else:
            spoken_response = "Please say your destination, for example, go to the door."

    else:
        # User is asking for guidance
        # Get latest image
        latest_image = session.get_latest_image()

        if not latest_image:
            spoken_response = "Please capture a photo first before asking for guidance."
        else:
            # Analyze image with vision LLM
            result = vision_client.analyze_navigation(
                image_data=latest_image['data'],
                destination=session.destination,
                last_instruction=session.last_instruction,
                sensors=sensor_data
            )

            spoken_response = result.get("instruction", "Unable to analyze. Please try again.")
            session.set_last_instruction(spoken_response)

            # Check if arrived
            if result.get("arrived", False):
                print(f"[COMMAND] User arrived at {session.destination}")

    return build_response("ok", spoken_response)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "1100")),
    )
