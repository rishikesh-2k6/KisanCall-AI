# ============================================================
# main.py — FastAPI Application for KisanCall AI (Multilingual)
# ============================================================
#
# CALL FLOW:
#   1. Farmer calls Twilio number
#   2. /voice → Language selection menu (press 1-9)
#   3. /voice/language → Stores language, greets in chosen lang
#   4. Farmer speaks → Twilio transcribes → POST /voice/respond
#   5. Backend detects intent, calls LLM, returns TwiML
#   6. Twilio speaks the response and listens again
#
# Supports: Hindi, Telugu, Tamil, Bengali, Marathi,
#           Gujarati, Kannada, Malayalam, English
# ============================================================

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse, HTMLResponse
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.rest import Client as TwilioClient

from config import HOST, PORT, TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, MY_PHONE_NUMBER
from intent import detect_intent
from weather import get_weather_for_place
from llm import ask_llm
from prompts import (
    get_system_prompt, build_weather_prompt,
    GREETINGS, LOCATION_ASK, LOCATION_NOT_FOUND,
    GOODBYE, SILENCE_PROMPT,
)
from languages import (
    get_language, get_language_by_dtmf,
    build_language_menu_text, DEFAULT_LANGUAGE,
)
from session import get_session, clear_session

# ── Create FastAPI App ───────────────────────────────────
app = FastAPI(
    title="KisanCall AI",
    description="Multilingual voice-based agricultural assistant for Indian farmers",
    version="2.0.0",
)


# ===========================================================
# HELPER: Build TwiML <Say> with correct language/voice
# ===========================================================
def _say(response: VoiceResponse, text: str, lang_code: str = "hi"):
    """
    Add a <Say> element with the correct voice and language.

    Uses Polly.Aditi for Hindi/English, basic TTS for others.
    """
    lang_config = get_language(lang_code)
    voice = lang_config.get("tts_voice")
    tts_lang = lang_config.get("tts_lang", "hi-IN")

    if voice:
        response.say(text, voice=voice, language=tts_lang)
    else:
        # For languages without a Polly voice, use basic TTS
        response.say(text, language=tts_lang)


def _build_listen_response(text: str, lang_code: str = "hi") -> PlainTextResponse:
    """
    Creates a TwiML response that:
      1. Speaks the AI's reply in the farmer's language
      2. Starts listening for the next question

    Args:
        text:      The AI's response to speak.
        lang_code: The farmer's selected language code.

    Returns:
        PlainTextResponse with TwiML XML.
    """
    lang_config = get_language(lang_code)
    stt_code = lang_config.get("stt_code", "hi-IN")

    response = VoiceResponse()

    # Speak the AI's response
    _say(response, text, lang_code)

    # Listen for the next question in the farmer's language
    gather = Gather(
        input="speech",
        language=stt_code,
        speech_timeout="auto",
        action="/voice/respond",
        method="POST",
    )
    response.append(gather)

    # If silence, say goodbye
    _say(response, GOODBYE.get(lang_code, GOODBYE["hi"]), lang_code)

    return PlainTextResponse(
        content=str(response),
        media_type="application/xml",
    )


# ===========================================================
# ENDPOINT 1: /voice — Language Selection Menu
# ===========================================================
@app.post("/voice", response_class=PlainTextResponse)
async def handle_incoming_call(request: Request):
    """
    Called by Twilio when a farmer dials the number.
    Plays a language selection menu (press 1-9).
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")

    # Create a fresh session
    session = get_session(call_sid)
    session.is_first_turn = True

    response = VoiceResponse()

    # Play language selection menu
    # Use Gather with DTMF input (keypad presses)
    gather = Gather(
        input="dtmf",
        num_digits=1,
        timeout=10,
        action="/voice/language",
        method="POST",
    )
    gather.say(
        build_language_menu_text(),
        voice="Polly.Aditi",
        language="hi-IN",
    )
    response.append(gather)

    # If no input, default to Hindi
    response.say(
        "Koi button nahi daba, Hindi mein madad karunga.",
        voice="Polly.Aditi",
        language="hi-IN",
    )
    response.redirect("/voice/default-hindi", method="POST")

    return PlainTextResponse(
        content=str(response),
        media_type="application/xml",
    )


# ===========================================================
# ENDPOINT 2: /voice/language — Handle Language Selection
# ===========================================================
@app.post("/voice/language", response_class=PlainTextResponse)
async def handle_language_selection(request: Request):
    """
    Called after the farmer presses a digit to select language.
    Stores the language and greets in the chosen language.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")
    digit = form_data.get("Digits", "1")

    # Look up the language by keypad digit
    lang_config = get_language_by_dtmf(digit)
    if not lang_config:
        # Invalid digit — default to Hindi
        lang_config = get_language(DEFAULT_LANGUAGE)
        lang_config["code"] = DEFAULT_LANGUAGE

    lang_code = lang_config["code"]

    # Store language in session
    session = get_session(call_sid)
    session.language = lang_code
    session.language_selected = True

    print(f"[Call {call_sid}] Language selected: {lang_config['name']} ({lang_code})")

    # Greet in the chosen language and start listening
    greeting = GREETINGS.get(lang_code, GREETINGS["hi"])
    return _build_listen_response(greeting, lang_code)


