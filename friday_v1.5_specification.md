# Friday AI Assistant - v1.5 Specification

## Document Info
- **Version**: 1.5
- **Created**: January 24, 2026
- **Purpose**: Implementation guide for Claude Code
- **Builds on**: v1.0 MVP

---

## 1. Version Overview

### 1.1 What's New in v1.5

| Feature | Description |
|---------|-------------|
| Lightweight mode | CPU-only mode when GPU is busy |
| Auto mode switching | Detects resource-heavy apps, switches automatically |
| Voice mode control | "Friday, go lightweight" / "Friday, full power" |
| Web search | Search the internet and summarize results |
| App launching | Open applications by voice command |

### 1.2 Complete Feature Set (v1.0 + v1.5)

| Feature | Version | Status |
|---------|---------|--------|
| Wake word detection | v1.0 | ✅ |
| Speech-to-text | v1.0 | ✅ |
| LLM conversation | v1.0 | ✅ |
| Text-to-speech | v1.0 | ✅ |
| Memory store/recall | v1.0 | ✅ |
| Conversation history | v1.0 | ✅ |
| Keyboard shortcut | v1.0 | ✅ |
| **Lightweight mode** | v1.5 | ✅ NEW |
| **Auto mode switching** | v1.5 | ✅ NEW |
| **Web search** | v1.5 | ✅ NEW |
| **App launching** | v1.5 | ✅ NEW |

### 1.3 Still NOT in v1.5

- ❌ Timers
- ❌ Reminders
- ❌ System commands (volume, screenshot, etc.)
- ❌ Multi-device sync
- ❌ Settings UI
- ❌ File search
- ❌ Third-party integrations

---

## 2. Feature: Dual Mode Operation

### 2.1 Overview

Friday operates in two modes depending on system resources:

| Mode | When Used | STT Model | LLM Model | Runs On |
|------|-----------|-----------|-----------|---------|
| **Full Power** | GPU available | Whisper Large V3 Turbo | Llama 3.3 70B Q4 | GPU |
| **Lightweight** | GPU busy | Moonshine Base | Llama 3.2 3B Q8 | CPU |

### 2.2 Resource Usage by Mode

**Full Power Mode:**
| Resource | Usage |
|----------|-------|
| VRAM | ~14GB |
| RAM | ~2GB |
| CPU | ~20% during inference |

**Lightweight Mode:**
| Resource | Usage |
|----------|-------|
| VRAM | 0GB |
| RAM | ~6GB |
| CPU | ~50% during inference |

### 2.3 Mode Switching Triggers

#### 2.3.1 Automatic Switching (GPU → CPU)

Friday automatically switches to lightweight mode when:

1. **VRAM threshold exceeded**: Available VRAM drops below 6GB
2. **Known apps detected**: Resource-heavy applications are running

**Detection method - VRAM monitoring:**
- Poll NVIDIA GPU every 10 seconds using `nvidia-smi` or `pynvml`
- If free VRAM < 6GB, trigger switch to lightweight
- If free VRAM > 10GB and in lightweight mode, offer to switch back

**Detection method - Process monitoring:**
- Monitor running processes every 10 seconds
- Check against list of known resource-heavy applications
- If detected, switch to lightweight mode

**Known resource-heavy apps (configurable list):**
```yaml
resource_heavy_apps:
  # Games (detect by process name)
  - steam_game  # Generic Steam games
  - csgo.exe
  - valorant.exe
  - cyberpunk2077.exe
  - baldursgate3.exe
  - eldenring.exe
  
  # CAD/3D Software
  - Fusion360.exe
  - blender.exe
  - 3dsmax.exe
  - maya.exe
  - solidworks.exe
  - AutoCAD.exe
  
  # Video/Rendering
  - premiere.exe
  - afterfx.exe
  - resolve.exe
  - obs64.exe  # OBS streaming
  
  # Other GPU-intensive
  - chrome.exe  # Only if using GPU acceleration heavily
```

**Game detection heuristic:**
- Any fullscreen application using >2GB VRAM
- Any process with "game" in path
- Any process running from Steam/Epic/GOG directories

#### 2.3.2 Manual Switching (Voice Commands)

| Command | Action |
|---------|--------|
| "Friday, go lightweight" | Switch to CPU mode |
| "Friday, full power" | Switch to GPU mode (if available) |
| "Friday, what mode are you in?" | Report current mode |

