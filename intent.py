# ============================================================
# intent.py — Simple Intent Detection
# ============================================================
# Detects whether the farmer is asking about weather or
# a general agricultural topic. Uses keyword matching for
# speed — no LLM call needed for classification.
# ============================================================


# Keywords that indicate a weather-related query
WEATHER_KEYWORDS = [
    # English
    "weather", "rain", "barish", "baarish", "temperature", "temp",
    "hot", "cold", "storm", "toofan", "humidity", "forecast",
    "sunny", "cloudy", "wind", "hawa",
    # Hindi / Hinglish
    "mausam", "mausam kaisa", "garmi", "sardi", "dhoop", "badal",
    "paani", "barsaat", "andhi", "loo", "thand",
    "kal mausam", "aaj mausam", "baarish hogi", "rain hoga",
    "pani girega", "baarish aayegi",
]


def detect_intent(user_text: str) -> str:
    """
    Classify the farmer's query into an intent category.

    Args:
        user_text: The transcribed speech from the farmer.

    Returns:
        "weather" if weather-related, otherwise "general".
    """
    # Normalize: lowercase and strip extra spaces
    text = user_text.lower().strip()

    # Check if any weather keyword appears in the text
    for keyword in WEATHER_KEYWORDS:
        if keyword in text:
            return "weather"

    # Default to general agriculture query
    return "general"
