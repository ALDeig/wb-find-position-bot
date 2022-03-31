import logging

from aiogram import Dispatcher
from aiogram.types import Message, ContentType
from aiogram.dispatcher.storage import FSMContext

from tgbot.services import db


async def cmd_edit_text_to_start(msg: Message, state: FSMContext):
    await msg.answer("Введите текст для команды старт")
    await state.set_state("get_text_for_start")


async def get_text_for_start(msg: Message, state: FSMContext):
    text = db.fetchone("messages", "message", {"name": "start"})
    if text:
        db.update("messages", {"message": msg.text}, {"name": "start"})
    else:
        db.insert("messages", {"name": "start", "message": msg.text})
    await state.finish()
    await msg.answer("Готово")


async def cmd_edit_text_to_caption(msg: Message, state: FSMContext):
    await msg.answer("Введите текст для подписи в результате")
    await state.set_state("get_text_for_caption")


async def get_text_for_caption(msg: Message, state: FSMContext):
    text = db.fetchone("messages", "message", {"name": "caption"})
    if text:
        db.update("messages", {"message": msg.text}, {"name": "caption"})
    else:
        db.insert("messages", {"name": "caption", "message": msg.text})
    await state.finish()
    await msg.answer("Готово")


async def cmd_get_count_users(msg: Message):
    users = db.fetchall(["user_id"], "users")
    await msg.answer(f"Количество пользователей - {len(users)}")


async def cmd_sending_to_all_users(msg: Message, state: FSMContext):
    await msg.answer("Введите сообщение для пересылки")
    await state.set_state("get_message_for_sending")


async def get_message_for_sending(msg: Message, state: FSMContext):
    users = db.fetchall(["user_id"], "users")
    for user in users:
        try:
            await msg.copy_to(user["user_id"])
        except Exception as er:
            logging.error(er)
    await msg.answer("Готово")
    await state.finish()

    
def register_admin(dp: Dispatcher):
    dp.register_message_handler(cmd_edit_text_to_start, commands=["edit_start"], is_admin=True)
    dp.register_message_handler(get_text_for_start, state="get_text_for_start")
    dp.register_message_handler(cmd_edit_text_to_caption, commands=["edit_caption"], is_admin=True)
    dp.register_message_handler(get_text_for_caption, state="get_text_for_caption")
    dp.register_message_handler(cmd_get_count_users, commands=["get_count_users"], is_admin=True)
    dp.register_message_handler(cmd_sending_to_all_users, commands=["sending_message"], is_admin=True)
    dp.register_message_handler(get_message_for_sending, state="get_message_for_sending", content_types=ContentType.ANY)
    
