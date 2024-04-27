import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.strategy import FSMStrategy
from pathlib import Path

from aiogram_i18n import I18nMiddleware
from aiogram_i18n.cores.gnu_text_core import GNUTextCore
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv())

from handlers.user_handlers import user_handlers_router
from handlers.admin_handlers import admin_handlers_router
from common.bot_commands import menu_items
from middlewares import i18nmiddleware

ALLOWED_UPDATES = ["message, inline_query"]
I18N_BASE_DIR = os.path.join(Path.cwd(), "locales")
log_file_path = os.getenv("LOGFILEPATH")
    
logging.getLogger().setLevel(level=os.getenv("LOGLEVEL"))

bot = Bot(token=os.getenv("TOKEN"))
dp = Dispatcher(fsm_strategy=FSMStrategy.USER_IN_CHAT)
dp.include_routers(user_handlers_router, admin_handlers_router)
i18n = I18nMiddleware(
        core=GNUTextCore(
            path=I18N_BASE_DIR,
        ),
        manager=i18nmiddleware.UserManager(),
        default_locale="en"
    )

i18n.setup(dp)


async def main() -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(
        commands=menu_items, scope=types.BotCommandScopeAllPrivateChats()
    )
    await dp.start_polling(bot, allowed_updates=ALLOWED_UPDATES)


if __name__ == "__main__":
    logging.basicConfig(filename=log_file_path, filemode='w', format='%(asctime)s - %(levelname)s - %(message)s')
    asyncio.run(main())
