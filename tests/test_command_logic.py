import sys
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

import main


class CommandLogicTest(TestCase):
    def test_extract_destination_ignores_greetings_and_questions(self):
        self.assertIsNone(main.extract_destination("Hello."))
        self.assertIsNone(main.extract_destination("What is in front of me?"))
        self.assertIsNone(main.extract_destination("testing"))

    def test_extract_destination_handles_known_and_freeform_destinations(self):
        self.assertEqual(main.extract_destination("Go to the door"), "door")
        self.assertEqual(main.extract_destination("Take me to the podium"), "podium")
        self.assertEqual(main.extract_destination("Set destination to the library"), "the library")

    def test_build_response_can_skip_tts(self):
        fake_speech = SimpleNamespace(synthesize=lambda text: b"audio", tts_content_type="audio/wav")

        with patch.object(main, "speech_client", fake_speech):
            payload = main.build_response("ok", "Photo captured!", synthesize_audio=False)

        self.assertIsNone(payload["audio_base64"])
        self.assertIsNone(payload["audio_content_type"])