# ===========================================================
# ENDPOINT 3: /voice/default-hindi — Fallback to Hindi
# ===========================================================
@app.post("/voice/default-hindi", response_class=PlainTextResponse)
async def handle_default_hindi(request: Request):
    """
    Fallback when farmer doesn't press any digit.
    Defaults to Hindi and starts listening.
    """
    form_data = await request.form()
    call_sid = form_data.get("CallSid", "unknown")

    session = get_session(call_sid)
    session.language = "hi"
    session.language_selected = True

    print(f"[Call {call_sid}] No language selected, defaulting to Hindi")

    greeting = GREETINGS["hi"]
    return _build_listen_response(greeting, "hi")


# ===========================================================
# ENDPOINT 4: /voice/respond — Processes farmer's speech
# ===========================================================
@app.post("/voice/respond", response_class=PlainTextResponse)
async def handle_speech(request: Request):
    """
    Called by Twilio after the farmer speaks.
    Processes speech, detects intent, generates response
    in the farmer's selected language.
    """
    form_data = await request.form()

    # Get the transcribed text from Twilio
    user_speech = form_data.get("SpeechResult", "")
    call_sid = form_data.get("CallSid", "unknown")

    # Get the session and language
    session = get_session(call_sid)
    lang = session.language
    session.is_first_turn = False

    print(f"\n[Call {call_sid}] [{lang}] Farmer said: \"{user_speech}\"")

    # ── Step 1: Check if this is a follow-up (location answer) ──
    if session.pending_intent == "weather_needs_location":
        location_name = user_speech.strip()
        print(f"[Call {call_sid}] Location received: {location_name}")

        # Fetch real weather data
        weather_data = await get_weather_for_place(location_name)

        if weather_data:
            # Build a prompt with real weather data in the right language
            system_prompt = get_system_prompt(lang)
            weather_prompt = build_weather_prompt(
                session.pending_query, weather_data, lang
            )
            ai_reply = await ask_llm(
                user_message=session.pending_query,
                system_override=system_prompt + "\n\n" + weather_prompt,
            )
        else:
            ai_reply = LOCATION_NOT_FOUND.get(lang, LOCATION_NOT_FOUND["hi"])
            return _build_listen_response(ai_reply, lang)

        # Clear the pending state
        session.pending_intent = None
        session.pending_query = None

        print(f"[Call {call_sid}] AI reply: \"{ai_reply}\"")
        return _build_listen_response(ai_reply, lang)

    # ── Step 2: Detect intent from speech ────────────────────
    intent = detect_intent(user_speech)
    print(f"[Call {call_sid}] Detected intent: {intent}")

    # ── Step 3: Handle weather intent ────────────────────────
    if intent == "weather":
        session.pending_intent = "weather_needs_location"
        session.pending_query = user_speech

        ai_reply = LOCATION_ASK.get(lang, LOCATION_ASK["hi"])
        print(f"[Call {call_sid}] Asking for location in {lang}...")
        return _build_listen_response(ai_reply, lang)

    # ── Step 4: Handle general agriculture queries ───────────
    system_prompt = get_system_prompt(lang)
    ai_reply = await ask_llm(
        user_message=user_speech,
        system_override=system_prompt,
    )
    print(f"[Call {call_sid}] AI reply: \"{ai_reply}\"")

    return _build_listen_response(ai_reply, lang)


