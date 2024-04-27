import logging
import os
from aiogram import F, types, Router, methods
from aiogram.filters import CommandStart, Command, StateFilter, or_f
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram_i18n import I18nContext, LazyProxy, I18nMiddleware

from filters.chat_types import ChatTypeFilter
from keyboards.inline_keyboard import build_inline_callback_keyboard
from workload_handlers.pdf_compressor import compressPDF
from workload_handlers.pdf_converter import convertToPDF
from workload_handlers.file_downloader import fileDownloader
from workload_handlers.pdf_merger import mergeTwoPDF
from common.bot_commands import menu_items

from dotenv import find_dotenv, load_dotenv
from workload_handlers.pdf_rotator import rotatePDF

load_dotenv(find_dotenv())

logger = logging.getLogger(__name__)

file_input_location = os.getenv("FILE_INPUT_LOCATION")
file_output_location = os.getenv("FILE_OUTPUT_LOCATION")

user_handlers_router = Router()
user_handlers_router.message.filter(ChatTypeFilter(["private"]))


INITIAL_KEYBOARD = build_inline_callback_keyboard(
    buttons={
        LazyProxy("Convert to PDF"): f"topdf",
        LazyProxy("Compress PDF file"): f"compress",
        LazyProxy("Rotate PDF"): f"rotate",
        LazyProxy("Merge two PDFs"): f"merge",
    }
)


FILE_FIRST_KEYBOARD_PDF_FILE = build_inline_callback_keyboard(
    buttons={
        LazyProxy("Compress PDF file"): f"compress_file_first",
        LazyProxy("Rotate PDF"): f"rotate_file_first",
        LazyProxy("Merge two PDFs"): f"merge_file_first",
    }
)


FILE_FIRST_KEYBOARD_NON_PDF_FILE = build_inline_callback_keyboard(
    buttons={
        LazyProxy("Convert to PDF"): f"topdf_file_first",
    }
)


ROTATE_KEYBOARD = build_inline_callback_keyboard(
    buttons={
        LazyProxy("Rotate left - 90°"): f"left90",
        LazyProxy("Rotate right - 90°"): f"right90",
        LazyProxy("Rotate - 180°"): f"right180",
    }
)


SUPPORTED_FILES_LIST = [
    ".txt",
    ".csv",
    ".odt",
    ".ods",
    ".odp",
    ".odg",
    ".odf",
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",
    ".html",
    ".htm",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
]

class ToPDF(StatesGroup):
    input = State()

    texts = {"ToPDF:input": "Upload your file"}


class ToPDFFileFirst(StatesGroup):
    process = State()

    texts = {"ToPDFFileFirst:process": "Processing your file"}


class CompressPDF(StatesGroup):
    input = State()

    texts = {"CompressPDF:input": "Upload your file"}


class CompressPDFFileFirst(StatesGroup):
    process = State()

    texts = {"CompressPDFFileFirst:process": "Processing your file"}


class Rotate(StatesGroup):
    input = State()
    selectOption = State()

    texts = {"Rotate:input": "Upload your file", "Rotate:option": "Select your option"}


class RotateFileFirst(StatesGroup):
    selectOption = State()

    texts = {"RotateFileFirst:selectOption": "Select desired option"}


class MergePDF(StatesGroup):
    input_file1 = State()
    input_file2 = State()

    texts = {
        "MergePDF:input1": "Upload your first file",
        "MergePDF:input2": "Upload your second file",
    }


class MergePDFFileFirst(StatesGroup):
    input_file2 = State()
    process = State()

    texts = {
        "MergePDFFileFirst:input2": "Upload your second file",
        "MergePDFFileFirst:process": "Processing your files",
    }


class DocumentWithoutCommand(StatesGroup):
    selectOption = State()

    texts = {"DocumentWithoutCommand:selectOption": "Select desired option"}