#### 2.3.3 Automatic Switching (CPU → GPU)

Friday offers to switch back to full power when:
- Resource-heavy app closes
- VRAM becomes available (>10GB free)
- User hasn't interacted in 5+ minutes (models can be preloaded)

**Behavior:**
- Don't auto-switch during conversation (disruptive)
- Notify user: "Your GPU is free now. Want me to switch to full power?"
- Or silently preload models in background, switch on next interaction

### 2.4 Mode Switching Implementation

#### 2.4.1 Model Management

**Full Power models:**
- Whisper Large V3 Turbo: Load via faster-whisper with CUDA
- Llama 70B: Load via Ollama (stays resident)

**Lightweight models:**
- Moonshine Base: Load via moonshine library (CPU/ONNX)
- Llama 3.2 3B: Load via Ollama with CPU-only flag

**Switching process:**
```
1. Detect trigger (auto or manual)
2. Finish current response if mid-conversation
3. Announce: "Switching to lightweight mode"
4. Unload GPU models (free VRAM)
5. Load CPU models
6. Confirm: "Now in lightweight mode"
7. Continue wake word listening
```

**Estimated switch time:** 5-15 seconds

#### 2.4.2 New Module: Resource Monitor

```
friday/
├── ...
├── resources/
│   ├── monitor.py          # GPU/process monitoring
│   ├── mode_manager.py     # Handle mode switching
│   └── process_list.py     # Known heavy apps list
```

**monitor.py responsibilities:**
- Poll GPU stats via pynvml
- Poll running processes via psutil
- Emit events when thresholds crossed

**mode_manager.py responsibilities:**
- Listen to monitor events
- Manage model loading/unloading
- Coordinate switching without interrupting user

### 2.5 Configuration

Add to `config.yaml`:

```yaml
modes:
  # Starting mode
  default_mode: "auto"  # auto, full, lightweight
  
  # Auto-switching settings
  auto_switch:
    enabled: true
    vram_threshold_mb: 6000  # Switch to light if free VRAM below this
    vram_recovery_mb: 10000  # Offer full power if free VRAM above this
    check_interval_seconds: 10
    
  # Full power mode models
  full_power:
    stt_model: "large-v3-turbo"
    stt_device: "cuda"
    llm_model: "llama3.3:70b-instruct-q4_K_M"
    
  # Lightweight mode models  
  lightweight:
    stt_model: "moonshine-base"
    stt_device: "cpu"
    llm_model: "llama3.2:3b-instruct-q8_0"

  # Apps that trigger lightweight mode
  resource_heavy_apps:
    - Fusion360.exe
    - blender.exe
    - steam_game
    # ... user can add more
```

---

## 3. Feature: Web Search

### 3.1 Overview

Friday can search the internet and provide summarized answers.

**Trigger phrases:**
- "Search for..."
- "Look up..."
- "What's the latest on..."
- "Find information about..."
- "Google..." (colloquial)

**Example interactions:**

```
User: "Hey Friday, search for NVIDIA Audio Flamingo 3"
Friday: "NVIDIA's Audio Flamingo 3 is an open-source audio language model 
        released in July 2025. It handles speech, sounds, and music 
        understanding with support for up to 10 minutes of audio input. 
        It's designed for research purposes and runs on NVIDIA GPUs."

User: "Hey Friday, what's the weather in London?"
Friday: "Currently in London it's 8 degrees Celsius, cloudy with a chance 
        of rain this afternoon."

User: "Hey Friday, look up linear actuator force calculations"
Friday: "For linear actuator force calculations, you need to consider: 
        the load force, friction coefficient, angle of operation, and 
        safety factor. The basic formula is F = ma + μmg for horizontal 
        movement. Want me to go deeper on any of these?"
```

### 3.2 Search Implementation

#### 3.2.1 Search Provider Options

**Option A: SearXNG (Self-hosted) - Recommended**
- Free, private, no API limits
- Aggregates multiple search engines
- Can run on same VPS as Friday cloud server
- Docker deployment available

**Option B: DuckDuckGo Instant Answer API**
- Free, no API key needed
- Limited to instant answers (not full search)
- Good for quick facts, weather, calculations

**Option C: Serper API**
- Google results, $50 free credit
- 2,500 free searches
- Good accuracy

