import asyncio
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from RessoMusic import app
from RessoMusic.misc import SUDOERS, mongodb

# --- DATABASE SETUP ---
# Collection to store allowed admins and group settings
antilink_db = mongodb.antilink
# Cache lists
allowed_admins = []  # Jo admins allow kar diye gaye hain
antilink_chats = []  # Jin groups me antilink ON hai

# --- LOAD DATABASE ---
async def load_antilink_cache():
    # Load settings
    async for doc in antilink_db.find({"chat_id": {"$exists": True}}):
        if doc.get("status") == "on":
            antilink_chats.append(doc["chat_id"])
    
    # Load allowed admins
    async for doc in antilink_db.find({"user_id": {"$exists": True}}):
        allowed_admins.append(doc["user_id"])
    
    print(f"[ANTILINK] Loaded {len(antilink_chats)} chats and {len(allowed_admins)} allowed admins.")

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
        pass
    return False

# --- 1. COMMAND: /antilink on/off ---
@app.on_message(filters.command(["antilink", "antipromo"]) & filters.group)
async def antilink_command(client, message: Message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ **Sirf Admins ye command use kar sakte hain.**")

    if len(message.command) != 2:
        return await message.reply_text("⚠️ **Usage:**\n`/antilink on` - Enable\n`/antilink off` - Disable")

    status = message.command[1].lower()
    chat_id = message.chat.id

    if status == "on":
        if chat_id not in antilink_chats:
            antilink_chats.append(chat_id)
            await antilink_db.update_one({"chat_id": chat_id}, {"$set": {"status": "on"}}, upsert=True)
            await message.reply_text("✅ **Anti-Link & Promo Guard Enabled!**\nAb koi link nahi bhej payega.")
        else:
            await message.reply_text("ℹ️ Pehle se **ON** hai.")

    elif status == "off":
        if chat_id in antilink_chats:
            antilink_chats.remove(chat_id)
            await antilink_db.update_one({"chat_id": chat_id}, {"$set": {"status": "off"}}, upsert=True)
            await message.reply_text("❌ **Anti-Link Guard Disabled.**")
        else:
            await message.reply_text("ℹ️ Pehle se **OFF** hai.")

# --- 2. MAIN LINK WATCHER ---
@app.on_message(filters.group & (filters.text | filters.caption), group=100)
async def antilink_watcher(client, message: Message):
    chat_id = message.chat.id
    
    # 1. Check if Feature is ON
    if chat_id not in antilink_chats:
        return

    if not message.from_user:
        return

    user_id = message.from_user.id
    text = message.text or message.caption
    text = text.lower()

    # 2. Link Detection Logic
    is_link = False
    if "http" in text or "https" in text or "t.me" in text or "www." in text or ".com" in text or "joinchat" in text:
        is_link = True
    
    # Agar Link nahi hai to return
    if not is_link:
        return

    # --- ACTION LOGIC ---

    # A. Agar Sudo User hai to ignore (Owner is always allowed)
    if user_id in SUDOERS:
        return

    # B. Agar Admin hai to Warning do (Delete mat karo)
    if await is_admin(chat_id, user_id):
        # Agar Admin pehle se Allowed list me hai, to ignore karo
        if user_id in allowed_admins:
            return
        
        # Agar allowed nahi hai, to WARNING bhejo
        bot_username = (await app.get_me()).username
        buttons = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Allow Me", callback_data=f"allow_link|{user_id}"),
                InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{bot_username}?startgroup=true")
            ],
            [
                InlineKeyboardButton("🗑️ Close", callback_data="close_data")
            ]
        ])
        
        await message.reply_text(
            f"⚠️ **Admin Link Detected!**\n\n👤 **User:** {message.from_user.mention}\n\n"
            f"Admins ko link bhejne ke liye khud ko **Allow** karna padega.",
            reply_markup=buttons
        )
        return

    # C. Agar Member ya Bot hai to -> DELETE
    # (Admins upar handle ho gaye, ab jo bacha wo member/bot hi hai)
    try:
        await message.delete()
        
        # Optional: Ek choti warning bhejo jo auto delete ho jaye
        msg = await message.reply_text(
            f"🚫 **Link Deleted!**\n👤 {message.from_user.mention}, Links are not allowed here."
        )
        await asyncio.sleep(5)
        await msg.delete()
    except:
        pass


# --- 3. CALLBACKS (Allow Button) ---
@app.on_callback_query(filters.regex("allow_link"))
async def allow_link_callback(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    clicker_id = callback_query.from_user.id
    
    # Data se target user nikaalo
    target_id = int(callback_query.data.split("|")[1])

    # Sirf wahi banda click kar sakta hai jiska link pakda gaya, ya dusra admin
    if clicker_id != target_id:
        if not await is_admin(chat_id, clicker_id):
            return await callback_query.answer("❌ Only Admins can do this.", show_alert=True)

    if target_id not in allowed_admins:
        allowed_admins.append(target_id)
        # Database me save karo taaki restart ke baad bhi yaad rahe
        await antilink_db.insert_one({"user_id": target_id})
        
        await callback_query.answer("✅ You are now Allowed!", show_alert=True)
        await callback_query.message.edit_text(
            f"✅ **Permission Granted!**\n\n👤 {callback_query.from_user.mention} ab links bhej sakte hain."
        )
    else:
        await callback_query.answer("Already Allowed hai bhai.", show_alert=True)
        await callback_query.message.delete()

@app.on_callback_query(filters.regex("close_data"))
async def close_cb(client, callback_query: CallbackQuery):
    try:
        await callback_query.message.delete()
    except:
        pass
  
