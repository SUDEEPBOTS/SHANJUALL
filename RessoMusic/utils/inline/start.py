from pyrogram.types import InlineKeyboardButton

import config
from RessoMusic import app


def start_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"], url=f"https://t.me/{app.username}?startgroup=true"
            ),
            InlineKeyboardButton(text=_["S_B_2"], url=config.SUPPORT_GROUP),
        ],
    ]
    return buttons


def private_panel(_):
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                url=f"https://t.me/{app.username}?startgroup=true",
            )
        ],
        [
            InlineKeyboardButton(text=_["S_B_4"], callback_data="settings_back_helper"),
            InlineKeyboardButton(text=_["S_B_2"], url=config.SUPPORT_GROUP),
            InlineKeyboardButton("˹ϻʏ ʜᴏϻє˼", url="https://t.me/+JSJvtrVjf780YTQ9"),
        ],
        [
            InlineKeyboardButton("˹ᴀɴɪʏᴀ ᴛᴜɴᴇs˼♪", url="https://yukiapp-steel.vercel.app/"),
        ],
        [
            InlineKeyboardButton("˹ ϻʏ ϻᴧsᴛєʀ ˼", url="http://T.me/II_Mikey"),
            # InlineKeyboardButton(text=_["S_B_7"], url=config.UPSTREAM_REPO),
        ],
    ]
    return buttons