**Option D: Tavily API**
- Built for AI applications
- 1,000 free searches/month
- Returns AI-ready summaries

**Recommendation for MVP:** Start with DuckDuckGo for instant answers + SearXNG for full search. Both free.

#### 3.2.2 Search Flow

```
1. User asks question with search intent
2. Intent router detects SEARCH intent
3. Extract search query from user input
4. Call search API
5. Receive search results (titles, snippets, URLs)
6. Pass results to LLM with prompt:
   "Based on these search results, answer the user's question: {question}
    
    Search results:
    {results}
    
    Provide a concise, accurate answer. Cite sources if needed."
7. LLM generates summarized response
8. Speak response to user
```

#### 3.2.3 Search Module Structure

```
friday/
├── ...
├── search/
│   ├── router.py           # Detect search intent
│   ├── searxng.py          # SearXNG client
│   ├── duckduckgo.py       # DuckDuckGo client
│   └── summarizer.py       # Format results for LLM
```

#### 3.2.4 Intent Detection for Search

**Keywords that trigger search:**
- "search for", "search"
- "look up", "lookup"
- "find information about", "find info on"
- "what's the latest on", "latest news"
- "google" (verb usage)
- "who is" (current events)
- "what happened with"
- "how do I" (how-to questions without memory context)

**Questions that should NOT trigger search:**
- "What's my name?" (memory recall)
- "What did I tell you about X?" (memory recall)
- "Remember that..." (memory store)
- General knowledge LLM can answer (capital cities, math, etc.)

**Implementation approach:**
- Simple keyword matching first
- If ambiguous, check if answer exists in memory
- If no memory match and question seems factual/current, search

### 3.3 Search Configuration

Add to `config.yaml`:

```yaml
search:
  enabled: true
  
  # Primary search provider
  provider: "searxng"  # searxng, duckduckgo, serper, tavily
  
  # SearXNG settings (if self-hosted)
  searxng:
    url: "https://your-searxng-instance.com"
    
  # API keys (if using paid services)
  serper_api_key: ""
  tavily_api_key: ""
  
  # Search behavior
  max_results: 5
  timeout_seconds: 10
  
  # Fallback if search fails
  fallback_to_llm: true  # Let LLM answer from training data
```

### 3.4 Search Error Handling

| Scenario | Behavior |
|----------|----------|
| Search timeout | "I couldn't complete the search. Let me try to answer from what I know..." |
| No results | "I couldn't find specific information on that. Based on what I know..." |
| API error | "Search is temporarily unavailable. Here's what I know..." |
| Rate limited | Switch to fallback provider or use LLM knowledge |

---

## 4. Feature: App Launching

### 4.1 Overview

Friday can open applications by voice command.

**Trigger phrases:**
- "Open [app]"
- "Launch [app]"
- "Start [app]"
- "Run [app]"

**Example interactions:**

```
User: "Hey Friday, open Chrome"
Friday: "Opening Chrome."
[Chrome launches]

User: "Hey Friday, launch Fusion 360"
Friday: "Opening Fusion 360."
[Fusion 360 launches, Friday auto-switches to lightweight mode]

User: "Hey Friday, open VS Code"
Friday: "Opening Visual Studio Code."
[VS Code launches]
```

### 4.2 App Registry

Friday maintains a registry of known applications with their executable paths.

#### 4.2.1 Default App Registry

Pre-configured common applications:

```yaml
apps:
  # Browsers
  chrome:
    names: ["chrome", "google chrome"]
    path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    
  firefox:
    names: ["firefox", "mozilla firefox"]
    path: "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    
  edge:
    names: ["edge", "microsoft edge"]
    path: "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe"

  # Development
  vscode:
    names: ["vs code", "vscode", "visual studio code", "code"]
    path: "%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\Code.exe"
    
  # Creative/CAD
  fusion360:
    names: ["fusion", "fusion 360", "fusion360"]
    path: "%LOCALAPPDATA%\\Autodesk\\webdeploy\\production\\*\\Fusion360.exe"
    triggers_lightweight: true
    
  blender:
    names: ["blender"]
    path: "C:\\Program Files\\Blender Foundation\\Blender *\\blender.exe"
    triggers_lightweight: true

  # Media
  spotify:
    names: ["spotify"]
    path: "%APPDATA%\\Spotify\\Spotify.exe"
    
  vlc:
    names: ["vlc", "vlc player"]
    path: "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"

  # Productivity
  notepad:
    names: ["notepad"]
    path: "notepad.exe"
    
  calculator:
    names: ["calculator", "calc"]
    path: "calc.exe"
    
  explorer:
    names: ["explorer", "file explorer", "files"]
    path: "explorer.exe"
```

