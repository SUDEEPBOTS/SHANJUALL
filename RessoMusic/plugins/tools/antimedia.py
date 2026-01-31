import asyncio
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from RessoMusic import app
from RessoMusic.misc import SUDOERS, mongodb
from config import BANNED_USERS

# --- DATABASE SETUP ---
media_db = mongodb.media_whitelist
allowed_cache = []

# --- LOAD CACHE ON STARTUP ---
async def load_allowed_cache():
    global allowed_cache
    async for doc in media_db.find({"user_id": {"$exists": True}}):
        allowed_cache.append(doc["user_id"])
    print(f"[ANTIMEDIA] Loaded {len(allowed_cache)} allowed users.")

loop = asyncio.get_event_loop()
loop.create_task(load_allowed_cache())

# --- HELPER: ADMIN CHECK (For Button Clicking Only) ---
async def is_admin_or_sudo(chat_id, user_id):
    if user_id in SUDOERS: return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return True
    except:
        pass
    return False

# --- COMMAND: /clearall ---
@app.on_message(filters.command(["clearall", "resetmedia"]) & filters.group & ~BANNED_USERS)
async def clear_allow_list(client, message: Message):
    # Command sirf Admin use kar sakta hai
    if not await is_admin_or_sudo(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You are not an Admin.")

    await media_db.delete_many({})
    allowed_cache.clear()
    
    await message.reply_text("✅ **Media Whitelist Cleared!**\n\nAb sabke media messages (Admins included) wapas check honge.")


# --- MAIN LOGIC: MEDIA WATCHER ---
@app.on_message(filters.group & (filters.photo | filters.video | filters.document | filters.audio | filters.animation) & ~BANNED_USERS, group=80)
async def anti_media_watcher(client, message: Message):
    chat_id = message.chat.id
    
    if not message.from_user:
        return

    user_id = message.from_user.id

    # 1. Sirf Sudoers (Bot Owners) Ignore honge.
    # Group Admins ab ignore NAHI honge.
    if user_id in SUDOERS:
        return

    # 2. Whitelisted User Ignore
    # Agar Admin ne button daba kar allow kiya hai, toh ignore karo
    if user_id in allowed_cache:
        return

    # --- WARNING PROCESS START ---
    
    bot_username = (await app.get_me()).username
    user_mention = message.from_user.mention
    
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Allow User (Admin Only)", callback_data=f"allow_media|{user_id}")
        ],
        [
            InlineKeyboardButton("Add Me", url=f"https://t.me/{bot_username}?startgroup=true")
        ]
    ])

    text = (
        f"🚫 **Media Not Allowed**\n"
        f"👤 **User:** {user_mention}\n"
        f"⏳ **Status:** **Deleting in 3 mins...**\n"
        f"ℹ️ **Admin can allow this user below to stop deletion.**"
    )

    # Warning Bhejo
    warn_msg = await message.reply_text(text, reply_markup=buttons)

    # 3. Wait 3 Minutes (180 Seconds)
    await asyncio.sleep(180)

    # 4. RE-CHECK BEFORE DELETE (Important!)
    # Agar 3 minute ke andar kisi ne "Allow" daba diya, toh ab delete mat karo.
    if user_id in allowed_cache:
        try:
            await warn_msg.delete() # Warning hata do kyunki banda allow ho gaya
        except:
            pass
        return # Message delete mat karo

    # 5. Delete Message (Agar abhi bhi allowed nahi hai)
    try:
        await message.delete()
    except:
        pass 

    # 6. Delete Warning
    try:
        await warn_msg.delete()
    except:
        pass


# --- CALLBACK: IGNORE BUTTON ---
@app.on_callback_query(filters.regex("allow_media") & ~BANNED_USERS)
async def allow_user_callback(client, callback_query: CallbackQuery):
    # Button sirf Admin daba sakta hai
    if not await is_admin_or_sudo(callback_query.message.chat.id, callback_query.from_user.id):
        return await callback_query.answer("❌ Sirf Admin allow kar sakta hai!", show_alert=True)

    target_user_id = int(callback_query.data.split("|")[1])

    if target_user_id not in allowed_cache:
        allowed_cache.append(target_user_id)
        await media_db.insert_one({"user_id": target_user_id})
        
        await callback_query.answer("User Allowed!", show_alert=True)
        
        # Message update karo taaki pata chale allow ho gaya
        await callback_query.message.edit_text(
            f"✅ **User Allowed Successfully!**\n\nAb is user ka media delete nahi hoga."
        )
    else:
        await callback_query.answer("User pehle se Allowed hai.", show_alert=True)
        await callback_query.message.delete()
        
