# ============================================================
# llm.py — Ollama Local LLM Integration
# ============================================================
# Connects to a locally running Ollama server to generate
# responses. Uses the Phi-3 model by default (small, fast).
#
# Ollama must be running: `ollama serve`
# Model must be pulled: `ollama pull phi3`
# ============================================================

import ollama as ollama_client
from config import OLLAMA_MODEL
from prompts import SYSTEM_PROMPT


async def ask_llm(user_message: str, system_override: str = None) -> str:
    """
    Send a message to the local Ollama LLM and get a response.

    Args:
        user_message:    The farmer's query (transcribed speech).
        system_override: Optional override for the system prompt
                         (used when injecting weather data).

    Returns:
        The LLM's response text, cleaned up for speech.
    """
    system_prompt = system_override or SYSTEM_PROMPT

    try:
        # Call Ollama with the chat API
        response = ollama_client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            options={
                "temperature": 0.7,    # Balanced creativity
                "num_predict": 100,    # Limit tokens for short replies
                "top_p": 0.9,
            },
        )

        # Extract the response text
        reply = response["message"]["content"].strip()

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
        # Fallback response if LLM is unavailable
        return (
            "Maaf kijiye, abhi jawaab dene mein dikkat aa rahi hai. "
            "Kripya thodi der baad dobara call karein."
        )
