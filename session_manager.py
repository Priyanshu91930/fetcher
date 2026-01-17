"""
Session Manager for handling multiple Telegram sessions.
Automatically switches sessions when long flood waits are encountered.
"""

import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionManager:
    """
    Manages multiple Telegram session strings and handles session switching.
    """
    
    def __init__(self, session_strings: List[str]):
        """
        Initialize the session manager.
        
        Args:
            session_strings: List of session strings to use
        """
        if not session_strings:
            raise ValueError("At least one session string is required")
        
        self.sessions = session_strings
        self.current_index = 0
        self.switch_history = []
        
        logger.info(f"SessionManager initialized with {len(self.sessions)} session(s)")
    
    def get_current_session(self) -> str:
        """
        Get the currently active session string.
        
        Returns:
            Current session string
        """
        return self.sessions[self.current_index]
    
    def get_current_session_number(self) -> int:
        """
        Get the current session number (1-indexed for display).
        
        Returns:
            Current session number
        """
        return self.current_index + 1
    
    def get_total_sessions(self) -> int:
        """
        Get the total number of available sessions.
        
        Returns:
            Total session count
        """
        return len(self.sessions)
    
    def switch_to_next_session(self) -> tuple[str, int]:
        """
        Switch to the next available session.
        
        Returns:
            Tuple of (new_session_string, new_session_number)
        """
        old_index = self.current_index
        self.current_index = (self.current_index + 1) % len(self.sessions)
        
        # Record switch
        switch_time = datetime.now()
        self.switch_history.append({
            'from_session': old_index + 1,
            'to_session': self.current_index + 1,
            'timestamp': switch_time
        })
        
        logger.warning(
            f"🔄 Session switched: Session {old_index + 1} → Session {self.current_index + 1} "
            f"(Total sessions: {len(self.sessions)})"
        )
        
        return self.get_current_session(), self.current_index + 1
    
    def has_alternate_sessions(self) -> bool:
        """
        Check if there are alternate sessions available.
        
        Returns:
            True if more than one session is configured
        """
        return len(self.sessions) > 1


class LongFloodWaitException(Exception):
    """
    Exception raised when a flood wait exceeds the threshold and session switch is needed.
    """
    
    def __init__(self, wait_time: int, threshold: int):
        self.wait_time = wait_time
        self.threshold = threshold
        super().__init__(
            f"FloodWait of {wait_time}s exceeds threshold of {threshold}s. Session switch required."
        )
