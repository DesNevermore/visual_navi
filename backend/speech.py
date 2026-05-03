"""
Speech-to-text and text-to-speech clients.
"""

import os
from openai import OpenAI
from typing import Optional


class SpeechClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def transcribe(self, audio_data: bytes, filename: str = "audio.webm") -> str:
        """
        Transcribe audio to text using Whisper API.
        Returns transcribed text.
        """
        if not self.client:
            # Mock response if no API key
            return "go to the podium"

        try:
            # Whisper API expects a file-like object
            from io import BytesIO
            audio_file = BytesIO(audio_data)
            audio_file.name = filename

            response = self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="en"  # Can be auto-detected or set to "zh" for Chinese
            )

            return response.text.strip()

        except Exception as e:
            print(f"[SPEECH] Transcription error: {e}")
            return ""

    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech using OpenAI TTS.
        Returns audio bytes (mp3).
        For MVP, we use browser speechSynthesis instead, so this is optional.
        """
        if not self.client:
            return None

        try:
            response = self.client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text
            )

            return response.content

        except Exception as e:
            print(f"[SPEECH] TTS error: {e}")
            return None
