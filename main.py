import asyncio
import logging
import random
import string
import mysql.connector
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage

API_TOKEN = '6734266029:AAH5k-aomS9Tzuzti1MPOJYhl_H4nbQee_k'
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

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

db_config = {
    'user': 'root',
    'password': 'root',
    'host': '127.0.0.1',
    'database': 'telegram_bot'
}
conn = mysql.connector.connect(**db_config)
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
CREATE TABLE IF NOT EXISTS videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    link VARCHAR(255) NOT NULL
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
    cursor.execute("""
        SELECT videos.link 
        FROM videos 
        LEFT JOIN video_views ON videos.id = video_views.video_id AND video_views.user_id = %s
        WHERE video_views.user_id IS NULL
        ORDER BY videos.id ASC
        LIMIT 1
    """, (user_id,))
    result = cursor.fetchone()
    return result[0] if result else None

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
                [KeyboardButton(text="Share Phone Number", request_contact=True)],
            ],
            resize_keyboard=True
        )
        await message.answer(
            f"Greetings {first_name} {last_name},\n"
            "🌟 Welcome to Our Platform! 🌟\n"
            "🤑 Earn money just by watching YouTube videos! 🤑\n\n"
            "👉 How to Start:\n"
            "    1. Sign Up: Authorize with your phone number.\n"
            "    2. Watch Videos: Browse and watch from our wide selection.\n"
            "    3. Earn Money: Convert your watch time into real cash!\n\n"
            "🔑 Get Started:\n"
            "    1. Authorize your phone number.\n"
            "    2. Start watching videos immediately.\n"
            "    3. Track and withdraw your earnings through various payment methods.\n\n"
            "💡 Why Choose Us?\n"
            "    - Easy to Use: Simple and intuitive interface.\n"
            "    - Secure and Private: Your data and earnings are safe.\n"
            "    - Flexible: Watch videos anytime, anywhere.\n\n"
            "Ready to start earning? Authorize now and dive into the world of paid video watching! 🚀",
            reply_markup=keyboard
        )
    else:
        balance = user[0]
        await message.answer(f"👋 Welcome back! Your current balance is {balance} $.", reply_markup=markup)
        await display_main_menu(message, user_id)

async def display_main_menu(message, user_id):
    next_video_url = get_next_video(user_id)
    keyboard1 = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Watch Video", callback_data="channel"),
            InlineKeyboardButton(text="Withdraw $", callback_data="withdraw")
        ]
    ])

    if next_video_url:
        await message.answer("📺 Watch a video to start earning money!", reply_markup=keyboard1)
    else:
        await message.answer("🚫 No more videos available right now. Please check back later for more earning opportunities!", reply_markup=keyboard1)

unique_code = generate_unique_code()

@dp.message(Form.waiting_for_phone, F.contact)
async def process_phone(message: types.Message, state: FSMContext):
    contact = message.contact.phone_number
    user_id = message.from_user.id

    cursor.execute("INSERT INTO contacts (user_id, phone, unique_code) VALUES (%s, %s, %s)",
                   (user_id, contact, unique_code))
    conn.commit()

    await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)

    await state.set_state(Form.waiting_for_action)
    await message.answer("🎉 Your account has been successfully registered!", reply_markup=markup)

    await display_main_menu(message, user_id)

@dp.message(lambda message: message.text == 'Main Menu')
async def main_menu_handler(message: types.Message):
    user_id = message.from_user.id
    await display_main_menu(message, user_id)

@dp.message(lambda message: message.text == 'View Balance')
async def view_balance_handler(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT balance FROM contacts WHERE user_id = %s", (user_id,))
    balance = cursor.fetchone()[0]
    await message.answer(f"💰 Your current balance is {balance} $.", reply_markup=markup)

@dp.callback_query(lambda callback_query: callback_query.data == "next_video")
async def process_next_video(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cursor.execute("UPDATE contacts SET current_video = current_video + 1 WHERE user_id = %s", (user_id,))
    conn.commit()

    await display_main_menu(callback_query.message, user_id)
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    await callback_query.answer()

@dp.callback_query(lambda callback_query: callback_query.data == "channel")
async def channel(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    next_video_url = get_next_video(user_id)

    if not next_video_url:
        await callback_query.message.answer(
            "🚫 No more videos available right now. Please check back later for more earning opportunities!",
            reply_markup=markup
        )
        return

    cursor.execute("SELECT current_video FROM contacts WHERE user_id = %s", (user_id,))
    current_video = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM video_views WHERE user_id = %s AND video_id = %s", (user_id, current_video))
    already_earned = cursor.fetchone()[0] > 0

    if not already_earned:
        await callback_query.message.answer(
            "👀 Watch the video below to proceed.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Video", url=next_video_url)]
            ]))
        await asyncio.sleep(5)
        await state.update_data(current_video=current_video)  # Track the current video being watched
        await state.set_state(Form.waiting_for_confirmation)
        await callback_query.message.answer(
            "✅ Press the button below to confirm you've watched the video and claim your earnings!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Confirm", callback_data="confirm_video")]
            ])
        )
    else:
        await process_next_video(callback_query)

@dp.callback_query(lambda callback_query: callback_query.data == "confirm_video")
async def confirm_video(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)

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
            await state.update_data(current_video=None)  # Reset current video
            await state.set_state(Form.waiting_for_action)  # Reset state
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

    await callback_query.answer("🔄 Your balance has been updated!", show_alert=True)

@dp.callback_query(F.data == "withdraw")
async def process_withdraw(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    cursor.execute("SELECT balance FROM contacts WHERE user_id = %s", (user_id,))
    balance = cursor.fetchone()[0]

    if balance >= 2:
        await bot.send_message(callback_query.message.chat.id,
                               f"💸 To withdraw your earnings, please complete verification. Contact our manager @manager and provide your unique code: {generate_unique_code()}.")
        await callback_query.answer("🔒 Withdrawals are available only for verified users.", show_alert=True)
    else:
        await callback_query.answer(f"🚀 Keep earning to reach the withdrawal threshold! {balance}/20.00$6", show_alert=True)

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
