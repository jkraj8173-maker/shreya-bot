# Jeet-AI main.py
import os, random, logging, secrets, shutil, psycopg2, psycopg2.extras
from threading import Thread
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler
from flask import Flask, render_template, request, jsonify, session, redirect

# 1. SETUP & CONFIG
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL:
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
else:
    print("DATABASE_URL not set, using fallback TinyDB")
    from tinydb import TinyDB, Query
    db = TinyDB("memory.json")
    Users = Query()

client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

# Environment Variables
TG_TOKEN = os.getenv("TG_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
MODEL = os.getenv("MODEL_NAME", "gpt-4o-mini")
BOT_NAME = os.getenv("BOT_NAME", "Jeet")
GF_NAME = os.getenv("GF_NAME", "Aradhya")
WEB_PASSWORD = os.getenv("WEB_PASSWORD", "love u")

# Create tables if using PostgreSQL
if DATABASE_URL:
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                memory TEXT DEFAULT '',
                mood TEXT DEFAULT 'loving'
            );
            CREATE TABLE IF NOT EXISTS config (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                message TEXT,
                response TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS diary (
                id SERIAL PRIMARY KEY,
                user_id BIGINT,
                notes JSONB DEFAULT '[]',
                last_ai_line TEXT DEFAULT 'Thinking of you... ✨'
            );
        """)

# Helper functions
def get_user_data(user_id):
    if DATABASE_URL:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else {"id": user_id, "memory": "", "mood": "loving"}
    else:
        return db.get(Users.id == user_id) or {"id": user_id, "memory": "", "mood": "loving"}

def update_user_data(user_id, memory, mood):
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO users (id, memory, mood) VALUES (%s, %s, %s) ON CONFLICT (id) DO UPDATE SET memory = EXCLUDED.memory, mood = EXCLUDED.mood", (user_id, memory, mood))
    else:
        db.upsert({"id": user_id, "memory": memory, "mood": mood}, Users.id == user_id)

def save_message(user_id, message, response):
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO messages (user_id, message, response) VALUES (%s, %s, %s)", (user_id, message, response))

def get_messages(user_id):
    if DATABASE_URL:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM messages WHERE user_id = %s ORDER BY timestamp", (user_id,))
            return [dict(row) for row in cur.fetchall()]
    else:
        return []  # Fallback

def get_config(key, default=''):
    if DATABASE_URL:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT value FROM config WHERE key = %s", (key,))
            row = cur.fetchone()
            return row['value'] if row else default
    else:
        config_table = db.table('config')
        res = config_table.search(Query().key == key)
        return res[0]['value'] if res else default

def set_config(key, value):
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO config (key, value) VALUES (%s, %s) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value", (key, value))
    else:
        db.table('config').upsert({'key': key, 'value': value}, Query().key == key)

def get_diary(user_id):
    if DATABASE_URL:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM diary WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return dict(row) if row else {"notes": [], "last_ai_line": "Thinking of you... ✨"}
    else:
        diary_table = db.table('diary')
        entry = diary_table.get(Users.id == user_id) or {"notes": [], "last_ai_line": "Thinking of you... ✨"}
        return entry

def update_diary(user_id, notes, last_ai_line):
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO diary (user_id, notes, last_ai_line) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET notes = EXCLUDED.notes, last_ai_line = EXCLUDED.last_ai_line", (user_id, notes, last_ai_line))
    else:
        diary_table = db.table('diary')
        diary_table.upsert({"id": user_id, "notes": notes, "last_ai_line": last_ai_line}, Users.id == user_id)

# 2. FLASK WEB SERVER
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

@app.route("/")
def index():
    if not session.get("auth"): return render_template("login.html")
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    password = get_config('web_password', WEB_PASSWORD)
    if request.json.get("password") == password:
        session["auth"] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route("/chat", methods=["POST"])
def chat():
    if not session.get("auth"): return jsonify({"error": "No Auth"}), 401
    msg = request.json.get("message", "")
    user_id = OWNER_ID  # Web chat is for owner/Aradhya
    user_data = get_user_data(user_id)
    memory = user_data.get('memory', "")
    mood = user_data.get('mood', "loving")
    is_owner = True  # Web is owner mode? Wait, according to desc, web is for Aradhya, but owner control.
    # For web, since it's romantic chat, use romantic mode.
    prompt = f"You are Jeet 💙, a loving AI boyfriend for {GF_NAME}. Use nicknames like bubu, sona, guddi, poku, chikki, mishti, laddoo, rasmalai, baby doll, gudiya, pari, shona, jaani, coco, puchi. History: {memory}. User: {msg}"
    try:
        res = client.chat.completions.create(model=MODEL, messages=[{"role":"system","content":prompt}], max_tokens=200)
        reply = res.choices[0].message.content.strip()
    except:
        reply = "Network slow hai bubu... 😅"
    new_mem = (memory + f"\nU: {msg}\nB: {reply}")[-5000:]
    update_user_data(user_id, new_mem, mood)
    save_message(user_id, msg, reply)
    return jsonify({"reply": reply})

@app.route("/diary/get")
def get_diary_route():
    if not session.get("auth"): return jsonify({}), 401
    diary = get_diary(OWNER_ID)
    return jsonify(diary)

@app.route("/diary/add_note", methods=["POST"])
def add_diary_note():
    if not session.get("auth"): return jsonify({}), 401
    note = request.json.get("note", "").strip()
    if not note: return jsonify({"success": False})
    diary = get_diary(OWNER_ID)
    notes = diary["notes"]
    notes.append({"text": note, "date": datetime.now().strftime("%I:%M %p, %d %b")})
    update_diary(OWNER_ID, notes, diary["last_ai_line"])
    return jsonify({"success": True})

@app.route("/diary/delete_note", methods=["POST"])
def delete_diary_note():
    if not session.get("auth"): return jsonify({}), 401
    idx = request.json.get("index")
    diary = get_diary(OWNER_ID)
    notes = diary["notes"]
    if 0 <= idx < len(notes):
        notes.pop(idx)
        update_diary(OWNER_ID, notes, diary["last_ai_line"])
        return jsonify({"success": True})
    return jsonify({"success": False})

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route("/music/list")
def music_list():
    path = 'static/music'
    if not os.path.exists(path): os.makedirs(path)
    return jsonify([f for f in os.listdir(path) if f.endswith(('.mp3', '.wav'))])

@app.route("/admin_login", methods=["POST"])
def admin_login():
    if request.json.get("password") == "admin":
        session["admin_auth"] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route("/admin_dashboard")
def admin_dashboard():
    if not session.get("admin_auth"): return redirect("/")
    return render_template("admin.html")

@app.route("/admin/users")
def admin_users():
    if not session.get("admin_auth"): return jsonify([]), 401
    if DATABASE_URL:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM users")
            return jsonify([dict(row) for row in cur.fetchall()])
    else:
        return jsonify(db.all())

@app.route("/admin/update_password", methods=["POST"])
def update_pw():
    if not session.get("admin_auth"): return jsonify({"success": False}), 401
    new_pw = request.json.get("password")
    set_config('web_password', new_pw)
    return jsonify({"success": True})

# Repair Routes
@app.route("/repair/history")
def repair_history():
    if not session.get("auth"): return jsonify([]), 401
    if DATABASE_URL:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM messages ORDER BY timestamp DESC")
            return jsonify([dict(row) for row in cur.fetchall()])
    else:
        return jsonify([])

@app.route("/repair/clear_user", methods=["POST"])
def repair_clear_user():
    if not session.get("auth"): return jsonify({"success": False}), 401
    user_id = request.json.get("user_id")
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM messages WHERE user_id = %s", (user_id,))
            cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
            cur.execute("DELETE FROM diary WHERE user_id = %s", (user_id,))
        return jsonify({"message": f"Data cleared for user {user_id}"})
    else:
        return jsonify({"message": "Not using database"})

@app.route("/repair/delete_old", methods=["POST"])
def repair_delete_old():
    if not session.get("auth"): return jsonify({"success": False}), 401
    if DATABASE_URL:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM messages WHERE timestamp < NOW() - INTERVAL '30 days'")
        return jsonify({"message": "Old messages deleted"})
    else:
        return jsonify({"message": "Not using database"})

@app.route("/status")
def status():
    return "Jeet 💙 is alive and ready!"

# 3. TELEGRAM BOT
nicknames = ["bubu", "sona", "guddi", "poku", "chikki", "mishti", "laddoo", "rasmalai", "baby doll", "gudiya", "pari", "shona", "jaani", "coco", "puchi"]

async def handle_tg_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    uid = update.effective_user.id
    msg = update.message.text
    user_data = get_user_data(uid)
    memory = user_data.get('memory', "")
    mood = user_data.get('mood', "loving")
    is_owner = uid == OWNER_ID
    if is_owner:
        prompt = f"You are Jeet 💙, a smart and helpful AI assistant for {GF_NAME}. Be intelligent, provide study help, notes summary, planning, decision making, general AI help. History: {memory}. User: {msg}"
    else:
        prompt = f"You are Jeet 💙, a loving AI boyfriend for {GF_NAME}. Use nicknames like {', '.join(nicknames)}. History: {memory}. User: {msg}"
    try:
        res = client.chat.completions.create(model=MODEL, messages=[{"role":"system","content":prompt}], max_tokens=200)
        reply = res.choices[0].message.content.strip()
    except:
        reply = "Thoda wait karo bubu... 💙" if not is_owner else "Wait a sec..."
    new_mem = (memory + f"\nU: {msg}\nB: {reply}")[-2000:]
    update_user_data(uid, new_mem, mood)
    save_message(uid, msg, reply)
    await update.message.reply_text(reply)

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    is_owner = uid == OWNER_ID
    greeting = f"Aww {random.choice(nicknames)} 🫶 idhar aa… Jeet 💙 hai na 💙" if not is_owner else f"Hello {GF_NAME}, Jeet 💙 here to help!"
    await update.message.reply_text(greeting)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🤖 Commands:
/start - Cute greeting
/help - This list
/mood - Show current mood
/forgetme - Clear memory
/history - Full chat history (Owner only)
/about - About Jeet 💙
    """
    await update.message.reply_text(help_text)

async def mood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data = get_user_data(uid)
    mood = user_data.get('mood', "loving")
    await update.message.reply_text(f"Current mood: {mood} 💙")

async def forgetme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    update_user_data(uid, "", "loving")
    await update.message.reply_text("Memory cleared! Fresh start 💙")

async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid != OWNER_ID:
        await update.message.reply_text("This command is for owner only.")
        return
    messages = get_messages(uid)
    if not messages:
        await update.message.reply_text("No history yet.")
        return
    history_text = "\n".join([f"{m['timestamp']}: U: {m['message']} B: {m['response']}" for m in messages[-20:]])  # Last 20
    await update.message.reply_text(f"Chat History:\n{history_text}")

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    about_text = f"Hi, I'm Jeet 💙, AI boyfriend for {GF_NAME}. Loving, teasing, protective, comforting."
    await update.message.reply_text(about_text)

# 4. RUN EVERYTHING
if __name__ == "__main__":
    if not os.path.exists('static/music'): os.makedirs('static/music')
    set_config('web_password', WEB_PASSWORD)
    
    # Port configuration for hosting (Defaults to 5000)
    port = int(os.environ.get("PORT", 5000))
    Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()
    
    # Start Telegram Bot
    if TG_TOKEN:
        bot = ApplicationBuilder().token(TG_TOKEN).build()
        bot.add_handler(CommandHandler("start", start_command))
        bot.add_handler(CommandHandler("help", help_command))
        bot.add_handler(CommandHandler("mood", mood_command))
        bot.add_handler(CommandHandler("forgetme", forgetme_command))
        bot.add_handler(CommandHandler("history", history_command))
        bot.add_handler(CommandHandler("about", about_command))
        bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_tg_message))
        bot.run_polling()
    else:
        logging.warning("TG_TOKEN not set. Telegram bot will not start.")
