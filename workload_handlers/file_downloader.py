import os
from aiogram import Bot
from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())
bot = Bot(token=os.getenv('TOKEN'))

async def fileDownloader(message) -> str:
    file_id_telegram = message.document.file_id
    file_name_telegram = message.document.file_name
    file_telegram = await bot.get_file(file_id_telegram)
    file_path_telegram = file_telegram.file_path
    file_local_path = "/var/lib/telegram-bot/input/" + file_name_telegram
    file_local = await bot.download_file(file_path_telegram, file_local_path)
    
    return file_local_path