#### 4.2.2 App Discovery

For apps not in default registry:
1. Search Windows Start Menu shortcuts
2. Search Program Files directories
3. Check Windows App Paths registry

**Auto-discovery locations:**
```
- %APPDATA%\Microsoft\Windows\Start Menu\Programs\
- %PROGRAMDATA%\Microsoft\Windows\Start Menu\Programs\
- C:\Program Files\
- C:\Program Files (x86)\
- %LOCALAPPDATA%\Programs\
```

#### 4.2.3 Custom App Registration

User can add apps via voice:

```
User: "Hey Friday, add an app called Obsidian"
Friday: "What's the path to Obsidian?"
User: "It's in my local app data, Programs, Obsidian"
Friday: "Found Obsidian at AppData\Local\Programs\Obsidian\Obsidian.exe. 
        I'll remember that."
```

Or via config file:

```yaml
apps:
  # User-added apps
  obsidian:
    names: ["obsidian"]
    path: "%LOCALAPPDATA%\\Programs\\Obsidian\\Obsidian.exe"
```

### 4.3 App Launch Implementation

#### 4.3.1 Launch Flow

```
1. User says "Open Chrome"
2. Intent router detects APP_OPEN intent
3. Extract app name: "Chrome"
4. Fuzzy match against app registry
5. If found:
   a. Get executable path
   b. Check if app triggers lightweight mode
   c. If yes, switch to lightweight first
   d. Launch app via subprocess
   e. Confirm: "Opening Chrome"
6. If not found:
   a. Try auto-discovery
   b. If found, add to registry and launch
   c. If not found: "I couldn't find Chrome. Is it installed?"
```

#### 4.3.2 Fuzzy Matching

Use fuzzy string matching to handle variations:
- "Chrome" → chrome
- "Google Chrome" → chrome
- "VS Code" → vscode
- "Visual Studio Code" → vscode
- "Fusion" → fusion360

**Library:** thefuzz (formerly fuzzywuzzy)

**Matching threshold:** 80% similarity

#### 4.3.3 App Module Structure

```
friday/
├── ...
├── commands/
│   ├── app_launcher.py     # Launch applications
│   ├── app_registry.py     # Manage known apps
│   └── app_discovery.py    # Find apps on system
```

#### 4.3.4 Launching with Arguments

Support for opening apps with arguments:

```
User: "Hey Friday, open Chrome with YouTube"
Friday: "Opening YouTube in Chrome."
[Chrome opens with youtube.com]

User: "Hey Friday, open VS Code with my projects folder"
Friday: "Opening VS Code with your projects folder."
[VS Code opens in projects directory]
```

**Implementation:**
- Detect "with" keyword
- Parse argument (URL, path, file)
- Pass as command line argument to app

### 4.4 App Configuration

Add to `config.yaml`:

```yaml
apps:
  # Auto-discovery
  auto_discover: true
  discovery_paths:
    - "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs"
    - "%PROGRAMDATA%\\Microsoft\\Windows\\Start Menu\\Programs"
    - "C:\\Program Files"
    - "C:\\Program Files (x86)"
    
  # Fuzzy match threshold (0-100)
  match_threshold: 80
  
  # Default apps registry
  registry:
    chrome:
      names: ["chrome", "google chrome"]
      path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    # ... more apps
    
  # User-added apps (populated via voice or manual edit)
  custom:
    # obsidian:
    #   names: ["obsidian"]
    #   path: "..."
```

### 4.5 App Launch Error Handling

| Scenario | Behavior |
|----------|----------|
| App not found | "I couldn't find [app]. Is it installed?" |
| App path invalid | "The path for [app] seems incorrect. Can you help me find it?" |
| Launch failed | "I couldn't open [app]. It may have crashed or requires admin rights." |
| Multiple matches | "Did you mean [app1] or [app2]?" |

---

## 5. Updated System Architecture

