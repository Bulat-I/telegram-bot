import asyncio
from aiogram import types, Router
from aiogram.filters import CommandStart

from filters.chat_types import ChatTypeFilter, IsAdmin


admin_handlers_router = Router()
admin_handlers_router.message.filter(ChatTypeFilter(['private']), IsAdmin())