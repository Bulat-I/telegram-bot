import asyncio
import os
from aiogram import F, types, Router, methods
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from pydantic import ValidationError

from filters.chat_types import ChatTypeFilter
from keyboards.inline_keyboard import build_inline_callback_keyboard
from workload_handlers.pdf_compressor import compressPDF
from workload_handlers.pdf_converter import convertToPDF
from workload_handlers.file_downloader import fileDownloader

from dotenv import find_dotenv, load_dotenv
load_dotenv(find_dotenv())

file_input_location = os.getenv('FILE_INPUT_LOCATION')
file_output_location = os.getenv('FILE_OUTPUT_LOCATION')

user_handlers_router = Router()
user_handlers_router.message.filter(ChatTypeFilter(['private']))

INITIAL_KEYBOARD = build_inline_callback_keyboard(
            buttons={
                "Convert to PDF":f"topdf",
                "Compress PDF file":f"compress"
            }
)

SUPPORTED_FILES_LIST = [
    ".txt", ".csv", ".odt", ".ods", ".odp", ".odg", ".odf",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", 
    ".html", ".htm", ".jpg", ".jpeg", ".png", ".tif"]

class ToPDF(StatesGroup):
    input = State()

    texts = {
        "ToPDF:input": "Upload your file"
    }



class CompressPDF(StatesGroup):
    input = State()

    texts = {
        "CompressPDF:input": "Upload your file"
    }


@user_handlers_router.message(CommandStart())
async def start_cmd(message: types.Message) -> None:
    await message.answer(
        'Hi, I am your PDF converter assistant',
        reply_markup=INITIAL_KEYBOARD
    )


@user_handlers_router.message(StateFilter(None), Command("topdf"))
@user_handlers_router.callback_query(F.data.contains("topdf"))
async def convert_to_pdf_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer("Convert to PDF")
    await callback.message.answer("Upload your file")
    await state.set_state(ToPDF.input)


@user_handlers_router.message(StateFilter(None), Command("compress"))
@user_handlers_router.callback_query(F.data.contains("compress"))
async def compress_pdf_callback(callback: types.CallbackQuery, state: FSMContext):

    await callback.answer("Compress PDF")
    await callback.message.answer("Upload your file")
    await state.set_state(CompressPDF.input)

@user_handlers_router.message(StateFilter("*"), Command("cancel"))
@user_handlers_router.message(StateFilter("*"), F.text.casefold() == "cancel")
async def cancel_handler(message: types.Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer("Your actions were cancelled. Let's start it over", reply_markup=INITIAL_KEYBOARD)

#To PDF - User sent a proper document
@user_handlers_router.message(ToPDF.input, F.document)
async def topdf_Input(message: types.Message, state: FSMContext):
 
    await state.update_data(input=message.document)
    
    original_file_name = message.document.file_name
    file_id_telegram = message.document.file_id
    file_name_output_temp = os.path.splitext(original_file_name)
    file_name_output_original_pdf = file_name_output_temp[0] + ".pdf"
    temp_file_name_with_id = file_id_telegram + "_" + file_name_output_temp[0] + ".pdf"
    
    if (file_name_output_temp[1] not in SUPPORTED_FILES_LIST):
        await message.answer("Your file is in an unsupported format \n Please try another file")
        await state.set_state(ToPDF.input)
        return

    if (file_name_output_temp[1] == ".pdf"):
        await message.answer("Your file is already in PDF format \n Please try another file")
        await state.set_state(ToPDF.input)
        return
    
    if (message.document.file_size / (1024 * 1024) >= 20):
        await message.answer("Your file exceeds 20 MB \n Please try a smaller file")
        await state.set_state(ToPDF.input)
        return
    
    await message.answer("Please wait")

    file_path_input = await fileDownloader(message)

    if not (os.path.exists(file_path_input)):
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return
    
    file_path_output = os.path.join(file_output_location, temp_file_name_with_id)
    
    converter_exit_code = await convertToPDF(file_path_input, file_output_location)
    
    if converter_exit_code != 0:
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return
    
    if os.path.exists(file_path_output):
        await message.reply_document(types.FSInputFile(file_path_output, 'converted_' + file_name_output_original_pdf))
        await message.answer("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return
    
    if os.path.isfile(file_path_output):
        os.remove(file_path_output)
    
    await state.clear()

#To PDF - User sent an improper document
@user_handlers_router.message(ToPDF.input)
async def topdf_Input(message: types.Message, state: FSMContext):

    await message.answer("Your response is not a document \n Please upload a document")
    return

#Compress - User sent a proper document
@user_handlers_router.message(CompressPDF.input, F.document)
async def compresspdf_Input(message: types.Message, state: FSMContext):
            
    await state.update_data(input=message.document)
    
    original_file_name = message.document.file_name
    file_name_output_temp = os.path.splitext(original_file_name)

    if (file_name_output_temp[1] != ".pdf"):
        await message.answer("Your file must be in PDF format \n Please try another file")
        await state.set_state(CompressPDF.input)
        return

    await message.answer("Please wait")
    
    if (message.document.file_size / (1024 * 1024) >= 20):
        await message.answer("Your file exceeds 20 MB \n Please try a smaller file")
        await state.set_state(CompressPDF.input)
        return

    
    file_path_input = await fileDownloader(message)
    file_path_output = os.path.join(file_output_location, os.path.basename(file_path_input))
    
    compressor_exit_code = await compressPDF(file_path_input, file_output_location)

    if compressor_exit_code != 0:
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return
    
    if (os.path.exists(file_path_output)):
        await message.reply_document(types.FSInputFile(file_path_output, 'compressed_' + original_file_name))
        await message.answer("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return

    if os.path.isfile(file_path_output):
        os.remove(file_path_output)
    
    await state.clear()


#Compress - User sent an improper document
@user_handlers_router.message(CompressPDF.input)
async def compresspdf_Input(message: types.Message, state: FSMContext):
            
    await message.answer("Your response is not a document \n Please upload a document")
    return