@user_handlers_router.message(CommandStart())
async def start_cmd(message: types.Message, i18n: I18nContext) -> None:
    await message.bot.delete_my_commands(scope=types.BotCommandScopeChat(chat_id=message.chat.id))
    await message.bot.set_my_commands(
        commands=menu_items, scope=types.BotCommandScopeChat(chat_id=message.chat.id)
    )
    await message.answer(
        i18n.get("Hi, I am your PDF converter assistant"), reply_markup=INITIAL_KEYBOARD
    )
    logger.info("Started for user " + str(message.from_user.id))


async def switch_language(message: types.Message, i18n: I18nContext, locale_code: str) -> None:
    await i18n.set_locale(locale_code)
    if locale_code == "en":
        await message.answer("Language switched to: " + locale_code, reply_markup=INITIAL_KEYBOARD)
    else:
        await message.answer("Язык переключен на : " + locale_code, reply_markup=INITIAL_KEYBOARD)

@user_handlers_router.message(Command("en"))
async def switch_to_en(message: types.Message, i18n: I18nContext) -> None:
    logger.debug(str(message.from_user.id) + " switched the language to English")
    await switch_language(message, i18n,"en")


@user_handlers_router.message(Command("ru"))
async def switch_to_en(message: types.Message, i18n: I18nContext) -> None:
    logger.debug(str(message.from_user.id) + " switched the language to Russian")
    await switch_language(message, i18n,"ru")


