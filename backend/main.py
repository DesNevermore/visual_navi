"""
FastAPI backend for blind navigation demo.
Handles /capture and /command endpoints.
"""

from fastapi import FastAPI, File, UploadFile, Form, Cookie, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
from typing import Optional
import io
from PIL import Image

from session import session_store

app = FastAPI(title="Blind Navigation API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    return {
        "status": "ok",
        "spoken_text": "Photo captured!",
        "capture_count": len(session.images)
    }


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

    # TODO: Implement transcription and reasoning in Day 3
    # For now, return mock response

    # Mock: detect if this is first command (setting destination)
    if session.destination is None:
        mock_transcription = "go to the podium"
        session.set_destination("podium")
        spoken_response = f"Destination set to podium. Tap capture to take photos as you walk."
    else:
        # Mock navigation instruction
        spoken_response = "Move forward three steps, then capture again."
        session.set_last_instruction(spoken_response)

    return {
        "status": "ok",
        "spoken_text": spoken_response,
        "audio_base64": None  # Will add TTS in Day 3 if needed
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
