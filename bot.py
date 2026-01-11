import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from mido import Message, MidiFile, MidiTrack
import random

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN is not set")

bot = telebot.TeleBot(TOKEN)

# ================= STATE =================
user_state = {}

KEYS = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
MODES = ["Minor", "Major"]

# ================= UI =================
def main_keyboard():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🎚 Выбрать BPM", callback_data="bpm"),
        InlineKeyboardButton("🎲 AUTO BPM", callback_data="auto_bpm"),
        InlineKeyboardButton("🎹 Тональность", callback_data="key"),
        InlineKeyboardButton("🎛 Аккорды ON/OFF", callback_data="chords"),
    )
    return kb


def key_keyboard():
    kb = InlineKeyboardMarkup(row_width=3)
    for key in KEYS:
        kb.add(InlineKeyboardButton(key, callback_data=f"key_{key}"))
    kb.add(
        InlineKeyboardButton("Минор", callback_data="mode_Minor"),
        InlineKeyboardButton("Мажор", callback_data="mode_Major"),
        InlineKeyboardButton("⬅ Назад", callback_data="back"),
    )
    return kb


# ================= MIDI =================
def generate_midi(bpm: int, filename: str):
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)

    track.append(Message("program_change", program=0, time=0))

    tempo = int(60000000 / bpm)

    notes = [60, 64, 67]  # C major chord
    for note in notes:
        track.append(Message("note_on", note=note, velocity=64, time=0))
    for note in notes:
        track.append(Message("note_off", note=note, velocity=64, time=480))

    mid.save(filename)


# ================= HANDLERS =================
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
    s = user_state.get(chat_id)
    text = (
        "🎧 *Продюсер-панель*\n\n"
        f"🎚 BPM: *{s['bpm']}*\n"
        f"🎹 Тональность: *{s['key']} {s['mode']}*\n"
        f"🎛 Аккорды: *{'ВКЛ' if s['chords'] else 'ВЫКЛ'}*\n\n"
        "✍️ Можешь написать BPM цифрами (например: 140)"
    )
    bot.send_message(chat_id, text, reply_markup=main_keyboard(), parse_mode="Markdown")


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

    with open(filename, "rb") as f:
        bot.send_document(
            message.chat.id,
            f,
            caption=f"🎼 MIDI с BPM {bpm}"
        )


@bot.callback_query_handler(func=lambda c: True)
def callbacks(call):
    chat_id = call.message.chat.id
    state = user_state.setdefault(chat_id, {
        "bpm": 140,
        "key": "C",
        "mode": "Minor",
        "chords": True,
    })

    data = call.data

    if data == "auto_bpm":
        bpm = random.randint(90, 180)
        state["bpm"] = bpm
        filename = f"auto_bpm_{bpm}.mid"
        generate_midi(bpm, filename)

        with open(filename, "rb") as f:
            bot.send_document(
                chat_id,
                f,
                caption=f"🎲 AUTO BPM: {bpm}"
            )

    elif data == "key":
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=key_keyboard())

    elif data.startswith("key_"):
        state["key"] = data.split("_")[1]
        send_status(chat_id)

    elif data.startswith("mode_"):
        state["mode"] = data.split("_")[1]
        send_status(chat_id)

    elif data == "chords":
        state["chords"] = not state["chords"]
        send_status(chat_id)

    elif data == "back":
        send_status(chat_id)

    bot.answer_callback_query(call.id)


print("Bot started (polling)")
bot.infinity_polling(skip_pending=True)

