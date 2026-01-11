import telebot
from telebot import types
from midiutil import MIDIFile
import random
import os

import os
TOKEN = os.getenv("TOKEN")

bot = telebot.TeleBot(TOKEN)

user_state = {}

# ========= THEORY =========
SCALES = {
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "major": [0, 2, 4, 5, 7, 9, 11]
}

KEYS = {
    "C": 48, "C#": 49, "D": 50, "D#": 51,
    "E": 52, "F": 53, "F#": 54, "G": 55,
    "G#": 56, "A": 57, "A#": 58, "B": 59
}

CHORDS = {
    "minor": [[0,3,7],[0,5,7],[0,3,10]],
    "major": [[0,4,7],[0,5,7],[0,4,11]]
}

# ========= GENRES =========
GENRES = {
    "🔥 Trap": (90, 220),
    "🩸 Detroit": (175, 220),
    "🥶 West Coast": (85, 105),
    "🕺 Club": (95, 115),
}

# ========= KEYBOARDS =========
def genre_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("🔥 Trap", "🩸 Detroit")
    kb.row("🥶 West Coast", "🕺 Club")
    return kb

def settings_kb(s):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row(f"🎼 Chords: {'ON' if s['chords'] else 'OFF'}")
    kb.row(f"🎚 BPM: {s['bpm_mode']}")
    kb.row(f"🎹 Key: {s['key']} {s['scale']}")
    kb.row("🎵 GENERATE MIDI")
    kb.row("🔙 Back")
    return kb

def key_kb():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i in range(0,12,2):
        kb.row(list(KEYS)[i], list(KEYS)[i+1])
    kb.row("🔁 Scale")
    kb.row("🔙 Back")
    return kb

# ========= MIDI =========
def generate_midi(s):
    gmin, gmax = GENRES[s["genre"]]

    if s["bpm_mode"] == "LOW":
        bpm = gmin
    elif s["bpm_mode"] == "HIGH":
        bpm = gmax
    else:
        bpm = random.randint(gmin, gmax)

    root = KEYS[s["key"]]
    scale = SCALES[s["scale"]]

    midi = MIDIFile(2)
    midi.addTempo(0, 0, bpm)
    midi.addTempo(1, 0, bpm)

    t = 0
    if s["chords"]:
        for _ in range(4):
            chord = random.choice(CHORDS[s["scale"]])
            for n in chord:
                midi.addNote(0, 0, root+n, t, 2, 70)
            t += 2

    t = 0
    for _ in range(16):
        note = root + random.choice(scale)
        midi.addNote(1, 1, note, t, 0.5, 100)
        t += 0.5

    os.makedirs("generated", exist_ok=True)
    path = f"generated/{s['genre'].replace(' ','_')}_{bpm}.mid"
    with open(path, "wb") as f:
        midi.writeFile(f)

    return path, bpm

# ========= HANDLERS =========
@bot.message_handler(commands=["start"])
def start(m):
    bot.send_message(m.chat.id, "🎧 Choose genre", reply_markup=genre_kb())

@bot.message_handler(func=lambda m: m.text in GENRES)
def choose_genre(m):
    user_state[m.chat.id] = {
        "genre": m.text,
        "bpm_mode": "AUTO",
        "key": "C",
        "scale": "minor",
        "chords": True
    }
    bot.send_message(m.chat.id, "⚙ Settings", reply_markup=settings_kb(user_state[m.chat.id]))

@bot.message_handler(func=lambda m: m.text.startswith("🎼 Chords"))
def toggle_chords(m):
    s = user_state[m.chat.id]
    s["chords"] = not s["chords"]
    bot.send_message(m.chat.id, "Updated", reply_markup=settings_kb(s))

@bot.message_handler(func=lambda m: m.text.startswith("🎚 BPM"))
def toggle_bpm(m):
    s = user_state[m.chat.id]
    modes = ["AUTO","LOW","HIGH"]
    s["bpm_mode"] = modes[(modes.index(s["bpm_mode"])+1)%3]
    bot.send_message(m.chat.id, "Updated", reply_markup=settings_kb(s))

@bot.message_handler(func=lambda m: m.text.startswith("🎹 Key"))
def choose_key(m):
    bot.send_message(m.chat.id, "Choose key", reply_markup=key_kb())

@bot.message_handler(func=lambda m: m.text in KEYS)
def set_key(m):
    s = user_state[m.chat.id]
    s["key"] = m.text
    bot.send_message(m.chat.id, "Updated", reply_markup=settings_kb(s))

@bot.message_handler(func=lambda m: m.text == "🔁 Scale")
def toggle_scale(m):
    s = user_state[m.chat.id]
    s["scale"] = "major" if s["scale"]=="minor" else "minor"
    bot.send_message(m.chat.id, "Updated", reply_markup=settings_kb(s))

@bot.message_handler(func=lambda m: m.text == "🎵 GENERATE MIDI")
def send_midi(m):
    path, bpm = generate_midi(user_state[m.chat.id])
    with open(path,"rb") as f:
        bot.send_document(m.chat.id, f, caption=f"BPM: {bpm}")

@bot.message_handler(func=lambda m: m.text == "🔙 Back")
def back(m):
    bot.send_message(m.chat.id, "🎧 Choose genre", reply_markup=genre_kb())

# ========= RUN =========
bot.infinity_polling()
