import logging
import os
import sys
from aiogram import F, types, Router
from aiogram.filters import Command, StateFilter, or_f, CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import find_dotenv, load_dotenv

from filters.chat_types import ChatTypeFilter, IsAdmin
from common.bot_commands import menu_items_admin
from keyboards.inline_keyboard import build_inline_callback_keyboard

load_dotenv(find_dotenv())
log_file_path = os.getenv("LOGFILEPATH")

class AdminFeatures(StatesGroup):
    selectOption = State()

    texts = {"AdminFeatures:selectOption": "Select desired option"}


admin_handlers_router = Router()
admin_handlers_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

logger = logging.getLogger(__name__)


@admin_handlers_router.message(StateFilter("*"), Command("cancel"))
@admin_handlers_router.message(
    StateFilter("*"), or_f(F.data.contains("cancel"), F.text.casefold() == "cancel")
)
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    logger.info("cancel_handler from state " + str(state.get_state()))
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer(
        message.answer("Your actions were cancelled. Let's start it over"),
        CommandStart()
    )


@admin_handlers_router.message(StateFilter(None), Command("admin"))
async def admin_features(message: types.Message, state: FSMContext) -> None:
    logger.info("admin_features")
    await message.bot.delete_my_commands(scope=types.BotCommandScopeChat(chat_id=message.chat.id))
    await message.bot.set_my_commands(
        commands=menu_items_admin, scope=types.BotCommandScopeChat(chat_id=message.chat.id)
    )
    await state.set_state(AdminFeatures.selectOption)
    await message.answer(
        "Hey, Admin",
        reply_markup=build_inline_callback_keyboard(buttons={"Restart bot": f"restart", "Get logfile": f"logfile"})
    )


@admin_handlers_router.callback_query(StateFilter(AdminFeatures.selectOption), F.data.contains("restart"))
async def restart_callback(callback: types.CallbackQuery,  state: FSMContext) -> None:
    logger.info("restart_callback")
    await callback.answer("Restarting, please wait...")
    await state.clear()
    await sys.exit(0)


@admin_handlers_router.callback_query(StateFilter(AdminFeatures.selectOption), F.data.contains("logfile"))
async def logfile_callback(callback: types.CallbackQuery, state: FSMContext) -> None:
    logger.info("logfile_callback")
    await callback.answer("Here is the log file")
    await callback.message.answer_document(types.FSInputFile(log_file_path))
    await callback.message.answer(
        "Let's start it over",
        reply_markup=build_inline_callback_keyboard(buttons={"Restart bot": f"restart", "Get logfile": f"logfile"})
    )

