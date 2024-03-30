import asyncio
from aiogram import types, Router
from aiogram.filters import CommandStart, Command
from filters.chat_types import ChatTypeFilter

user_handlers_router = Router()
user_handlers_router.message.filter(ChatTypeFilter(['private']))

@user_handlers_router.message(CommandStart())
async def start_cmd(message: types.Message) -> None:
    await message.answer('start')

@user_handlers_router.message()
async def echo(message: types.Message) -> None:
    await message.answer('You sent me: ' + message.text)