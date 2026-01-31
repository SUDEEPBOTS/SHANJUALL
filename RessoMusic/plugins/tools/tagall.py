import asyncio
import random
import re
from pyrogram import filters, enums
from pyrogram.errors import FloodWait
from pyrogram.enums import ChatMembersFilter, ParseMode

from RessoMusic import app
from RessoMusic.misc import SUDOERS

# --- STATE MANAGEMENT ---
SPAM_CHATS = []

# --- EMOJI LIST (AESTHETIC) ---
EMOJI = [
    "🦋🦋🦋🦋🦋",
    "🧚🌸🧋🍬🫖",
    "🥀🌷🌹🌺💐",
    "🌸🌿💮🌱🌵",
    "❤️💚💙💜🖤",
    "💓💕💞💗💖",
    "🌸💐🌺🌹🦋",
    "🍔🦪🍛🍲🥗",
    "🍎🍓🍒🍑🌶️",
    "🧋🥤🧋🥛🍷",
    "🍬🍭🧁🎂🍡",
    "🍨🧉🍺☕🍻",
    "🥪🥧🍦🍥🍚",
    "🫖☕🍹🍷🥛",
    "☕🧃🍩🍦🍙",
    "🍁🌾💮🍂🌿",
    "🌨️🌥️⛈️🌩️🌧️",
    "🌷🏵️🌸🌺💐",
    "💮🌼🌻🍀🍁",
    "🧟🦸🦹🧙👸",
    "🧅🍠🥕🌽🥦",
    "🐷🐹🐭🐨🐻‍❄️",
    "🦋🐇🐀🐈🐈‍⬛",
    "🌼🌳🌲🌴🌵",
    "🥩🍋🍐🍈🍇",
    "🍴🍽️🔪🍶🥃",
    "🕌🏰🏩⛩️🏩",
    "🎉🎊🎈🎂🎀",
    "🪴🌵🌴🌳🌲",
    "🎄🎋🎍🎑🎎",
    "🦅🦜🕊️🦤🦢",
    "🦤🦩🦚🦃🦆",
    "🐬🦭🦈🐋🐳",
    "🐔🐟🐠🐡🦐",
    "🦩🦀🦑🐙🦪",
    "🐦🦂🕷️🕸️🐚",
    "🥪🍰🥧🍨🍨",
    "🥬🍉🧁🧇🔮",
]

# --- HELPER FUNCTIONS ---

def clean_text(text):
    if not text:
        return ""
    return re.sub(r'([_*()~`>#+-=|{}.!])', r'\\1', text)

async def is_admin(chat_id, user_id):
    if user_id in SUDOERS:
        return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
            return True
    except:
        return False
    return False

