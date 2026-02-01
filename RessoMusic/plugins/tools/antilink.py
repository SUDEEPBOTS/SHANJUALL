import asyncio
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from RessoMusic import app
from RessoMusic.misc import SUDOERS, mongodb

# --- DATABASE SETUP ---
antilink_db = mongodb.antilink
# Cache lists
allowed_admins = []  # Globally allowed admins
antilink_chats = []  # Chats where antilink is ON

# --- SMALL CAPS HELPER ---
def to_small_caps(text):
    chars = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 
        'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 
        'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉'
    }
    return "".join(chars.get(c, c) for c in text.lower())

# --- LOAD DATABASE ---
async def load_antilink_cache():
    try:
        async for doc in antilink_db.find({"chat_id": {"$exists": True}}):
            if doc.get("status") == "on":
                antilink_chats.append(doc["chat_id"])
        
        async for doc in antilink_db.find({"user_id": {"$exists": True}}):
            allowed_admins.append(doc["user_id"])
        
        print(f"[ANTILINK] Loaded {len(antilink_chats)} chats and {len(allowed_admins)} allowed admins.")
    except Exception as e:
        print(f"[ANTILINK] Database Error: {e}")

loop = asyncio.get_event_loop()
loop.create_task(load_antilink_cache())

# --- HELPER: ADMIN CHECK ---
async def is_admin(chat_id, user_id):
    if user_id in SUDOERS: return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return True
    except:
        return False
    return False

# --- 1. COMMAND: /antilink on/off ---
@app.on_message(filters.command(["antilink", "antipromo"]) & filters.group)
async def antilink_command(client, message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ **Admins Only.**")

    if len(message.command) != 2:
        return await message.reply_text("⚠️ **Usage:**\n`/antilink on` - Enable\n`/antilink off` - Disable")

    status = message.command[1].lower()
    chat_id = message.chat.id

    if status == "on":
        if chat_id not in antilink_chats:
            antilink_chats.append(chat_id)
            await antilink_db.update_one({"chat_id": chat_id}, {"$set": {"status": "on"}}, upsert=True)
            
            header = to_small_caps("anti-link system")
            msg = to_small_caps("enabled successfully")
            await message.reply_text(f"<blockquote>✅ <b>{header}</b>\n{msg}</blockquote>", parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text("ℹ️ **Already Enabled.**")

    elif status == "off":
        if chat_id in antilink_chats:
            antilink_chats.remove(chat_id)
            await antilink_db.update_one({"chat_id": chat_id}, {"$set": {"status": "off"}}, upsert=True)
            
            header = to_small_caps("anti-link system")
            msg = to_small_caps("disabled successfully")
            await message.reply_text(f"<blockquote>❌ <b>{header}</b>\n{msg}</blockquote>", parse_mode=enums.ParseMode.HTML)
        else:
            await message.reply_text("ℹ️ **Already Disabled.**")

# --- 2. MAIN LINK WATCHER ---
# Priority Group 1 (High Priority)
@app.on_message(filters.group & (filters.text | filters.caption), group=1)
async def antilink_watcher(client, message: Message):
    chat_id = message.chat.id
    
    # Check if this group has enabled anti-link
    if chat_id not in antilink_chats:
        return

    if not message.from_user:
        return

    user_id = message.from_user.id
    text = message.text or message.caption
    if not text:
        return
    
    text = text.lower()

    # Link Detection Logic
    is_link = False
    if any(keyword in text for keyword in ["http", "https", "t.me", "www.", ".com", "joinchat"]):
        is_link = True
    
    if not is_link:
        return

    # Debug Log (Logs me dikhega ki link pakda gaya ya nahi)
    print(f"[ANTILINK] Link detected in {chat_id} by {user_id}")

    # --- ACTION LOGIC ---

    # A. Ignore Sudo Users (Owners)
    if user_id in SUDOERS:
        print(f"[ANTILINK] Ignored Sudo User: {user_id}")
        return

    # B. Check Admin Status
    if await is_admin(chat_id, user_id):
        # Allow if whitelist
        if user_id in allowed_admins:
            return
        
        # Warning for Admins
        bot_username = (await app.get_me()).username
        
        lbl_head = to_small_caps("admin link detected")
        lbl_user = to_small_caps("user")
        lbl_info = to_small_caps("admins must allow themselves to send links")
        
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ ᴀʟʟᴏᴡ ᴍᴇ", callback_data=f"allow_link|{user_id}"),
                InlineKeyboardButton("➕ ᴀᴅᴅ ᴍᴇ", url=f"https://t.me/{bot_username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("🗑️ ᴄʟᴏsᴇ", callback_data="close_data")
            ]
        ])
        
        text_msg = (
            f"<blockquote>⚠️ <b>{lbl_head}</b>\n"
            f"👤 <b>{lbl_user}:</b> {message.from_user.mention}\n"
            f"ℹ️ {lbl_info}</blockquote>"
        )
        
        await message.reply_text(text_msg, reply_markup=buttons, parse_mode=enums.ParseMode.HTML)
        return

    # C. Delete for Members/Bots
    try:
        await message.delete()
        
        lbl_del = to_small_caps("link deleted")
        lbl_warn = to_small_caps("links are not allowed")
        
        msg = await message.reply_text(
            f"<blockquote>🚫 <b>{lbl_del}</b>\n"
            f"👤 {message.from_user.mention}, {lbl_warn}</blockquote>",
            parse_mode=enums.ParseMode.HTML
        )
        await asyncio.sleep(5)
        await msg.delete()
    except Exception as e:
        # Permission Check Failure
        print(f"[Antilink Error] Could not delete message: {e}")


# --- 3. CALLBACKS (Allow Button) ---
@app.on_callback_query(filters.regex("allow_link"))
async def allow_link_callback(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    clicker_id = callback_query.from_user.id
    target_id = int(callback_query.data.split("|")[1])

    # Only the user who sent the link or another admin can click
    if clicker_id != target_id:
        if not await is_admin(chat_id, clicker_id):
            return await callback_query.answer("❌ Admins Only!", show_alert=True)

    if target_id not in allowed_admins:
        allowed_admins.append(target_id)
        await antilink_db.insert_one({"user_id": target_id})
        
        lbl_head = to_small_caps("permission granted")
        lbl_msg = to_small_caps("can now send links")
        
        await callback_query.answer("✅ Allowed!", show_alert=True)
        await callback_query.message.edit_text(
            f"<blockquote>✅ <b>{lbl_head}</b>\n"
            f"👤 {callback_query.from_user.mention} {lbl_msg}</blockquote>",
            parse_mode=enums.ParseMode.HTML
        )
    else:
        await callback_query.answer("Already Allowed!", show_alert=True)
        await callback_query.message.delete()

@app.on_callback_query(filters.regex("close_data"))
async def close_cb(client, callback_query: CallbackQuery):
    try:
        await callback_query.message.delete()
    except:
        pass
        
