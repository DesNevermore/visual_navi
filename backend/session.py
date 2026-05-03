"""
Session storage for blind navigation demo.
Simple in-memory storage - no database required.
"""

import uuid
from typing import Dict, List, Optional
from datetime import datetime


class Session:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.destination: Optional[str] = None
        self.images: List[Dict] = []  # List of {blob, sensors, timestamp}
        self.last_instruction: Optional[str] = None
        self.created_at = datetime.now()
        self.max_images = 5  # Keep last 5 images only

    def add_image(self, image_data: bytes, sensors: dict):
        """Store image with sensor data"""
        self.images.append({
            'data': image_data,
            'sensors': sensors,
            'timestamp': datetime.now()
        })
        # Keep only last N images
        if len(self.images) > self.max_images:
            self.images = self.images[-self.max_images:]

    def get_latest_image(self) -> Optional[Dict]:
        """Get the most recent image"""
        return self.images[-1] if self.images else None

    def set_destination(self, destination: str):
        """Set navigation destination"""
        self.destination = destination

    def set_last_instruction(self, instruction: str):
        """Store last given instruction"""
        self.last_instruction = instruction


class SessionStore:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}

    def create_session(self) -> str:
        """Create a new session and return its ID"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = Session(session_id)
        return session_id

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        return self.sessions.get(session_id)

    def get_or_create_session(self, session_id: Optional[str] = None) -> tuple[str, Session]:
        """Get existing session or create new one"""
        if session_id and session_id in self.sessions:
            return session_id, self.sessions[session_id]
        else:
            new_id = self.create_session()
            return new_id, self.sessions[new_id]


# Global session store
session_store = SessionStore()
