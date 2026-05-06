import base64
import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from backend.speech import SpeechClient


class FakeTranscriptions:
    def __init__(self):
        self.models = []

    def create(self, model, file, language):
        self.models.append(model)
        if model == "saturated-model":
            raise RuntimeError("upstream saturated")
        return SimpleNamespace(text="go to the podium")


class FakeClient:
    def __init__(self):
        self.transcriptions = FakeTranscriptions()
        self.audio = SimpleNamespace(transcriptions=self.transcriptions)


class FakeChatCompletions:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content="go to the podium")
                )
            ]
        )


class FakeChatAudioClient:
    def __init__(self):
        self.chat_completions = FakeChatCompletions()
        self.chat = SimpleNamespace(completions=self.chat_completions)


class FakeSpeech:
    def __init__(self, failures_before_success=0):
        self.calls = []
        self.failures_before_success = failures_before_success

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if len(self.calls) <= self.failures_before_success:
            raise RuntimeError("tts model unavailable")
        return SimpleNamespace(content=b"fallback audio")


class FakeTtsClient:
    def __init__(self, failures_before_success=0):
        self.speech = FakeSpeech(failures_before_success=failures_before_success)
        self.audio = SimpleNamespace(speech=self.speech)


class SpeechClientTest(TestCase):
    def test_transcribe_tries_fallback_models_after_primary_failure(self):
        with patch.dict(
            "os.environ",
            {"SPEECH_TO_TEXT_FALLBACK_MODELS": "gpt-4o-transcribe,whisper-1"},
            clear=True,
        ):
            speech = SpeechClient(api_key=None, model="saturated-model")
            fake_client = FakeClient()
            speech.client = fake_client

            result = speech.transcribe(b"audio", "command.webm")

        self.assertEqual(result, "go to the podium")
        self.assertEqual(
            fake_client.transcriptions.models,
            ["saturated-model", "gpt-4o-transcribe"],
        )

    def test_gemini_model_uses_chat_audio_transcription(self):
        speech = SpeechClient(api_key=None, model="gemini-3-flash-preview")
        fake_client = FakeChatAudioClient()
        speech.client = fake_client

        result = speech.transcribe(b"RIFF wav bytes", "command.wav")

        self.assertEqual(result, "go to the podium")
        call = fake_client.chat_completions.calls[0]
        self.assertEqual(call["model"], "gemini-3-flash-preview")
        content = call["messages"][0]["content"]
        self.assertEqual(content[1]["type"], "input_audio")
        self.assertEqual(content[1]["input_audio"]["format"], "wav")

    def test_gemini_tts_uses_native_generate_content_and_returns_wav(self):
        pcm = b"\x00\x00\x01\x00"
        response_payload = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "inlineData": {
                                    "mimeType": "audio/pcm",
                                    "data": base64.b64encode(pcm).decode("ascii"),
                                }
                            }
                        ]
                    }
                }
            ]
        }

        class FakeResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return json.dumps(response_payload).encode()

        requests = []

        def fake_urlopen(request, timeout):
            requests.append((request, timeout))
            return FakeResponse()

        with patch.dict(
            "os.environ",
            {
                "TTS_PROVIDER": "gemini",
                "TTS_API_KEY": "token",
                "TTS_GEMINI_BASE_URL": "https://yunwu.ai",
                "TTS_MODEL": "gemini-3.1-flash-tts-preview",
                "TTS_VOICE": "Kore",
            },
            clear=True,
        ), patch("urllib.request.urlopen", fake_urlopen):
            speech = SpeechClient(api_key=None)
            audio = speech.synthesize("Hello")

        request = requests[0][0]
        body = json.loads(request.data.decode())
        self.assertEqual(
            request.full_url,
            "https://yunwu.ai/v1beta/models/gemini-3.1-flash-tts-preview:generateContent",
        )
        self.assertEqual(request.headers["Authorization"], "Bearer token")
        self.assertEqual(body["generationConfig"]["responseModalities"], ["AUDIO"])
        self.assertEqual(
            body["generationConfig"]["speechConfig"]["voiceConfig"]["prebuiltVoiceConfig"]["voiceName"],
            "Kore",
        )
        self.assertTrue(audio.startswith(b"RIFF"))

    def test_gemini_tts_falls_back_to_gpt_4o_mini_tts(self):
        with patch.dict(
            "os.environ",
            {
                "TTS_PROVIDER": "gemini",
                "TTS_API_KEY": "token",
                "TTS_BASE_URL": "https://yunwu.ai/v1",
                "TTS_MODEL": "gemini-3.1-flash-tts-preview",
                "TTS_VOICE": "Kore",
                "TTS_FALLBACK_MODEL": "gpt-4o-mini-tts",
                "TTS_FALLBACK_VOICE": "alloy",
            },
            clear=True,
        ):
            speech = SpeechClient(api_key=None)
            fake_tts_client = FakeTtsClient()
            speech.fallback_tts_client = fake_tts_client

            with patch.object(speech, "_synthesize_gemini", return_value=None):
                audio = speech.synthesize("Hello")

        self.assertEqual(audio, b"fallback audio")
        self.assertEqual(
            fake_tts_client.speech.calls,
            [
                {
                    "model": "gpt-4o-mini-tts",
                    "voice": "alloy",
                    "input": "Hello",
                }
            ],
        )

    def test_openai_tts_tries_configured_models_in_order(self):
        with patch.dict(
            "os.environ",
            {
                "TTS_PROVIDER": "openai",
                "TTS_API_KEY": "token",
                "TTS_BASE_URL": "https://api.gpt.ge/v1/",
                "TTS_MODEL": "gemini-2.5-flash-preview-tts",
                "TTS_FALLBACK_MODELS": "qwen-tts,qwen-tts-latest",
                "TTS_VOICE": "Kore",
            },
            clear=True,
        ):
            speech = SpeechClient(api_key=None)
            fake_tts_client = FakeTtsClient(failures_before_success=2)
            speech.tts_client = fake_tts_client

            audio = speech.synthesize("Hello")

        self.assertEqual(audio, b"fallback audio")
        self.assertEqual(
            [call["model"] for call in fake_tts_client.speech.calls],
            [
                "gemini-2.5-flash-preview-tts",
                "qwen-tts",
                "qwen-tts-latest",
            ],
        )

    def test_openai_compatible_gemini_tts_uses_audio_instruction_input(self):
        with patch.dict(
            "os.environ",
            {
                "TTS_PROVIDER": "openai",
                "TTS_API_KEY": "token",
                "TTS_BASE_URL": "https://api.gpt.ge/v1/",
                "TTS_MODEL": "gemini-2.5-flash-preview-tts",
                "TTS_VOICE": "Kore",
            },
            clear=True,
        ):
            speech = SpeechClient(api_key=None)
            fake_tts_client = FakeTtsClient()
            speech.tts_client = fake_tts_client

            speech.synthesize("Hello")

        call = fake_tts_client.speech.calls[0]
        self.assertIn("spoken audio only", call["input"])
        self.assertIn("Hello", call["input"])