### 5.1 Architecture Diagram (v1.5)

```
LOCAL CLIENT (Windows PC)
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  RESOURCE MONITOR                        │   │
│  │  • GPU VRAM monitoring (pynvml)                         │   │
│  │  • Process monitoring (psutil)                          │   │
│  │  • Mode switching triggers                              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   MODE MANAGER                           │   │
│  │                                                          │   │
│  │   FULL POWER MODE          LIGHTWEIGHT MODE             │   │
│  │   ┌─────────────┐          ┌─────────────┐              │   │
│  │   │ Whisper LV3 │          │  Moonshine  │              │   │
│  │   │   Turbo     │    OR    │    Base     │              │   │
│  │   │   (GPU)     │          │    (CPU)    │              │   │
│  │   └─────────────┘          └─────────────┘              │   │
│  │   ┌─────────────┐          ┌─────────────┐              │   │
│  │   │ Llama 70B   │          │ Llama 3.2   │              │   │
│  │   │    Q4       │    OR    │  3B Q8      │              │   │
│  │   │   (GPU)     │          │   (CPU)     │              │   │
│  │   └─────────────┘          └─────────────┘              │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            │                                    │
│                            ▼                                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   INTENT ROUTER                          │   │
│  │                                                          │   │
│  │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │   │
│  │   │  CHAT   │ │ MEMORY  │ │ SEARCH  │ │  APP    │      │   │
│  │   │         │ │         │ │         │ │ LAUNCH  │      │   │
│  │   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘      │   │
│  └────────┼──────────┼──────────┼──────────┼──────────────┘   │
│           │          │          │          │                   │
│           ▼          ▼          ▼          ▼                   │
│       ┌───────┐  ┌───────┐  ┌───────┐  ┌───────┐              │
│       │  LLM  │  │ Cloud │  │Search │  │Launch │              │
│       │       │  │  API  │  │  API  │  │Process│              │
│       └───────┘  └───────┘  └───────┘  └───────┘              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTPS
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CLOUD SERVER                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ Memories │  │  Convos  │  │ SearXNG  │                      │
│  │          │  │          │  │ (Search) │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Updated Module Structure

```
friday/
├── main.py
├── config.py
├── audio/
│   ├── wake_word.py
│   ├── listener.py
│   ├── stt.py              # Now supports multiple backends
│   └── tts.py
├── brain/
│   ├── llm.py              # Now supports multiple models
│   ├── memory.py
│   ├── prompts.py
│   └── intent_router.py    # Route to correct handler
├── cloud/
│   ├── client.py
│   ├── auth.py
│   └── sync.py
├── resources/              # NEW in v1.5
│   ├── monitor.py          # GPU/process monitoring
│   ├── mode_manager.py     # Handle mode switching
│   └── process_list.py     # Known heavy apps
├── search/                 # NEW in v1.5
│   ├── router.py           # Detect search intent
│   ├── searxng.py          # SearXNG client
│   ├── duckduckgo.py       # DuckDuckGo client
│   └── summarizer.py       # Format for LLM
├── commands/               # NEW in v1.5
│   ├── app_launcher.py     # Launch applications
│   ├── app_registry.py     # Manage known apps
│   └── app_discovery.py    # Find apps on system
├── utils/
│   ├── audio_utils.py
│   └── logging.py
└── config.yaml
```

---

## 6. Updated Intent Router

### 6.1 Intent Types

| Intent | Trigger Examples | Handler |
|--------|------------------|---------|
| CHAT | General conversation | LLM direct |
| MEMORY_STORE | "Remember that...", "Note that..." | Cloud API + confirm |
| MEMORY_RECALL | "What's my...", "Do you remember..." | Cloud API + LLM |
| SEARCH | "Search for...", "Look up...", "What's the latest..." | Search API + LLM |
| APP_OPEN | "Open...", "Launch...", "Start..." | App launcher |
| MODE_SWITCH | "Go lightweight", "Full power" | Mode manager |
| MODE_QUERY | "What mode are you in?" | Mode manager |

### 6.2 Intent Detection Logic

```
function detect_intent(user_input):
    
    # Check for mode commands first (highest priority)
    if matches(user_input, ["go lightweight", "lightweight mode"]):
        return MODE_SWITCH_LIGHT
    if matches(user_input, ["full power", "full power mode"]):
        return MODE_SWITCH_FULL
    if matches(user_input, ["what mode", "which mode"]):
        return MODE_QUERY
    
    # Check for app commands
    if starts_with(user_input, ["open ", "launch ", "start ", "run "]):
        return APP_OPEN
    
    # Check for memory operations
    if starts_with(user_input, ["remember that", "note that", "don't forget"]):
        return MEMORY_STORE
    if contains(user_input, ["what's my", "what is my", "do you remember"]):
        return MEMORY_RECALL
    
    # Check for search intent
    if starts_with(user_input, ["search for", "look up", "google"]):
        return SEARCH
    if starts_with(user_input, ["what's the latest", "latest news"]):
        return SEARCH
    if is_factual_question(user_input) and not in_memory(user_input):
        return SEARCH
    
    # Default to general chat
    return CHAT
