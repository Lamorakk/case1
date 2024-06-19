import asyncio
import logging
import MySQLdb
import mysql.connector
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


API_TOKEN = '6878895871:AAH32aBrhA7RyIddgKBVTtbA3QVSstaNo7s'
ACTIVATION_COMMAND = "/buewuofcwbcfhpoqwbp"
CORRECT_PASSWORD = "kdwcjnpocwcwo"

logging.basicConfig(level=logging.INFO)

button1 = KeyboardButton(text='Get all contacts')
markup = ReplyKeyboardMarkup(
    keyboard=[
        [button1]
    ],
    resize_keyboard=True,
)

class AuthorizationState(StatesGroup):
    waiting_for_password = State()

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

db_config = {
    'user': 'videobot',
    'password': 'nuxbu2-hudhyp-vymGuq',
    'host': '77.37.49.219',
    'database': 'videobotdb'
}
async def admin():
    await dp.start_polling(bot)

@dp.message(Command(commands=[ACTIVATION_COMMAND[1:]]))
async def activate_command(message: types.Message, state: FSMContext):
    await message.answer("Please enter the password to access the bot:")
    await state.set_state(AuthorizationState.waiting_for_password)

@dp.message(AuthorizationState.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    if message.text == CORRECT_PASSWORD:
        await message.answer("Access granted! Please choose an option:", reply_markup=markup)
        await state.clear()
    else:
        await message.answer("Incorrect password. Try again or contact the administrator.")

@dp.message(lambda message: message.text in ['Get all contacts', 'Refresh Contacts'])
async def get_all_contacts(message: types.Message, state: FSMContext):
    if await state.get_state() is None:
        conn = MySQLdb.connect(**db_config)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, phone FROM contacts")
        contacts = cursor.fetchall()
        cursor.close()
        conn.close()

        if contacts:
            contact_list = "📇 All Contacts:\n"
            for contact in contacts:
                user_id, phone = contact
                contact_list += (
                    f"👤 User ID: {user_id}\n"
                    f"📞 Phone: {phone}\n"
                    f"\n"
                )
            await message.answer(contact_list)
        else:
            await message.answer("No contacts found in the database.")
    else:
        await message.answer("You are not authorized to use this command.")
if __name__ == "__main__":
    asyncio.run(admin())
