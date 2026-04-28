# ============================================================
# main.py — FastAPI Application Entry Point for KisanCall AI
# ============================================================
#
# CALL FLOW:
#   1. Farmer calls Twilio number
#   2. Twilio sends webhook to /voice (initial greeting)
#   3. AI greets and listens via <Gather>
#   4. Farmer speaks → Twilio transcribes → POST /voice/respond
#   5. Backend detects intent, calls LLM, returns TwiML
#   6. Twilio speaks the response and listens again
#
# ============================================================

from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse
from twilio.twiml.voice_response import VoiceResponse, Gather

from config import HOST, PORT
from intent import detect_intent
from weather import get_weather_for_place
from llm import ask_llm
from prompts import build_weather_prompt, SYSTEM_PROMPT
from session import get_session, clear_session

# ── Create FastAPI App ───────────────────────────────────
app = FastAPI(
    title="KisanCall AI",
    description="Voice-based agricultural assistant for Indian farmers",
    version="1.0.0",
)


# ===========================================================
# ENDPOINT 1: /voice — Handles incoming calls (initial hook)
# ===========================================================
@app.post("/voice", response_class=PlainTextResponse)
async def handle_incoming_call(request: Request):
    """
    Called by Twilio when a farmer dials the number.
    Greets the user and starts listening for speech.
    """
    # Get the unique call identifier from Twilio
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")

    # Create a fresh session for this call
    session = get_session(call_sid)
    session.is_first_turn = True

    # Build TwiML response
    response = VoiceResponse()

    # Greet the farmer warmly
    response.say(
        "Namaste! Main aapka Kisan Mitra hoon. "
        "Aap mujhse kheti, mausam, ya fasal ke baare mein kuch bhi pooch sakte hain. "
        "Boliye, main sun raha hoon.",
        voice="Polly.Aditi",   # Hindi voice
        language="hi-IN",
    )

    # Start listening for the farmer's speech
    gather = Gather(
        input="speech",
        language="hi-IN",           # Recognize Hindi speech
        speech_timeout="auto",      # Auto-detect end of speech
        action="/voice/respond",    # Where to send the transcription
        method="POST",
    )
    response.append(gather)

    # If farmer doesn't say anything, prompt again
    response.say(
        "Kya aap sun sakte hain? Kripya apna sawaal bolein.",
        voice="Polly.Aditi",
        language="hi-IN",
    )
    response.redirect("/voice")  # Try again

    return PlainTextResponse(
        content=str(response),
        media_type="application/xml",
    )


# ===========================================================
# ENDPOINT 2: /voice/respond — Processes farmer's speech
# ===========================================================
@app.post("/voice/respond", response_class=PlainTextResponse)
async def handle_speech(request: Request):
    """
    Called by Twilio after the farmer speaks.
    Processes speech, detects intent, generates response.
    """
    form_data = await request.form()

    # Get the transcribed text from Twilio
    user_speech = form_data.get("SpeechResult", "")
    call_sid = form_data.get("CallSid", "unknown")

    print(f"\n[Call {call_sid}] Farmer said: \"{user_speech}\"")

    # Get the session for this call
    session = get_session(call_sid)
    session.is_first_turn = False

    # ── Step 1: Check if this is a follow-up (location answer) ──
    if session.pending_intent == "weather_needs_location":
        # The farmer is providing their location
        location_name = user_speech.strip()
        print(f"[Call {call_sid}] Location received: {location_name}")

        # Fetch real weather data
        weather_data = await get_weather_for_place(location_name)

        if weather_data:
            # Build a prompt with real weather data
            weather_prompt = build_weather_prompt(
                session.pending_query, weather_data
            )
            ai_reply = await ask_llm(
                user_message=session.pending_query,
                system_override=SYSTEM_PROMPT + "\n\n" + weather_prompt,
            )
        else:
            ai_reply = (
                "Maaf kijiye, yeh jagah nahi mil rahi. "
                "Kripya apne shehar ya district ka naam bataiye."
            )
            # Keep waiting for location
            return _build_listen_response(ai_reply)

        # Clear the pending state
        session.pending_intent = None
        session.pending_query = None

        print(f"[Call {call_sid}] AI reply: \"{ai_reply}\"")
        return _build_listen_response(ai_reply)

    # ── Step 2: Detect intent from speech ────────────────────
    intent = detect_intent(user_speech)
    print(f"[Call {call_sid}] Detected intent: {intent}")

    # ── Step 3: Handle weather intent ────────────────────────
    if intent == "weather":
        # We need the farmer's location for weather data
        # Save the query and ask for location
        session.pending_intent = "weather_needs_location"
        session.pending_query = user_speech

        ai_reply = "Mausam jaanne ke liye aapka gaon ya shehar ka naam bataiye."
        print(f"[Call {call_sid}] Asking for location...")
        return _build_listen_response(ai_reply)

    # ── Step 4: Handle general agriculture queries ───────────
    ai_reply = await ask_llm(user_message=user_speech)
    print(f"[Call {call_sid}] AI reply: \"{ai_reply}\"")

    return _build_listen_response(ai_reply)


# ===========================================================
# ENDPOINT 3: /voice/status — Call status callback
# ===========================================================
@app.post("/voice/status")
async def handle_call_status(request: Request):
    """
    Called by Twilio when a call ends.
    Cleans up the session.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    status = form_data.get("CallStatus", "unknown")

    print(f"[Call {call_sid}] Call status: {status}")

    if status in ("completed", "failed", "busy", "no-answer", "canceled"):
        clear_session(call_sid)

    return {"status": "ok"}


# ===========================================================
# ENDPOINT 4: /health — Health check
# ===========================================================
@app.get("/health")
async def health_check():
    """Simple health check for monitoring."""
    return {"status": "ok", "service": "KisanCall AI"}


# ===========================================================
# HELPER: Build TwiML response that speaks and listens again
# ===========================================================
def _build_listen_response(text: str) -> PlainTextResponse:
    """
    Creates a TwiML response that:
      1. Speaks the AI's reply
      2. Starts listening for the next question

    Args:
        text: The AI's response to speak.

    Returns:
        PlainTextResponse with TwiML XML.
    """
    response = VoiceResponse()

    # Speak the AI's response
    response.say(
        text,
        voice="Polly.Aditi",   # Hindi voice
        language="hi-IN",
    )

    # Listen for the next question
    gather = Gather(
        input="speech",
        language="hi-IN",
        speech_timeout="auto",
        action="/voice/respond",
        method="POST",
    )
    response.append(gather)

    # If silence, say goodbye
    response.say(
        "Dhanyavaad! Agar aur koi sawaal ho toh dubara call karein. Namaste!",
        voice="Polly.Aditi",
        language="hi-IN",
    )

    return PlainTextResponse(
        content=str(response),
        media_type="application/xml",
    )


# ===========================================================
# Run the server
# ===========================================================
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  🌾 KisanCall AI — Starting Server")
    print("=" * 50)
    uvicorn.run(app, host=HOST, port=PORT)