```

---

## 7. Cloud Server Updates

### 7.1 New: SearXNG Integration

If self-hosting search, add SearXNG to Docker Compose:

```yaml
services:
  # ... existing services (api, db)
  
  searxng:
    image: searxng/searxng:latest
    environment:
      - SEARXNG_BASE_URL=https://search.your-domain.com
    volumes:
      - ./searxng:/etc/searxng
    restart: unless-stopped
```

### 7.2 Search Endpoint (Optional Proxy)

If proxying search through cloud server:

**GET /search?q={query}**
- Purpose: Search web via SearXNG
- Headers: `Authorization: Bearer <token>`
- Query: `q` - search query
- Response: 
```json
{
  "results": [
    {
      "title": "string",
      "url": "string", 
      "snippet": "string"
    }
  ]
}
```

---

## 8. Configuration File (Complete v1.5)

```yaml
# Friday v1.5 Configuration

general:
  startup_with_windows: true
  language: en-US

# Cloud server
cloud:
  server_url: "https://your-friday-server.com"

# Audio settings
audio:
  input_device: null
  output_device: null

# Wake word
wake_word:
  enabled: true
  sensitivity: 0.5
  keyword: "hey friday"

# Keyboard shortcut
hotkey:
  enabled: true
  combination: "ctrl+shift+f"

# Dual mode operation (NEW in v1.5)
modes:
  default_mode: "auto"  # auto, full, lightweight
  
  auto_switch:
    enabled: true
    vram_threshold_mb: 6000
    vram_recovery_mb: 10000
    check_interval_seconds: 10
    
  full_power:
    stt_model: "large-v3-turbo"
    stt_device: "cuda"
    llm_model: "llama3.3:70b-instruct-q4_K_M"
    
  lightweight:
    stt_model: "moonshine-base"
    stt_device: "cpu"
    llm_model: "llama3.2:3b-instruct-q8_0"

  resource_heavy_apps:
    - Fusion360.exe
    - blender.exe
    - 3dsmax.exe
    - premiere.exe
    - resolve.exe

# Web search (NEW in v1.5)
search:
  enabled: true
  provider: "searxng"
  searxng:
    url: "https://your-searxng-instance.com"
  max_results: 5
  timeout_seconds: 10
  fallback_to_llm: true

# App launching (NEW in v1.5)
apps:
  auto_discover: true
  match_threshold: 80
  
  discovery_paths:
    - "%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs"
    - "%PROGRAMDATA%\\Microsoft\\Windows\\Start Menu\\Programs"
    - "C:\\Program Files"
    - "C:\\Program Files (x86)"
  
  registry:
    chrome:
      names: ["chrome", "google chrome"]
      path: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    firefox:
      names: ["firefox"]
      path: "C:\\Program Files\\Mozilla Firefox\\firefox.exe"
    vscode:
      names: ["vs code", "vscode", "code"]
      path: "%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\Code.exe"
    fusion360:
      names: ["fusion", "fusion 360"]
      path: "%LOCALAPPDATA%\\Autodesk\\webdeploy\\production\\*\\Fusion360.exe"
      triggers_lightweight: true
    blender:
      names: ["blender"]
      path: "C:\\Program Files\\Blender Foundation\\Blender *\\blender.exe"
      triggers_lightweight: true
    notepad:
      names: ["notepad"]
      path: "notepad.exe"
    calculator:
      names: ["calculator", "calc"]
      path: "calc.exe"
      
  custom: {}
  
