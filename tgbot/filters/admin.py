import typing

from aiogram.dispatcher.filters import BoundFilter

from tgbot.config import Settings


class AdminFilter(BoundFilter):
    key = "is_admin"

    def __init__(self, is_admin: typing.Optional[bool] = None):
        self.is_admin = is_admin

    async def check(self, obj):
        if self.is_admin is None:
            return True
        settings: Settings = obj.bot.get("settings")
        return obj.from_user.id in settings.tg.admins
