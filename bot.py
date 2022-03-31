import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram.utils.exceptions import ChatNotFound

from tgbot.config import Settings
from tgbot.filters.admin import AdminFilter
from tgbot.handlers.admin import register_admin
from tgbot.handlers.user import register_user
from tgbot.services.logger import setup_logger
from tgbot.services.scheduler import add_tasks


def register_all_filters(dp):
    dp.filters_factory.bind(AdminFilter)


def register_all_handlers(dp):
    register_admin(dp)
    register_user(dp)


async def set_commands(dp: Dispatcher, admin_ids: list[int]):
    await dp.bot.set_my_commands(
        commands=[BotCommand("start", "Старт"), BotCommand("my_subscribes", "Мои подписки")]
    )
    commands_for_admin = [
        BotCommand("start", "Старт"),
        BotCommand("edit_start", "Изменить текст на команду старт"),
        BotCommand("edit_caption", "Изменить текст подписи"),
        BotCommand("get_count_users", "Количество пользователей"),
        BotCommand("my_subscribes", "Мои подписки"),
        BotCommand("sending_message", "Рассылка сообщения")
    ]
    for admin_id in admin_ids:
        try:
            await dp.bot.set_my_commands(
                commands=commands_for_admin,
                scope=BotCommandScopeChat(admin_id)
            )
        except ChatNotFound as er:
            logging.error(f"Установка команд для администратора {admin_id}: {er}")


async def main():
    setup_logger("INFO")
    logging.info("Starting bot")
    settings = Settings()

    storage = MemoryStorage()

    bot = Bot(token=settings.tg.token, parse_mode="HTML")
    dp = Dispatcher(bot, storage=storage)

    bot["settings"] = settings
    bot_info = await bot.get_me()
    logging.info(f"<yellow>Name: <b>{bot_info['first_name']}</b>, username: {bot_info['username']}</yellow>")

    register_all_filters(dp)
    register_all_handlers(dp)
    await set_commands(dp, settings.tg.admins)

    schduler = add_tasks(dp)

    # start
    try:
        schduler.start()
        await dp.start_polling()
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.error("Bot stopped!")
