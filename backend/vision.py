"""
Vision LLM client for image analysis.
Supports multiple providers: Gemini, OpenAI GPT-4o, etc.
"""

import os
import base64
from typing import Optional, Dict, Any
import json


class VisionClient:
    def __init__(self, provider: str = "gemini", api_key: Optional[str] = None):
        """
        Initialize vision client.
        provider: "gemini" or "openai"
        """
        self.provider = provider
        self.api_key = api_key

        if provider == "gemini":
            self.api_key = self.api_key or os.getenv("GEMINI_API_KEY")
            if self.api_key:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            else:
                self.model = None

        elif provider == "openai":
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if self.api_key:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
            else:
                self.client = None

    def analyze_navigation(
        self,
        image_data: bytes,
        destination: str,
        last_instruction: Optional[str],
        sensors: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze image for navigation guidance.
        Returns: {"instruction": "...", "arrived": bool, "needs_recapture": bool}
        """
        if not self.api_key:
            # Mock response if no API key
            return self._mock_response(destination, last_instruction)

        # Build prompt
        prompt = self._build_prompt(destination, last_instruction, sensors)

        try:
            if self.provider == "gemini":
                return self._analyze_gemini(image_data, prompt)
            elif self.provider == "openai":
                return self._analyze_openai(image_data, prompt)
            else:
                return self._mock_response(destination, last_instruction)

        except Exception as e:
            print(f"[VISION] Analysis error: {e}")
            return {
                "instruction": "Analysis failed. Please try again.",
                "arrived": False,
                "needs_recapture": True
            }

    def _build_prompt(
        self,
        destination: str,
        last_instruction: Optional[str],
        sensors: Dict[str, Any]
    ) -> str:
        """Build the vision prompt with context"""
        orientation = sensors.get("orientation", {})
        alpha = orientation.get("alpha", "N/A") if orientation else "N/A"
        beta = orientation.get("beta", "N/A") if orientation else "N/A"
        gamma = orientation.get("gamma", "N/A") if orientation else "N/A"

        prompt = f"""You are a navigation assistant for a blind user in a classroom.

Destination: {destination}
Last instruction: {last_instruction or "None"}

The user is holding a phone. Sensor data:
- Orientation: alpha={alpha}°, beta={beta}°, gamma={gamma}°
  (alpha: compass heading 0-360°, beta: front-back tilt -180 to 180°, gamma: left-right tilt -90 to 90°)

Based on the image and sensors:
1. If the phone is tilted down too much (beta < -30°), say: "Raise your phone to chest level"
2. If the image is blurry, dark, or unclear, say: "Image unclear, please capture again"
3. If you can see the destination ({destination}), estimate distance and give direction
4. If there's an obstacle in the path, say: "Stop. Obstacle ahead."
5. If the user has reached the destination, say: "You have arrived at the {destination}"
6. Otherwise, give a short movement instruction (≤ 20 words)

Return JSON only in this exact format:
{{
  "instruction": "your instruction here",
  "arrived": false,
  "needs_recapture": false
}}

Keep instructions short, clear, and actionable. Use simple directions like "Move forward 3 steps", "Turn left 45 degrees", "Stop", etc.
"""
        return prompt

    def _analyze_gemini(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze using Gemini"""
        from PIL import Image
        import io

        # Convert bytes to PIL Image
        image = Image.open(io.BytesIO(image_data))

        # Generate response
        response = self.model.generate_content([prompt, image])

        # Parse JSON response
        text = response.text.strip()

        # Extract JSON from markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            result = json.loads(text)
            return result
        except json.JSONDecodeError:
            # If JSON parsing fails, extract instruction from text
            return {
                "instruction": text[:100],  # First 100 chars
                "arrived": "arrived" in text.lower(),
                "needs_recapture": "unclear" in text.lower() or "again" in text.lower()
            }

    def _analyze_openai(self, image_data: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze using OpenAI GPT-4o"""
        # Encode image to base64
        image_b64 = base64.b64encode(image_data).decode('utf-8')

        response = self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_b64}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=300
        )

        text = response.choices[0].message.content.strip()

        # Extract JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0].strip()
        elif "```" in text:
            text = text.split("```")[1].split("```")[0].strip()

        try:
            result = json.loads(text)
            return result
        except json.JSONDecodeError:
            return {
                "instruction": text[:100],
                "arrived": "arrived" in text.lower(),
                "needs_recapture": "unclear" in text.lower()
            }

    def _mock_response(self, destination: str, last_instruction: Optional[str]) -> Dict[str, Any]:
        """Mock response for testing without API key"""
        if last_instruction is None:
            return {
                "instruction": f"I can see the classroom. Move forward 5 steps toward the {destination}.",
                "arrived": False,
                "needs_recapture": False
            }
        else:
            return {
                "instruction": "Continue forward 3 more steps, then capture again.",
                "arrived": False,
                "needs_recapture": False
            }
