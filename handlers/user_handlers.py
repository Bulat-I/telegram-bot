import asyncio
import os
from aiogram import F, types, Router, methods
from aiogram.filters import CommandStart, Command, StateFilter, or_f
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from pydantic import ValidationError

from filters.chat_types import ChatTypeFilter
from keyboards.inline_keyboard import build_inline_callback_keyboard
from workload_handlers.pdf_compressor import compressPDF
from workload_handlers.pdf_converter import convertToPDF
from workload_handlers.file_downloader import fileDownloader
from workload_handlers.pdf_merger import mergeTwoPDF

from dotenv import find_dotenv, load_dotenv

from workload_handlers.pdf_rotator import rotatePDF
load_dotenv(find_dotenv())

file_input_location = os.getenv('FILE_INPUT_LOCATION')
file_output_location = os.getenv('FILE_OUTPUT_LOCATION')

user_handlers_router = Router()
user_handlers_router.message.filter(ChatTypeFilter(['private']))


INITIAL_KEYBOARD = build_inline_callback_keyboard(
            buttons={
                "Convert to PDF":f"topdf",
                "Compress PDF file":f"compress",
                "Rotate PDF":f"rotate",
                "Merge two PDFs":f"merge"
            }
)


ROTATE_KEYBOARD = build_inline_callback_keyboard(
    buttons={
        "Rotate left - 90°":f"left90",
        "Rotate right - 90°":f"right90",
        "Rotate - 180°":f"right180"
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


class Rotate(StatesGroup):
    input = State()
    selectOption = State()

    texts = {
        "Rotate:input": "Upload your file",
        "Rotate:option": "Select your option"
    }


class MergePDF(StatesGroup):
    input_file1 = State()
    input_file2 = State()

    texts = {
        "MergePDF:input1": "Upload your first file",
        "MergePDF:input2": "Upload your second file"
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


@user_handlers_router.message(StateFilter(None), Command("rotate"))
@user_handlers_router.callback_query(F.data.contains("rotate"))
async def rotate_pdf_callback(callback: types.CallbackQuery, state: FSMContext):
    
    await callback.answer("Rotate your PDF")
    await callback.message.answer("Upload your file")
    await state.set_state(Rotate.input)


@user_handlers_router.message(StateFilter(None), Command("merge"))
@user_handlers_router.callback_query(F.data.contains("merge"))
async def merge_pdf_callback(callback: types.CallbackQuery, state: FSMContext):
    
    await callback.answer("Merge your PDFs")
    await callback.message.answer("Upload your first file")
    await state.set_state(MergePDF.input_file1)


@user_handlers_router.message(StateFilter("*"), Command("cancel"))
@user_handlers_router.message(StateFilter("*"), or_f(F.data.contains("cancel"), F.text.casefold() == "cancel"))
async def cancel_handler(message: types.Message, state: FSMContext) -> None:

    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.clear()
    await message.answer("Your actions were cancelled. Let's start it over", reply_markup=INITIAL_KEYBOARD)


#To PDF - User sent a proper document
@user_handlers_router.message(StateFilter(ToPDF.input), ToPDF.input, F.document)
async def topdf_Input(message: types.Message, state: FSMContext):
    
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

    file_path_input = await fileDownloader(file_id_telegram, original_file_name)

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
@user_handlers_router.message(StateFilter(ToPDF.input), ToPDF.input)
async def topdf_Input_Improper(message: types.Message, state: FSMContext):

    await message.answer("Your response is not a document \n Please upload a document")
    return

#Compress - User sent a proper document
@user_handlers_router.message(StateFilter(CompressPDF.input), CompressPDF.input, F.document)
async def compresspdf_Input(message: types.Message, state: FSMContext):
    
    original_file_name = message.document.file_name
    file_id_telegram = message.document.file_id
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

    file_path_input = await fileDownloader(file_id_telegram, original_file_name)

    if not (os.path.exists(file_path_input)):
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return

    file_path_output = os.path.join(file_output_location, os.path.basename(file_path_input))
    
    compressor_result = await compressPDF(file_path_input, file_output_location)

    #if compressor_exit_code != 0:
    #    await state.clear()
    #    await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
    #    return
    
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
@user_handlers_router.message(StateFilter(CompressPDF.input), CompressPDF.input)
async def compresspdf_Input_Improper(message: types.Message, state: FSMContext):
            
    await message.answer("Your response is not a document \n Please upload a document")
    return


#Rotate PDF - User sent a proper document
@user_handlers_router.message(StateFilter(Rotate.input), Rotate.input, F.document)
async def rotatePDF_Input(message: types.Message, state: FSMContext):
    
    original_file_name = message.document.file_name
    file_id_telegram = message.document.file_id
    file_name_output_temp = os.path.splitext(original_file_name)

    if (file_name_output_temp[1] != ".pdf"):
        await message.answer("Your file must be in PDF format \n Please try another file")
        await state.set_state(Rotate.input)
        return

    await message.answer("Please wait")
    
    if (message.document.file_size / (1024 * 1024) >= 20):
        await message.answer("Your file exceeds 20 MB \n Please try a smaller file")
        await state.set_state(Rotate.input)
        return
    
    file_path_input = await fileDownloader(file_id_telegram, original_file_name)

    if not (os.path.exists(file_path_input)):
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return
    
    await state.update_data(file_path_input=file_path_input)
    await state.update_data(original_file_name=original_file_name)
    
    await message.answer("Select how you want to rotate your PDF", reply_markup=ROTATE_KEYBOARD)
    await state.set_state(Rotate.selectOption)
    

#Rotate PDF - User sent an improper document
@user_handlers_router.message(StateFilter(Rotate.input), Rotate.input)
async def rotatePDF_Input_Improper(message: types.Message, state: FSMContext):

    await message.answer("Your response is not a PDF document \n Please upload a PDF document")
    return


@user_handlers_router.message(StateFilter(Rotate.selectOption), Command("right90"))
@user_handlers_router.callback_query(F.data.contains("right90"))
async def rotate_pdf_right90_callback(callback: types.CallbackQuery, state: FSMContext):
    
    data = await state.get_data()
    
    file_path_input = data["file_path_input"]
    original_file_name = data["original_file_name"]
    
    file_name_output_temp = os.path.splitext(original_file_name)

    if (file_name_output_temp[1] != ".pdf"):
        await data.answer("Your file must be in PDF format \n Please try another file")
        await state.set_state(Rotate.input)
        return
    
    file_path_output = os.path.join(file_output_location, os.path.basename(file_path_input))

    rotator_result = await rotatePDF(file_path_input, file_output_location, 90)
    
    if (os.path.exists(file_path_output) and os.path.getsize(file_path_input) > 0):
        await callback.message.reply_document(types.FSInputFile(file_path_output, 'rotated_' + original_file_name))
        await callback.message.reply("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        await callback.message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return

    if os.path.isfile(file_path_output):
        os.remove(file_path_output)

    await state.clear()


@user_handlers_router.message(StateFilter(Rotate.selectOption), Command("left90"))
@user_handlers_router.callback_query(F.data.contains("left90"))
async def rotate_pdf_left90_callback(callback: types.CallbackQuery, state: FSMContext):

    data = await state.get_data()
    
    file_path_input = data["file_path_input"]
    original_file_name = data["original_file_name"]
    
    file_name_output_temp = os.path.splitext(original_file_name)

    if (file_name_output_temp[1] != ".pdf"):
        await data.answer("Your file must be in PDF format \n Please try another file")
        await state.set_state(Rotate.input)
        return
    
    file_path_output = os.path.join(file_output_location, os.path.basename(file_path_input))

    rotator_result = await rotatePDF(file_path_input, file_output_location, 270)
    
    if (os.path.exists(file_path_output) and os.path.getsize(file_path_input) > 0):
        await callback.message.reply_document(types.FSInputFile(file_path_output, 'rotated_' + original_file_name))
        await callback.message.reply("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        await callback.message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return

    if os.path.isfile(file_path_output):
        os.remove(file_path_output)

    await state.clear()

@user_handlers_router.message(StateFilter(Rotate.selectOption), Command("right180"))
@user_handlers_router.callback_query(F.data.contains("right180"))
async def rotate_pdf_right180_callback(callback: types.CallbackQuery, state: FSMContext):
    
    data = await state.get_data()
    
    file_path_input = data["file_path_input"]
    original_file_name = data["original_file_name"]
    
    file_name_output_temp = os.path.splitext(original_file_name)

    if (file_name_output_temp[1] != ".pdf"):
        await data.answer("Your file must be in PDF format \n Please try another file")
        await state.set_state(Rotate.input)
        return
    
    file_path_output = os.path.join(file_output_location, os.path.basename(file_path_input))
    
    rotator_result = await rotatePDF(file_path_input, file_output_location, 180)
    
    if (os.path.exists(file_path_output) and os.path.getsize(file_path_input) > 0):
        await callback.message.reply_document(types.FSInputFile(file_path_output, 'rotated_' + original_file_name))
        await callback.message.reply("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        await callback.message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return

    if os.path.isfile(file_path_output):
        os.remove(file_path_output)

    await state.clear()


@user_handlers_router.message(StateFilter(Rotate.selectOption), Rotate.selectOption)
async def rotatePDF_Option(message: types.Message, state: FSMContext):

    await message.answer("Something went wrong \n Please try again", reply_markup=ROTATE_KEYBOARD)
    return


#Merge PDF - Input1 - User sent a proper document
@user_handlers_router.message(StateFilter(MergePDF.input_file1), MergePDF.input_file1, F.document)
async def merge_pdf_Input1(message: types.Message, state: FSMContext):
    
    original_file_name = message.document.file_name
    file_id_telegram = message.document.file_id
    file_name_output_temp = os.path.splitext(original_file_name)

    if (file_name_output_temp[1] != ".pdf"):
        await message.answer("Your file must be in PDF format \n Please try another file")
        await state.set_state(MergePDF.input_file1)
        return
    
    if (message.document.file_size / (1024 * 1024) >= 20):
        await message.answer("Your file exceeds 20 MB \n Please try a smaller file")
        await state.set_state(MergePDF.input_file1)
        return
    
    file_path_input = await fileDownloader(file_id_telegram, original_file_name)
    
    if not (os.path.exists(file_path_input)):
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return
    
    await state.update_data(file_path_input1=file_path_input)
    await state.update_data(original_file_name1=original_file_name)
    await message.answer("Upload your second file")
    await state.set_state(MergePDF.input_file2)
    

#Merge PDF - Input1 - User sent an improper document
@user_handlers_router.message(StateFilter(MergePDF.input_file1), MergePDF.input_file1)
async def merge_pdf_Input1_Improper(message: types.Message, state: FSMContext):

    await message.answer("Your response is not a PDF document \n Please upload a PDF document")
    return


#Merge PDF - Input2 - User sent a proper document
@user_handlers_router.message(StateFilter(MergePDF.input_file2), MergePDF.input_file2, F.document)
async def merge_pdf_Input2(message: types.Message, state: FSMContext):
    
    data = await state.get_data()
    
    file_path_input1 = data["file_path_input1"]
    original_file_name1 = data["original_file_name1"]

    original_file_name2 = message.document.file_name
    file_id_telegram2 = message.document.file_id
    file_name_output_temp2 = os.path.splitext(original_file_name2)

    if (file_name_output_temp2[1] != ".pdf"):
        await message.answer("Your file must be in PDF format \n Please try another file")
        await state.set_state(MergePDF.input_file2)
        return

    await message.answer("Please wait")
    
    if (message.document.file_size / (1024 * 1024) >= 20):
        await message.answer("Your file exceeds 20 MB \n Please try a smaller file")
        await state.set_state(MergePDF.input_file2)
        return
    
    file_path_input2 = await fileDownloader(file_id_telegram2, original_file_name2)

    if not (os.path.exists(file_path_input2)):
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return
    
    file_path_output = os.path.join(file_output_location, os.path.basename(file_path_input1))
    
    merger_exit_code = await mergeTwoPDF(file_path_input1, file_path_input2, file_output_location)
    
    if (os.path.exists(file_path_output)):
        await message.reply_document(types.FSInputFile(file_path_output, 'merged_' + original_file_name1))
        await message.answer("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        await message.answer("Something went wrong \n Please try again", reply_markup=INITIAL_KEYBOARD)
        return

    if os.path.isfile(file_path_output):
        os.remove(file_path_output)

    await state.clear()
    

#Merge PDF - Input2 - User sent an improper document
@user_handlers_router.message(StateFilter(MergePDF.input_file2), MergePDF.input_file2)
async def merge_pdf_Input2_Improper(message: types.Message, state: FSMContext):

    await message.answer("Your response is not a PDF document \n Please upload a PDF document")
    return

