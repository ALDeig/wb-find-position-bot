from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb_for_find_result(query_id: str, user_id: int, subscribe_id: str = None):
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(text="\U0001F504 Обновить", callback_data=f"up:{query_id}:{user_id}"),
    )
    if subscribe_id:
        kb.add(InlineKeyboardButton(
            text="\U0001F515 Отписаться",
            callback_data=f"unsub:{subscribe_id}"
        ))
    else:
        kb.add(InlineKeyboardButton(
            text="\U0001F514 Отслеживать позиции",
            callback_data=f"sub:{query_id}:{user_id}"
        ))
    return kb


def kb_unsubscribe(subscribe_id: str):
    kb = InlineKeyboardMarkup(row_width=1).add(
        InlineKeyboardButton(text="\U0001F515 Отписаться", callback_data=f"delsub:{subscribe_id}")
    )
    return kb

