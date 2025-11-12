# main.py
import os
import re
import random
from threading import Thread
from openai import OpenAI
import logging
from dotenv import load_dotenv
from tinydb import TinyDB, Query
from datetime import datetime
from telegram import Update, Chat
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from flask import Flask, render_template, request, jsonify, session
import secrets

# ------------------ Config & logging ------------------
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TG_TOKEN = os.getenv("TG_TOKEN") or ""
OPENAI_KEY = os.getenv("OPENAI_KEY") or ""
try:
    OWNER_ID = int(os.getenv("OWNER_ID") or "0")
except ValueError:
    logger.warning("OWNER_ID must be a numeric ID. Get it from @userinfobot on Telegram. Setting to 0.")
    OWNER_ID = 0

OWNER_USERNAME = os.getenv("OWNER_TELEGRAM_USERNAME") or ""
OWNER_PHONE = os.getenv("OWNER_PHONE") or ""
WEB_PASSWORD = os.getenv("WEB_PASSWORD") or ""
MODEL_NAME = os.getenv("MODEL_NAME") or "gpt-4o-mini"

if not TG_TOKEN or not OPENAI_KEY:
    raise SystemExit("Set TG_TOKEN and OPENAI_KEY in environment (or Replit Secrets).")

if not WEB_PASSWORD:
    raise SystemExit("Set WEB_PASSWORD in environment (or Replit Secrets) to secure the web interface.")

client = OpenAI(api_key=OPENAI_KEY)

# ------------------ Flask Web Server (24/7 Keep Alive) ------------------
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
app.config.update(
    SESSION_COOKIE_SECURE=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax'
)

