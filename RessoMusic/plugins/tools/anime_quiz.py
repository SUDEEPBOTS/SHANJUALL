import asyncio
import random
import requests
import json
from datetime import datetime
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from RessoMusic import app
from RessoMusic.misc import SUDOERS
from config import BANNED_USERS

# Import Database functions
from RessoMusic.plugins.tools.quiz_db import (
    smcp, add_points, get_leaderboard, reset_leaderboard,
    set_prize, get_prize, add_question, get_random_question,
    get_stored_month, set_stored_month,
    add_api_key, remove_api_key, get_random_api_key,
    is_question_used, mark_question_used
)

# ================= CONFIGURATION =================
MAIN_GROUP_ID = -1003482585012
PROOF_LINK = "https://t.me/Aura_Hunter"
MAIN_GROUP_LINK = "https://t.me/+wHJrM9GWRgtmMzZl"
QUIZ_IMAGE_URL = "https://files.catbox.moe/abaile.png"

# Fix Sudo List
SUDO_LIST = list(SUDOERS)
# =================================================

# --- GLOBAL VARS ---
MSG_COUNTS = {}
QUIZ_STATE = {}
TRIGGER_LIMIT = 70

# --- GROQ AI FUNCTION ---
async def get_ai_question():
    api_key = await get_random_api_key()
    if not api_key:
        return None

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = """
    Generate 1 UNIQUE and RANDOM Anime Trivia Question from diverse genres (Shonen, Seinen, Isekai, Old School).
    Do not ask common questions like 'Who is Naruto's son?'.
    Output strictly valid JSON format:
    {
        "q": "Question Text",
        "o": ["Option1", "Option2", "Option3", "Option4"],
        "a": "Correct Option Text"
    }
    """
    
    data = {
        "messages": [{"role": "user", "content": prompt}],
        "model": "llama-3.3-70b-versatile",
        "response_format": {"type": "json_object"}
    }

    for _ in range(3):
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, lambda: requests.post(url, headers=headers, json=data))
            
            if response.status_code == 200:
                res_json = response.json()
                content = res_json['choices'][0]['message']['content']
                q_data = json.loads(content)
                
                if await is_question_used(q_data['q']):
                    continue 
                
                await mark_question_used(q_data['q'])
                return q_data
        except Exception as e:
            print(f"AI Error: {e}")
            break
            
    return None

# --- REDIRECT HANDLER ---
@app.on_message((filters.private | filters.group) & ~filters.chat(MAIN_GROUP_ID) & ~filters.bot & ~BANNED_USERS)
async def redirect_handler(client, message):
    if not message.text or not message.text.startswith("/"):
        return

    if message.text.split()[0] in ["/quiz", "/leaderboard", "/top", "/rank"]:
        prizes = await get_prize()
        # HTML Formatting
        txt = (
            f"<blockquote>🚫 <b>{smcp('Wrong Place!')}</b>\n\n"
            f"🎮 {smcp('The Quiz Tournament is running only in the Main Group.')}\n\n"
            f"🎁 <b>{smcp('Current Prizes')}:</b>\n{prizes}</blockquote>"
        )
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton(text="🔥 JOIN MAIN GROUP", url=MAIN_GROUP_LINK)]
        ])
        await message.reply(txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)

# --- WATCHER ---
@app.on_message(filters.chat(MAIN_GROUP_ID) & ~filters.bot & ~BANNED_USERS, group=69)
async def quiz_watcher(client, message):
    if not message.text:
        return
        
    chat_id = message.chat.id
    current = MSG_COUNTS.get(chat_id, 0)
    MSG_COUNTS[chat_id] = current + 1

    if MSG_COUNTS[chat_id] >= TRIGGER_LIMIT:
        MSG_COUNTS[chat_id] = 0
        await send_quiz(chat_id)

# --- TEST COMMAND (NEW) ---
@app.on_message(filters.command("test") & filters.user(SUDO_LIST))
async def test_quiz_cmd(client, message):
    await message.reply_text("⚡ **Starting Quiz Test...**")
    await send_quiz(message.chat.id)

# --- AUTO END SYSTEM ---
async def check_season_end():
    while True:
        try:
            now_month = datetime.now().strftime("%Y-%m")
            stored_month = await get_stored_month()

            if stored_month is None:
                await set_stored_month(now_month)
            elif stored_month != now_month:
                await end_season_logic(auto=True)
                await set_stored_month(now_month)
        except Exception as e:
            print(f"Auto-End Error: {e}")
        await asyncio.sleep(3600)

