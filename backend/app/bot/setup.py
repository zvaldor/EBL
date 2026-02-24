from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config import settings


def create_bot() -> Bot:
    return Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    from app.bot.handlers import mentions, commands, callbacks, bath_wizard
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(commands.router)
    dp.include_router(mentions.router)
    dp.include_router(bath_wizard.router)
    dp.include_router(callbacks.router)
    return dp
