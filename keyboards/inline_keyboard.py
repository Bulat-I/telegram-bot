from aiogram import types
from aiogram_i18n import LazyProxy
from aiogram_i18n.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def build_inline_callback_keyboard(*, buttons: dict[str, str]):
    keyboard = InlineKeyboardBuilder()

    for button_text, data in buttons.items():
        keyboard.row(InlineKeyboardButton(text=button_text, callback_data=data))

    return keyboard.as_markup()