asyncio.create_task(check_season_end())

async def end_season_logic(auto=False):
    top = await get_leaderboard(3)
    if not top:
        return
        
    txt = f"<blockquote>🏁 <b>{smcp('Monthly Season Ended')}!</b> 🏁\n\n"
    for i, user in enumerate(top, 1):
        txt += f"👑 {i}. {user['name']} — {user['points']} {smcp('pts')}\n"
    
    txt += f"\n👉 {smcp('Check Proof Channel for rewards!')}</blockquote>"
    
    btn = InlineKeyboardMarkup([[InlineKeyboardButton(text="🔎 CHECK PROOF", url=PROOF_LINK)]])
    await app.send_message(MAIN_GROUP_ID, txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)
    
    for user in top:
        try:
            await app.send_message(user['user_id'], f"🎉 {smcp('Congratulations!')} You are in the Top 3!\nContact Admin for prizes.")
        except:
            pass
    await reset_leaderboard()
    await app.send_message(MAIN_GROUP_ID, f"<blockquote>🗑 <b>{smcp('Leaderboard Reset. New Season Starts Now!')}</b></blockquote>", parse_mode=enums.ParseMode.HTML)

# --- QUIZ SENDER LOGIC (HTML + PHOTO) ---
async def send_quiz(chat_id):
    if chat_id in QUIZ_STATE and QUIZ_STATE[chat_id]['active']:
        return

    # TRY AI FIRST
    question_data = await get_ai_question()
    
    # IF AI FAILS, USE DATABASE
    if not question_data:
        question_data = await get_random_question()

    if not question_data:
        return

    correct_ans = question_data['a']
    options = question_data['o']
    random.shuffle(options)

    keyboard = []
    for opt in options:
        btn_text = opt if len(opt) < 30 else opt[:27] + "..."
        keyboard.append([InlineKeyboardButton(text=btn_text, callback_data=f"qAns|{opt}")])

    # HTML Formatting with Blockquote
    txt = (
        f"<blockquote>🚨 <b>{smcp('Anime Quiz Event')}</b> 🚨\n\n"
        f"❓ <b>{smcp('Question')}:</b>\n{question_data['q']}\n\n"
        f"💰 <b>{smcp('Prize')}:</b> ₁₀-₂₀ {smcp('Points')}\n"
        f"⏳ <b>{smcp('Time')}:</b> ₃₀ {smcp('Seconds')}</blockquote>"
    )

    # SEND PHOTO WITH BLUR (SPOILER) EFFECT
    msg = await app.send_photo(
        chat_id,
        photo=QUIZ_IMAGE_URL,
        caption=txt,
        has_spoiler=True,
        parse_mode=enums.ParseMode.HTML, # Explicitly use HTML
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    QUIZ_STATE[chat_id] = {
        "active": True,
        "answer": correct_ans,
        "attempts": [],
        "msg_id": msg.id
    }

    await asyncio.sleep(30)
    
    if chat_id in QUIZ_STATE and QUIZ_STATE[chat_id]['active']:
        QUIZ_STATE[chat_id]['active'] = False
        try:
            await msg.edit_caption(
                caption=f"<blockquote>🛑 <b>{smcp('Time Up')}!</b> 🛑\n\n✅ {smcp('Correct Answer')}: <b>{correct_ans}</b></blockquote>",
                parse_mode=enums.ParseMode.HTML,
                reply_markup=None
            )
        except:
            pass

# --- ANSWER HANDLER ---
@app.on_callback_query(filters.regex("qAns"))
async def check_answer(client, query: CallbackQuery):
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    name = query.from_user.first_name
    
    try:
        selected = query.data.split("|")[1]
    except IndexError:
        return await query.answer("Error.", show_alert=True)

    if chat_id not in QUIZ_STATE or not QUIZ_STATE[chat_id]['active']:
        return await query.answer(smcp("Quiz Ended!"), show_alert=True)

    state = QUIZ_STATE[chat_id]

    if user_id in state['attempts']:
        return await query.answer(smcp("You already used your only attempt!"), show_alert=True)

    state['attempts'].append(user_id)

    if selected == state['answer']:
        state['active'] = False
        points = random.randint(10, 20)
        await add_points(user_id, name, points)
        
        txt = (
            f"<blockquote>🎉 <b>{smcp('Winner Announcement')}</b> 🎉\n\n"
            f"👤 <b>{smcp('User')}:</b> {query.from_user.mention}\n"
            f"✅ <b>{smcp('Answer')}:</b> {selected}\n"
            f"📈 <b>{smcp('Points Won')}:</b> +{points}</blockquote>"
        )
        # Edit caption on win
        await query.message.edit_caption(caption=txt, parse_mode=enums.ParseMode.HTML, reply_markup=None)
    else:
        await query.answer(smcp("Wrong Answer! You cannot answer again."), show_alert=True)

# --- PUBLIC COMMANDS ---
@app.on_message(filters.command(["top", "leaderboard", "rank"]) & filters.chat(MAIN_GROUP_ID) & ~BANNED_USERS)
async def show_lb(client, message):
    data = await get_leaderboard()
    prizes = await get_prize()
    
    txt = f"<blockquote>🏆 <b>{smcp('Monthly Leaderboard')}</b> 🏆\n\n"
    if not data:
        txt += f"{smcp('No Data Found.')}"
    else:
        for i, user in enumerate(data, 1):
            txt += f"{i}. {user['name']} ➾ {user['points']} {smcp('pts')}\n"
    
    txt += f"\n🎁 <b>{smcp('Current Prizes')}:</b>\n{prizes}</blockquote>"
    
    btn = InlineKeyboardMarkup([[InlineKeyboardButton(text="🔎 CHECK PROOF", url=PROOF_LINK)]])
    await message.reply(txt, reply_markup=btn, parse_mode=enums.ParseMode.HTML)

# --- GROQ ADMIN COMMANDS ---
@app.on_message(filters.command("gadd") & filters.user(SUDO_LIST))
async def add_groq_key(client, message):
    try:
        key = message.text.split(None, 1)[1].strip()
        success = await add_api_key(key)
        if success:
            await message.reply(f"<blockquote>✅ <b>{smcp('API Key Added')}!</b>\nAI Quiz System is now active.</blockquote>", parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply(f"<blockquote>⚠️ <b>{smcp('Key Already Exists')}!</b></blockquote>", parse_mode=enums.ParseMode.HTML)
    except:
        await message.reply("Usage: `/gadd sk-xxxx...`")

@app.on_message(filters.command("gremove") & filters.user(SUDO_LIST))
async def remove_groq_key(client, message):
    try:
        key = message.text.split(None, 1)[1].strip()
        success = await remove_api_key(key)
        if success:
            await message.reply(f"<blockquote>🗑 <b>{smcp('API Key Removed')}!</b></blockquote>", parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply(f"<blockquote>⚠️ <b>{smcp('Key Not Found')}!</b></blockquote>", parse_mode=enums.ParseMode.HTML)
    except:
        await message.reply("Usage: `/gremove sk-xxxx...`")

# --- OTHER ADMIN COMMANDS ---
@app.on_message(filters.command("addq") & filters.user(SUDO_LIST))
async def add_q_cmd(client, message):
    try:
        text = message.text.split(None, 1)[1]
        parts = [x.strip() for x in text.split("|")]
        if len(parts) != 6:
            return await message.reply("Usage: `/addq Quest | A | B | C | D | CorrectAnswer`")
        q, opts, ans = parts[0], parts[1:5], parts[5]
        if ans not in opts:
            return await message.reply("⚠️ The correct answer is not in the options!")
        await add_question(q, opts, ans)
        await message.reply(f"<blockquote>✅ <b>{smcp('Question Added to DB')}!</b></blockquote>", parse_mode=enums.ParseMode.HTML)
    except:
        await message.reply("Error in format.")

@app.on_message(filters.command("setprize") & filters.user(SUDO_LIST))
async def set_p_cmd(client, message):
    try:
        text = message.text.split(None, 1)[1]
        await set_prize(smcp(text))
        await message.reply(f"<blockquote>✅ <b>{smcp('Prizes Updated')}!</b></blockquote>", parse_mode=enums.ParseMode.HTML)
    except:
        pass

@app.on_message(filters.command("endseason") & filters.user(SUDO_LIST))
async def manual_end_season(client, message):
    await end_season_logic(auto=False)
            
