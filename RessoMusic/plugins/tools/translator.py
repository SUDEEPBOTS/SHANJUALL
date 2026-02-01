import asyncio
from pyrogram import filters, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from gpytranslate import Translator
from RessoMusic import app
from RessoMusic.misc import SUDOERS
from RessoMusic.utils.database import mongodb

# --- 1. SETUP & DATABASE ---
trans = Translator()
antilink_db = mongodb.antilink
allowed_admins = [] 

# Note: Ab hum "Disabled" chats ko store karenge.
# Agar chat is list mein nahi hai, to wahan AntiLink ON rahega.
disabled_antilink_chats = []

# --- 2. CACHE LOADER ---
async def load_antilink_cache():
    try:
        # Load only those chats where status is explicitly 'off'
        async for doc in antilink_db.find({"chat_id": {"$exists": True}}):
            if doc.get("status") == "off":
                disabled_antilink_chats.append(doc["chat_id"])
        
        async for doc in antilink_db.find({"user_id": {"$exists": True}}):
            allowed_admins.append(doc["user_id"])
        print(f"[ANTILINK] Default ON Mode. Loaded {len(disabled_antilink_chats)} DISABLED chats.")
    except Exception as e:
        print(f"[ANTILINK] DB Error: {e}")

loop = asyncio.get_event_loop()
loop.create_task(load_antilink_cache())

# --- 3. HELPER FUNCTIONS ---
def to_small_caps(text):
    chars = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 
        'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 
        'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
    }
    return "".join(chars.get(c, c) for c in text.lower())

async def is_admin(chat_id, user_id):
    if user_id in SUDOERS: return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return True
    except:
        return False
    return False

# ==========================================
#          PART A: TRANSLATOR CODE
# ==========================================

@app.on_message(filters.command(["tr", "tl", "translate"]) & filters.group)
async def translate_command(client, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("⚠️ **Reply to a message to translate it!**")

    if len(message.command) > 1:
        target_lang = message.command[1]
    else:
        target_lang = "en"

    wait_msg = await message.reply_text("🔄 **Translating...**")
    
    try:
        text_to_tr = message.reply_to_message.text or message.reply_to_message.caption
        if not text_to_tr:
            return await wait_msg.edit("❌ No text found.")

        translation = await trans(text_to_tr, targetlang=target_lang)
        
        output_text = (
            f"🌍 **Translation ({translation.lang})**\n\n"
            f"<blockquote>{translation.text}</blockquote>"
        )
        await wait_msg.edit(output_text, parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        await wait_msg.edit(f"❌ **Error:** Invalid Code or API Error.")

# ==========================================
#          PART B: ANTI-LINK CODE (DEFAULT ON)
# ==========================================

# --- COMMAND: /antilink on/off ---
@app.on_message(filters.command(["antilink", "antipromo", "linklock"], prefixes=["/", "!", "."]) & filters.group)
async def antilink_command(client, message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ **Admins Only.**")

    if len(message.command) != 2:
        return await message.reply_text("⚠️ **Usage:**\n`/antilink on` - Enable (Default)\n`/antilink off` - Disable")

    status = message.command[1].lower()
    chat_id = message.chat.id

    if status == "on":
        if chat_id in disabled_antilink_chats:
            disabled_antilink_chats.remove(chat_id)
            await antilink_db.update_one({"chat_id": chat_id}, {"$set": {"status": "on"}}, upsert=True)
            
            h = to_small_caps("anti-link system")
            m = to_small_caps("enabled successfully")
            await message.reply_text(f"<blockquote>✅ <b>{h}</b>\n{m}</blockquote>", parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text("ℹ️ **Already Enabled (Default).**")

    elif status == "off":
        if chat_id not in disabled_antilink_chats:
            disabled_antilink_chats.append(chat_id)
            await antilink_db.update_one({"chat_id": chat_id}, {"$set": {"status": "off"}}, upsert=True)
            
            h = to_small_caps("anti-link system")
            m = to_small_caps("disabled successfully")
            await message.reply_text(f"<blockquote>❌ <b>{h}</b>\n{m}</blockquote>", parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text("ℹ️ **Already Disabled.**")

# --- WATCHER: Detects Links ---
@app.on_message(filters.group & (filters.text | filters.caption), group=1)
async def antilink_watcher(client, message: Message):
    chat_id = message.chat.id
    
    # LOGIC CHANGE: 
    # Agar chat 'disabled_antilink_chats' list mein hai, tabhi return karo.
    # Warna (matlab list me nahi hai) to CHECK karo (Default ON).
    if chat_id in disabled_antilink_chats:
        return

    if not message.from_user:
        return

    user_id = message.from_user.id
    text = (message.text or message.caption or "").lower()

    if not any(k in text for k in ["http", "https", "t.me", "www.", ".com", "joinchat"]):
        return

    # 1. Ignore Sudo
    if user_id in SUDOERS:
        return

    # 2. Admin Logic
    if await is_admin(chat_id, user_id):
        if user_id in allowed_admins:
            return
        
        bot_u = (await app.get_me()).username
        h = to_small_caps("admin link detected")
        u = to_small_caps("user")
        
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ ᴀʟʟᴏᴡ ᴍᴇ", callback_data=f"allow_link|{user_id}")],
            [InlineKeyboardButton("🗑️ ᴄʟᴏsᴇ", callback_data="close_data")]
        ])
        
        await message.reply_text(
            f"<blockquote>⚠️ <b>{h}</b>\n👤 <b>{u}:</b> {message.from_user.mention}\nℹ️ <i>Admins must click Allow to send links.</i></blockquote>",
            reply_markup=btn,
            parse_mode=enums.ParseMode.HTML
        )
        return

    # 3. Member Logic (Delete)
    try:
        await message.delete()
        h = to_small_caps("link deleted")
        m = await message.reply_text(
            f"<blockquote>🚫 <b>{h}</b>\n👤 {message.from_user.mention}</blockquote>",
            parse_mode=enums.ParseMode.HTML
        )
        await asyncio.sleep(5)
        await m.delete()
    except:
        pass

# --- CALLBACKS ---
@app.on_callback_query(filters.regex("allow_link"))
async def allow_link_cb(client, callback_query: CallbackQuery):
    c_id = callback_query.from_user.id
    t_id = int(callback_query.data.split("|")[1])
    chat_id = callback_query.message.chat.id

    if c_id != t_id and not await is_admin(chat_id, c_id):
        return await callback_query.answer("❌ Admins Only!", show_alert=True)

    if t_id not in allowed_admins:
        allowed_admins.append(t_id)
        await antilink_db.insert_one({"user_id": t_id})
        await callback_query.answer("✅ Allowed!", show_alert=True)
        await callback_query.message.edit_text(f"✅ **Allowed:** {callback_query.from_user.mention}")
    else:
        await callback_query.answer("Already Allowed!", show_alert=True)

@app.on_callback_query(filters.regex("close_data"))
async def close_cb(client, callback_query: CallbackQuery):
    try: await callback_query.message.delete()
    except: pass
        
