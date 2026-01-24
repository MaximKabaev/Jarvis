# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Friday is a personal voice AI assistant with a local Python client and cloud FastAPI backend. The client handles wake word detection, speech-to-text (Whisper), LLM interaction (Ollama), and text-to-speech (Piper). The backend stores memories and conversation history in PostgreSQL.

## Architecture

```
frontend/               Local Python client
├── friday/
│   ├── main.py         Entry point, main conversation loop
│   ├── audio/          Wake word (Porcupine), STT (faster-whisper), TTS (Piper)
│   ├── brain/          LLM client (Ollama), memory extraction, prompts
│   └── cloud/          API client, auth token management
└── config.yaml         User configuration (gitignored - contains secrets)

backend/                Cloud FastAPI server
├── app/
│   ├── main.py         FastAPI entry point
│   ├── models/         SQLAlchemy models (User, Memory, Conversation, Message)
│   ├── schemas/        Pydantic schemas
│   ├── routers/        API endpoints (auth, memories, conversations)
│   └── services/       Business logic
└── docker-compose.yml  PostgreSQL + API deployment
```

## Commands

### Backend
```bash
cd backend
docker-compose up              # Start PostgreSQL + API
docker-compose down            # Stop services
docker-compose build --no-cache  # Rebuild after requirements change
```

### Frontend
```bash
cd frontend
python -m venv .venv
.venv\Scripts\activate         # Windows
pip install -r requirements.txt
python -m friday.main          # Run the assistant
```

### Prerequisites
- Ollama running with model: `ollama pull llama3.2`
- Piper TTS model in `frontend/models/piper/`
- Porcupine API key from picovoice.ai

## Key Configuration

`frontend/config.yaml` (copy from `config.example.yaml`):
- `cloud.server_url`: Backend API URL
- `audio.porcupine_access_key`: Wake word API key
- `audio.wake_word`: Must be a built-in Porcupine keyword (jarvis, computer, alexa, etc.)
- `tts.model_path`: Path to Piper ONNX model
- `llm.model`: Ollama model name

## Data Flow

1. Wake word detected (Porcupine) → Record audio
2. Speech-to-text (faster-whisper) → User text
3. Fetch relevant memories from cloud → Build prompt
4. LLM generates response (Ollama) → Response text
5. Save conversation to cloud
6. Text-to-speech (Piper) → Play audio

## API Authentication

Backend uses JWT tokens. Register user once, then login:
```bash
curl -X POST http://localhost:8000/auth/register -H "Content-Type: application/json" \
  -d '{"username": "user", "email": "email@example.com", "password": "pass"}'
```

Frontend auto-authenticates using credentials from `config.yaml`.
