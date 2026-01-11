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

AUTO_BPM_PRESETS = {
    "trap": list(range(120, 151)),
    "drill": list(range(130, 146)),
    "club": list(range(124, 129)),
    "any": list(range(80, 221)),
}

# ================= MIDI =================
def generate_midi(bpm: int, filename: str):
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)

    tempo = int(60000000 / bpm)
    track.append(MetaMessage("set_tempo", tempo=tempo, time=0))

    # простой аккорд (C)
    notes = [60, 64, 67]
    for note in notes:
        track.append(Message("note_on", note=note, velocity=90, time=0))
    for note in notes:
        track.append(Message("note_off", note=note, velocity=90, time=480))

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

def auto_bpm_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🎧 Trap", callback_data="auto_trap"),
        InlineKeyboardButton("🔫 Drill", callback_data="auto_drill"),
        InlineKeyboardButton("🪩 Club", callback_data="auto_club"),
        InlineKeyboardButton("🎲 Любой BPM", callback_data="auto_any"),
        InlineKeyboardButton("⬅ Назад", callback_data="back"),
    )
    return kb

def key_keyboard():
    kb = InlineKeyboardMarkup(row_width=3)
    for k in KEYS:
        kb.add(InlineKeyboardButton(k, callback_data=f"key_{k}"))
    kb.add(InlineKeyboardButton("⬅ Назад", callback_data="back"))
    return kb

# ================= ЛОГИКА =================
@bot.message_handler(commands=["start"])
def start(message):
    user_state[message.chat.id] = {
        "bpm": 140,
        "key": "C",
        "chords": True,
    }
    send_status(message.chat.id)

def send_status(chat_id):
    s = user_state[chat_id]
    text = (
        "🎧 Продюсер-панель\n\n"
        f"🎚 BPM: {s['bpm']}\n"
        f"🎹 Тональность: {s['key']}\n"
        f"🎛 Аккорды: {'ВКЛ' if s['chords'] else 'ВЫКЛ'}\n\n"
        "✍️ Напиши BPM цифрами (например: 140)"
    )
    bot.send_message(chat_id, text, reply_markup=main_keyboard())

# ===== ВВОД BPM ЦИФРАМИ =====
@bot.message_handler(func=lambda m: m.text.isdigit())
def bpm_from_text(message):
    bpm = int(message.text)
    if bpm < 60 or bpm > 220:
        bot.reply_to(message, "❌ BPM должен быть от 60 до 220")
        return

    state = user_state.setdefault(message.chat.id, {})
    state["bpm"] = bpm

    filename = f"bpm_{bpm}.mid"
    generate_midi(bpm, filename)

    bot.send_message(message.chat.id, f"🎚 BPM установлен: {bpm}")
    with open(filename, "rb") as f:
        bot.send_document(message.chat.id, f, caption=f"🎼 MIDI ({bpm} BPM)")

# ===== CALLBACKS =====
@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    chat_id = call.message.chat.id
    state = user_state.setdefault(chat_id, {"bpm": 140, "key": "C", "chords": True})
    data = call.data

    if data == "auto_menu":
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=auto_bpm_keyboard())

    elif data.startswith("auto_"):
        mode = data.replace("auto_", "")
        bpm = random.choice(AUTO_BPM_PRESETS[mode])
        state["bpm"] = bpm

        filename = f"auto_{mode}_{bpm}.mid"
        generate_midi(bpm, filename)

        bot.send_message(chat_id, f"🎲 AUTO BPM ({mode.upper()}): {bpm}")
        with open(filename, "rb") as f:
            bot.send_document(chat_id, f, caption=f"🎼 MIDI ({bpm} BPM)")

    elif data == "key":
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=key_keyboard())

    elif data.startswith("key_"):
        state["key"] = data.split("_")[1]
        send_status(chat_id)

    elif data == "chords":
        state["chords"] = not state["chords"]
        send_status(chat_id)

    elif data == "back":
        send_status(chat_id)

    bot.answer_callback_query(call.id)

print("Bot started (polling)")
bot.infinity_polling(skip_pending=True)