# ===========================================================
# ENDPOINT 5: /voice/status — Call status callback
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
# ENDPOINT 6: /health — Health check
# ===========================================================
@app.get("/health")
async def health_check():
    """Simple health check for monitoring."""
    return {
        "status": "ok",
        "service": "KisanCall AI",
        "version": "2.0.0",
        "multilingual": True,
        "languages": ["hi", "te", "ta", "bn", "mr", "gu", "kn", "ml", "en"],
    }


# ===========================================================
# ENDPOINT 7: /call-me — Trigger outbound call to your phone
# ===========================================================
@app.get("/call-me")
async def call_me_page():
    """
    Simple web page with a button to trigger a call.
    Open http://localhost:8000/call-me in your browser.
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>KisanCall AI — Test Call</title>
        <style>
            body { font-family: Arial, sans-serif; background: #1a1a2e; color: #eee;
                   display: flex; justify-content: center; align-items: center;
                   min-height: 100vh; margin: 0; }
            .card { background: #16213e; padding: 40px; border-radius: 16px;
                    text-align: center; box-shadow: 0 8px 32px rgba(0,0,0,0.3); }
            h1 { color: #4ecca3; margin-bottom: 8px; }
            p { color: #aaa; margin-bottom: 24px; }
            button { background: #4ecca3; color: #1a1a2e; border: none;
                     padding: 16px 48px; font-size: 18px; border-radius: 8px;
                     cursor: pointer; font-weight: bold; }
            button:hover { background: #3db88c; }
            #status { margin-top: 20px; font-size: 14px; color: #4ecca3; }
        </style>
    </head>
    <body>
        <div class="card">
            <h1>🌾 KisanCall AI</h1>
            <p>Click the button below — AI will call your phone!</p>
            <button onclick="makeCall()">📞 Call Me Now</button>
            <div id="status"></div>
        </div>
        <script>
            async function makeCall() {
                document.getElementById('status').innerText = '📞 Calling...';
                try {
                    const res = await fetch('/call-me/trigger', { method: 'POST' });
                    const data = await res.json();
                    if (data.success) {
                        document.getElementById('status').innerText =
                            '✅ Call initiated! Pick up your phone.';
                    } else {
                        document.getElementById('status').innerText =
                            '❌ Error: ' + data.error;
                    }
                } catch (e) {
                    document.getElementById('status').innerText = '❌ Server error';
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


@app.post("/call-me/trigger")
async def trigger_call(request: Request):
    """
    Triggers an outbound call from Twilio to your phone.
    Twilio calls YOUR number, and when you pick up,
    the /voice endpoint handles the conversation.
    """
    try:
        # Determine the base URL for webhooks
        # Use the Host header from the request (works with ngrok)
        host = request.headers.get("host", f"localhost:{PORT}")
        scheme = request.headers.get("x-forwarded-proto", "http")
        base_url = f"{scheme}://{host}"

        if not MY_PHONE_NUMBER or MY_PHONE_NUMBER == "+91XXXXXXXXXX":
            return {
                "success": False,
                "error": "Set MY_PHONE_NUMBER in .env file first! (e.g., +919876543210)"
            }

        # Create Twilio client and make the call
        client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

        call = client.calls.create(
            to=MY_PHONE_NUMBER,              # Your Indian phone number
            from_=TWILIO_PHONE_NUMBER,        # Your Twilio US number
            url=f"{base_url}/voice",          # Same webhook as incoming calls
            status_callback=f"{base_url}/voice/status",
        )

        print(f"\n[Outbound Call] Calling {MY_PHONE_NUMBER}...")
        print(f"[Outbound Call] Call SID: {call.sid}")

        return {
            "success": True,
            "call_sid": call.sid,
            "calling": MY_PHONE_NUMBER,
        }

    except Exception as e:
        print(f"[Call Error] {e}")
        return {"success": False, "error": str(e)}


# ===========================================================
# Run the server
# ===========================================================
if __name__ == "__main__":
    import uvicorn
    print("=" * 50)
    print("  🌾 KisanCall AI v2.0 — Multilingual")
    print("  Languages: HI TE TA BN MR GU KN ML EN")
    print(f"  Call-Me: http://localhost:{PORT}/call-me")
    print("=" * 50)
    uvicorn.run(app, host=HOST, port=PORT)