# Text-to-speech
tts:
  model: "en_US-amy-medium"
  speed: 1.0
```

---

## 9. User Interaction Examples (v1.5)

### 9.1 Mode Switching

```
[User launches Fusion 360]

Friday: "I see you've started Fusion 360. Switching to lightweight mode."

[Later, user closes Fusion 360]

Friday: "Fusion 360 closed. Want me to switch back to full power?"
User: "Yes"
Friday: "Switching to full power mode. Ready."
```

```
User: "Hey Friday, go lightweight"
Friday: "Switching to lightweight mode. I'll use less resources but 
        might be a bit slower."

User: "Hey Friday, what mode are you in?"
Friday: "I'm currently in lightweight mode, running on CPU."
```

### 9.2 Web Search

```
User: "Hey Friday, search for best linear actuators for robotics"
Friday: "Based on my search, popular choices for robotics include 
        Actuonix L12 and L16 for small applications, Firgelli for 
        medium loads, and Thomson or SKF for industrial use. Key 
        factors are stroke length, force rating, and speed. Want 
        more details on any of these?"

User: "Hey Friday, what's the weather like today?"
Friday: "In London, it's currently 7 degrees and cloudy. 
        Expecting rain this afternoon with highs of 9 degrees."
```

### 9.3 App Launching

```
User: "Hey Friday, open Chrome"
Friday: "Opening Chrome."

User: "Hey Friday, launch Fusion 360"
Friday: "Opening Fusion 360. Switching to lightweight mode."

User: "Hey Friday, open VS Code with my projects folder"
Friday: "Opening VS Code with your projects folder."
```

### 9.4 Combined Workflow

```
User: "Hey Friday"
Friday: *activation sound*
User: "I need to work on my gripper design"
Friday: "Okay, want me to open Fusion 360?"
User: "Yes please"
Friday: "Opening Fusion 360. I'll switch to lightweight mode. 
        Good luck with the gripper!"

[User works in Fusion 360, closes it later]

User: "Hey Friday"
Friday: *activation sound*
User: "Search for Haydon Kerk captive linear actuators"
Friday: "Haydon Kerk makes captive stepper motor linear actuators 
        with anti-rotation design. They're known for precision 
        positioning in the 5-50N force range. The 21000 series 
        is popular for compact applications. Want specs or pricing?"
```

---

## 10. Success Criteria for v1.5

### 10.1 Mode Switching

| Test | Pass Criteria |
|------|---------------|
| Auto-switch on app launch | Launching Fusion 360 triggers lightweight mode within 15s |
| Auto-switch on VRAM pressure | Reducing VRAM below threshold triggers switch |
| Manual switch via voice | "Go lightweight" switches mode within 10s |
| Mode query | "What mode" returns correct current mode |
| Switch back offer | Closing heavy app prompts offer to return to full power |

### 10.2 Web Search

| Test | Pass Criteria |
|------|---------------|
| Basic search | "Search for X" returns relevant summarized results |
| Weather query | "What's the weather" returns current conditions |
| No false triggers | "What's my name" does NOT trigger search |
| Search failure graceful | Timeout shows fallback message, no crash |

### 10.3 App Launching

| Test | Pass Criteria |
|------|---------------|
| Launch known app | "Open Chrome" launches Chrome |
| Fuzzy matching | "Open VS Code" matches vscode entry |
| Unknown app discovery | "Open [installed app]" finds and launches |
| Launch with lightweight | "Open Blender" switches mode then launches |
| App not found | "Open FakeApp" gives helpful error message |

---

## 11. Migration from v1.0

### 11.1 Steps to Upgrade

1. Update code with new modules (resources/, search/, commands/)
2. Install new dependencies:
   - `pynvml` (GPU monitoring)
   - `psutil` (process monitoring)
   - `moonshine` (lightweight STT)
   - `thefuzz` (fuzzy matching)
3. Pull lightweight LLM: `ollama pull llama3.2:3b-instruct-q8_0`
4. Download Moonshine model
5. Update config.yaml with new sections
6. (Optional) Deploy SearXNG on cloud server
7. Test mode switching, search, and app launching

### 11.2 Backward Compatibility

- All v1.0 features continue to work
- Existing memories and conversations preserved
- Config file is additive (new sections, no breaking changes)

---

*End of v1.5 Specification*
