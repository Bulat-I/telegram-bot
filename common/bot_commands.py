from aiogram.types import BotCommand

menu_items = [
    BotCommand(command="en", description="Switch to English"),
    BotCommand(command="ru", description="Switch to Russian"),
    BotCommand(command="cancel", description="Cancel"),
]

menu_items_admin = [
    BotCommand(command="start", description="Back to user menu"),
    BotCommand(command="cancel", description="Cancel"),
]