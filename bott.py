import logging
import asyncio
from datetime import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram_calendar import dialog_cal_callback, DialogCalendar
import google.generativeai as genai
from pymongo import MongoClient

# --- KONFIGURATSIYA ---
API_TOKEN = '7216327008:AAHGw9r0p8m6m48pI6N7K0-S7hT7eX_T5c' # Tokeningiz
genai.configure(api_key="AIzaSyBIaB9RKMU50aBn26sbgiA33aJuQyhRJiI") # Gemini keyni qo'ying
MONGO_URL = "mongodb+srv://nurmuhammadergashev98_db_user:Xo4SsKMAzKPfgNuP@cluster0.4ren87b.mongodb.net/?retryWrites=true&w=majority"

# MongoDB ulanishi
client = MongoClient(MONGO_URL)
db = client['tabrik_bot_db']
collection = db['users']

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# --- FUNKSIYALAR ---
def save_birthday(user_id, username, chat_id, date_str):
    collection.update_one(
        {"user_id": user_id, "chat_id": chat_id},
        {"$set": {"username": username, "birthday": date_str}},
        upsert=True
    )

async def check_birthdays():
    while True:
        today = datetime.now().strftime("%d-%m")
        users = collection.find({"birthday": {"$regex": f"^{today}"}})
        
        for user in users:
            model = genai.GenerativeModel('gemini-pro')
            prompt = f"{user['username']} ismli do'stimizning tug'ilgan kuni. Uni samimiy va hazil aralash tabriklab bering."
            response = model.generate_content(prompt)
            await bot.send_message(user['chat_id'], f"🎉 {response.text}")
        
        await asyncio.sleep(86400) # Bir kunda bir marta tekshiradi

# --- HANDLERLAR ---
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        f"Salom {message.from_user.full_name}! Tug'ilgan kuningizni saqlash uchun quyidagi tugmani bosing:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("Sana tanlash", callback_data="set_birthday")
        )
    )

@dp.callback_query_handler(lambda c: c.data == "set_birthday")
async def process_callback_calendar(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(
        callback_query.from_user.id,
        "Tug'ilgan kuningizni tanlang:",
        reply_markup=await DialogCalendar().start_calendar()
    )

@dp.callback_query_handler(dialog_cal_callback.filter())
async def process_dialog_calendar(callback_query: types.CallbackQuery, callback_data: dict):
    selected, date = await DialogCalendar().process_selection(callback_query, callback_data)
    if selected:
        date_str = date.strftime("%d-%m-%Y")
        save_birthday(
            callback_query.from_user.id,
            callback_query.from_user.full_name,
            callback_query.message.chat.id,
            date_str
        )
        await bot.send_message(callback_query.from_user.id, f"Sana saqlandi: {date_str} ✅")

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.create_task(check_birthdays())
    executor.start_polling(dp, skip_updates=True)