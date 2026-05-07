"""
Session management: Persist and restore application state.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from .config import SESSION_FILE, CHECKPOINT_FILE, SESSION_EXPIRY_HOURS
from .logger import logger


class SessionManager:
    """Manage application session state and checkpoints."""

    def __init__(self, session_file: str = SESSION_FILE, checkpoint_file: str = CHECKPOINT_FILE):
        self.session_file = session_file
        self.checkpoint_file = checkpoint_file

    def load_session(self) -> Optional[Dict[str, Any]]:
        """
        Load existing session if it exists and is not expired.

        Returns:
            Session dict if valid, None otherwise
        """
        if not os.path.exists(self.session_file):
            return None

        try:
            with open(self.session_file, "r") as f:
                session = json.load(f)

            # Check if session is expired
            last_updated = datetime.fromisoformat(session.get("lastUpdated", ""))
            if datetime.utcnow() - last_updated > timedelta(hours=SESSION_EXPIRY_HOURS):
                logger.info("SESSION_LOAD", "Session expired, creating new session")
                return None

            logger.info("SESSION_LOAD", f"Loaded existing session from {last_updated}")
            return session

        except (json.JSONDecodeError, IOError, ValueError) as e:
            logger.error("SESSION_LOAD", f"Failed to load session: {str(e)}")
            return None

    def save_session(self, session_state: Dict[str, Any]) -> None:
        """
        Save session state to file.

        Args:
            session_state: Session data to persist
        """
        try:
            session_state["lastUpdated"] = datetime.utcnow().isoformat()
            with open(self.session_file, "w") as f:
                json.dump(session_state, f, indent=2)
        except IOError as e:
            logger.error("SESSION_SAVE", f"Failed to save session: {str(e)}")

    def save_checkpoint(self, checkpoint_data: Dict[str, Any]) -> None:
        """
        Save checkpoint for recovery.

        Args:
            checkpoint_data: Checkpoint data to persist
        """
        try:
            checkpoint_data["timestamp"] = datetime.utcnow().isoformat()
            with open(self.checkpoint_file, "w") as f:
                json.dump(checkpoint_data, f, indent=2)
            logger.info("CHECKPOINT_SAVE", "Checkpoint saved")
        except IOError as e:
            logger.error("CHECKPOINT_SAVE", f"Failed to save checkpoint: {str(e)}")

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Load last checkpoint if exists.

        Returns:
            Checkpoint dict if exists, None otherwise
        """
        if not os.path.exists(self.checkpoint_file):
            return None

        try:
            with open(self.checkpoint_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error("CHECKPOINT_LOAD", f"Failed to load checkpoint: {str(e)}")
            return None

    def cleanup_session(self) -> None:
        """Delete session and checkpoint files."""
        try:
            if os.path.exists(self.session_file):
                os.remove(self.session_file)
            if os.path.exists(self.checkpoint_file):
                os.remove(self.checkpoint_file)
            logger.info("SESSION_CLEANUP", "Session and checkpoint cleaned up")
        except IOError as e:
            logger.error("SESSION_CLEANUP", f"Failed to cleanup session: {str(e)}")

    def create_session(self, url: str) -> Dict[str, Any]:
        """
        Create a new session.

        Args:
            url: Application URL

        Returns:
            New session dict
        """
        session = {
            "url": url,
            "startTime": datetime.utcnow().isoformat(),
            "lastUpdated": datetime.utcnow().isoformat(),
            "filledFields": {},
            "failedFields": [],
            "flaggedFields": [],
            "checkpointCount": 0,
        }
        self.save_session(session)
        return session


# Create a singleton instance
session_manager = SessionManager()