# This is a handler for incoming document without a command
@user_handlers_router.message(StateFilter(None), F.document)
async def document_without_command(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    await state.set_state(DocumentWithoutCommand.selectOption)
    original_file_name = message.document.file_name
    file_id_telegram = message.document.file_id
    file_name_output_temp = os.path.splitext(original_file_name)
    temp_file_name_with_id = file_id_telegram + "_" + file_name_output_temp[0] + ".pdf"
    logger.info(
        "Recieved document "
        + original_file_name
        + " from user "
        + str(message.from_user.id)
    )

    if message.document.file_size / (1024 * 1024) >= 20:
        logger.debug(original_file_name + " is more than 20MB")
        await message.answer(i18n.get("Your file exceeds 20 MB \n Please try a smaller file"))
        return

    file_path_input = await fileDownloader(file_id_telegram, original_file_name)
    logger.debug("fileDownloader output is: " + file_path_input)

    if not (os.path.exists(file_path_input)):
        logger.info(
            "Something went wrong with the file "
            + file_path_input
            + " from the user "
            + str(message.from_user.id)
        )
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    await state.update_data(file_path_input=file_path_input)
    await state.update_data(file_id_telegram=file_id_telegram)
    await state.update_data(original_file_name=original_file_name)

    if file_name_output_temp[1] != ".pdf":
        logger.debug("Input file is not a PDF")
        if file_name_output_temp[1] not in SUPPORTED_FILES_LIST:
            logger.debug("Input file is not in the supported file types list")
            await message.answer(
                i18n.get("Your file is in an unsupported format \n Please try another file"),
                reply_markup=INITIAL_KEYBOARD,
            )
            os.remove(file_path_input)
            logger.debug("File " + file_name_output_temp + " removed")
            return
        else:
            logger.debug("Input file is in the supported file types list")
            await message.answer(
                i18n.get("Please select what you want to do with this file"),
                reply_markup=FILE_FIRST_KEYBOARD_NON_PDF_FILE,
            )
            return

    if file_name_output_temp[1] == ".pdf":
        logger.debug("Input file is not a PDF")
        await message.answer(
            i18n.get("Please select what you want to do with this file"),
            reply_markup=FILE_FIRST_KEYBOARD_PDF_FILE,
        )
        return


@user_handlers_router.callback_query(
    StateFilter(DocumentWithoutCommand.selectOption),
    F.data.contains("topdf_file_first"),
)
async def topdf_file_first(callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("topdf_file_first")
    await state.set_state(ToPDFFileFirst.process)

    data = await state.get_data()

    file_path_input = data["file_path_input"]
    file_id_telegram = data["file_id_telegram"]
    original_file_name = data["original_file_name"]

    file_name_output_temp = os.path.splitext(original_file_name)
    file_name_output_original_pdf = file_name_output_temp[0] + ".pdf"
    temp_file_name_with_id = file_id_telegram + "_" + file_name_output_temp[0] + ".pdf"

    await callback.message.answer(i18n.get("Please wait"))

    file_path_output = os.path.join(file_output_location, temp_file_name_with_id)

    converter_exit_code = await convertToPDF(file_path_input, file_output_location)
    logger.debug("Converter exit code is: " + str(converter_exit_code))

    if converter_exit_code != 0:
        await state.clear()
        await callback.message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.exists(file_path_output):
        await callback.message.reply_document(
            types.FSInputFile(
                file_path_output, "converted_" + file_name_output_original_pdf
            )
        )
        logger.debug(
            "File " + file_path_output + " sent to user " + str(callback.from_user.id)
        )
        await callback.message.answer(i18n.get("Here is your PDF"), reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " to user "
            + str(callback.from_user.id)
        )
        await callback.message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.isfile(file_path_output):
        logger.debug("File " + file_path_output + " removed")
        os.remove(file_path_output)

    await state.clear()


@user_handlers_router.callback_query(
    StateFilter(DocumentWithoutCommand.selectOption),
    F.data.contains("compress_file_first"),
)
async def compress_file_first(callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("compress_file_first")
    await state.set_state(CompressPDFFileFirst.process)

    data = await state.get_data()

    file_path_input = data["file_path_input"]
    file_id_telegram = data["file_id_telegram"]
    original_file_name = data["original_file_name"]

    file_name_output_temp = os.path.splitext(original_file_name)
    file_name_output_original_pdf = file_name_output_temp[0] + ".pdf"
    temp_file_name_with_id = file_id_telegram + "_" + file_name_output_temp[0] + ".pdf"

    await callback.message.answer(i18n.get("Please wait"))

    file_path_output = os.path.join(file_output_location, temp_file_name_with_id)

    compressor_result = await compressPDF(file_path_input, file_output_location)
    logger.debug("Compressor result is: " + str(compressor_result))

    if os.path.exists(file_path_output):
        await callback.message.reply_document(
            types.FSInputFile(
                file_path_output, "compressed_" + file_name_output_original_pdf
            )
        )
        logger.debug(
            "File " + file_path_output + " sent to user " + str(callback.from_user.id)
        )
        await callback.message.answer(i18n.get("Here is your PDF"), reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " to user "
            + str(callback.from_user.id)
        )
        await callback.message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.isfile(file_path_output):
        logger.debug("File " + file_path_output + " removed")
        os.remove(file_path_output)

    await state.clear()


@user_handlers_router.callback_query(
    StateFilter(DocumentWithoutCommand.selectOption),
    F.data.contains("rotate_file_first"),
)
async def rotate_file_first(callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("rotate_file_first")
    await state.set_state(RotateFileFirst.selectOption)

    await callback.message.answer(
        i18n.get("Select how you want to rotate your PDF"), reply_markup=ROTATE_KEYBOARD
    )
    await state.set_state(Rotate.selectOption)


@user_handlers_router.callback_query(
    StateFilter(DocumentWithoutCommand.selectOption),
    F.data.contains("merge_file_first"),
)
async def merge_file_first_input1(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext
) -> None:
    logger.info("merge_file_first_input1")
    await state.set_state(MergePDFFileFirst.input_file2)

    await callback.message.answer(i18n.get("Upload your second file"))
    await state.set_state(MergePDFFileFirst.process)


@user_handlers_router.message(StateFilter(MergePDFFileFirst.process), F.document)
async def merge_file_first_input2(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("merge_file_first_input2")
    data = await state.get_data()

    file_path_input1 = data["file_path_input"]
    original_file_name1 = data["original_file_name"]

    original_file_name2 = message.document.file_name
    file_id_telegram2 = message.document.file_id
    file_name_output_temp2 = os.path.splitext(original_file_name2)

    if file_name_output_temp2[1] != ".pdf":
        logger.info("File " + original_file_name2 + " is not a PDF")
        await message.answer(
            i18n.get("Your response is not a PDF document\nPlease upload a PDF document")
        )
        await state.set_state(MergePDFFileFirst.process)
        return

    await message.answer("Please wait")

    if message.document.file_size / (1024 * 1024) >= 20:
        logger.debug(original_file_name2 + " is more than 20MB")
        await message.answer(i18n.get("Your file exceeds 20 MB \n Please try a smaller file"))
        await state.set_state(MergePDFFileFirst.process)
        return

    file_path_input2 = await fileDownloader(file_id_telegram2, original_file_name2)

    if not (os.path.exists(file_path_input2)):
        logger.debug("Something went wrong with the file " + file_path_input2)
        await state.clear()
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    file_path_output = os.path.join(
        file_output_location, os.path.basename(file_path_input1)
    )

    merger_exit_code = await mergeTwoPDF(
        file_path_input1, file_path_input2, file_output_location
    )
    logger.debug("Merger result is: " + str(merger_exit_code))

    if os.path.exists(file_path_output):
        await message.reply_document(
            types.FSInputFile(file_path_output, "merged_" + original_file_name1)
        )
        logger.debug(
            "File " + file_path_output + " sent to user " + str(message.from_user.id)
        )
        await message.answer(i18n.get("Here is your PDF"), reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " to user "
            + str(message.from_user.id)
        )
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.isfile(file_path_output):
        logger.debug("File " + file_path_output + " removed")
        os.remove(file_path_output)

    await state.clear()


# This is a ToPDF command handler
@user_handlers_router.message(StateFilter(None), Command("topdf"))
@user_handlers_router.callback_query(F.data.contains("topdf"))
async def convert_to_pdf_callback(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext
) -> None:
    logger.info("convert_to_pdf_callback")
    await callback.answer(i18n.get("Convert to PDF"))
    await callback.message.answer(i18n.get("Upload your file"))
    await state.set_state(ToPDF.input)


@user_handlers_router.message(StateFilter(None), Command("compress"))
@user_handlers_router.callback_query(F.data.contains("compress"))
async def compress_pdf_callback(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext
) -> None:
    logger.info("compress_pdf_callback")
    await callback.answer(i18n.get("Compress PDF"))
    await callback.message.answer(i18n.get("Upload your file"))
    await state.set_state(CompressPDF.input)


@user_handlers_router.message(StateFilter(None), Command("rotate"))
@user_handlers_router.callback_query(F.data.contains("rotate"))
async def rotate_pdf_callback(callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("rotate_pdf_callback")
    await callback.answer(i18n.get("Rotate your PDF"))
    await callback.message.answer(i18n.get("Upload your file"))
    await state.set_state(Rotate.input)


@user_handlers_router.message(StateFilter(None), Command("merge"))
@user_handlers_router.callback_query(F.data.contains("merge"))
async def merge_pdf_callback(callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("merge_pdf_callback")
    await callback.answer(i18n.get("Merge your PDFs"))
    await callback.message.answer(i18n.get("Upload your first file"))
    await state.set_state(MergePDF.input_file1)


@user_handlers_router.message(StateFilter("*"), Command("cancel"))
@user_handlers_router.message(
    StateFilter("*"), or_f(F.data.contains("cancel"), F.text.casefold() == "cancel")
)
async def cancel_handler(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("cancel_handler from state " + str(state.get_state()))
    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer(
        i18n.get("Your actions were cancelled. Let's start it over"),
        reply_markup=INITIAL_KEYBOARD,
    )


# To PDF - User sent a proper document
@user_handlers_router.message(StateFilter(ToPDF.input), ToPDF.input, F.document)
async def to_pdf_input(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("to_pdf_input")
    original_file_name = message.document.file_name
    file_id_telegram = message.document.file_id
    file_name_output_temp = os.path.splitext(original_file_name)
    file_name_output_original_pdf = file_name_output_temp[0] + ".pdf"
    temp_file_name_with_id = file_id_telegram + "_" + file_name_output_temp[0] + ".pdf"

    if file_name_output_temp[1] not in SUPPORTED_FILES_LIST:
        logger.debug("Input file is not in the supported file types list")
        await message.answer(
            i18n.get("Your file is in an unsupported format \n Please try another file")
        )
        await state.set_state(ToPDF.input)
        return

    if file_name_output_temp[1] == ".pdf":
        logger.debug(original_file_name + " is already a PDF")
        await message.answer(
            i18n.get("Your file is already in PDF format \n Please try another file")
        )
        await state.set_state(ToPDF.input)
        return

    if message.document.file_size / (1024 * 1024) >= 20:
        logger.debug(original_file_name + " is more than 20MB")
        await message.answer(i18n.get("Your file exceeds 20 MB \n Please try a smaller file"))
        await state.set_state(ToPDF.input)
        return

    await message.answer(i18n.get("Please wait"))

    file_path_input = await fileDownloader(file_id_telegram, original_file_name)

    if not (os.path.exists(file_path_input)):
        logger.debug(
            "Something went wrong with the file "
            + file_path_input
            + " to user "
            + str(message.from_user.id)
        )
        await state.clear()
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    file_path_output = os.path.join(file_output_location, temp_file_name_with_id)

    converter_exit_code = await convertToPDF(file_path_input, file_output_location)
    logger.debug("Converter exit code is " + str(converter_exit_code))

    if converter_exit_code != 0:
        await state.clear()
        logger.debug("Converter exit code is: " + str(converter_exit_code))
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.exists(file_path_output):
        await message.reply_document(
            types.FSInputFile(
                file_path_output, "converted_" + file_name_output_original_pdf
            )
        )
        logger.debug(
            "File " + file_path_output + " sent to user " + str(message.from_user.id)
        )
        await message.answer(i18n.get("Here is your PDF"), reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " from the user "
            + str(message.from_user.id)
        )
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.isfile(file_path_output):
        logger.debug("File " + file_path_output + " removed")
        os.remove(file_path_output)

    await state.clear()


# To PDF - User sent an improper document
@user_handlers_router.message(StateFilter(ToPDF.input), ToPDF.input)
async def to_pdf_input_improper(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("to_pdf_input_improper")
    await message.answer(i18n.get("Your response is not a document \n Please upload a document"))
    return


# Compress - User sent a proper document
@user_handlers_router.message(
    StateFilter(CompressPDF.input), CompressPDF.input, F.document
)
async def compress_pdf_input(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("compress_pdf_input")
    original_file_name = message.document.file_name
    file_id_telegram = message.document.file_id
    file_name_output_temp = os.path.splitext(original_file_name)

    if file_name_output_temp[1] != ".pdf":
        logger.debug(original_file_name + " is already a PDF")
        await message.answer(
            i18n.get("Your response is not a PDF document\nPlease upload a PDF document")
        )
        await state.set_state(CompressPDF.input)
        return

    await message.answer(i18n.get("Please wait"))

    if message.document.file_size / (1024 * 1024) >= 20:
        logger.debug(original_file_name + " is more than 20MB")
        await message.answer(i18n.get("Your file exceeds 20 MB \n Please try a smaller file"))
        await state.set_state(CompressPDF.input)
        return

    file_path_input = await fileDownloader(file_id_telegram, original_file_name)
    logger.debug("Downloader result is " + file_path_input)

    if not (os.path.exists(file_path_input)):
        await state.clear()
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " from the user "
            + str(message.from_user.id)
        )
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    file_path_output = os.path.join(
        file_output_location, os.path.basename(file_path_input)
    )

    compressor_result = await compressPDF(file_path_input, file_output_location)
    logger.debug("Compressor result is " + compressor_result)

    if os.path.exists(file_path_output):
        await message.reply_document(
            types.FSInputFile(file_path_output, "compressed_" + original_file_name)
        )
        logger.debug(
            "File " + file_path_output + " sent to user " + str(message.from_user.id)
        )
        await message.answer(i18n.get("Here is your PDF"), reply_markup=INITIAL_KEYBOARD)
    else:
        await state.clear()
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " from the user "
            + str(message.from_user.id)
        )
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.isfile(file_path_output):
        logger.debug("File " + file_path_output + " removed")
        os.remove(file_path_output)

    await state.clear()


# Compress - User sent an improper document
@user_handlers_router.message(StateFilter(CompressPDF.input), CompressPDF.input)
async def compress_pdf_input_improper(
    message: types.Message, state: FSMContext, i18n: I18nContext
) -> None:
    logger.info("compress_pdf_input_improper")
    await message.answer(i18n.get("Your response is not a document \n Please upload a document"))
    return


# Rotate PDF - User sent a proper document
@user_handlers_router.message(StateFilter(Rotate.input), Rotate.input, F.document)
async def rotate_pdf_input(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("rotate_pdf_input")
    original_file_name = message.document.file_name
    file_id_telegram = message.document.file_id
    file_name_output_temp = os.path.splitext(original_file_name)

    if file_name_output_temp[1] != ".pdf":
        logger.info("File " + original_file_name + " is not a PDF")
        await message.answer(
            i18n.get("Your response is not a PDF document\nPlease upload a PDF document")
        )
        await state.set_state(Rotate.input)
        return

    await message.answer(i18n.get("Please wait"))

    if message.document.file_size / (1024 * 1024) >= 20:
        logger.debug(original_file_name + " is more than 20MB")
        await message.answer(i18n.get("Your file exceeds 20 MB \n Please try a smaller file"))
        await state.set_state(Rotate.input)
        return

    file_path_input = await fileDownloader(file_id_telegram, original_file_name)
    logger.debug("Downloader result is: " + str(file_path_input))

    if not (os.path.exists(file_path_input)):
        logger.debug(
            "Something went wrong with the file "
            + file_path_input
            + " to user "
            + str(message.from_user.id)
        )
        await state.clear()
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    await state.update_data(file_path_input=file_path_input)
    await state.update_data(original_file_name=original_file_name)

    await message.answer(
        i18n.get("Select how you want to rotate your PDF"), reply_markup=ROTATE_KEYBOARD
    )
    await state.set_state(Rotate.selectOption)


# Rotate PDF - User sent an improper document
@user_handlers_router.message(StateFilter(Rotate.input), Rotate.input)
async def rotate_pdf_input_improper(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("rotate_pdf_input_improper")
    await message.answer(
        i18n.get("Your response is not a PDF document\nPlease upload a PDF document")
    )
    return


@user_handlers_router.message(StateFilter(Rotate.selectOption), Command("right90"))
@user_handlers_router.callback_query(F.data.contains("right90"))
async def rotate_pdf_right90_callback(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext
) -> None:
    logger.info("rotate_pdf_right90_callback")
    data = await state.get_data()

    file_path_input = data["file_path_input"]
    original_file_name = data["original_file_name"]

    file_name_output_temp = os.path.splitext(original_file_name)

    if file_name_output_temp[1] != ".pdf":
        logger.info("File " + original_file_name + " is not a PDF")
        await data.answer(i18n.get("Your response is not a PDF document\nPlease upload a PDF document"))
        await state.set_state(Rotate.input)
        return

    file_path_output = os.path.join(
        file_output_location, os.path.basename(file_path_input)
    )

    rotator_result = await rotatePDF(file_path_input, file_output_location, 90)
    logger.debug("Rotator result is: " + str(rotator_result))

    if os.path.exists(file_path_output) and os.path.getsize(file_path_input) > 0:
        logger.debug(
            "File " + file_path_output + " sent to user " + str(callback.from_user.id)
        )
        await callback.message.reply_document(
            types.FSInputFile(file_path_output, "rotated_" + original_file_name)
        )
        await callback.message.reply("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
    else:
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " to user "
            + str(callback.from_user.id)
        )
        await state.clear()
        await callback.message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.isfile(file_path_output):
        logger.debug("File " + file_path_output + " removed")
        os.remove(file_path_output)

    await state.clear()


@user_handlers_router.message(StateFilter(Rotate.selectOption), Command("left90"))
@user_handlers_router.callback_query(F.data.contains("left90"))
async def rotate_pdf_left90_callback(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext
) -> None:
    logger.info("rotate_pdf_left90_callback")
    data = await state.get_data()

    file_path_input = data["file_path_input"]
    original_file_name = data["original_file_name"]

    file_name_output_temp = os.path.splitext(original_file_name)

    if file_name_output_temp[1] != ".pdf":
        logger.info("File " + original_file_name + " is not a PDF")
        await data.answer(i18n.get("Your response is not a PDF document\nPlease upload a PDF document"))
        await state.set_state(Rotate.input)
        return

    file_path_output = os.path.join(
        file_output_location, os.path.basename(file_path_input)
    )

    rotator_result = await rotatePDF(file_path_input, file_output_location, 270)
    logger.debug("Rotator result is: " + str(rotator_result))

    if os.path.exists(file_path_output) and os.path.getsize(file_path_input) > 0:
        logger.debug(
            "File " + file_path_output + " sent to user " + str(callback.from_user.id)
        )
        await callback.message.reply_document(
            types.FSInputFile(file_path_output, "rotated_" + original_file_name)
        )
        await callback.message.reply("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
    else:
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " to user "
            + str(callback.from_user.id)
        )
        await state.clear()
        await callback.message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.isfile(file_path_output):
        logger.debug("File " + file_path_output + " removed")
        os.remove(file_path_output)

    await state.clear()


@user_handlers_router.message(StateFilter(Rotate.selectOption), Command("right180"))
@user_handlers_router.callback_query(F.data.contains("right180"))
async def rotate_pdf_right180_callback(
    callback: types.CallbackQuery, state: FSMContext, i18n: I18nContext
) -> None:
    logger.info("rotate_pdf_right180_callback")
    data = await state.get_data()

    file_path_input = data["file_path_input"]
    original_file_name = data["original_file_name"]

    file_name_output_temp = os.path.splitext(original_file_name)

    if file_name_output_temp[1] != ".pdf":
        logger.info("File " + original_file_name + " is not a PDF")
        await data.answer(i18n.get("Your response is not a PDF document\nPlease upload a PDF document"))
        await state.set_state(Rotate.input)
        return

    file_path_output = os.path.join(
        file_output_location, os.path.basename(file_path_input)
    )

    rotator_result = await rotatePDF(file_path_input, file_output_location, 180)
    logger.debug("Rotator result is: " + str(rotator_result))

    if os.path.exists(file_path_output) and os.path.getsize(file_path_input) > 0:
        logger.debug(
            "File " + file_path_output + " sent to user " + str(callback.from_user.id)
        )
        await callback.message.reply_document(
            types.FSInputFile(file_path_output, "rotated_" + original_file_name)
        )
        await callback.message.reply("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
    else:
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " to user "
            + str(callback.from_user.id)
        )
        await state.clear()
        await callback.message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.isfile(file_path_output):
        logger.debug("File " + file_path_output + " removed")
        os.remove(file_path_output)

    await state.clear()


@user_handlers_router.message(StateFilter(Rotate.selectOption), Rotate.selectOption)
async def rotate_pdf_option(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("rotate_pdf_option")
    await message.answer(
        i18n.get("Something went wrong \n Please try again"), reply_markup=ROTATE_KEYBOARD
    )
    return


# Merge PDF - Input1 - User sent a proper document
@user_handlers_router.message(
    StateFilter(MergePDF.input_file1), MergePDF.input_file1, F.document
)
async def merge_pdf_input1(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("merge_pdf_input1")
    original_file_name = message.document.file_name
    file_id_telegram = message.document.file_id
    file_name_output_temp = os.path.splitext(original_file_name)

    if file_name_output_temp[1] != ".pdf":
        logger.info("File " + original_file_name + " is not a PDF")
        await message.answer(
            i18n.get("Your response is not a PDF document\nPlease upload a PDF document")
        )
        await state.set_state(MergePDF.input_file1)
        return

    if message.document.file_size / (1024 * 1024) >= 20:
        logger.debug(original_file_name + " is more than 20MB")
        await message.answer(i18n.get("Your file exceeds 20 MB \n Please try a smaller file"))
        await state.set_state(MergePDF.input_file1)
        return

    file_path_input = await fileDownloader(file_id_telegram, original_file_name)
    logger.debug("Downloader result is: " + str(file_path_input))

    if not (os.path.exists(file_path_input)):
        logger.debug("Something went wrong with the file " + file_path_input)
        await state.clear()
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    await state.update_data(file_path_input1=file_path_input)
    await state.update_data(original_file_name1=original_file_name)
    await message.answer(i18n.get("Upload your second file"))
    await state.set_state(MergePDF.input_file2)


# Merge PDF - Input1 - User sent an improper document
@user_handlers_router.message(StateFilter(MergePDF.input_file1), MergePDF.input_file1)
async def merge_pdf_input1_improper(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("merge_pdf_Input1_Improper")
    await message.answer(
        i18n.get("Your response is not a PDF document\nPlease upload a PDF document")
    )
    return


# Merge PDF - Input2 - User sent a proper document
@user_handlers_router.message(
    StateFilter(MergePDF.input_file2), MergePDF.input_file2, F.document
)
async def merge_pdf_input2(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("merge_pdf_input2")
    data = await state.get_data()

    file_path_input1 = data["file_path_input1"]
    original_file_name1 = data["original_file_name1"]

    original_file_name2 = message.document.file_name
    file_id_telegram2 = message.document.file_id
    file_name_output_temp2 = os.path.splitext(original_file_name2)

    if file_name_output_temp2[1] != ".pdf":
        logger.info("File " + original_file_name2 + " is not a PDF")
        await message.answer(
            i18n.get("Your response is not a PDF document\nPlease upload a PDF document")
        )
        await state.set_state(MergePDF.input_file2)
        return

    await message.answer(i18n.get("Please wait"))

    if message.document.file_size / (1024 * 1024) >= 20:
        logger.debug(original_file_name2 + " is more than 20MB")
        await message.answer(i18n.get("Your file exceeds 20 MB \n Please try a smaller file"))
        await state.set_state(MergePDF.input_file2)
        return

    file_path_input2 = await fileDownloader(file_id_telegram2, original_file_name2)
    logger.debug("Downloader result is: " + str(file_path_input2))

    if not (os.path.exists(file_path_input2)):
        logger.debug("Something went wrong with the file " + file_path_output)
        await state.clear()
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    file_path_output = os.path.join(
        file_output_location, os.path.basename(file_path_input1)
    )

    merger_exit_code = await mergeTwoPDF(
        file_path_input1, file_path_input2, file_output_location
    )
    logger.debug("Merger result is: " + str(merger_exit_code))

    if os.path.exists(file_path_output):
        logger.debug(
            "File " + file_path_output + " sent to user " + str(message.from_user.id)
        )
        await message.reply_document(
            types.FSInputFile(file_path_output, "merged_" + original_file_name1)
        )
        await message.answer(i18n.get("Here is your PDF"), reply_markup=INITIAL_KEYBOARD)
    else:
        logger.debug(
            "Something went wrong with the file "
            + file_path_output
            + " to user "
            + str(message.from_user.id)
        )
        await state.clear()
        await message.answer(
            i18n.get("Something went wrong \n Please try again"), reply_markup=INITIAL_KEYBOARD
        )
        return

    if os.path.isfile(file_path_output):
        logger.debug("File " + file_path_output + " removed")
        os.remove(file_path_output)

    await state.clear()


# Merge PDF - Input2 - User sent an improper document
@user_handlers_router.message(StateFilter(MergePDF.input_file2), MergePDF.input_file2)
async def merge_pdf_input2_improper(message: types.Message, state: FSMContext, i18n: I18nContext) -> None:
    logger.info("merge_pdf_input2_Improper")
    await message.answer(
        i18n.get("Your response is not a PDF document \n Please upload a PDF document")
    )
    return
