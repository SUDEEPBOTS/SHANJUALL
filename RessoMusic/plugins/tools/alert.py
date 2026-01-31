from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from RessoMusic import app
from RessoMusic.misc import SUDOERS
from config import BANNED_USERS

# List to temporarily disable alerts in specific chats
disable_alerts = []

# --- HELPER: ADMIN CHECK ---
async def is_admin_or_sudo(chat_id, user_id):
    if user_id in SUDOERS:
        return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return True
    except:
        pass
    return False

# --- ALERT SYSTEM ---
# Hum Group=10 use kar rahe hain taaki ye original commands ke saath run ho
@app.on_message(filters.command(["info", "profile", "filter", "whois"]) & filters.group & ~BANNED_USERS, group=10)
async def command_alert_watcher(client, message: Message):
    if not message.from_user:
        return
    
    chat_id = message.chat.id

    # 0. Check if alerts are disabled for this chat
    if chat_id in disable_alerts:
        return

    # 1. If Admin/Sudo uses command -> STAY SILENT
    if await is_admin_or_sudo(chat_id, message.from_user.id):
        return

    # 2. If Normal User -> SEND ALERT
    user_mention = message.from_user.mention
    command_used = message.text.split()[0] # e.g. /info, /filter

    # Customize message based on command
    action_text = ""
    if "filter" in command_used:
        action_text = "⚠️ **This user is trying to set/change Filters!**"
    elif "info" in command_used or "profile" in command_used or "whois" in command_used:
        action_text = "🕵️ **This user is checking Profile/Info!**"
    else:
        action_text = f"⚠️ **Used the command:** `{command_used}`"

    # Button Setup
    bot_username = (await app.get_me()).username
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔕 Temp Off", callback_data=f"alert_off|{chat_id}"),
            InlineKeyboardButton("➕ Add Me", url=f"https://t.me/{bot_username}?startgroup=true")
        ]
    ])

    # 3. Send Alert Message
    await message.reply_text(
        f"🚨 **ADMIN ALERT!** 🚨\n\n"
        f"👤 **User:** {user_mention}\n"
        f"{action_text}\n\n"
        f"👀 **Admins, please check this!** @admins",
        reply_markup=buttons
    )

# --- CALLBACK: TURN OFF ALERT ---
@app.on_callback_query(filters.regex("alert_off") & ~BANNED_USERS)
async def alert_off_callback(client, callback_query: CallbackQuery):
    # Check if user is Admin
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    
    if not await is_admin_or_sudo(chat_id, user_id):
        return await callback_query.answer("❌ Only Admins can do this!", show_alert=True)

    target_chat_id = int(callback_query.data.split("|")[1])
    
    if target_chat_id not in disable_alerts:
        disable_alerts.append(target_chat_id)
        await callback_query.answer("Alerts Disabled Temporarily!", show_alert=True)
        await callback_query.message.edit_text("✅ **Admin Alerts have been Disabled for this session.**")
    else:
        await callback_query.answer("Already Disabled!", show_alert=True)
      
