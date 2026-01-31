import asyncio
from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from RessoMusic import app
from RessoMusic.misc import SUDOERS
from config import BANNED_USERS

# List to store disabled chats (Temporary Memory)
disable_bio_check = []

# --- SMALL CAPS CONVERTER FUNCTION ---
def to_small_caps(text):
    if not text:
        return ""
    chars = {
        'a': 'ᴀ', 'b': 'ʙ', 'c': 'ᴄ', 'd': 'ᴅ', 'e': 'ᴇ', 'f': 'ғ', 'g': 'ɢ', 'h': 'ʜ', 'i': 'ɪ', 'j': 'ᴊ', 
        'k': 'ᴋ', 'l': 'ʟ', 'm': 'ᴍ', 'n': 'ɴ', 'o': 'ᴏ', 'p': 'ᴘ', 'q': 'ǫ', 'r': 'ʀ', 's': 's', 't': 'ᴛ', 
        'u': 'ᴜ', 'v': 'ᴠ', 'w': 'ᴡ', 'x': 'x', 'y': 'ʏ', 'z': 'ᴢ',
        '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄', '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
        'A': 'ᴀ', 'B': 'ʙ', 'C': 'ᴄ', 'D': 'ᴅ', 'E': 'ᴇ', 'F': 'ғ', 'G': 'ɢ', 'H': 'ʜ', 'I': 'ɪ', 'J': 'ᴊ', 
        'K': 'ᴋ', 'L': 'ʟ', 'M': 'ᴍ', 'N': 'ɴ', 'O': 'ᴏ', 'P': 'ᴘ', 'Q': 'ǫ', 'R': 'ʀ', 'S': 's', 'T': 'ᴛ', 
        'U': 'ᴜ', 'V': 'ᴠ', 'W': 'ᴡ', 'X': 'x', 'Y': 'ʏ', 'Z': 'ᴢ'
    }
    return "".join(chars.get(c, c) for c in text)

# --- HELPER: CHECK IF USER IS ADMIN/SUDO ---
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

# --- FEATURE 0: COMMANDS TO ON/OFF BIO CHECK ---
@app.on_message(filters.command(["bio"]) & filters.group & ~BANNED_USERS)
async def bio_command_handler(client, message: Message):
    # Check if user is Admin
    if not await is_admin_or_sudo(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ You are not an Admin.")

    if len(message.command) != 2:
        return await message.reply_text("⚠️ Usage:\n`/bio on` - Enable Bio Check\n`/bio off` - Disable Bio Check")

    state = message.command[1].lower()
    chat_id = message.chat.id

    if state == "off":
        if chat_id not in disable_bio_check:
            disable_bio_check.append(chat_id)
            await message.reply_text(f">✅ {to_small_caps('Bio Check Disabled')}")
        else:
            await message.reply_text("ℹ️ Bio Check is already OFF.")
    
    elif state == "on":
        if chat_id in disable_bio_check:
            disable_bio_check.remove(chat_id)
            await message.reply_text(f">✅ {to_small_caps('Bio Check Enabled')}")
        else:
            await message.reply_text("ℹ️ Bio Check is already ON.")
    
    else:
        await message.reply_text("⚠️ Invalid Command. Use `on` or `off`.")


# --- FEATURE 1: EDIT MESSAGE MONITOR ---
@app.on_edited_message(filters.group & ~BANNED_USERS)
async def edit_watcher(client, message: Message):
    if not message.from_user:
        return

    # Check Admin/Sudo (Ignore them)
    if await is_admin_or_sudo(message.chat.id, message.from_user.id):
        return

    # Name & Username Fetching
    fname = message.from_user.first_name
    username = message.from_user.username
    
    display_name = fname
    if username:
        display_name = f"{fname} (@{username})"
    
    sc_user = to_small_caps(display_name)

    # Formatting (Stars Removed)
    header = to_small_caps("Editing Not Allowed")
    lbl_user = to_small_caps("User")
    lbl_status = to_small_caps("Status")
    lbl_msg = to_small_caps("Deleting in 3 mins...")
    
    text = (
        f">⚠️ {header}\n"
        f">👤 {lbl_user}: {sc_user}\n"
        f">⏳ {lbl_status}: {lbl_msg}"
    )
    
    # Send Warning
    warning_msg = await message.reply_text(text)
    
    # Wait 3 Mins
    await asyncio.sleep(180)
    
    # Delete Both
    try:
        await message.delete()
    except:
        pass 
    try:
        await warning_msg.delete()
    except:
        pass


# --- FEATURE 2: BIO LINK CHECKER ---
@app.on_message(filters.group & ~BANNED_USERS, group=69)
async def bio_link_checker(client, message: Message):
    chat_id = message.chat.id
    
    # Check if disabled via command/button
    if chat_id in disable_bio_check:
        return

    if not message.from_user:
        return

    # Check Admin/Sudo
    if await is_admin_or_sudo(chat_id, message.from_user.id):
        return

    try:
        # Check Bio
        full_user = await client.get_chat(message.from_user.id)
        bio = full_user.bio
        
        if bio and ("http" in bio or "t.me" in bio or ".com" in bio or "www." in bio):
            
            # Delete User Message Immediately
            try:
                await message.delete()
            except:
                pass

            buttons = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("🔕 ᴛᴜʀɴ ᴏғғ", callback_data=f"bio_check_off|{chat_id}"),
                    InlineKeyboardButton("🗑️ ɪɢɴᴏʀᴇ", callback_data="close_data")
                ]
            ])

            # Name & Username Fetching
            fname = message.from_user.first_name
            username = message.from_user.username
            
            display_name = fname
            if username:
                display_name = f"{fname} (@{username})"
            
            sc_user = to_small_caps(display_name)

            # Formatting (Stars Removed)
            header = to_small_caps("Anti-Promotion")
            lbl_user = to_small_caps("User")
            lbl_reason = to_small_caps("Reason")
            reason_msg = to_small_caps("Link in Bio detected.")
            lbl_action = to_small_caps("Remove link to chat here.")

            text = (
                f">🚫 {header}\n"
                f">👤 {lbl_user}: {sc_user}\n"
                f">⚠️ {lbl_reason}: {reason_msg}\n"
                f">❗ {lbl_action}"
            )

            await message.reply_text(text, reply_markup=buttons)
    except Exception as e:
        pass


# --- BUTTON CALLBACKS ---
@app.on_callback_query(filters.regex("bio_check_off") & ~BANNED_USERS)
async def bio_off_callback(client, callback_query: CallbackQuery):
    # Check Admin for Button
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    is_admin = await is_admin_or_sudo(chat_id, user_id)

    if not is_admin:
        return await callback_query.answer("❌ You are not an Admin!", show_alert=True)

    chat_id_val = int(callback_query.data.split("|")[1])
    
    if chat_id_val not in disable_bio_check:
        disable_bio_check.append(chat_id_val)
        msg_text = to_small_caps("Bio Check Disabled")
        await callback_query.answer("Disabled!", show_alert=True)
        await callback_query.message.edit_text(f">✅ {msg_text}")
    else:
        await callback_query.answer("Already Disabled!", show_alert=True)

@app.on_callback_query(filters.regex("close_data"))
async def close_callback(client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    chat_id = callback_query.message.chat.id
    is_admin = await is_admin_or_sudo(chat_id, user_id)
    
    if not is_admin:
        return await callback_query.answer("❌ You are not an Admin!", show_alert=True)
        
    await callback_query.message.delete()
    
