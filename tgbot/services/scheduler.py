import asyncio
import logging
import random
from datetime import datetime

from aiogram import Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tgbot.services import db
from tgbot.services import parser
from tgbot.keyboards.kb_user import kb_unsubscribe


scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def send_to_subscribe(dp: Dispatcher):
    subscribes = db.fetchall(["subscribe_id", "scu", "query_text", "user_id", "page", "position"], "subscribe")
    for subscribe in subscribes:
        index_scu, page = await parser.find_position(subscribe["query_text"], subscribe["scu"])
        kb = kb_unsubscribe(subscribe["subscribe_id"])
        if not index_scu:
            text = f"<b>Артикул {subscribe['scu']} по запросу {subscribe['query_text']} на {page} страницах не" \
                   f"ранжируется</b>"
            try:
                await dp.bot.send_message(chat_id=subscribe["user_id"], text=text, reply_markup=kb)
            except Exception as er:
                logging.error(er)
                db.delete_subscribe(subscribe["subscribe_id"])
            continue
        caption = db.fetchone("messages", "message", {"name": "caption"})
        text = f"<b>👍Артикул {subscribe['scu']} по запросу {subscribe['query_text']} найден</b>\n\n" \
               f"Страница: {page}\nПозиция: {index_scu}\n\n{caption['message'] if caption else 'Подпись'}"
        try:
            await dp.bot.send_message(chat_id=subscribe["user_id"], text=text, reply_markup=kb)
        except Exception as er:
            logging.error(er)
            db.delete_subscribe(subscribe["subscribe_id"])
        await asyncio.sleep(random.randint(2, 5))


def delete_old_query():
    queries = db.fetchall(["query_id", "created_at"], "query")
    now = str(datetime.now().timestamp()).split('.')[0]
    for query in queries:
        if int(now) - int(query["created_at"]) > 604800:
            db.delete("query", "query_id", query["query_id"])


def add_tasks(dp):
    scheduler.add_job(send_to_subscribe, 'cron', day='*', hour='9', minute='30', args=[dp])
    scheduler.add_job(delete_old_query, 'cron', day='*', hour='4', minute='00')
    return scheduler
