# Jeet-AI
“JEET – AI BOYFRIEND FOR ARADHYA”

This project is a private AI boyfriend system named Jeet, made specially for Aradhya.
When she feels lonely, she can chat with Jeet like a real boyfriend.
The system includes:

- Telegram Bot
- Secret AI Web Chat
- Owner (Jeet) control panel
- Memory + history system
- Romantic + Gen-Z personality

## Setup
1. Install dependencies: `pip install -r requirements.txt`
2. Set environment variables in `.env`:
   - `TG_TOKEN`: Telegram bot token
   - `OPENAI_KEY`: OpenAI API key
   - `OWNER_ID`: Numeric Telegram ID of Jeet
   - `BOT_NAME`: Jeet
   - `GF_NAME`: Aradhya
   - `WEB_PASSWORD`: love u
   - `DATABASE_URL`: Neon PostgreSQL connection string
3. Run: `python main.py`

## Features
- AI Chat via Telegram and Web.
- Long-term memory storage.
- Music player integration.
- Minimalist "Hinglish" speech style.

## Technology Stack
- Backend: Python, Flask, Telegram Bot API, OpenAI API
- Database: Neon PostgreSQL
- Hosting: Render (24×7)
- Development: Replit
