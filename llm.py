# ============================================================
# llm.py - Groq Cloud LLM Integration
# ============================================================
# Connects to Groq's ultra-fast inference API.
# Uses Llama 3.1 8B Instant model (fast, free tier available).
#
# Groq provides ~10x faster inference than local Ollama,
# which is critical for real-time phone call responses.
#
# Get your API key at: https://console.groq.com
# ============================================================

import httpx
from config import GROQ_API_KEY, GROQ_MODEL
from prompts import SYSTEM_PROMPT

# Groq API endpoint
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


async def ask_llm(user_message: str, system_override: str = None) -> str:
    """
    Send a message to Groq's LLM and get a response.

    Args:
        user_message:    The farmer's query (transcribed speech).
        system_override: Optional override for the system prompt
                         (used when injecting weather data).

    Returns:
        The LLM's response text, cleaned up for speech.
    """
    system_prompt = system_override or SYSTEM_PROMPT

    try:
        # Build the request payload (OpenAI-compatible format)
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.7,
            "max_tokens": 150,       # Keep responses short for phone calls
            "top_p": 0.9,
        }

        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        }

        # Make async HTTP request to Groq API
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                GROQ_API_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

        # Extract the response text
        reply = data["choices"][0]["message"]["content"].strip()

        # Clean up for speech: remove markdown artifacts
        reply = reply.replace("*", "").replace("#", "").replace("_", "")

        # Ensure response isn't too long for a phone call
        # (Split into sentences and keep first two)
        sentences = reply.replace("।", ".").split(".")
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) > 2:
            reply = ". ".join(sentences[:2]) + "."

        return reply

    except Exception as e:
        print(f"[LLM Error] {e}")
        # Fallback response if Groq API is unavailable
        return (
            "Maaf kijiye, abhi jawaab dene mein dikkat aa rahi hai. "
            "Kripya thodi der baad dobara call karein."
        )
