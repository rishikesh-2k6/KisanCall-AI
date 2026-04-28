# ============================================================
# languages.py — Multilingual Configuration for KisanCall AI
# ============================================================
# Maps supported Indian languages to their Twilio STT codes,
# TTS voices, and display names.
#
# Twilio uses Amazon Polly voices for TTS and Google/Deepgram
# for STT. Not all Indian languages have dedicated Polly
# voices, so we fall back to Google TTS where needed.
# ============================================================


# Each language entry contains:
#   - name:       Human-readable name
#   - native:     Name in native script (for reference)
#   - stt_code:   Twilio speech recognition language code
#   - tts_voice:  Amazon Polly voice name (or None for basic TTS)
#   - tts_lang:   Language code for Twilio <Say> element
#   - dtmf:       Keypad digit to select this language

SUPPORTED_LANGUAGES = {
    "hi": {
        "name": "Hindi",
        "native": "हिन्दी",
        "stt_code": "hi-IN",
        "tts_voice": "Polly.Aditi",
        "tts_lang": "hi-IN",
        "dtmf": "1",
    },
    "te": {
        "name": "Telugu",
        "native": "తెలుగు",
        "stt_code": "te-IN",
        "tts_voice": None,          # No Polly voice — use basic TTS
        "tts_lang": "te-IN",
        "dtmf": "2",
    },
    "ta": {
        "name": "Tamil",
        "native": "தமிழ்",
        "stt_code": "ta-IN",
        "tts_voice": None,
        "tts_lang": "ta-IN",
        "dtmf": "3",
    },
    "bn": {
        "name": "Bengali",
        "native": "বাংলা",
        "stt_code": "bn-IN",
        "tts_voice": None,
        "tts_lang": "bn-IN",
        "dtmf": "4",
    },
    "mr": {
        "name": "Marathi",
        "native": "मराठी",
        "stt_code": "mr-IN",
        "tts_voice": None,
        "tts_lang": "mr-IN",
        "dtmf": "5",
    },
    "gu": {
        "name": "Gujarati",
        "native": "ગુજરાતી",
        "stt_code": "gu-IN",
        "tts_voice": None,
        "tts_lang": "gu-IN",
        "dtmf": "6",
    },
    "kn": {
        "name": "Kannada",
        "native": "ಕನ್ನಡ",
        "stt_code": "kn-IN",
        "tts_voice": None,
        "tts_lang": "kn-IN",
        "dtmf": "7",
    },
    "ml": {
        "name": "Malayalam",
        "native": "മലയാളം",
        "stt_code": "ml-IN",
        "tts_voice": None,
        "tts_lang": "ml-IN",
        "dtmf": "8",
    },
    "en": {
        "name": "English",
        "native": "English",
        "stt_code": "en-IN",
        "tts_voice": "Polly.Aditi",  # Aditi speaks English too
        "tts_lang": "en-IN",
        "dtmf": "9",
    },
}

# Default language if none selected
DEFAULT_LANGUAGE = "hi"


def get_language_by_dtmf(digit: str) -> dict | None:
    """
    Look up language config by the keypad digit pressed.

    Args:
        digit: The DTMF digit pressed by the farmer (1-9).

    Returns:
        Language config dict, or None if invalid digit.
    """
    for lang_code, config in SUPPORTED_LANGUAGES.items():
        if config["dtmf"] == digit:
            return {**config, "code": lang_code}
    return None


def get_language(lang_code: str) -> dict:
    """
    Get language config by language code.

    Args:
        lang_code: Two-letter language code (e.g., "hi", "te").

    Returns:
        Language config dict with defaults if not found.
    """
    config = SUPPORTED_LANGUAGES.get(lang_code, SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])
    return {**config, "code": lang_code}


def build_language_menu_text() -> str:
    """
    Build the spoken text for the language selection menu.
    Uses each language's native greeting so farmers can
    recognize their language.
    """
    lines = [
        "Namaste! Welcome to Kisan Mitra.",
        "Please select your language. Apni bhasha chunein.",
        "",
        "Hindi ke liye 1 dabaiye.",
        "Telugu kosam 2 noppandi.",
        "Tamil-ukku 3 azhuttavum.",
        "Bangla-r jonyo 4 tipun.",
        "Marathi sathi 5 daba.",
        "Gujarati mate 6 dabaavo.",
        "Kannada-kke 7 otti.",
        "Malayalam-inu 8 amartuka.",
        "For English press 9.",
    ]
    return " ".join(lines)
