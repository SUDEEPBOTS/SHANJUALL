import aiohttp
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, Message, InlineKeyboardButton, CallbackQuery

from RessoMusic import app
from RessoMusic.utils.database import get_playmode, get_playtype, is_nonadmin_chat
from RessoMusic.utils.decorators import language, languageCB
from RessoMusic.utils.inline.settings import playmode_users_markup
from RessoMusic.utils.stream.stream import stream
from config import BANNED_USERS

# ==========================================
# 🎵 ORIGINAL PLAYMODE CODE
# ==========================================
@app.on_message(filters.command(["playmode", "mode"]) & filters.group & ~BANNED_USERS)
@language
async def playmode_(client, message: Message, _):
    playmode = await get_playmode(message.chat.id)
    if playmode == "Direct":
        Direct = True
    else:
        Direct = None
    is_non_admin = await is_nonadmin_chat(message.chat.id)
    if not is_non_admin:
        Group = True
    else:
        Group = None
    playty = await get_playtype(message.chat.id)
    if playty == "Everyone":
        Playtype = None
    else:
        Playtype = True
    buttons = playmode_users_markup(_, Direct, Group, Playtype)
    response = await message.reply_text(
        _["play_22"].format(message.chat.title),
        reply_markup=InlineKeyboardMarkup(buttons),
    )

# ==========================================
# 📺 HELLFIREDEVS LIVE TV (UPDATED WITH FIXES)
# ==========================================
HINDI_CHANNELS = []

async def fetch_channels():
    global HINDI_CHANNELS
    if HINDI_CHANNELS:
        return "SUCCESS"
    
    url = "[https://iptv-org.github.io/iptv/languages/hin.m3u](https://iptv-org.github.io/iptv/languages/hin.m3u)"
    # 🔥 Website ko lagna chahiye ki Chrome browser se aayi hai request
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status != 200:
                    return f"HTTP ᴇʀʀᴏʀ {resp.status}"
                text = await resp.text()
                
        lines = text.strip().split("\n")
        current_name = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith("#EXTINF"):
                current_name = line.split(",")[-1].strip()
            elif line.startswith("http"):
                if current_name:
                    HINDI_CHANNELS.append({"name": current_name, "url": line})
                    current_name = ""
                    
        if not HINDI_CHANNELS:
            return "ʟɪsᴛ ɪs ᴇᴍᴘᴛʏ ᴏʀ ғᴏʀᴍᴀᴛ ᴄʜᴀɴɢᴇᴅ"
        return "SUCCESS"
        
    except Exception as e:
        return str(e)

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

@app.on_message(filters.command(["tvplay", "livetv"]) & filters.group & ~BANNED_USERS)
@language
async def tv_play_cmd(client, message, _):
    mystic = await message.reply_text("🔄 ʟᴏᴀᴅɪɴɢ ʜᴇʟʟғɪʀᴇᴅᴇᴠs ʟɪᴠᴇ ᴛᴠ...")
    
    status = await fetch_channels() 
    
    if not HINDI_CHANNELS:
        # 🔥 Ab actual error Telegram pe dikhega
        return await mystic.edit_text(f"❌ ғᴀɪʟᴇᴅ ᴛᴏ ʟᴏᴀᴅ ᴄʜᴀɴɴᴇʟs !\n⚠️ ʀᴇᴀsᴏɴ : {status[:50]}")
    
    keyboard = get_tv_keyboard(page=0)
    await mystic.edit_text(
        "📡 ʜᴇʟʟғɪʀᴇᴅᴇᴠs ʟɪᴠᴇ ᴛᴠ\n\n📺 sᴇʟᴇᴄᴛ ᴀ ᴄʜᴀɴɴᴇʟ ᴛᴏ sᴛʀᴇᴀᴍ ᴏɴ ᴠᴄ :",
        reply_markup=keyboard
    )

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
            f"📺 ᴘʟᴀʏɪɴɢ ʟɪᴠᴇ ᴛᴠ : {channel_name}\n\n⚡ ʜᴇʟʟғɪʀᴇ ᴇɴɢɪɴᴇ ʟᴏᴀᴅɪɴɢ..."
        )
        
        user_id = CallbackQuery.from_user.id
        user_
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
            await mystic.edit_text(f"❌ ᴇʀʀᴏʀ : {e}")
        l8kk88
