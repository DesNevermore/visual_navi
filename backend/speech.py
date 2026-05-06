"""
Speech-to-text and text-to-speech clients.
"""

import base64
import json
import os
import urllib.request
import wave
from io import BytesIO
from openai import OpenAI
from typing import Optional


class SpeechClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("SPEECH_TO_TEXT_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("SPEECH_TO_TEXT_BASE_URL", "https://api.openai.com/v1")
        self.model = model or os.getenv("SPEECH_TO_TEXT_MODEL", "whisper-1")
        self.fallback_models = [
            fallback_model.strip()
            for fallback_model in os.getenv("SPEECH_TO_TEXT_FALLBACK_MODELS", "").split(",")
            if fallback_model.strip()
        ]
        self.language = os.getenv("SPEECH_TO_TEXT_LANGUAGE", "en")
        self.tts_provider = os.getenv("TTS_PROVIDER", "browser").lower()
        self.tts_model = os.getenv("TTS_MODEL", "tts-1")
        self.tts_voice = os.getenv(
            "TTS_VOICE",
            "Kore" if "gemini" in self.tts_model.lower() else "alloy"
        )
        self.tts_content_type = os.getenv(
            "TTS_CONTENT_TYPE",
            "audio/wav" if self.tts_provider == "gemini" else "audio/mpeg"
        )
        self.tts_api_key = (
            os.getenv("TTS_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or self.api_key
        )
        self.tts_gemini_base_url = os.getenv("TTS_GEMINI_BASE_URL", "https://generativelanguage.googleapis.com")
        self.tts_fallback_model = os.getenv(
            "TTS_FALLBACK_MODEL",
            "gpt-4o-mini-tts" if self.tts_provider == "gemini" else ""
        )
        self.tts_fallback_models = [
            fallback_model.strip()
            for fallback_model in os.getenv("TTS_FALLBACK_MODELS", "").split(",")
            if fallback_model.strip()
        ]
        if self.tts_fallback_model and self.tts_fallback_model not in self.tts_fallback_models:
            self.tts_fallback_models.append(self.tts_fallback_model)
        self.tts_fallback_voice = os.getenv("TTS_FALLBACK_VOICE", "alloy")
        self.api_timeout = float(os.getenv("API_TIMEOUT_SECONDS", "30"))

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.api_timeout,
            )
        else:
            self.client = None

        self.tts_client = None
        if self.tts_provider == "openai":
            tts_api_key = (
                os.getenv("TTS_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or self.api_key
            )
            tts_base_url = (
                os.getenv("TTS_BASE_URL")
                or os.getenv("OPENAI_BASE_URL")
                or self.base_url
            )
            if tts_api_key:
                self.tts_client = OpenAI(
                    api_key=tts_api_key,
                    base_url=tts_base_url,
                    timeout=self.api_timeout,
                )

        self.fallback_tts_client = None
        if self.tts_fallback_models:
            tts_api_key = (
                os.getenv("TTS_API_KEY")
                or os.getenv("OPENAI_API_KEY")
                or self.api_key
            )
            tts_base_url = (
                os.getenv("TTS_BASE_URL")
                or os.getenv("OPENAI_BASE_URL")
                or self.base_url
            )
            if tts_api_key:
                self.fallback_tts_client = OpenAI(
                    api_key=tts_api_key,
                    base_url=tts_base_url,
                    timeout=self.api_timeout,
                )

    def transcribe(self, audio_data: bytes, filename: str = "audio.webm") -> str:
        """
        Transcribe audio to text using Whisper API.
        Returns transcribed text.
        """
        if not self.client:
            # Mock response if no API key
            print("[SPEECH] No API key, using mock transcription")
            return "go to the podium"

        models = []
        for candidate in [self.model, *self.fallback_models]:
            if candidate not in models:
                models.append(candidate)

        for model in models:
            try:
                return self._transcribe_with_model(model, audio_data, filename)

            except Exception as e:
                print(f"[SPEECH] Transcription error with {model}: {e}")

        return ""

    def _transcribe_with_model(self, model: str, audio_data: bytes, filename: str) -> str:
        if "gemini" in model.lower():
            return self._transcribe_chat_audio(model, audio_data, filename)

        # Transcription APIs expect a fresh file-like object for each attempt.
        from io import BytesIO
        audio_file = BytesIO(audio_data)
        audio_file.name = filename

        response = self.client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            language=self.language
        )

        return response.text.strip()

    def _transcribe_chat_audio(self, model: str, audio_data: bytes, filename: str) -> str:
        audio_format = self._audio_format(filename)
        audio_b64 = base64.b64encode(audio_data).decode("ascii")

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Transcribe the speech in this audio exactly. "
                                "Return only the transcript text. "
                                "If there is no intelligible speech, return exactly EMPTY."
                            ),
                        },
                        {
                            "type": "input_audio",
                            "input_audio": {
                                "data": audio_b64,
                                "format": audio_format,
                            },
                        },
                    ],
                }
            ],
            max_tokens=120,
        )

        text = (response.choices[0].message.content or "").strip()
        if text.upper() == "EMPTY":
            return ""
        return text

    def _audio_format(self, filename: str) -> str:
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else "wav"
        if extension in {"wav", "mp3"}:
            return extension
        return "wav"

    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Convert text to speech.
        Returns audio bytes.
        For MVP, we use browser speechSynthesis instead, so this is optional.
        """
        if self.tts_provider == "gemini":
            return self._synthesize_gemini(text) or self._synthesize_fallback_tts(text)

        if not self.tts_client:
            return None

        return self._synthesize_openai_tts(
            text,
            [self.tts_model, *self.tts_fallback_models],
            self.tts_voice,
            self.tts_client,
            "TTS",
        )

    def _synthesize_fallback_tts(self, text: str) -> Optional[bytes]:
        if not self.fallback_tts_client:
            return None

        return self._synthesize_openai_tts(
            text,
            self.tts_fallback_models,
            self.tts_fallback_voice,
            self.fallback_tts_client,
            "Fallback TTS",
        )

    def _synthesize_openai_tts(
        self,
        text: str,
        models: list[str],
        voice: str,
        client,
        log_label: str,
    ) -> Optional[bytes]:
        tried_models = []
        for model in models:
            if not model or model in tried_models:
                continue
            tried_models.append(model)

            try:
                response = client.audio.speech.create(
                    model=model,
                    voice=voice,
                    input=self._tts_input_for_model(model, text),
                )
                self.tts_content_type = "audio/mpeg"
                return response.content
            except Exception as e:
                print(f"[SPEECH] {log_label} error with {model}: {e}")

        return None

    def _tts_input_for_model(self, model: str, text: str) -> str:
        if "gemini" in model.lower():
            return f"Say clearly as spoken audio only: {text}"
        return text

    def _synthesize_gemini(self, text: str) -> Optional[bytes]:
        if not self.tts_api_key:
            return None

        model = self.tts_model or "gemini-3.1-flash-tts-preview"
        endpoint = (
            self.tts_gemini_base_url.rstrip("/")
            + f"/v1beta/models/{model}:generateContent"
        )
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": f"Say clearly and calmly: {text}",
                        }
                    ]
                }
            ],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {
                            "voiceName": self.tts_voice,
                        }
                    }
                },
            },
            "model": model,
        }

        request = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.tts_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.api_timeout) as response:
                data = json.loads(response.read().decode("utf-8"))

            inline_data = data["candidates"][0]["content"]["parts"][0].get("inlineData") or data["candidates"][0]["content"]["parts"][0].get("inline_data")
            audio_data = base64.b64decode(inline_data["data"])
            mime_type = inline_data.get("mimeType") or inline_data.get("mime_type") or ""
            if "wav" in mime_type.lower() or audio_data.startswith(b"RIFF"):
                return audio_data
            return self._pcm_to_wav(audio_data)

        except Exception as e:
            print(f"[SPEECH] Gemini TTS error: {e}")
            return None

    def _pcm_to_wav(self, pcm: bytes, channels: int = 1, rate: int = 24000, sample_width: int = 2) -> bytes:
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(rate)
            wav_file.writeframes(pcm)
        return buffer.getvalue()
