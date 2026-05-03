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
        # Check phone angle first (before calling expensive API)
        angle_warning = self._check_phone_angle(sensors)
        if angle_warning:
            return {
                "instruction": angle_warning,
                "arrived": False,
                "needs_recapture": True
            }

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

    def _check_phone_angle(self, sensors: Dict[str, Any]) -> Optional[str]:
        """
        Check if phone angle is bad and return warning message.
        Returns None if angle is OK.
        """
        orientation = sensors.get("orientation")
        if not orientation:
            return None

        beta = orientation.get("beta")
        gamma = orientation.get("gamma")

        if beta is None:
            return None

        # Check tilt
        if beta < -30:
            return "Raise your phone to chest level and point it forward"
        elif beta > 30:
            return "Lower your phone to chest level and point it forward"

        if gamma is not None and abs(gamma) > 45:
            return "Hold your phone upright, not tilted sideways"

        return None

    def _build_prompt(
        self,
        destination: str,
        last_instruction: Optional[str],
        sensors: Dict[str, Any]
    ) -> str:
        """Build the vision prompt with context"""
        orientation = sensors.get("orientation", {})
        motion = sensors.get("motion", {})

        # Extract orientation data
        alpha = orientation.get("alpha") if orientation else None
        beta = orientation.get("beta") if orientation else None
        gamma = orientation.get("gamma") if orientation else None

        # Extract motion data
        accel = motion.get("accelerationIncludingGravity") if motion else None
        rotation = motion.get("rotationRate") if motion else None

        # Build sensor description
        sensor_desc = []

        if alpha is not None and beta is not None and gamma is not None:
            sensor_desc.append(f"- Orientation: alpha={alpha:.1f}°, beta={beta:.1f}°, gamma={gamma:.1f}°")
            sensor_desc.append(f"  (alpha: compass heading 0-360°, beta: front-back tilt -180 to 180°, gamma: left-right tilt -90 to 90°)")

            # Interpret phone angle
            if beta < -30:
                sensor_desc.append(f"  ⚠️ Phone is tilted DOWN (beta={beta:.1f}°) - user may be looking at the ground")
            elif beta > 30:
                sensor_desc.append(f"  ⚠️ Phone is tilted UP (beta={beta:.1f}°) - user may be looking at the ceiling")
            else:
                sensor_desc.append(f"  ✓ Phone angle is good (beta={beta:.1f}°)")

            if abs(gamma) > 45:
                sensor_desc.append(f"  ⚠️ Phone is tilted sideways (gamma={gamma:.1f}°)")
        else:
            sensor_desc.append("- Orientation: not available")

        if accel:
            sensor_desc.append(f"- Acceleration: x={accel.get('x', 0):.2f}, y={accel.get('y', 0):.2f}, z={accel.get('z', 0):.2f} m/s²")

        if rotation:
            sensor_desc.append(f"- Rotation rate: alpha={rotation.get('alpha', 0):.2f}, beta={rotation.get('beta', 0):.2f}, gamma={rotation.get('gamma', 0):.2f} deg/s")

        sensor_text = "\n".join(sensor_desc)

        prompt = f"""You are a navigation assistant for a blind user in a classroom.

Destination: {destination}
Last instruction: {last_instruction or "None"}

The user is holding a phone. Sensor data:
{sensor_text}

Based on the image and sensors, provide navigation guidance:

1. **Phone angle check**: If beta < -30° or beta > 30°, or |gamma| > 45°, tell the user to adjust the phone angle first before giving movement instructions.
   - If tilted down: "Raise your phone to chest level and point it forward"
   - If tilted up: "Lower your phone to chest level and point it forward"
   - If tilted sideways: "Hold your phone upright"

2. **Image quality check**: If the image is blurry, dark, too bright, or unclear, say: "Image unclear, please capture again"

3. **Destination detection**: If you can see the destination ({destination}) in the image:
   - Estimate the distance (in steps or meters)
   - Provide direction (forward, left, right, slight left, etc.)
   - Example: "I can see the {destination} ahead. Move forward 5 steps."

4. **Obstacle detection**: If there's an obstacle in the path (chair, desk, person, wall, etc.):
   - Say: "Stop. [Obstacle type] ahead. Turn [direction] to avoid it."

5. **Arrival check**: If the user is very close to or at the destination:
   - Say: "You have arrived at the {destination}"

6. **General guidance**: Otherwise, give a short, clear movement instruction:
   - Use simple directions: "Move forward X steps", "Turn left/right", "Stop"
   - Keep it under 20 words
   - Be specific about distance (in steps, not meters)

Return JSON only in this exact format:
{{
  "instruction": "your instruction here",
  "arrived": false,
  "needs_recapture": false
}}

IMPORTANT: Prioritize safety. If unsure, ask for another capture rather than giving potentially dangerous movement instructions.
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
