import os
import random
import time
import zipfile

from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from midiutil import MIDIFile

# ================== ENV ==================

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise ValueError("TOKEN не задан")
if not WEBHOOK_URL:
    raise ValueError("WEBHOOK_URL не задан")

# ================== BOT + APP ==================

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

# ================== ЖАНРЫ ==================

GENRES = {
    "Trap": list(range(90, 221)),
    "Detroit": list(range(170, 221)),
    "Club": list(range(120, 141)),
    "WestCoast": list(range(80, 116)),
    "Drill": list(range(135, 146)),
}

GENRE_NAMES = {
    "Trap": "Trap",
    "Detroit": "Detroit",
    "Club": "Club",
    "WestCoast": "West Coast",
    "Drill": "Drill",
}

GENRE_EMOJI = {
    "Trap": "🔥",
    "Detroit": "🏭",
    "Club": "🪩",
    "WestCoast": "🚗",
    "Drill": "🔫",
}

KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# ================== STATE ==================

user_state = {}

def init_user(chat_id):
    user_state[chat_id] = {
        "genre": "Trap",
        "bpm": 140,
        "key": "C",
        "mode": "Minor",
        "files": []
    }

# ================== KEYBOARDS ==================

def main_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🎧 Жанр", callback_data="genre"),
        InlineKeyboardButton("🎲 AUTO", callback_data="auto"),
        InlineKeyboardButton("🎹 Тональность", callback_data="key"),
        InlineKeyboardButton("📦 PACK", callback_data="pack"),
    )
    return kb

def genre_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    for g in GENRES:
        kb.add(
            InlineKeyboardButton(
                f"{GENRE_EMOJI[g]} {GENRE_NAMES[g]}",
                callback_data=f"genre_{g}"
            )
        )
    kb.add(InlineKeyboardButton("⬅ Назад", callback_data="back"))
    return kb

def key_kb():
    kb = InlineKeyboardMarkup(row_width=3)
    for k in KEYS:
        kb.add(InlineKeyboardButton(k, callback_data=f"key_{k}"))
    kb.add(
        InlineKeyboardButton("Minor", callback_data="mode_Minor"),
        InlineKeyboardButton("Major", callback_data="mode_Major"),
        InlineKeyboardButton("⬅ Назад", callback_data="back")
    )
    return kb

# ================== MIDI ==================

def make_midi(filename, bpm):
    midi = MIDIFile(1)
    midi.addTempo(0, 0, bpm)

    notes = [60, 63, 67]
    t = 0
    for _ in range(8):
        for n in notes:
            midi.addNote(0, 0, n, t, 1, 100)
        t += 1

    with open(filename, "wb") as f:
        midi.writeFile(f)

# ================== HANDLERS ==================

@bot.message_handler(commands=["start"])
def start(m):
    init_user(m.chat.id)
    bot.send_message(
        m.chat.id,
        "🎧 Producer MIDI Bot\n"
        "Жанры • BPM • MIDI • ZIP\n\n"
        "Работаем 👇",
        reply_markup=main_kb()
    )

@bot.callback_query_handler(func=lambda c: True)
def callbacks(c):
    chat_id = c.message.chat.id
    s = user_state.get(chat_id)
    d = c.data

    if not s:
        init_user(chat_id)
        s = user_state[chat_id]

    if d == "genre":
        bot.edit_message_reply_markup(chat_id, c.message.message_id, reply_markup=genre_kb())

    elif d.startswith("genre_"):
        g = d.replace("genre_", "")
        s["genre"] = g
        s["bpm"] = random.choice(GENRES[g])
        bot.send_message(chat_id, f"{GENRE_EMOJI[g]} {GENRE_NAMES[g]} · {s['bpm']} BPM")

    elif d == "auto":
        s["bpm"] = random.choice(GENRES[s["genre"]])
        generate_and_send(chat_id)

    elif d == "key":
        bot.edit_message_reply_markup(chat_id, c.message.message_id, reply_markup=key_kb())

    elif d.startswith("key_"):
        s["key"] = d.replace("key_", "")
        bot.send_message(chat_id, f"🎹 {s['key']} {s['mode']}")

    elif d.startswith("mode_"):
        s["mode"] = d.replace("mode_", "")
        bot.send_message(chat_id, f"🎹 {s['key']} {s['mode']}")

    elif d == "pack":
        send_pack(chat_id)

    elif d == "back":
        bot.edit_message_reply_markup(chat_id, c.message.message_id, reply_markup=main_kb())

# ================== GENERATION ==================

def generate_and_send(chat_id):
    s = user_state[chat_id]

    filename = f"{GENRE_NAMES[s['genre']]}_{s['bpm']}_BPM_{s['key']}_{s['mode']}.mid"
    make_midi(filename, s["bpm"])
    s["files"].append(filename)

    bot.send_message(
        chat_id,
        f"{GENRE_EMOJI[s['genre']]} {GENRE_NAMES[s['genre']]}\n"
        f"🎚 {s['bpm']} BPM\n"
        f"🎹 {s['key']} {s['mode']}"
    )

    with open(filename, "rb") as f:
        bot.send_document(chat_id, f)

# ================== PACK ==================

def send_pack(chat_id):
    s = user_state[chat_id]
    if not s["files"]:
        bot.send_message(chat_id, "📭 Нет файлов для пака")
        return

    zip_name = f"{GENRE_NAMES[s['genre']]}_MIDI_Pack_{int(time.time())}.zip"

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as z:
        for f in s["files"]:
            z.write(f)

    with open(zip_name, "rb") as zf:
        bot.send_document(chat_id, zf)

    s["files"].clear()

# ================== WEBHOOK ==================

@app.route("/", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(
        request.stream.read().decode("utf-8")
    )
    bot.process_new_updates([update])
    return "OK", 200

# ================== START ==================

bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))



