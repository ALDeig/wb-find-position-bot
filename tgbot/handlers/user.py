import uuid
import logging
from datetime import datetime

from aiogram import Dispatcher
from aiogram.types import Message, CallbackQuery
from aiogram.dispatcher.storage import FSMContext

from tgbot.keyboards import kb_user
from tgbot.services import db
from tgbot.services import errors
from tgbot.services import parser


async def user_start(msg: Message, state: FSMContext):
    await state.finish()
    text = db.fetchone("messages", "message", {"name": "start"})
    db.insert_user(str(msg.from_user.id))
    await msg.answer(text["message"] if text else "Сообщение на команду старт")


async def get_search_query(msg: Message):
    parsed_message = parser.parse_message(msg.text)
    if not parsed_message:
        await msg.answer("Неверный запрос")
        return
    await msg.answer("\U0001F50E Запрос создан! В ближайшее время вам будет отправлен результат")
    try:
        index_scu, page = await parser.find_position(parsed_message.query, parsed_message.scu)
    except errors.BadRequestInWB:
        await msg.answer("<b>Не удалось обработать запрос</b>")
        return
    query_id = str(uuid.uuid4())
    created_at = str(datetime.now().timestamp()).split('.')[0]
    db.insert("query", {
        "query_id": query_id,
        "scu": parsed_message.scu,
        "query_text": parsed_message.query.lower(),
        "created_at": created_at
    })
    kb = kb_user.kb_for_find_result(query_id, msg.from_user.id)
    if not index_scu:
        text = f"<b>Артикул {parsed_message.scu} по запросу {parsed_message.query} на {page} страницах не ранжируется</b>"
        await msg.answer(text, reply_markup=kb)
        return
    caption = db.fetchone("messages", "message", {"name": "caption"})
    text = f"<b>👍Артикул {parsed_message.scu} по запросу {parsed_message.query} найден</b>\n\n" \
           f"Страница: {page}\nПозиция: {index_scu}\n\n{caption['message'] if caption else 'Подпись'}"
    await msg.answer(text, disable_web_page_preview=True, reply_markup=kb)


async def update_query(call: CallbackQuery):
    await call.answer(cache_time=60)
    callback_data = call.data.split(":")
    query_id = callback_data[1]
    query_info = db.fetchone("query", "scu, query_text", {"query_id": query_id})
    if not query_info:
        await call.message.edit_text("Не удалось обновить. Повторите запрос")
        return
    try:
        index_scu, page = await parser.find_position(query_info["query_text"], int(query_info["scu"]))
    except errors.BadRequestInWB:
        await call.message.answer("Не удалось обработать запрос")
        return
    now = datetime.now().strftime("%d-%m-%Y в %H:%M")
    if not index_scu:
        text = f"<b>Артикул {query_info['scu']} по запросу {query_info['query_text']} на {page} страницах не" \
               f"ранжируется</b>\n\nОбновлено: {now}"
    else:
        caption = db.fetchone("messages", "message", {"name": "caption"})
        text = f"<b>👍Артикул {query_info['scu']} по запросу {query_info['query_text']} найден</b>\n\n" \
               f"Страница: {page}\nПозиция: {index_scu}\n\n{caption['message'] if caption else 'Подпись'}\n\n" \
               f"Обновлено: {now}"
    subscribe = db.fetchone("subscribe", "subscribe_id, scu",
            {"scu": int(query_info["scu"]), "user_id": str(call.from_user.id), "query_text": query_info["query_text"]})
    kb = kb_user.kb_for_find_result(query_id, call.from_user.id, subscribe["subscribe_id"] if subscribe else None)
    try:
        await call.message.edit_text(text, reply_markup=kb)
    except Exception as er:
        logging.error(er)


async def subscribe(call: CallbackQuery):
    await call.answer(cache_time=60)
    callback_data = call.data.split(":")
    query_id = callback_data[1]
    query_info = db.fetchone("query", "scu, query_text, page, position", {"query_id": query_id})
    if not query_info:
        await call.message.edit_text("Не удалось подписаться. Повторите запрос")
        return
    subscribes = db.fetchone(
        table="subscribe",
        columns="subscribe_id, scu, query_text, user_id, page, position",
        filters={"scu": query_info["scu"], "query_text": query_info["query_text"], "user_id": str(call.from_user.id)}
    )
    if subscribes:
        await call.message.answer("Вы уже подписаны")
        kb = kb_user.kb_for_find_result(query_id, call.from_user.id, subscribes["subscribe_id"])
        await call.message.edit_reply_markup(kb)
        return
    subscribe_id = uuid.uuid4()
    db.insert('subscribe', {
        "subscribe_id": str(subscribe_id),
        "scu": query_info["scu"],
        "query_text": query_info["query_text"],
        "user_id": str(call.from_user.id),
        "page": query_info["page"],
        "position": query_info["position"]
    })
    kb = kb_user.kb_for_find_result(query_id, call.from_user.id, str(subscribe_id))
    await call.message.edit_reply_markup(kb)
    await call.message.answer("Вы подписались")


async def no_subscribe(call: CallbackQuery):
    await call.answer()
    callback_data = call.data.split(":")
    subscribe_id = callback_data[1]
    subscribe = db.fetchone("subscribe", "scu, query_text", {"subscribe_id": subscribe_id})
    try:
        db.delete_subscribe(subscribe_id)
    except Exception as er:
        logging.error(er)
    await call.message.answer("Вы отписались")
    if subscribe:
        query_id = str(uuid.uuid4())
        created_at = str(datetime.now().timestamp()).split('.')[0]
        db.insert("query", {
            "query_id": query_id,
            "scu": subscribe["scu"],
            "query_text": subscribe["query_text"],
            "created_at": created_at
        })
        kb = kb_user.kb_for_find_result(query_id, call.from_user.id)
        await call.message.edit_reply_markup(kb)


async def btn_unsubscribe_on_notification(call: CallbackQuery):
    _, subscribe_id = call.data.split(":")
    db.delete_subscribe(subscribe_id)
    await call.message.edit_reply_markup()


async def cmd_my_subscribe(msg: Message):
    subscribes = db.fetchall_by_filter("subscribe", "subscribe_id, scu, query_text", {"user_id": str(msg.from_user.id)})
    if not subscribes:
        await msg.answer("У вас нет подписок")
        return
    for subscribe in subscribes:
        kb = kb_user.kb_unsubscribe(subscribe["subscribe_id"])
        await msg.answer(f"{subscribe['scu']} - {subscribe['query_text']}", reply_markup=kb)


def register_user(dp: Dispatcher):
    dp.register_message_handler(user_start, commands=["start"], state="*")
    dp.register_message_handler(cmd_my_subscribe, commands=["my_subscribes"])
    dp.register_message_handler(get_search_query)
    dp.register_callback_query_handler(update_query, lambda call: call.data.startswith("up:"))
    dp.register_callback_query_handler(subscribe, lambda call: call.data.startswith("sub"))
    dp.register_callback_query_handler(no_subscribe, lambda call: call.data.startswith("unsub"))
    dp.register_callback_query_handler(btn_unsubscribe_on_notification, lambda call: call.data.startswith("delsub"))
