import pytest
from unittest.mock import AsyncMock, Mock
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey

from handlers.user_handlers import document_without_command, start_cmd, switch_language
from handlers.user_handlers import INITIAL_KEYBOARD

@pytest.mark.asyncio
async def test_start_cmds():
    message = AsyncMock()
    mock_i18n = Mock()
    mock_i18n.get.return_value = "Hi, I am your PDF converter assistant"
    await start_cmd(message, mock_i18n)
    message.answer.assert_called()

    message.answer.assert_called_once_with("Hi, I am your PDF converter assistant", reply_markup=INITIAL_KEYBOARD)


@pytest.mark.asyncio
async def test_switch_language_en():
    message = AsyncMock()
    mock_i18n = AsyncMock()
    await switch_language(message, mock_i18n, "en")
    message.answer.assert_called()
    message.answer.assert_called_once_with("Language switched to: en", reply_markup=INITIAL_KEYBOARD)


@pytest.mark.asyncio
async def test_switch_language_ru():
    message = AsyncMock()
    mock_i18n = AsyncMock()
    await switch_language(message, mock_i18n, "ru")
    message.answer.assert_called()
    message.answer.assert_called_once_with("Язык переключен на : ru", reply_markup=INITIAL_KEYBOARD)
