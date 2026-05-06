from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND_HTML = ROOT / "frontend" / "index.html"


class FrontendRecordingFlowTest(unittest.TestCase):
    def test_recording_flow_stops_audio_before_upload(self):
        html = FRONTEND_HTML.read_text()
        stop_flow = html.split("// Stop recording", 1)[1].split("// Initialize on load", 1)[0]

        self.assertLess(
            stop_flow.index("stopAudioRecording()"),
            stop_flow.index("uploadCommand(audioBlob)"),
        )

    def test_recording_flow_does_not_speak_while_microphone_is_active(self):
        html = FRONTEND_HTML.read_text()
        recording_flow = html.split("// Handle speak button", 1)[1].split("// Initialize on load", 1)[0]

        self.assertNotIn("speak('Recording started')", recording_flow)
        self.assertNotIn("speak('Recording stopped')", recording_flow)

    def test_command_upload_uses_wav_audio_for_gemini_audio_input(self):
        html = FRONTEND_HTML.read_text()

        self.assertIn("formData.append('audio', audioBlob, 'command.wav')", html)
        self.assertIn("new Blob([wavBuffer], { type: 'audio/wav' })", html)

    def test_main_buttons_play_click_tone(self):
        html = FRONTEND_HTML.read_text()
        capture_flow = html.split("captureButton.addEventListener", 1)[1].split("// Handle speak button", 1)[0]
        speak_flow = html.split("speakButton.addEventListener", 1)[1].split("// Initialize on load", 1)[0]

        self.assertIn("function playClickTone()", html)
        self.assertIn("playClickTone();", capture_flow)
        self.assertIn("playClickTone();", speak_flow)
