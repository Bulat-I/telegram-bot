import os
from aiogram import Bot
from dotenv import find_dotenv, load_dotenv
from pydantic import ValidationError

load_dotenv(find_dotenv())
bot = Bot(token=os.getenv("TOKEN"))
file_input_location = os.getenv("FILE_INPUT_LOCATION")


async def fileDownloader(file_id_telegram, file_name_telegram) -> str:

    file_telegram = await bot.get_file(file_id_telegram)
    file_path_telegram = file_telegram.file_path
    file_local_path = os.path.join(
        file_input_location, file_id_telegram + "_" + file_name_telegram
    )

    file_local = await bot.download_file(file_path_telegram, file_local_path)

    return file_local_path
