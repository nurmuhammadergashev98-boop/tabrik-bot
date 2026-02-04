import logging
import asyncio
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram_calendar import SimpleCalendar, SimpleCalendarCallback
import google.generativeai as genai

# --- 1. SOZLAMALAR ---
API_TOKEN = '7216327008:AAHODKTaw61YJwUn0jwWO1D-_mBkMkrRGoA' # O'zingizning to'liq tokeningizni qo'ying
GEMINI_KEY = 'AIzaSyBIaB9RKMU50aBn26sbgiA33aJuQyhRJiI'

# AI ni sozlash
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# --- 2. BAZA (GROUP_ID QO'SHILDI) ---
conn = sqlite3.connect('birthdays.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER, chat_id INTEGER, full_name TEXT, bday TEXT)''')
# Agar jadval bo'lsa, chat_id ustuni borligiga ishonch hosil qilamiz
conn.commit()

# --- 3. KOMANDALAR ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="📅 Tug'ilgan kunimni qo'shish", callback_data="add_bday"))
    await message.answer(f"Salom! Tug'ilgan kuningizni saqlash uchun pastdagi tugmani bosing.", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "add_bday")
async def show_calendar(callback: types.CallbackQuery):
    await callback.message.answer("Tug'ilgan kuningizni tanlang:", reply_markup=await SimpleCalendar().start_calendar())

@dp.callback_query(SimpleCalendarCallback.filter())
async def process_calendar(callback: types.CallbackQuery, callback_data: SimpleCalendarCallback):
    calendar = SimpleCalendar()
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected:
        bday_str = date.strftime("%d.%m")
        u_id = callback.from_user.id
        c_id = callback.message.chat.id # Guruhning ID-si saqlanadi
        name = callback.from_user.full_name
        
        # Eskisini o'chirib yangisini yozish
        cursor.execute("DELETE FROM users WHERE user_id = ? AND chat_id = ?", (u_id, c_id))
        cursor.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (u_id, c_id, name, bday_str))
        conn.commit()
        await callback.message.answer(f"✅ {name}, ushbu guruh uchun tug'ilgan kuningiz {bday_str} deb saqlandi!")

# --- 4. AVTOMATIK TABRIKLASH (HAR BIR GURUHGA ALOHIDA) ---
async def send_daily_congrats():
    while True:
        now = datetime.now()
        # Soat 09:00 da tekshirish
        if now.hour == 9 and now.minute == 0: 
            today = now.strftime("%d.%m")
            cursor.execute("SELECT full_name, chat_id FROM users WHERE bday = ?", (today,))
            winners = cursor.fetchall()
            
            for name, chat_id in winners:
                try:
                    prompt = f"{name} ismli insonni tug'ilgan kuni bilan o'zbekcha juda chiroyli tabriklab ber."
                    response = model.generate_content(prompt)
                    
                    if response and response.text:
                        txt = response.text
                    else:
                        txt = f"Bugun {name}ning tug'ilgan kuni! 🎉"
                    
                    # Xabar aynan o'sha guruhga boradi
                    await bot.send_message(chat_id, f"🎊 DIQQAT! 🎊\n\n{txt}")
                    await asyncio.sleep(2) # Telegram limitidan oshib ketmaslik uchun
                except Exception as e:
                    logging.error(f"Xato: {e}")
            
            await asyncio.sleep(60)
        await asyncio.sleep(30)

# --- 5. ISHGA TUSHIRISH ---
async def main():
    asyncio.create_task(send_daily_congrats())
    print("Bot universal rejimda ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi")