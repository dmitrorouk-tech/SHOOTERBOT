import os
import random
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from mido import Message, MidiFile, MidiTrack, MetaMessage

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN is not set")

bot = telebot.TeleBot(TOKEN)

# ================= СОСТОЯНИЕ =================
user_state = {}

KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MODES = ["Minor", "Major"]

AUTO_BPM = {
    "trap": list(range(120, 151)),
    "drill": list(range(130, 146)),
    "club": list(range(124, 129)),
    "any": list(range(80, 221)),
}

# ================= HELPERS =================
def bpm_comment(bpm):
    if bpm < 100:
        return "🧊 Медленный темп, больше чилла"
    if bpm < 130:
        return "🔥 Классический trap вайб"
    if bpm < 146:
        return "🔫 Drill territory, можно жёстко"
    return "⚡ Быстро, почти rage"

def bpm_emoji(bpm):
    if bpm < 100: return "🧊"
    if bpm < 130: return "🔥"
    if bpm < 146: return "🔫"
    return "⚡"

# ================= MIDI =================
def generate_midi(bpm, filename):
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)

    tempo = int(60000000 / bpm)
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))

    notes = [60, 63, 67]  # минорный аккорд
    for n in notes:
        track.append(Message("note_on", note=n, velocity=90, time=0))
    for n in notes:
        track.append(Message("note_off", note=n, velocity=90, time=480))

    mid.save(filename)

# ================= UI =================
def main_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("✍️ Ввести BPM", callback_data="enter_bpm"),
        InlineKeyboardButton("🎲 AUTO BPM", callback_data="auto_menu"),
        InlineKeyboardButton("🎹 Тональность", callback_data="key"),
        InlineKeyboardButton("🎛 Аккорды ON / OFF", callback_data="chords"),
    )
    return kb

def auto_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🔥 Trap", callback_data="auto_trap"),
        InlineKeyboardButton("🔫 Drill", callback_data="auto_drill"),
        InlineKeyboardButton("🪩 Club", callback_data="auto_club"),
        InlineKeyboardButton("🎲 Any", callback_data="auto_any"),
        InlineKeyboardButton("⬅ Назад", callback_data="back"),
    )
    return kb

def key_keyboard():
    kb = InlineKeyboardMarkup(row_width=3)
    for k in KEYS:
        kb.add(InlineKeyboardButton(k, callback_data=f"key_{k}"))
    kb.add(
        InlineKeyboardButton("Минор", callback_data="mode_Minor"),
        InlineKeyboardButton("Мажор", callback_data="mode_Major"),
        InlineKeyboardButton("⬅ Назад", callback_data="back"),
    )
    return kb

# ================= ЛОГИКА =================
@bot.message_handler(commands=["start"])
def start(message):
    user_state[message.chat.id] = {
        "bpm": 140,
        "key": "C",
        "mode": "Minor",
        "chords": True,
    }
    send_status(message.chat.id)

def send_status(chat_id):
    s = user_state[chat_id]
    text = (
        "🎧 Продюсер-панель\n\n"
        f"{bpm_emoji(s['bpm'])} {s['bpm']} BPM · {s['key']} {s['mode']}\n"
        f"{bpm_comment(s['bpm'])}\n\n"
        "✍️ Можешь написать BPM цифрами"
    )
    bot.send_message(chat_id, text, reply_markup=main_keyboard())

# ===== ВВОД BPM ЦИФРАМИ =====
@bot.message_handler(func=lambda m: m.text.isdigit())
def bpm_text(message):
    bpm = int(message.text)
    if not 60 <= bpm <= 220:
        bot.reply_to(message, "❌ BPM от 60 до 220")
        return

    s = user_state.setdefault(message.chat.id, {})
    s["bpm"] = bpm

    filename = f"{bpm}_BPM_{s['key']}_{s['mode']}.mid"
    generate_midi(bpm, filename)

    bot.send_message(
        message.chat.id,
        f"{bpm_emoji(bpm)} Окей\n"
        f"{bpm} BPM · {s['key']} {s['mode']}\n"
        f"{bpm_comment(bpm)}"
    )

    with open(filename, "rb") as f:
        bot.send_document(message.chat.id, f)

# ===== CALLBACKS =====
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    chat_id = call.message.chat.id
    s = user_state.setdefault(chat_id, {"bpm": 140, "key": "C", "mode": "Minor", "chords": True})
    d = call.data

    if d == "auto_menu":
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=auto_keyboard())

    elif d.startswith("auto_"):
        style = d.replace("auto_", "")
        bpm = random.choice(AUTO_BPM[style])
        s["bpm"] = bpm

        filename = f"{style.capitalize()}_{bpm}_BPM_{s['key']}_{s['mode']}.mid"
        generate_midi(bpm, filename)

        bot.send_message(
            chat_id,
            f"{bpm_emoji(bpm)} {style.upper()} вайб\n"
            f"{bpm} BPM · {s['key']} {s['mode']}\n"
            f"{bpm_comment(bpm)}"
        )

        with open(filename, "rb") as f:
            bot.send_document(chat_id, f)

    elif d == "key":
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=key_keyboard())

    elif d.startswith("key_"):
        s["key"] = d.split("_")[1]
        send_status(chat_id)

    elif d.startswith("mode_"):
        s["mode"] = d.split("_")[1]
        send_status(chat_id)

    elif d == "chords":
        s["chords"] = not s["chords"]
        send_status(chat_id)

    elif d == "back":
        send_status(chat_id)

    bot.answer_callback_query(call.id)

print("Bot started (polling)")
bot.infinity_polling(skip_pending=True)