async def process_members(chat_id, members, text=None, replied=None):
    tagged_members = 0
    usernum = 0
    usertxt = ""
    
    emoji_sequence = random.choice(EMOJI)
    emoji_index = 0
    
    for member in members:
        if chat_id not in SPAM_CHATS:
            break
            
        if member.user.is_deleted or member.user.is_bot:
            continue
            
        tagged_members += 1
        usernum += 1
        
        emoji = emoji_sequence[emoji_index % len(emoji_sequence)]
        emoji_index += 1
        
        usertxt += f"[{emoji}](tg://user?id={member.user.id}) "
        
        if usernum == 5:
            try:
                # Prepare Message Content
                final_text = f"{text}\n{usertxt}" if text else usertxt

                if replied:
                    await replied.reply_text(
                        final_text,
                        disable_web_page_preview=True,
                        parse_mode=ParseMode.MARKDOWN
                    )
                else:
                    await app.send_message(
                        chat_id,
                        final_text,
                        disable_web_page_preview=True,
                        parse_mode=ParseMode.MARKDOWN
                    )
                
                await asyncio.sleep(2)  # Floodwait Protection
                
                usernum = 0
                usertxt = ""
                emoji_sequence = random.choice(EMOJI)
                emoji_index = 0
                
            except FloodWait as e:
                await asyncio.sleep(e.value + 2)
            except Exception as e:
                # Silent Error Pass
                continue
    
    # Send Last Batch
    if usernum > 0 and chat_id in SPAM_CHATS:
        try:
            final_text = f"{text}\n\n{usertxt}" if text else usertxt
            if replied:
                await replied.reply_text(
                    final_text,
                    disable_web_page_preview=True,
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                await app.send_message(
                    chat_id,
                    final_text,
                    disable_web_page_preview=True,
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception:
            pass
    
    return tagged_members

# --- COMMANDS ---

@app.on_message(filters.command(["tagall", "all", "mentionall", "everyone"], prefixes=["/", "@", "!", "."]) & filters.group)
async def tag_all_users(_, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ **Only admins can use this command!**")

    if message.chat.id in SPAM_CHATS:  
        return await message.reply_text("⚠️ **Tagging process is already running.**\nUse `/cancel` to stop it.")  
    
    replied = message.reply_to_message  
    text = None

    # Logic: If no reply and no text -> Error
    if len(message.command) < 2 and not replied:  
        return await message.reply_text("⚠️ **Please provide some text!**\nExample: `/tagall Good Morning`\nOr reply to a message with `/tagall`.")  
    
    if replied:
        if len(message.command) > 1:
            text = clean_text(message.text.split(None, 1)[1])
    else:
        text = clean_text(message.text.split(None, 1)[1])
    
    await message.reply_text("📣 **Tagging Started...**")

    try:  
        # Optimize: Fetch members once
        members = []
        async for m in app.get_chat_members(message.chat.id):
            members.append(m)
        
        total_members = len(members)
        SPAM_CHATS.append(message.chat.id)
        
        tagged_members = await process_members(
            message.chat.id,
            members,
            text=text,
            replied=replied
        )
        
        if message.chat.id in SPAM_CHATS:
            await app.send_message(
                message.chat.id,
                f"✅ **Tagging Completed!**\n\n👥 **Total Members:** {total_members}\n📣 **Tagged:** {tagged_members}"
            )

    except Exception as e:  
        await message.reply_text(f"Error: {e}")  
    finally:  
        if message.chat.id in SPAM_CHATS:
            SPAM_CHATS.remove(message.chat.id)

@app.on_message(filters.command(["admintag", "admins", "report"], prefixes=["/", "@", "!", "."]) & filters.group)
async def tag_all_admins(_, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ **Admins Only!**")

    if message.chat.id in SPAM_CHATS:  
        return await message.reply_text("⚠️ **Tagging process is already running.**")  
    
    replied = message.reply_to_message  
    text = None
    
    if len(message.command) < 2 and not replied:  
        text = "📣 **Admin Report**"
    elif replied:
        if len(message.command) > 1:
            text = clean_text(message.text.split(None, 1)[1])
    else:
        text = clean_text(message.text.split(None, 1)[1])
    
    await message.reply_text("👮 **Tagging Admins...**")

    try:  
        members = []
        async for m in app.get_chat_members(message.chat.id, filter=ChatMembersFilter.ADMINISTRATORS):
            members.append(m)
        
        SPAM_CHATS.append(message.chat.id)
        
        tagged_admins = await process_members(
            message.chat.id,
            members,
            text=text,
            replied=replied
        )
        
        if message.chat.id in SPAM_CHATS:
            await app.send_message(
                message.chat.id,
                f"✅ **Admin Tagging Completed!**\n📣 **Tagged:** {tagged_admins} Admins"
            )

    except Exception as e:
        await message.reply_text(f"Error: {e}")
    finally:
        if message.chat.id in SPAM_CHATS:
            SPAM_CHATS.remove(message.chat.id)

@app.on_message(filters.command(["stop", "cancel", "stopmention", "offmention"], prefixes=["/", "@", "!", "."]) & filters.group)
async def cancelcmd(_, message):
    if not await is_admin(message.chat.id, message.from_user.id):
        return await message.reply_text("❌ **Admins Only!**")

    if message.chat.id in SPAM_CHATS:  
        try:  
            SPAM_CHATS.remove(message.chat.id)  
            await message.reply_text("🛑 **Tagging Process Stopped Successfully!**")  
        except:  
            pass  
    else:  
        await message.reply_text("ℹ️ **No tagging process is currently running.**")

