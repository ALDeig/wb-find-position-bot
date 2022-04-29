import asyncio
import logging
# import random
from datetime import datetime

from aiogram import Dispatcher
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from tgbot.services import db
from tgbot.services import parser
from tgbot.services.service import create_text_position
from tgbot.keyboards.kb_user import kb_unsubscribe


scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


async def process_update(subscribe: dict):
    index_scu, page = await parser.find_position(subscribe["query_text"], subscribe["scu"])
    db.insert(
        table="tmp_subscribe",
        column_values={
            "subscribe_id": subscribe["subscribe_id"],
            "scu": subscribe["scu"],
            "query_text": subscribe["query_text"],
            "user_id": subscribe["user_id"],
            "old_page": subscribe["page"],
            "old_position": subscribe["position"],
            "new_page": page,
            "new_position": index_scu if index_scu else -1 
        }
    )
    return True


def as_completed(max_workers: int, awaitables):
    semaphore = asyncio.Semaphore(max_workers)

    async def worker(awaitable):
        async with semaphore:
            return await awaitable

    workers = [worker(aw) for aw in awaitables]
    return asyncio.as_completed(workers)


async def update_subscribe():
    logging.info("Update subscribes start")
    subscribes = db.fetchall(["subscribe_id", "scu", "query_text", "user_id", "page", "position"], "subscribe")
    max_workers = 15
    processors = [process_update(subscribe) for subscribe in subscribes]
    for task in as_completed(max_workers, processors):
        await task
    logging.info("Update subscribes done")


# async def update_subscribe():
#     subscribes = db.fetchall(["subscribe_id", "scu", "query_text", "user_id", "page", "position"], "subscribe")
#     amount_subscribe = len(subscribes)
#     cnt = 1
#     for subscribe in subscribes:
#         logging.info(f"{cnt} in {amount_subscribe}")
#         cnt += 1
#         index_scu, page = await parser.find_position(subscribe["query_text"], subscribe["scu"])
#         db.insert(
#             table="tmp_subscribe",
#             column_values={
#                 "subscribe_id": subscribe["subscribe_id"],
#                 "scu": subscribe["scu"],
#                 "query_text": subscribe["query_text"],
#                 "user_id": subscribe["user_id"],
#                 "old_page": subscribe["page"],
#                 "old_position": subscribe["position"],
#                 "new_page": page,
#                 "new_position": index_scu if index_scu else -1 
#             }
#         )
#         # await asyncio.sleep(random.randint(1, 3))
#     logging.info("Update subscribes done")


async def send_to_subscribe(dp: Dispatcher):
    subscribes = db.fetchall(
        ["subscribe_id", "scu", "query_text", "user_id", "old_page",  "new_page", "old_position", "new_position"],
        "tmp_subscribe"
    )
    for subscribe in subscribes:
        kb = kb_unsubscribe(subscribe["subscribe_id"])
        if subscribe["new_position"] < 0:
            text = f"<b>Артикул {subscribe['scu']} по запросу {subscribe['query_text']} на {subscribe['new_page']} " \
                   f"страницах не ранжируется</b>"
            try:
                await dp.bot.send_message(chat_id=subscribe["user_id"], text=text, reply_markup=kb)
            except Exception as er:
                logging.error(er)
                db.delete_subscribe(subscribe["subscribe_id"])
            continue
        caption = db.fetchone("messages", "message", {"name": "caption"})
        text = f"<b>👍Артикул {subscribe['scu']} по запросу {subscribe['query_text']} найден</b>\n\n" \
               f"Страница: {create_text_position(subscribe['old_page'], subscribe['new_page'])}\n" \
               f"Позиция: {create_text_position(subscribe['old_position'], subscribe['new_position'])}\n\n" \
               f"{caption['message'] if caption else 'Подпись'}"
        try:
            await dp.bot.send_message(chat_id=subscribe["user_id"], text=text, reply_markup=kb)
            if subscribe["old_page"] != subscribe["new_page"] or subscribe["old_position"] != subscribe["new_position"]:
                db.update("subscribe", {"page": subscribe["new_page"], "position": subscribe["new_position"]},
                          {"subscribe_id": subscribe["subscribe_id"]})
        except Exception as er:
            logging.error(er)
            db.delete_subscribe(subscribe["subscribe_id"])
        await asyncio.sleep(0.5)
    db.delete_tmp_subscribes()
    logging.info("Send subscribe done")


def delete_old_query():
    queries = db.fetchall(["query_id", "created_at"], "query")
    now = str(datetime.now().timestamp()).split('.')[0]
    for query in queries:
        if int(now) - int(query["created_at"]) > 604800:
            db.delete("query", "query_id", query["query_id"])


def add_tasks(dp):
    scheduler.add_job(update_subscribe, "cron", hour=9, minute=0)
    scheduler.add_job(send_to_subscribe, "cron", hour=9, minute=30, args=[dp])
    scheduler.add_job(delete_old_query, "cron", hour=4, minute=0)
    return scheduler
