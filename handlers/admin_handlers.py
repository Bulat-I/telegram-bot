import asyncio
from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command

from filters.chat_types import ChatTypeFilter, IsAdmin
from keyboards.inline_keyboard import build_inline_callback_keyboard


admin_handlers_router = Router()
admin_handlers_router.message.filter(ChatTypeFilter(['private']), IsAdmin())

@admin_handlers_router.message(Command("admin"))
async def admin_features(message: types.Message):
    await message.answer(
        "Hey BOSS",
        reply_markup=build_inline_callback_keyboard(
            buttons={
                "I am the boss":f"boss"
            }
        ))
    
@admin_handlers_router.callback_query(F.data.contains("compress"))
async def boss_callback(callback: types.CallbackQuery):

    await callback.answer("Yes you are the boss")
    await callback.message.answer("Yes you are the boss")