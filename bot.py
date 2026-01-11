import os
import random
from flask import Flask, request
import telebot
from telebot import types
from midiutil import MIDIFile

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN is not set")

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ===== ДАННЫЕ =====
GENRES = {
    "Trap": (90, 220),
    "Drill": (135, 145),
    "Detroit Club": (170, 220),
    "Club": (120, 140),
    "West Coast": (80, 115)
}

KEYS = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B"
]

user_state = {}

# ===== MIDI =====
def generate_midi(bpm, key, genre):
    midi = MIDIFile(1)
    midi.addTempo(0, 0, bpm)

    time = 0
    for _ in range(16):
        midi.addNote(0, 9, 36, time, 0.5, 100)  # kick
        midi.addNote(0, 9, 42, time, 0.25, 70)  # hat
        time += 0.5

    filename = f"{genre}_{bpm}BPM_{key}.mid"
    with open(filename, "wb") as f:
        midi.writeFile(f)

    return filename

# ===== КНОПКИ =====
def main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for g in GENRES:
        kb.add(g)
    kb.add("🎲 Авто BPM")
    return kb

def key_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=4)
    for k in KEYS:
        kb.add(k)
    kb.add("🎹 СГЕНЕРИРОВАТЬ MIDI")
    return kb

# ===== START =====
@bot.message_handler(commands=["start"])
def start(msg):
    user_state[msg.chat.id] = {}
    bot.send_message(
        msg.chat.id,
        "🎛 MIDI Producer Bot\n\n"
        "1️⃣ Выбери жанр\n"
        "2️⃣ Введи BPM или нажми авто\n"
        "3️⃣ Выбери тональность\n"
        "4️⃣ Нажми 🎹 СГЕНЕРИРОВАТЬ MIDI",
        reply_markup=main_keyboard()
    )

# ===== ЖАНР =====
@bot.message_handler(func=lambda m: m.text in GENRES)
def genre(msg):
    state = user_state.setdefault(msg.chat.id, {})
    state["genre"] = msg.text
    bot.send_message(msg.chat.id, f"Жанр выбран: {msg.text}\nВведи BPM цифрами или нажми 🎲 Авто BPM")

# ===== BPM ЦИФРАМИ =====
@bot.message_handler(func=lambda m: m.text.isdigit())
def bpm(msg):
    state = user_state.setdefault(msg.chat.id, {})
    state["bpm"] = int(msg.text)
    bot.send_message(msg.chat.id, f"BPM установлен: {msg.text}\nВыбери тональность", reply_markup=key_keyboard())

# ===== AUTO BPM =====
@bot.message_handler(func=lambda m: m.text == "🎲 Авто BPM")
def auto_bpm(msg):
    state = user_state.setdefault(msg.chat.id, {})
    genre = state.get("genre")

    if not genre:
        bot.send_message(msg.chat.id, "Сначала выбери жанр")
        return

    bpm = random.randint(*GENRES[genre])
    state["bpm"] = bpm
    bot.send_message(msg.chat.id, f"Авто BPM: {bpm}\nВыбери тональность", reply_markup=key_keyboard())

# ===== ТОН =====
@bot.message_handler(func=lambda m: m.text in KEYS)
def key(msg):
    state = user_state.setdefault(msg.chat.id, {})
    state["key"] = msg.text
    bot.send_message(
        msg.chat.id,
        f"Тональность: {msg.text}\n"
        f"Готово. Нажми 🎹 СГЕНЕРИРОВАТЬ MIDI",
        reply_markup=key_keyboard()
    )

# ===== GENERATE =====
@bot.message_handler(func=lambda m: m.text == "🎹 СГЕНЕРИРОВАТЬ MIDI")
def generate(msg):
    state = user_state.get(msg.chat.id)

    if not state or not all(k in state for k in ("genre", "bpm", "key")):
        bot.send_message(msg.chat.id, "Не все параметры выбраны")
        return

    filename = generate_midi(state["bpm"], state["key"], state["genre"])
    caption = f"{state['genre']} | {state['bpm']} BPM | {state['key']}"

    with open(filename, "rb") as f:
        bot.send_document(msg.chat.id, f, caption=caption)

    os.remove(filename)

# ===== WEBHOOK =====
@app.route("/", methods=["POST"])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

@app.route("/", methods=["GET"])
def index():
    return "Bot is running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

