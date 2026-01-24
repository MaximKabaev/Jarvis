# Friday AI Assistant - MVP v1.0 Specification

## Document Info
- **Version**: 1.0 MVP
- **Created**: January 24, 2026
- **Purpose**: Implementation guide for Claude Code

---

## 1. Project Overview

### 1.1 What is Friday?
Friday is a personal voice AI assistant (inspired by Iron Man's FRIDAY) that listens for a wake word, understands speech, responds verbally, and remembers information across sessions via cloud storage.

### 1.2 MVP Goal
Prove the core concept works:
- Voice pipeline functions end-to-end (wake → listen → think → speak)
- Cloud memory persists across sessions
- Conversations feel natural

### 1.3 MVP Scope - ONLY These Features

| Feature | In MVP | Notes |
|---------|--------|-------|
| Wake word detection | ✅ | "Hey Friday" activates listening |
| Speech-to-text | ✅ | Convert user speech to text |
| LLM conversation | ✅ | Generate intelligent responses |
| Text-to-speech | ✅ | Speak responses aloud |
| Memory - store | ✅ | "Remember that X" saves to cloud |
| Memory - recall | ✅ | "What's my X" retrieves from cloud |
| Conversation history | ✅ | Stored on cloud for context |
| Keyboard shortcut | ✅ | Alternative to wake word |

### 1.4 Explicitly NOT in MVP

- ❌ Opening applications
- ❌ System commands (volume, screenshot, etc.)
- ❌ Timers
- ❌ Reminders
- ❌ Web search
- ❌ File search
- ❌ Multi-device sync (infrastructure only)
- ❌ Settings UI
- ❌ Any third-party integrations

---

## 2. System Architecture

### 2.1 Overview

```
LOCAL CLIENT (Windows PC)              CLOUD SERVER (VPS)
┌────────────────────────┐            ┌────────────────────┐
│                        │            │                    │
│  [Microphone]          │            │    [FastAPI]       │
│       │                │            │        │           │
│       ▼                │            │        ▼           │
│  [Wake Word]           │            │   [PostgreSQL]     │
│  (Porcupine)           │            │   - memories       │
│       │                │            │   - conversations  │
│       ▼                │            │   - messages       │
│  [Speech-to-Text]      │   HTTPS    │                    │
│  (Faster Whisper)      │◄──────────►│                    │
│       │                │            │                    │
│       ▼                │            └────────────────────┘
│  [LLM Brain]           │
│  (Ollama + Llama)      │
│       │                │
│       ▼                │
│  [Text-to-Speech]      │
│  (Piper)               │
│       │                │
│       ▼                │
│  [Speaker]             │
│                        │
└────────────────────────┘
```

### 2.2 Data Flow

```
1. User says "Hey Friday"
2. Wake word detector triggers
3. Play activation sound
4. Listen for user speech (max 10 seconds)
5. Convert speech to text (Whisper)
6. Fetch relevant memories from cloud
7. Build prompt with memories + conversation history
8. Send to LLM, get response
9. Check if response contains new memory to store
10. Save conversation turn to cloud
11. Convert response to speech (Piper)
12. Play audio response
13. Return to wake word listening
```

---

## 3. Local Client Specification

### 3.1 Technology Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Language | Python 3.11+ | Ecosystem, ease of use |
| Wake word | Porcupine (Picovoice) | Accurate, lightweight, free tier available |
| Speech-to-text | faster-whisper | Fast, runs on GPU, good accuracy |
| STT model | large-v3-turbo | Best speed/accuracy balance for 16GB VRAM |
| LLM runtime | Ollama | Easy local LLM management |
| LLM model | Llama 3.3 70B Q4_K_M | Strong reasoning, fits in 16GB VRAM |
| Text-to-speech | Piper | Fast, natural sounding, runs on CPU |
| Audio input | sounddevice | Cross-platform audio capture |
| Audio output | sounddevice or pygame | Audio playback |
| HTTP client | httpx | Async HTTP requests |
| Config | PyYAML | Configuration file parsing |

### 3.2 Module Structure

```
friday/
├── main.py                 # Entry point, main loop
├── config.py               # Load and validate configuration
├── audio/
│   ├── wake_word.py        # Porcupine wake word detection
│   ├── listener.py         # Record audio after wake word
│   ├── stt.py              # Speech-to-text with Whisper
│   └── tts.py              # Text-to-speech with Piper
├── brain/
│   ├── llm.py              # Ollama LLM interaction
│   ├── memory.py           # Memory extraction and injection
│   └── prompts.py          # System prompts and templates
├── cloud/
│   ├── client.py           # API client for cloud server
│   ├── auth.py             # Authentication handling
│   └── sync.py             # Sync memories and conversations
├── utils/
│   ├── audio_utils.py      # Audio format conversion, VAD
│   └── logging.py          # Logging setup
└── config.yaml             # User configuration
```

### 3.3 Wake Word Detection

**Library**: Porcupine by Picovoice

**Behavior**:
- Runs continuously in background
- Listens for "Hey Friday" (or closest available, e.g., "Hey Google" modified, or custom if Picovoice account allows)
- On detection: trigger listening state
- Alternative: Keyboard shortcut (default Ctrl+Shift+F)

**Implementation approach**:
- Run Porcupine in a dedicated thread
- Use callback pattern to trigger main pipeline
- Keep CPU usage minimal (<2% when idle)

**Fallback**: If Porcupine free tier doesn't support custom wake word, use "Jarvis" or "Computer" from their built-in options, or implement simple keyboard shortcut only for MVP.

### 3.4 Audio Listener

**Purpose**: Record user speech after wake word triggers

**Behavior**:
- Start recording immediately after wake word
- Use Voice Activity Detection (VAD) to detect speech end
- Maximum recording duration: 10 seconds
- Minimum speech duration: 0.5 seconds
- Stop on 1.5 seconds of silence

**Audio format**:
- Sample rate: 16000 Hz
- Channels: Mono
- Format: 16-bit PCM (int16)
- Output: NumPy array

**Implementation approach**:
- Use sounddevice for audio capture
- Use webrtcvad or silero-vad for voice activity detection
- Buffer audio in memory, return complete utterance

### 3.5 Speech-to-Text

**Library**: faster-whisper

**Model**: large-v3-turbo

**Behavior**:
- Receive audio array from listener
- Transcribe to text
- Return transcription string

**Implementation approach**:
- Load model once at startup (keep in VRAM)
- Use CUDA for inference
- Use beam_size=5 for accuracy
- Return text with basic punctuation

**Resource management**:
- Model stays loaded while app is running
- Uses approximately 6GB VRAM

### 3.6 LLM Brain

**Runtime**: Ollama

**Model**: llama3.3:70b-instruct-q4_K_M

**Behavior**:
- Receive user text + relevant memories + recent conversation
- Generate appropriate response
- Detect if user wants to store a memory
- Return response text

**System prompt** (store in prompts.py):
```
You are Friday, a personal AI assistant. You are helpful, concise, and have a slightly witty personality.

Key behaviors:
- Keep responses brief and conversational (1-3 sentences typically)
- You have access to stored memories about the user (provided in context)
- If the user asks you to remember something, confirm you'll remember it
- If the user asks about something you have in memory, use that information
- Be natural - don't constantly remind the user you're an AI

Current memories about user:
{memories}

Recent conversation:
{conversation_history}
```

**Memory detection**:
- If user says "remember that...", "don't forget...", "note that...", "keep in mind..." → extract and flag for storage
- Use simple keyword detection, not LLM-based extraction for MVP

**Implementation approach**:
- Use Ollama Python library or HTTP API
- Stream responses for lower perceived latency
- Context window: last 10 conversation turns

### 3.7 Text-to-Speech

**Library**: Piper

**Voice**: en_US-amy-medium (or en_US-lessac-medium)

**Behavior**:
- Receive response text
- Convert to audio
- Play through speakers

**Implementation approach**:
- Load Piper model once at startup
- Generate WAV audio in memory
- Play using sounddevice or pygame
- Runs on CPU (doesn't compete with GPU models)

### 3.8 Cloud Client

**Purpose**: Communicate with cloud server API

**Responsibilities**:
- Authenticate and manage JWT token
- CRUD operations for memories
- Save/retrieve conversation history
- Handle offline gracefully

**Implementation approach**:
- Use httpx with async support
- Retry logic for transient failures
- Cache auth token locally
- Queue writes if offline, sync when back online

### 3.9 Configuration File

**Location**: `config.yaml` in app directory

**Contents**:
```yaml
# Cloud server
cloud:
  server_url: "https://your-friday-server.com"
  
# Audio settings
audio:
  input_device: null  # null = default
  output_device: null
  
# Wake word
wake_word:
  enabled: true
  sensitivity: 0.5
  
# Keyboard shortcut
hotkey:
  enabled: true
  combination: "ctrl+shift+f"

# Models (informational, paths managed by Ollama/Piper)
models:
  whisper: "large-v3-turbo"
  llm: "llama3.3:70b-instruct-q4_K_M"
  tts_voice: "en_US-amy-medium"
```

### 3.10 Main Loop

**Pseudocode logic**:
```
1. Load configuration
2. Initialize components (wake word, STT, LLM, TTS, cloud client)
3. Authenticate with cloud server
4. Start wake word detection thread
5. Main loop:
   a. Wait for wake word trigger OR hotkey
   b. Play activation sound
   c. Record user speech
   d. If no speech detected, play "didn't catch that" and continue
   e. Transcribe speech to text
   f. Fetch relevant memories from cloud
   g. Fetch recent conversation history from cloud
   h. Build LLM prompt
   i. Generate response
   j. If memory storage detected, save to cloud
   k. Save conversation turn to cloud
   l. Speak response
   m. Return to waiting state
```

---

## 4. Cloud Server Specification

### 4.1 Technology Stack

| Component | Technology | Why |
|-----------|------------|-----|
| Language | Python 3.11+ | Match client, fast development |
| Framework | FastAPI | Modern, async, auto-docs |
| Database | PostgreSQL | Reliable, good for structured data |
| ORM | SQLAlchemy 2.0 | Async support, migrations |
| Migrations | Alembic | Database schema versioning |
| Auth | JWT (python-jose) | Stateless authentication |
| Validation | Pydantic | Built into FastAPI |
| Server | Uvicorn | ASGI server |

### 4.2 Project Structure

```
server/
├── main.py                 # FastAPI app entry point
├── config.py               # Environment configuration
├── database.py             # Database connection setup
├── models/
│   ├── user.py             # User SQLAlchemy model
│   ├── memory.py           # Memory SQLAlchemy model
│   ├── conversation.py     # Conversation SQLAlchemy model
│   └── message.py          # Message SQLAlchemy model
├── schemas/
│   ├── user.py             # User Pydantic schemas
│   ├── memory.py           # Memory Pydantic schemas
│   ├── conversation.py     # Conversation Pydantic schemas
│   └── message.py          # Message Pydantic schemas
├── routers/
│   ├── auth.py             # Authentication endpoints
│   ├── memories.py         # Memory CRUD endpoints
│   └── conversations.py    # Conversation endpoints
├── services/
│   ├── auth.py             # Auth business logic
│   ├── memory.py           # Memory business logic
│   └── conversation.py     # Conversation business logic
├── middleware/
│   └── auth.py             # JWT validation middleware
├── alembic/                # Database migrations
│   └── versions/
├── alembic.ini
└── requirements.txt
```

### 4.3 Database Schema

**Users table**:
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | Primary key |
| username | VARCHAR(50) | Unique, not null |
| password_hash | VARCHAR(255) | Not null |
| created_at | TIMESTAMP | Default now |

**Memories table**:
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key → users |
| key | VARCHAR(255) | Not null |
| value | TEXT | Not null |
| category | VARCHAR(50) | Nullable (personal, work, etc.) |
| created_at | TIMESTAMP | Default now |
| updated_at | TIMESTAMP | Default now |
| is_active | BOOLEAN | Default true |

**Conversations table**:
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID | Foreign key → users |
| started_at | TIMESTAMP | Default now |
| last_message_at | TIMESTAMP | Default now |

**Messages table**:
| Column | Type | Constraints |
|--------|------|-------------|
| id | UUID | Primary key |
| conversation_id | UUID | Foreign key → conversations |
| role | VARCHAR(20) | Not null (user/assistant) |
| content | TEXT | Not null |
| created_at | TIMESTAMP | Default now |

### 4.4 API Endpoints

#### Authentication

**POST /auth/register**
- Purpose: Create new user (run once during setup)
- Body: `{ "username": "string", "password": "string" }`
- Response: `{ "id": "uuid", "username": "string" }`
- Notes: Disable after initial user created, or require admin token

**POST /auth/login**
- Purpose: Get JWT token
- Body: `{ "username": "string", "password": "string" }`
- Response: `{ "access_token": "string", "token_type": "bearer" }`

**POST /auth/refresh**
- Purpose: Refresh JWT token
- Headers: `Authorization: Bearer <token>`
- Response: `{ "access_token": "string", "token_type": "bearer" }`

#### Memories

**GET /memories**
- Purpose: List all active memories for user
- Headers: `Authorization: Bearer <token>`
- Response: `[{ "id": "uuid", "key": "string", "value": "string", "category": "string", "created_at": "datetime" }]`

**GET /memories/search?q={query}**
- Purpose: Search memories by key or value
- Headers: `Authorization: Bearer <token>`
- Query: `q` - search term
- Response: Array of matching memories

**POST /memories**
- Purpose: Create new memory
- Headers: `Authorization: Bearer <token>`
- Body: `{ "key": "string", "value": "string", "category": "string (optional)" }`
- Response: Created memory object

**DELETE /memories/{id}**
- Purpose: Soft delete memory (set is_active = false)
- Headers: `Authorization: Bearer <token>`
- Response: `{ "success": true }`

#### Conversations

**POST /conversations**
- Purpose: Start new conversation
- Headers: `Authorization: Bearer <token>`
- Response: `{ "id": "uuid", "started_at": "datetime" }`

**GET /conversations/recent?limit={n}**
- Purpose: Get recent conversations
- Headers: `Authorization: Bearer <token>`
- Query: `limit` - number of conversations (default 10)
- Response: Array of conversations with messages

**GET /conversations/{id}/messages**
- Purpose: Get messages for a conversation
- Headers: `Authorization: Bearer <token>`
- Response: Array of messages

**POST /conversations/{id}/messages**
- Purpose: Add message to conversation
- Headers: `Authorization: Bearer <token>`
- Body: `{ "role": "user|assistant", "content": "string" }`
- Response: Created message object

**GET /conversations/context?limit={n}**
- Purpose: Get last N messages across recent conversations for context
- Headers: `Authorization: Bearer <token>`
- Query: `limit` - number of message pairs (default 10)
- Response: Array of messages ordered by time

### 4.5 Authentication Flow

1. Client sends username/password to `/auth/login`
2. Server validates credentials, returns JWT token
3. Client stores token locally (in memory or encrypted file)
4. Client includes token in all subsequent requests
5. Token expires after 7 days
6. Client refreshes token before expiry using `/auth/refresh`

**JWT payload**:
```json
{
  "sub": "user_uuid",
  "username": "string",
  "exp": "expiry_timestamp"
}
```

### 4.6 Error Responses

All errors return JSON:
```json
{
  "detail": "Error message description"
}
```

| Status Code | Meaning |
|-------------|---------|
| 400 | Bad request (validation error) |
| 401 | Unauthorized (invalid/missing token) |
| 404 | Resource not found |
| 500 | Server error |

---

## 5. Deployment

### 5.1 Cloud Server Deployment

**Target**: Cheap VPS (~$5-6/month)

**Recommended providers**:
- Hetzner CX22 (€4.50/month) - 2 vCPU, 4GB RAM
- Vultr (($6/month) - 1 vCPU, 1GB RAM
- DigitalOcean ($6/month) - 1 vCPU, 1GB RAM

**Deployment approach**:
1. Use Docker Compose for easy deployment
2. Use Caddy as reverse proxy (automatic HTTPS)
3. PostgreSQL in container with volume for persistence

**Docker services**:
- `api` - FastAPI application
- `db` - PostgreSQL database
- `caddy` - Reverse proxy with auto-SSL

**Environment variables needed**:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - JWT signing key (generate random 256-bit)
- `ALLOWED_ORIGINS` - CORS origins (client IP or *)

### 5.2 Local Client Setup

**Prerequisites**:
1. Windows 10/11 64-bit
2. Python 3.11+
3. NVIDIA GPU with 16GB VRAM
4. CUDA 12.1+ and cuDNN installed
5. Ollama installed and running

**Setup steps**:
1. Clone repository
2. Create virtual environment: `python -m venv venv`
3. Activate: `venv\Scripts\activate`
4. Install requirements: `pip install -r requirements.txt`
5. Download Piper voice model to `models/` directory
6. Pull Ollama model: `ollama pull llama3.3:70b-instruct-q4_K_M`
7. Copy `config.example.yaml` to `config.yaml`
8. Edit `config.yaml` with cloud server URL
9. Run: `python -m friday.main`

**First run**:
- Prompts for cloud server credentials
- Tests connection to cloud server
- Verifies all models are loaded
- Starts wake word detection

---

## 6. User Interaction Examples

### 6.1 Basic Conversation

```
User: "Hey Friday"
Friday: *activation sound*
User: "What's the capital of France?"
Friday: "Paris is the capital of France."
```

### 6.2 Storing Memory

```
User: "Hey Friday"
Friday: *activation sound*
User: "Remember that my favorite color is blue"
Friday: "Got it, I'll remember your favorite color is blue."

[Memory saved to cloud: key="favorite color", value="blue"]
```

### 6.3 Recalling Memory

```
User: "Hey Friday"
Friday: *activation sound*
User: "What's my favorite color?"
Friday: "Your favorite color is blue."
```

### 6.4 Contextual Conversation

```
User: "Hey Friday"
Friday: *activation sound*
User: "I'm working on a gripper mechanism design"
Friday: "Nice! What kind of gripper are you building?"

User: "Hey Friday"
Friday: *activation sound*
User: "It's for picking up small tubes"
Friday: "Interesting - for the gripper mechanism, are these rigid tubes or flexible ones?"

[Context maintained across exchanges]
```

### 6.5 Memory with Context

```
User: "Hey Friday"
Friday: *activation sound*
User: "Remember that my project deadline is February 15th"
Friday: "Noted - your project deadline is February 15th."

[Later session]

User: "Hey Friday"
Friday: *activation sound*
User: "When's my deadline?"
Friday: "Your project deadline is February 15th."
```

---

## 7. Success Criteria for MVP

### 7.1 Functional Requirements

| Requirement | Test |
|-------------|------|
| Wake word activates listening | Say "Hey Friday" from 2m away, system responds |
| Hotkey activates listening | Press Ctrl+Shift+F, system responds |
| Speech is transcribed correctly | 90%+ accuracy on clear speech |
| LLM generates relevant responses | Responses are coherent and contextual |
| TTS speaks responses clearly | Audio is clear and natural sounding |
| Memory storage works | "Remember X" → X is saved to cloud |
| Memory recall works | "What's my X" → X is retrieved from cloud |
| Conversation context works | Follow-up questions understand context |
| App handles errors gracefully | No crashes on bad input or network issues |

### 7.2 Performance Requirements

| Metric | Target |
|--------|--------|
| Wake word to listening | < 500ms |
| Speech-to-text | < 2s for 5s audio |
| LLM response start | < 1s |
| LLM response complete | < 5s typical |
| TTS generation | < 500ms |
| Total end-to-end | < 8s typical |

### 7.3 Resource Requirements

| Resource | Limit |
|----------|-------|
| VRAM usage | < 14GB (leave room for other apps) |
| RAM usage | < 4GB |
| CPU idle | < 5% |
| CPU active | < 50% |

---

## 8. Known Limitations (MVP)

Document these for users:

1. **Single device only** - No sync between devices yet
2. **English only** - Speech recognition and responses in English
3. **No commands** - Cannot open apps, control system, set reminders
4. **No offline mode** - Requires internet for cloud memory
5. **No conversation search** - Cannot search old conversations
6. **Simple memory** - Basic key-value, no complex relationships
7. **No UI** - Command line only for MVP (no system tray)

---

## 9. Future Enhancements (Post-MVP)

Reserved for future versions:

- System tray UI with status indicator
- App launching commands
- Timer and reminder system
- Multi-device sync
- Offline fallback mode
- Web search integration
- Settings GUI
- Custom wake word

---

*End of MVP Specification*
