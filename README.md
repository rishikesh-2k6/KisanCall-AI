# 🌾 KisanCall AI — Voice-Based Agricultural Assistant

A real-time voice AI system that helps Indian farmers get agricultural advice through a simple phone call. No smartphone needed — just dial a number and talk.

## 🎯 What It Does

When a farmer calls the KisanCall AI number:
1. **Greets** the farmer in Hindi
2. **Listens** to their question (speech-to-text via Twilio)
3. **Understands** the query (weather, crops, fertilizers, etc.)
4. **Asks follow-ups** if needed (like location for weather)
5. **Fetches real data** (live weather from Open-Meteo)
6. **Responds** in simple Hinglish (text-to-speech via Twilio)

## 🏗️ Architecture

```
Farmer's Phone
     │
     ▼
Twilio (Telephony)
  ┌──────────────────────┐
  │ Speech → Text (STT)  │
  │ Text → Speech (TTS)  │
  └──────┬───────────────┘
         │ Webhook
         ▼
FastAPI Backend (/voice)
  ┌──────────────────────┐
  │ Intent Detection      │
  │ Session Management    │
  │ Response Orchestration│
  └──┬────────────┬──────┘
     │            │
     ▼            ▼
  Ollama       Open-Meteo
  (Local LLM)  (Weather API)
  Phi-3 Model   Free, No Key
```

## 📦 Project Structure

```
agriai/
├── main.py          # FastAPI app — handles Twilio webhooks
├── config.py        # Environment variables and settings
├── intent.py        # Keyword-based intent detection
├── llm.py           # Ollama LLM integration
├── weather.py       # Open-Meteo weather API
├── prompts.py       # System prompt for the AI
├── session.py       # In-memory call session manager
├── requirements.txt # Python dependencies
├── .env.example     # Environment variable template
└── README.md        # This file
```

## 🚀 Setup Guide

### Prerequisites

- Python 3.10+
- [Ollama](https://ollama.ai/) installed and running
- [Twilio Account](https://www.twilio.com/) (free trial works)
- [ngrok](https://ngrok.com/) for local development

### Step 1: Clone and Install

```bash
git clone https://github.com/rishikesh-2k6/KisanCall-AI.git
cd KisanCall-AI

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Set Up Ollama

```bash
# Install Ollama from https://ollama.ai/
# Then pull the Phi-3 model:
ollama pull phi3

# Verify it's running:
ollama list
```

### Step 3: Configure Environment

```bash
# Copy the example env file
copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux

# Edit .env with your Twilio credentials:
# TWILIO_ACCOUNT_SID=ACxxxxxxxxx
# TWILIO_AUTH_TOKEN=xxxxxxxxx
# TWILIO_PHONE_NUMBER=+1xxxxxxxxxx
```

### Step 4: Start the Server

```bash
python main.py
```

Server runs at `http://localhost:8000`

### Step 5: Expose with ngrok

```bash
ngrok http 8000
```

Copy the ngrok URL (e.g., `https://abc123.ngrok-free.app`)

### Step 6: Configure Twilio Webhook

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to **Phone Numbers → Manage → Active Numbers**
3. Click your phone number
4. Under **Voice Configuration**:
   - Set **"A call comes in"** to **Webhook**
   - URL: `https://your-ngrok-url.ngrok-free.app/voice`
   - Method: **POST**
5. Save

### Step 7: Test It!

Call your Twilio phone number from any phone. The AI will greet you and start listening.

## 💬 Example Conversations

```
Farmer: "Kal baarish hogi kya?"
AI:     "Mausam jaanne ke liye aapka gaon ya shehar ka naam bataiye."

Farmer: "Guntur"
AI:     "Kal baarish ki sambhavna hai, fasal mein paani dena band karein."

Farmer: "Meri fasal peeli ho rahi hai"
AI:     "Yeh nitrogen ki kami ho sakti hai. Urea fertilizer use karein."
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/voice` | POST | Handles incoming calls (Twilio webhook) |
| `/voice/respond` | POST | Processes farmer's speech |
| `/voice/status` | POST | Call status callback |
| `/health` | GET | Health check |

## ⚙️ Tech Stack

| Component | Technology |
|---|---|
| Telephony | Twilio (STT + TTS) |
| Backend | FastAPI (Python) |
| LLM | Ollama + Phi-3 |
| Weather | Open-Meteo (free) |
| Tunnel | ngrok |

## 📝 Notes

- **No smartphone needed** — works with any basic phone
- **Open-Meteo** is completely free, no API key required
- **Ollama** runs locally — no cloud LLM costs
- **Twilio free trial** gives you enough credits to test
- Responses are kept to **1-2 sentences** for phone clarity

## 📄 License

MIT License — free to use and modify.
