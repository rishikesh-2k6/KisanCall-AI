# ============================================================
# session.py — In-Memory Call Session Manager (Multilingual)
# ============================================================
# Tracks conversation state per phone call including the
# farmer's selected language, pending queries, and history.
#
# Uses Twilio's CallSid as the unique session key.
# ============================================================

from dataclasses import dataclass, field
from typing import Optional

# In-memory store: CallSid → Session
_sessions: dict[str, "CallSession"] = {}


@dataclass
class CallSession:
    """Tracks state for a single phone call."""
    call_sid: str
    # Selected language code (e.g., "hi", "te", "ta")
    language: str = "hi"
    # Whether language has been selected yet
    language_selected: bool = False
    # What the farmer is asking about
    pending_intent: Optional[str] = None
    # The original query (stored while we ask follow-ups)
    pending_query: Optional[str] = None
    # Whether this is the first interaction in the call
    is_first_turn: bool = True
    # Conversation history (for context)
    history: list[dict] = field(default_factory=list)


def get_session(call_sid: str) -> CallSession:
    """
    Get or create a session for a call.

    Args:
        call_sid: Twilio's unique call identifier.

    Returns:
        The CallSession for this call.
    """
    if call_sid not in _sessions:
        _sessions[call_sid] = CallSession(call_sid=call_sid)
    return _sessions[call_sid]


def clear_session(call_sid: str) -> None:
    """Remove a session when the call ends."""
    _sessions.pop(call_sid, None)
