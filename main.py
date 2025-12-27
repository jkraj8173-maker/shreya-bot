# main.py
import os, random, logging, secrets, shutil
from threading import Thread
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from tinydb import TinyDB, Query
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from flask import Flask, render_template, request, jsonify, session, redirect

# 1. SETUP & CONFIG
load_dotenv()
db = TinyDB("memory.json")
Users = Query()
client = OpenAI(api_key=os.getenv("OPENAI_KEY"))

# Environment Variables (Required for hosting)
TG_TOKEN = os.getenv("TG_TOKEN", "")
OWNER_ID = int(os.getenv("OWNER_ID", "0"))
MODEL = os.getenv("MODEL_NAME", "gpt-4o-mini")

# 2. FLASK WEB SERVER
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

def get_config(key, default=''):
    config_table = db.table('config')
    res = config_table.search(Query().key == key)
    return res[0]['value'] if res else default

@app.route("/")
def index():
    if not session.get("auth"): return render_template("login.html")
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    password = get_config('web_password', 'love u')
    if request.json.get("password") == password:
        session["auth"] = True
        return jsonify({"success": True})
    return jsonify({"success": False}), 401

@app.route("/chat", methods=["POST"])
def chat():
    if not session.get("auth"): return jsonify({"error": "No Auth"}), 401
    msg = request.json.get("message", "")
    user_data = db.get(Users.id == OWNER_ID) or {"id": OWNER_ID, "memory": "", "mood": "loving"}
    memory = user_data.get('memory', "")
    mood = user_data.get('mood', "loving")
    prompt = f"You are Shreya, a sweet AI girlfriend. History: {memory}. User: {msg}"
    try:
        res = client.chat.completions.create(model=MODEL, messages=[{"role":"system","content":prompt}], max_tokens=200)
        reply = res.choices[0].message.content.strip()
    except:
        reply = "Network slow hai baby... 😅"
    new_mem = (memory + f"\nU: {msg}\nB: {reply}")[-5000:]
    db.upsert({"id": OWNER_ID, "memory": new_mem, "mood": mood}, Users.id == OWNER_ID)
    return jsonify({"reply": reply})

@app.route("/diary/get")
def get_diary():
    if not session.get("auth"): return jsonify({}), 401
    diary_table = db.table('diary')
    entry = diary_table.get(Users.id == OWNER_ID) or {"notes": [], "last_ai_line": "Thinking of you... ✨"}
    return jsonify(entry)

@app.route("/diary/add_note", methods=["POST"])
def add_diary_note():
    if not session.get("auth"): return jsonify({}), 401
    note = request.json.get("note", "").strip()
    if not note: return jsonify({"success": False})
    diary_table = db.table('diary')
    entry = diary_table.get(Users.id == OWNER_ID) or {"notes": [], "last_ai_line": "Thinking of you... ✨"}
    entry["notes"].append({"text": note, "date": datetime.now().strftime("%I:%M %p, %d %b")})
    diary_table.upsert(entry, Users.id == OWNER_ID)
    return jsonify({"success": True})

@app.route("/diary/delete_note", methods=["POST"])
def delete_diary_note():
    if not session.get("auth"): return jsonify({}), 401
    idx = request.json.get("index")
    diary_table = db.table('diary')
    entry = diary_table.get(Users.id == OWNER_ID)
    if entry and 0 <= idx < len(entry["notes"]):
        entry["notes"].pop(idx)
        diary_table.upsert(entry, Users.id == OWNER_ID)
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
    return jsonify(db.all())

@app.route("/admin/update_password", methods=["POST"])
def update_pw():
    if not session.get("admin_auth"): return jsonify({"success": False}), 401
    new_pw = request.json.get("password")
    db.table('config').upsert({'key': 'web_password', 'value': new_pw}, Query().key == 'web_password')
    return jsonify({"success": True})

@app.route("/status")
def status():
    return "Shreya is alive and ready! 💖"

# 3. TELEGRAM BOT
async def handle_tg_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    uid = update.effective_user.id
    msg = update.message.text
    user_data = db.get(Users.id == uid) or {"id": uid, "memory": "", "mood": "loving"}
    memory = user_data.get('memory', "")
    mood = user_data.get('mood', "loving")
    prompt = f"You are Shreya, a sweet AI girlfriend. History: {memory}. User: {msg}"
    try:
        res = client.chat.completions.create(model=MODEL, messages=[{"role":"system","content":prompt}], max_tokens=200)
        reply = res.choices[0].message.content.strip()
    except:
        reply = "Thoda wait karo baby... 💖"
    db.upsert({"id": uid, "memory": (memory + f"\nU: {msg}\nB: {reply}")[-2000:], "mood": mood}, Users.id == uid)
    await update.message.reply_text(reply)

# 4. RUN EVERYTHING
if __name__ == "__main__":
    if not os.path.exists('static/music'): os.makedirs('static/music')
    db.table('config').upsert({'key': 'web_password', 'value': 'love u'}, Query().key == 'web_password')
    
    # Port configuration for hosting (Defaults to 5000)
    port = int(os.environ.get("PORT", 5000))
    Thread(target=lambda: app.run(host="0.0.0.0", port=port)).start()
    
    # Start Telegram Bot
    if TG_TOKEN:
        bot = ApplicationBuilder().token(TG_TOKEN).build()
        bot.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_tg_message))
        bot.run_polling()
    else:
        logging.warning("TG_TOKEN not set. Telegram bot will not start.")