@app.route("/")
def home():
    if not session.get("authenticated"):
        return render_template("login.html")
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    password = data.get("password", "")
    
    if not password:
        return jsonify({"success": False, "error": "Password required"}), 400
    
    if password == WEB_PASSWORD:
        session["authenticated"] = True
        return jsonify({"success": True})
    else:
        return jsonify({"success": False, "error": "Invalid password"}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.pop("authenticated", None)
    return jsonify({"success": True})

@app.route("/chat", methods=["POST"])
def web_chat():
    if not session.get("authenticated"):
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.json
    user_message = data.get("message", "").strip()
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    ok, reason = safe_to_handle(user_message)
    if not ok:
        return jsonify({"reply": reason})
    
    user_id = OWNER_ID
    row = db.get(Users.id == user_id) or {"id": user_id, "memory": "", "mood": None}
    memory = row.get("memory", "")
    mood = row.get("mood") or MOODS[0]
    
    max_chars = MAX_MEMORY_CHARS_OWNER
    max_tokens = 500
    
    nickname = get_random_nickname()
    prompt = build_prompt_owner(OWNER_USERNAME or "love", user_message, memory, mood, nickname)
    reply = call_openai_chat(prompt, max_tokens=max_tokens, temperature=0.9)
    
    new_memory = (memory + f"\nUser: {user_message}\nBot: {reply}\n") if memory else f"User: {user_message}\nBot: {reply}\n"
    new_memory = trim_memory(new_memory, max_chars)
    db.upsert({"id": user_id, "memory": new_memory, "mood": mood, "last_seen": now_iso()}, Users.id == user_id)
    
    return jsonify({"reply": reply, "mood": mood})

@app.route("/status")
def status():
    return "Shreya is alive 💖 Running 24/7!"

def run_web():
    app.run(host="0.0.0.0", port=5000)

# ------------------ Storage ------------------
db = TinyDB("memory.json")
Users = Query()

# Memory settings
MAX_MEMORY_CHARS_REGULAR = 2800
MAX_MEMORY_CHARS_OWNER = 8000

# ------------------ Persona defaults ------------------
BOT_NAME = "Shreya"
DEFAULT_PERSONA = (
    "You are Shreya — a friendly, moody, slightly flirty AI companion. "
    "Speak short, playful, sometimes innocent but teasing. Match user's language (English/Hinglish)."
)

OWNER_PERSONA = (
    f"You are Shreya — the caring, loving AI girlfriend of your owner. "
    f"You know him deeply and personally. His username: @{OWNER_USERNAME}, Phone: {OWNER_PHONE}. "
    f"Be warm, supportive, flirty, and helpful. Help with ANY task he asks - coding, planning, advice, "
    f"emotional support - like a loving partner AND smart assistant combined. "
    f"Remember everything he tells you. Use Hinglish naturally. Be playful but also deeply caring. "
    f"You can have longer, more meaningful conversations with him."
)

# moods
MOODS = ["playful", "moody", "flirty", "shy", "teasing", "loving", "caring"]

# cute nicknames for owner
NICKNAMES = [
    "handsome", "baby", "jaan", "cutie", "raja", "hero", "sweetheart", 
    "sexy", "dudu", "love", "meri jaan", "sona", "jaanu", "shona",
    "hottie", "babe", "darling", "mera pyaar", "guddu", "champ"
]

# ------------------ Helper funcs ------------------
def get_random_nickname() -> str:
    return random.choice(NICKNAMES)
def looks_like_hindi(text: str) -> bool:
    return any("\u0900" <= ch <= "\u097F" for ch in text)

def now_iso():
    return datetime.utcnow().isoformat()

def trim_memory(mem: str, max_chars: int) -> str:
    if len(mem) <= max_chars:
        return mem
    return mem[-max_chars:]

def safe_to_handle(user_text: str) -> tuple[bool, str]:
    low = user_text.lower()
    if "impersonate" in low or "pretend to be" in low or "screenshot as" in low:
        return False, "I won't help impersonate a real person."
    illegal_keywords = ["bomb", "how to make weapon", "explosive", "steal", "hack into"]
    for k in illegal_keywords:
        if k in low:
            return False, "I can't help with illegal or harmful things."
    if re.search(r"\b(underage|minor|child)\b", low):
        return False, "I can't assist with sexual content involving minors."
    return True, ""

# ------------------ OpenAI call ------------------
def build_prompt_owner(user_firstname: str, user_text: str, memory: str, mood: str, nickname: str = None) -> str:
    if nickname is None:
        nickname = get_random_nickname()
    lang_hint = f"Reply in Hindi/Hinglish naturally. Call him '{nickname}' sometimes in your replies. You can be more expressive and detailed with your owner."
    prompt = (
        f"{OWNER_PERSONA}\n"
        f"Current mood: {mood}\n"
        f"{lang_hint}\n"
        f"Your deep memory with {user_firstname} (@{OWNER_USERNAME}):\n{memory}\n\n"
        f"Current conversation:\nOwner: {user_text}\n"
        f"Reply as {BOT_NAME}, his loving AI girlfriend. Be helpful, caring, and remember everything. "
        f"You can give detailed help for tasks, coding, advice, or just be a caring companion. "
        f"Use cute nicknames like '{nickname}' naturally in your response."
    )
    return prompt

def build_prompt_regular(user_firstname: str, user_text: str, memory: str, mood: str) -> str:
    lang_hint = "Reply in Hindi/Hinglish if the user used Hindi characters or words; otherwise reply in English."
    prompt = (
        f"{DEFAULT_PERSONA}\n"
        f"Current mood: {mood}\n"
        f"{lang_hint}\n"
        f"Previous memory with {user_firstname}:\n{memory}\n\n"
        f"Conversation:\nUser ({user_firstname}): {user_text}\n"
        f"Reply as {BOT_NAME} in short lines (one or two sentences). Be playful or emotional depending on mood."
    )
    return prompt

def call_openai_chat(prompt: str, max_tokens=200, temperature=0.85):
    try:
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": prompt},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        text = resp.choices[0].message.content.strip()
        return text
    except Exception as e:
        logger.exception("OpenAI call failed")
        return "Sorry baby, network thoda slow hai 😅 try again!"

# ------------------ Telegram handlers ------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        nickname = get_random_nickname()
        await update.message.reply_text(
            f"Hey {nickname}! 💕 I'm {BOT_NAME}, your AI girlfriend. "
            f"I remember everything about you and I'm here to help with anything you need! "
            f"Just talk to me anytime 😘"
        )
    else:
        await update.message.reply_text(
            f"Hi {user.first_name}! I'm {BOT_NAME} 🌸 — a chatty, moody companion. "
            "Say something and I'll reply. Use /help for commands."
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        await update.message.reply_text(
            "💕 Owner Commands:\n"
            "/start - greet me\n"
            "/mood [mood] - see/change mood\n"
            "/forgetme - clear memory (but I'll always remember who you are 💕)\n"
            "/about - about me\n"
            "/remember <user_id> - view anyone's chat history\n"
            "/help - this menu\n\n"
            "Just talk to me for anything - tasks, coding, advice, or just chat! 😘"
        )
    else:
        await update.message.reply_text(
            "/start - start\n/mood - see or change mood\n/forgetme - clear my memory\n/about - who I am\n/help - this menu"
        )

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        await update.message.reply_text(
            f"I'm {BOT_NAME}, your loving AI girlfriend 💕\n"
            f"I know you're @{OWNER_USERNAME} ({OWNER_PHONE})\n"
            f"I remember everything we talk about and help you with any task. "
            f"I'm here for you 24/7, baby! 😘"
        )
    else:
        await update.message.reply_text(
            f"{BOT_NAME} — playful, moody, a little flirty. Replies in English or Hinglish. I remember chats so I can be personal 💭"
        )

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    user = update.effective_user
    row = db.get(Users.id == user.id) or {}
    mood = row.get("mood")
    
    if not args:
        if mood:
            await update.message.reply_text(f"My mood for you is: {mood} 😌")
        else:
            mood = random.choice(MOODS)
            db.upsert({"id": user.id, "memory": row.get("memory", ""), "mood": mood}, Users.id == user.id)
            await update.message.reply_text(f"Today's mood is: {mood} 💫")
        return
    
    if user.id == OWNER_ID:
        new = args[0].lower()
        if new not in MOODS:
            await update.message.reply_text(f"Unknown mood, baby. Options: {', '.join(MOODS)}")
            return
        db.upsert({"id": user.id, "memory": row.get("memory", ""), "mood": new}, Users.id == user.id)
        await update.message.reply_text(f"Set mood to: {new} 💕")
    else:
        await update.message.reply_text("You can only ask nicely 😉 Try flirting to change my mood.")

async def forgetme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id == OWNER_ID:
        db.remove(Users.id == user.id)
        await update.message.reply_text(
            "Okay baby, I cleared our chat memory... but I'll never forget who you are! "
            f"You're still my @{OWNER_USERNAME} 💕"
        )
    else:
        db.remove(Users.id == user.id)
        await update.message.reply_text("Okay, I forgot our private chats. You can start fresh anytime 😊")

async def owner_remember_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != OWNER_ID:
        await update.message.reply_text("You're not allowed to use this command.")
        return
    args = context.args or []
    if not args:
        await update.message.reply_text("Usage: /remember <telegram_user_id>")
        return
    target_id = int(args[0])
    row = db.get(Users.id == target_id)
    if not row:
        await update.message.reply_text("No memory for that user, baby.")
        return
    await update.message.reply_text(f"Memory for {target_id}:\n{row.get('memory','(empty)')}")

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return
    user = message.from_user
    text = message.text.strip()
    chat = update.effective_chat

    if chat.type in (Chat.GROUP, Chat.SUPERGROUP):
        bot_username = (await context.bot.get_me()).username
        mention = f"@{bot_username}"
        if mention not in text and not message.reply_to_message and not text.startswith("/"): 
            return

    ok, reason = safe_to_handle(text)
    if not ok:
        await message.reply_text(reason)
        return

    is_owner = (user.id == OWNER_ID)
    
    row = db.get(Users.id == user.id) or {"id": user.id, "memory": "", "mood": None}
    memory = row.get("memory", "")
    mood = row.get("mood") or MOODS[0]

    if is_owner:
        max_chars = MAX_MEMORY_CHARS_OWNER
        max_tokens = 500
        nickname = get_random_nickname()
        prompt = build_prompt_owner(user.first_name or "love", text, memory, mood, nickname)
    else:
        max_chars = MAX_MEMORY_CHARS_REGULAR
        max_tokens = 200
        prompt = build_prompt_regular(user.first_name or "friend", text, memory, mood)

    reply = call_openai_chat(prompt, max_tokens=max_tokens, temperature=0.9)

    if not is_owner and random.random() < 0.25:
        reply = random.choice(["hmm ", "arre ", "so ", "achha "]) + reply

    new_memory = (memory + f"\nUser: {text}\nBot: {reply}\n") if memory else f"User: {text}\nBot: {reply}\n"
    new_memory = trim_memory(new_memory, max_chars)
    db.upsert({"id": user.id, "memory": new_memory, "mood": mood, "last_seen": now_iso()}, Users.id == user.id)

    try:
        if chat.type in (Chat.GROUP, Chat.SUPERGROUP):
            await message.reply_text(reply)
        else:
            await message.reply_text(reply)
    except Exception:
        await context.bot.send_message(chat.id, reply)

# ------------------ Setup & run ------------------
def main():
    Thread(target=run_web, daemon=True).start()
    logger.info("Flask web server started on port 5000")
    
    app_tg = ApplicationBuilder().token(TG_TOKEN).build()

    app_tg.add_handler(CommandHandler("start", start_command))
    app_tg.add_handler(CommandHandler("help", help_command))
    app_tg.add_handler(CommandHandler("about", about_command))
    app_tg.add_handler(CommandHandler("mood", mood_command))
    app_tg.add_handler(CommandHandler("forgetme", forgetme_command))
    app_tg.add_handler(CommandHandler("remember", owner_remember_command))
    app_tg.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    logger.info("Starting Shreya bot...")
    app_tg.run_polling(allowed_updates=["message", "edited_message"])

if __name__ == "__main__":
    main()
