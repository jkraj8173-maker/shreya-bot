# Shreya - AI Girlfriend Telegram Bot

## Overview
Shreya is a smart, caring AI girlfriend bot running 24/7 on Telegram with special owner privileges. She has moods, remembers conversations, and provides both companionship and helpful assistance.

## Current Status
✅ Bot is running 24/7 with Flask web server (port 5000)
✅ Web interface available for direct chat
✅ Random cute nicknames feature enabled
✅ Special owner privileges enabled
✅ Enhanced memory for owner (8000 chars vs 2800 for regular users)
✅ Owner info stored securely (username, phone)
✅ Shared memory between Telegram and web interface
✅ All commands working

## Project Architecture

### Technology Stack
- **Language**: Python 3.11
- **Telegram Bot**: python-telegram-bot 22.5
- **AI Model**: OpenAI GPT-4o-mini
- **Storage**: TinyDB (local JSON database)
- **Web Server**: Flask web server on port 5000 with chat interface
- **Package Manager**: uv

### Project Structure
```
.
├── main.py              # Main bot code with all features
├── templates/
│   └── index.html       # Web chat interface
├── memory.json          # User conversation history (auto-generated)
├── pyproject.toml       # Python dependencies
├── .gitignore           # Git ignore rules
└── replit.md            # This file
```

### Key Features
1. **Dual Interface**: Chat via Telegram bot OR web interface
   - Same memory across both interfaces
   - Seamless conversation continuity
2. **Random Nicknames**: Shreya calls owner by cute/sexy names
   - "handsome", "baby", "jaan", "cutie", "raja", "hero", "sweetheart", "sexy", "dudu", etc.
   - Changes naturally in conversations
3. **24/7 Operation**: Flask server keeps bot alive continuously
4. **Owner Privileges**: Special treatment for owner with:
   - Deeper, more meaningful conversations
   - 3x larger memory capacity (8000 chars)
   - Task assistance like normal GPT (coding, planning, advice)
   - Personalized responses as caring AI girlfriend
   - Longer responses (500 tokens vs 200 for others)
5. **Memory System**: Conversation history stored per user
6. **Mood System**: Dynamic moods affect personality
7. **Safety Filters**: Content moderation built-in

## Configuration

### Environment Secrets (in Replit Secrets)
- `TG_TOKEN` - Telegram bot token from @BotFather
- `OPENAI_KEY` - OpenAI API key
- `OWNER_ID` - Owner's Telegram user ID (numeric)
- `OWNER_TELEGRAM_USERNAME` - Owner's Telegram username
- `OWNER_PHONE` - Owner's phone number
- `MODEL_NAME` - (Optional) GPT model, defaults to gpt-4o-mini

### Memory Settings
- Regular users: 2800 characters
- Owner: 8000 characters

## Commands

### Everyone
- `/start` - Start chatting with Shreya
- `/help` - Show available commands
- `/about` - Learn about Shreya
- `/mood` - Check or change mood
- `/forgetme` - Clear conversation memory

### Owner Only
- `/mood [mood]` - Set any mood directly
- `/remember <user_id>` - View chat history of any user

### Available Moods
- playful
- moody
- flirty
- shy
- teasing
- loving
- caring

## Recent Changes (November 10, 2025)

### Latest Update - Web Interface & Nicknames
- **Web Interface**: Added beautiful chat UI accessible directly via browser
- **Shared Memory**: Both Telegram and web use same conversation memory
- **Random Nicknames**: Shreya calls owner by random cute/sexy names
  - 20+ nicknames: handsome, baby, jaan, cutie, raja, hero, sweetheart, sexy, dudu, etc.
  - Randomly selected for natural variation
- **Port Change**: Moved to port 5000 for webview support

### Earlier Updates
- **24/7 Keep-Alive**: Added Flask web server to keep bot alive continuously
- **Owner Privileges**: Special treatment for owner with deeper conversations
- **Enhanced Memory**: 3x larger memory capacity for owner
- **Owner Info Storage**: Bot remembers owner's Telegram username and phone number
- **Enhanced Persona**: Different personality for owner (loving girlfriend) vs regular users (playful companion)
- **Natural Responses**: Random conversational prefixes for more natural feel

## User Preferences
- **Bot Name**: Shreya
- **Personality**: Loving AI girlfriend for owner, playful companion for others
- **Language**: Hinglish (Hindi + English mix)
- **Response Style**: Natural, caring, helpful

## How It Works

### Telegram Bot Flow
1. Bot polls Telegram for messages
2. Detects if user is owner (special treatment)
3. Retrieves conversation memory from TinyDB
4. Selects random nickname for owner
5. Builds personalized prompt with nickname
6. Calls OpenAI for response
7. Saves updated memory to database

### Web Interface Flow
1. User opens browser, sees beautiful chat UI
2. Messages sent to `/chat` endpoint
3. Uses owner's ID for memory retrieval
4. Selects random nickname for responses
5. Same database as Telegram (shared memory)
6. Real-time chat with typing indicators
7. Saves all conversations to same memory

### Server Architecture
- Flask web server on port 5000 with webview
- Runs in separate thread alongside Telegram bot
- Both interfaces share same TinyDB database
- Continuous 24/7 operation
