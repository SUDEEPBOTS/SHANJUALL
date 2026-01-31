from pyrogram import filters, enums
from pyrogram.types import Message
from gpytranslate import Translator
from RessoMusic import app

# Translator Object
trans = Translator()

@app.on_message(filters.command(["tr", "tl", "translate"]) & filters.group)
async def translate_command(client, message: Message):
    # 1. Check if replied
    if not message.reply_to_message:
        return await message.reply_text("⚠️ **Reply to a message to translate it!**\nExample: `/tr en` or `/tr hi`")

    # 2. Get Target Language (Default: English)
    if len(message.command) > 1:
        target_lang = message.command[1]
    else:
        target_lang = "en"

    # 3. Processing Message
    wait_msg = await message.reply_text("🔄 **Translating...**")
    
    try:
        # Text to translate
        text_to_tr = message.reply_to_message.text or message.reply_to_message.caption
        if not text_to_tr:
            return await wait_msg.edit("❌ No text found to translate.")

        # 4. Perform Translation
        translation = await trans(text_to_tr, targetlang=target_lang)
        
        output_text = (
            f"🌍 **Translation ({translation.lang})**\n\n"
            f"<blockquote>{translation.text}</blockquote>"
        )

        await wait_msg.edit(output_text, parse_mode=enums.ParseMode.HTML)

    except Exception as e:
        await wait_msg.edit(f"❌ **Error:** `Invalid Language Code` or API Error.")
