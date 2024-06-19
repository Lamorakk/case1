import asyncio
import logging
import random
import string
import os

import MySQLdb
import mysql.connector
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage

API_TOKEN = '7281966099:AAH9B-noKRMmQ-lE3xrFMNajIuQgN2FqmoI'
logging.basicConfig(level=logging.INFO)

button1 = KeyboardButton(text='Main Menu')
button2 = KeyboardButton(text='View Balance')
markup = ReplyKeyboardMarkup(
    keyboard=[
        [button1],
        [button2]
    ],
    resize_keyboard=True,
)

class Form(StatesGroup):
    waiting_for_phone = State()
    waiting_for_action = State()
    waiting_for_password = State()
    waiting_for_video_links = State()
    waiting_for_confirmation = State()
    waiting_for_verification = State()

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

db_config = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
    'database': 'telegram_bot'
}
conn = MySQLdb.connect(**db_config)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS contacts (
    user_id BIGINT PRIMARY KEY,
    phone VARCHAR(15),
    unique_code VARCHAR(7),
    balance DECIMAL(10, 2) DEFAULT 0,
    current_video INT DEFAULT 0
)
''')
cursor.execute('''
CREATE TABLE IF NOT EXISTS video_views (
    user_id BIGINT,
    video_id INT,
    PRIMARY KEY (user_id, video_id)
)
''')
conn.commit()

def get_next_video(user_id):
    video_folder = 'videos'
    watched_videos = set()
    cursor.execute("SELECT video_id FROM video_views WHERE user_id = %s", (user_id,))
    for (video_id,) in cursor.fetchall():
        watched_videos.add(video_id)

    video_files = [f for f in os.listdir(video_folder) if os.path.isfile(os.path.join(video_folder, f))]
    for video_id, video_file in enumerate(video_files):
        if video_id not in watched_videos:
            return video_id, os.path.join(video_folder, video_file)
    return None, None

def generate_unique_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=7))

@dp.message(CommandStart())
async def send_welcome(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "User"
    last_name = message.from_user.last_name or ""

    cursor.execute("SELECT balance FROM contacts WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    if user is None:
        await state.set_state(Form.waiting_for_phone)
        keyboard = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="Share phone number", request_contact=True)],
            ],
            resize_keyboard=True
        )
        await message.answer(
            f"Hi dear {first_name} {last_name},\n"
            "🌟 This is bot where you can earn money by watching our partners` videos 🌟\n"
            "Ready to start earning? To register enter your phone number 🚀",
            reply_markup=keyboard
        )
    else:
        balance = user[0]
        await message.answer(f"👋 Welcome back! Your current balance is {balance} $.", reply_markup=markup)
        await display_main_menu(message, user_id)

async def display_main_menu(message, user_id):
    next_video_id, next_video_path = get_next_video(user_id)
    keyboard1 = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Video viewing", callback_data="channel"),
            InlineKeyboardButton(text="Cash withdrawal $", callback_data="withdraw")
        ]
    ])

    if next_video_path:
        await message.answer("📺 Watch a video to start earning money!", reply_markup=keyboard1)
    else:
        await message.answer("🚫 No more videos available right now. Please check back later for more earning opportunities!", reply_markup=keyboard1)

unique_code = generate_unique_code()

@dp.message(Form.waiting_for_phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    contact = message.contact.phone_number
    user_id = message.from_user.id

    cursor.execute("INSERT INTO contacts (user_id, phone, unique_code) VALUES (%s, %s, %s)",
                   (user_id, contact, generate_unique_code()))
    conn.commit()

    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

    await state.set_state(Form.waiting_for_action)
    await message.answer("🎉 Registration was successful!", reply_markup=markup)

    await display_main_menu(message, user_id)

@dp.message(F.text == 'Main Menu')
async def main_menu_handler(message: types.Message):
    user_id = message.from_user.id
    await display_main_menu(message, user_id)

@dp.message(F.text == 'View Balance')
async def view_balance_handler(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM contacts WHERE user_id = %s", (user_id,))
    balance = cursor.fetchone()[0]
    await message.answer(f"💰 Your current balance is {balance} $.", reply_markup=markup)

@dp.callback_query(F.data == "next_video")
async def process_next_video(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cursor.execute("UPDATE contacts SET current_video = current_video + 1 WHERE user_id = %s", (user_id,))
    conn.commit()
    await display_main_menu(callback_query.message, user_id)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await callback_query.answer()

@dp.callback_query(F.data == "channel")
async def channel(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    next_video_id, next_video_path = get_next_video(user_id)
    cursor.execute("SELECT balance FROM contacts WHERE user_id = %s", (user_id,))
    balance = cursor.fetchone()[0]
    if not next_video_path:
        await callback_query.message.answer(
            "🚫 Videos are over, expect more videos soon!",
            reply_markup=markup
        )
        await callback_query.message.answer(
            f"👀 Your current balance is {balance} $. You can withdraw your money!"
        )
        return
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await callback_query.message.answer(
        f"👀 Your current balance is {balance} $. Watch the video below to proceed."
    )

    await bot.send_video(chat_id=callback_query.message.chat.id, video=FSInputFile(next_video_path))
    await asyncio.sleep(7)
    await state.update_data(current_video=next_video_id)
    await confirm_video(callback_query, state)

async def confirm_video(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    data = await state.get_data()
    current_video = data.get('current_video')
    if current_video is None:
        await callback_query.message.answer("⚠️ Error: No video to confirm. Please try again.")
        return

    cursor.execute("SELECT COUNT(*) FROM video_views WHERE user_id = %s AND video_id = %s", (user_id, current_video))
    already_earned = cursor.fetchone()[0] > 0

    if not already_earned:
        try:
            cursor.execute("INSERT INTO video_views (user_id, video_id) VALUES (%s, %s)", (user_id, current_video))
            cursor.execute("UPDATE contacts SET balance = balance + 0.5 WHERE user_id = %s", (user_id,))
            conn.commit()
            await state.update_data(current_video=None)
            await state.set_state(Form.waiting_for_action)
            await callback_query.message.answer("🎉 Congratulations! You've earned 0.50 $!",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Next Video", callback_data="next_video")],
                ])
            )
        except mysql.connector.Error as err:
            logging.error(f"Database error: {err}")
            await callback_query.message.answer("⚠️ An error occurred while processing your request. Please try again later.")
    else:
        await callback_query.message.answer("✔️ You've already earned money for watching this video.")

@dp.callback_query(F.data == "withdraw")
async def process_withdraw(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    cursor.execute("SELECT balance FROM contacts WHERE user_id = %s", (user_id,))
    balance = cursor.fetchone()[0]

    if balance >= 20:
        await state.set_state(Form.waiting_for_verification)

        link = "https://t.me/vasel_dovg"
        keyboarder = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Verification", url=link)],
        ])
        await callback_query.message.answer("🔒 Withdrawals are available only for verified users.", reply_markup=keyboarder)
    else:
        await callback_query.answer(f"🚀 Withdrawal is available when balance more than 20.00$, current: {balance}", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
