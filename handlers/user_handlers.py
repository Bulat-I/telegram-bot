import asyncio
from aiogram import F, types, Router, methods
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from filters.chat_types import ChatTypeFilter
from keyboards.inline_keyboard import build_inline_callback_keyboard
from workload_handlers.pdf_compressor import compressPDF
from workload_handlers.file_downloader import fileDownloader

user_handlers_router = Router()
user_handlers_router.message.filter(ChatTypeFilter(['private']))

INITIAL_KEYBOARD = build_inline_callback_keyboard(
            buttons={
                "Convert to PDF":f"topdf",
                "Compress PDF file":f"compress"
            }
)

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
        'Hi, I am a PDF converter assistant',
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
    await message.answer("Please wait")
    asyncio.sleep(1000)

    await message.answer("Here is your PDF", reply_markup=INITIAL_KEYBOARD)
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
    await message.answer("Please wait")
    file_name_telegram = message.document.file_name
    file_path_local = await fileDownloader(message)
    
    exit_code = await compressPDF(file_name_telegram, "/var/lib/telegram-bot/input", "/var/lib/telegram-bot/output")
    print(exit_code)
    print(file_path_local)
    
    await message.reply_document(types.FSInputFile(file_path_local))
    await message.answer("Here is your PDF", reply_markup=INITIAL_KEYBOARD)

    await state.clear()


#Compress - User sent an improper document
@user_handlers_router.message(CompressPDF.input)
async def compresspdf_Input(message: types.Message, state: FSMContext):
            
    await message.answer("Your response is not a document \n Please upload a document")
    return