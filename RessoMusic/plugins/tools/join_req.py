from pyrogram import filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, ChatJoinRequest
from RessoMusic import app
from RessoMusic.misc import SUDOERS

# --- HELPER: ADMIN CHECK ---
async def is_admin(chat_id, user_id):
    if user_id in SUDOERS: return True
    try:
        member = await app.get_chat_member(chat_id, user_id)
        if member.status in ["creator", "administrator"]:
            return True
    except:
        pass
    return False

# --- 1. NEW JOIN REQUEST HANDLER ---
@app.on_chat_join_request()
async def join_req_handler(client, request: ChatJoinRequest):
    chat = request.chat
    user = request.from_user
    
    # User Info
    user_name = user.first_name
    user_id = user.id
    chat_id = chat.id

    # HTML Link Construction (Kyunki hum HTML mode use karenge)
    user_link = f"<a href='tg://user?id={user_id}'>{user_name}</a>"

    # Buttons
    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"j_app|{user_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"j_rej|{user_id}")
        ],
        [
            InlineKeyboardButton("🗑️ Close", callback_data="close_data")
        ]
    ])

    # HTML Blockquote Styling
    text = (
        f"🔔 <b>New Join Request</b>\n\n"
        f"<blockquote>👤 <b>User:</b> {user_link}\n"
        f"🆔 <b>ID:</b> <code>{user_id}</code></blockquote>\n\n"
        f"👇 <i>Admins can Approve or Reject below.</i>"
    )

    # Message bhejo Group mein (Parse Mode HTML zaroori hai)
    await client.send_message(
        chat_id,
        text=text,
        reply_markup=buttons,
        parse_mode=enums.ParseMode.HTML
    )

# --- 2. CALLBACKS (Approve/Reject) ---
@app.on_callback_query(filters.regex("^(j_app|j_rej)"))
async def join_req_callbacks(client, callback_query: CallbackQuery):
    chat_id = callback_query.message.chat.id
    admin_id = callback_query.from_user.id
    
    # 1. Admin Check
    if not await is_admin(chat_id, admin_id):
        return await callback_query.answer("❌ You are not an Admin!", show_alert=True)

    data = callback_query.data.split("|")
    action = data[0]
    target_user_id = int(data[1])
    
    admin_name = callback_query.from_user.mention

    try:
        # 2. Approve Action
        if action == "j_app":
            await client.approve_chat_join_request(chat_id, target_user_id)
            await callback_query.message.edit_text(
                f"✅ <b>Request Approved</b>\n\n"
                f"👤 <b>User:</b> <a href='tg://user?id={target_user_id}'>User</a>\n"
                f"👮 <b>By Admin:</b> {admin_name}",
                parse_mode=enums.ParseMode.HTML
            )
        
        # 3. Reject Action
        elif action == "j_rej":
            await client.decline_chat_join_request(chat_id, target_user_id)
            await callback_query.message.edit_text(
                f"❌ <b>Request Rejected</b>\n\n"
                f"👤 <b>User:</b> <a href='tg://user?id={target_user_id}'>User</a>\n"
                f"👮 <b>By Admin:</b> {admin_name}",
                parse_mode=enums.ParseMode.HTML
            )

    except Exception as e:
        await callback_query.answer(f"⚠️ Error: User shayad pehle hi join ho gaya ya revoke kar diya.", show_alert=True)
        await callback_query.message.delete()

# --- 3. CLOSE BUTTON ---
@app.on_callback_query(filters.regex("close_data"))
async def close_callback(client, callback_query: CallbackQuery):
    if not await is_admin(callback_query.message.chat.id, callback_query.from_user.id):
        return await callback_query.answer("❌ Admins Only!", show_alert=True)
    await callback_query.message.delete()

