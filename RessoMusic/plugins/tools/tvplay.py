import aiohttp
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from config import BANNED_USERS
from RessoMusic import app
from RessoMusic.utils.stream.stream import stream
from RessoMusic.utils.decorators.language import language, languageCB

# Global list channel data store karne ke liye
HINDI_CHANNELS = []

async def fetch_channels():
    global HINDI_CHANNELS
    if HINDI_CHANNELS:
        return 
    
    url = "https://iptv-org.github.io/iptv/languages/hin.m3u"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                text = await resp.text()
                
        lines = text.strip().split("\n")
        current_name = ""
        
        for line in lines:
            if line.startswith("#EXTINF"):
                current_name = line.split(",")[-1].strip()
            elif line.startswith("http"):
                if current_name:
                    HINDI_CHANNELS.append({"name": current_name, "url": line.strip()})
                    current_name = ""
    except Exception as e:
        print(f"Error fetching TV channels: {e}")

# 10 channels per page dikhane ka function
def get_tv_keyboard(page: int = 0):
    buttons = []
    start_idx = page * 10
    end_idx = start_idx + 10
    current_page_channels = HINDI_CHANNELS[start_idx:end_idx]
    
    for i, chan in enumerate(current_page_channels):
        actual_idx = start_idx + i
        buttons.append([InlineKeyboardButton(text=f"📺 {chan['name'][:30]}", callback_data=f"tvplay_{actual_idx}")])
    
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ ʙᴀᴄᴋ", callback_data=f"tvpage_{page - 1}"))
    if end_idx < len(HINDI_CHANNELS):
        nav_buttons.append(InlineKeyboardButton("ɴᴇxᴛ ➡️", callback_data=f"tvpage_{page + 1}"))
        
    if nav_buttons:
        buttons.append(nav_buttons)
        
    buttons.append([InlineKeyboardButton("❌ ᴄʟᴏsᴇ", callback_data="close_tv_menu")])
    return InlineKeyboardMarkup(buttons)

# 🔥 COMMAND: /livetv ya /tvplay
@app.on_message(filters.command(["tvplay", "livetv"]) & filters.group & ~BANNED_USERS)
@language
async def tv_play_cmd(client, message, _):
    mystic = await message.reply_text("```\n🔄 ʟᴏᴀᴅɪɴɢ ʜᴇʟʟғɪʀᴇᴅᴇᴠs ʟɪᴠᴇ ᴛᴠ...\n```")
    await fetch_channels() 
    
    if not HINDI_CHANNELS:
        return await mystic.edit_text("```\n❌ ғᴀɪʟᴇᴅ ᴛᴏ ʟᴏᴀᴅ ᴄʜᴀɴɴᴇʟs !\n```")
    
    keyboard = get_tv_keyboard(page=0)
    await mystic.edit_text(
        "```\n📡 ʜᴇʟʟғɪʀᴇᴅᴇᴠs ʟɪᴠᴇ ᴛᴠ\n\n📺 sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ sᴛʀᴇᴀᴍ ᴏɴ ᴠᴄ :\n```",
        reply_markup=keyboard
    )

# 🔥 BUTTON CLICK HANDLER
@app.on_callback_query(filters.regex(r"^(tvpage_|tvplay_|close_tv_menu)") & ~BANNED_USERS)
@languageCB
async def tv_callbacks(client, CallbackQuery: CallbackQuery, _):
    data = CallbackQuery.data
    
    if data == "close_tv_menu":
        await CallbackQuery.message.delete()
        
    elif data.startswith("tvpage_"):
        page = int(data.split("_")[1])
        keyboard = get_tv_keyboard(page)
        await CallbackQuery.edit_message_reply_markup(reply_markup=keyboard)
        
    elif data.startswith("tvplay_"):
        idx = int(data.split("_")[1])
        channel = HINDI_CHANNELS[idx]
        channel_name = channel["name"]
        channel_url = channel["url"]
        
        await CallbackQuery.answer(f"sᴛᴀʀᴛɪɴɢ {channel_name}...", show_alert=False)
        mystic = await CallbackQuery.message.edit_text(
            f"```\n📺 ᴘʟᴀʏɪɴɢ ʟɪᴠᴇ ᴛᴠ : {channel_name}\n\n⚡ ʜᴇʟʟғɪʀᴇ ᴇɴɢɪɴᴇ ʟᴏᴀᴅɪɴɢ...\n```"
        )
        
        user_id = CallbackQuery.from_user.id
        user_name = CallbackQuery.from_user.first_name
        chat_id = CallbackQuery.message.chat.id
        
        try:
            await stream(
                _, 
                mystic, 
                user_id, 
                channel_url, 
                chat_id, 
                user_name, 
                chat_id, 
                video=True, 
                streamtype="index" 
            )
        except Exception as e:
            await mystic.edit_text(f"```\n❌ ᴇʀʀᴏʀ : {e}\n```")
          
