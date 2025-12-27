# Jeet - AI Boyfriend Telegram Bot

## Overview
Jeet is a smart, caring AI boyfriend bot running 24/7 on Telegram with a secret web interface for Aradhya.

## Project Structure
- `main.py`: Core logic for both Telegram and Web.
- `templates/`: HTML files for the web interface.
- `static/`: CSS, JS, and music assets.
- `Neon Database`: PostgreSQL for conversation history.

## Setup
1. Set environment secrets: `TG_TOKEN`, `OPENAI_KEY`, `OWNER_ID`, `BOT_NAME`, `GF_NAME`, `WEB_PASSWORD`, `DATABASE_URL`.
2. Run `python main.py`.

## Replit Configuration
- **Runtime**: Python
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn main:app`

## Features
- AI Chat via Telegram and Web.
- Long-term memory storage.
- Music player integration.
- Minimalist "Hinglish" speech style.
