import asyncio
import logging
import re
import mysql.connector
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

API_TOKEN = '6878895871:AAH32aBrhA7RyIddgKBVTtbA3QVSstaNo7s'

logging.basicConfig(level=logging.INFO)

button1 = KeyboardButton(text='Get all contacts')
button2 = KeyboardButton(text='Upload videos')
markup = ReplyKeyboardMarkup(
    keyboard=[
        [button1, button2]
    ],
    resize_keyboard=True,
)

class Form(StatesGroup):
    waiting_for_video_links = State()

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

db_config = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
    'database': 'telegram_bot'
}

def create_connection():
    return mysql.connector.connect(**db_config)

def is_valid_url(url):
    regex = re.compile(
        r'^(?:http|ftp)s?://' # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' # domain...
        r'localhost|' # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}|' # ...or ipv4
        r'\[?[A-F0-9]*:[A-F0-9:]+\]?)' # ...or ipv6
        r'(?::\d+)?' # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(regex, url) is not None

async def admin():
    await dp.start_polling(bot)

@dp.message(CommandStart())
async def send_welcome(message: types.Message, state: FSMContext):
    await message.answer("Welcome! Please choose an option:", reply_markup=markup)

@dp.message(lambda message: message.text == 'Get all contacts' or message.text == 'Refresh Contacts')
async def get_all_contacts(message: types.Message):
    conn = create_connection()
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

@dp.message(lambda message: message.text == 'Upload videos')
async def upload_videos(message: types.Message, state: FSMContext):
    await state.set_state(Form.waiting_for_video_links)
    await message.answer("Please input the video links, each on a new line:")

@dp.message(Form.waiting_for_video_links)
async def process_video_links(message: types.Message, state: FSMContext):
    video_links = message.text.split('\n')
    conn = create_connection()
    cursor = conn.cursor()
    valid_links = []
    for link in video_links:
        if is_valid_url(link.strip()):
            valid_links.append(link.strip())
            await message.answer("✅ Video links successfully added!")
        else:
            await message.answer(f"❌ Invalid URL: {link.strip()}")
    for link in valid_links:
        cursor.execute("INSERT INTO videos (link) VALUES (%s)", (link,))
    conn.commit()
    cursor.close()
    conn.close()
    await state.clear()

if __name__ == "__main__":
    asyncio.run(admin())
