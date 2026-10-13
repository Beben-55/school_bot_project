from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime
import logging

from database import db
from config import settings
from schedule import ScheduleManager

logger = logging.getLogger(name)
router = Router()
scheduler = ScheduleManager(settings.SCHEDULE_FILE)

# Список доступных дней для валидации ввода
VALID_DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

# Обновленное главное меню: теперь здесь 4 кнопки
def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Что сейчас?"), KeyboardButton(text="Расписание на сегодня")],
        [KeyboardButton(text="Расписание на день"), KeyboardButton(text="Сменить класс")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_classes_keyboard() -> ReplyKeyboardMarkup:
    classes = scheduler.get_all_classes()
    if not classes:
        return ReplyKeyboardRemove()
    
    buttons = [KeyboardButton(text=c) for c in classes]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)

# Инлайн-подсказки с днями недели (без кнопки "Сегодня", так как для нее теперь есть отдельная кнопка в меню)
def get_days_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [
            InlineKeyboardButton(text="Понедельник", callback_data="day_Понедельник"),
            InlineKeyboardButton(text="Вторник", callback_data="day_Вторник")
        ],
        [
            InlineKeyboardButton(text="Среда", callback_data="day_Среда"),
            InlineKeyboardButton(text="Четверг", callback_data="day_Четверг")
        ],
        [
            InlineKeyboardButton(text="Пятница", callback_data="day_Пятница"),
            InlineKeyboardButton(text="Суббота", callback_data="day_Суббота")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот-расписание. Для начала работы выбери свой класс:",
        reply_markup=get_classes_keyboard()
    )

@router.message(F.text == "Сменить класс")
async def change_class(message: Message):
    await message.answer("Выбери класс из списка:", reply_markup=get_classes_keyboard())

@router.message(F.text == "Что сейчас?")
async def what_is_now(message: Message):
    user_class = await db.get_user_class(message.from_user.id)
    if not user_class:
        return await message.answer("Сначала выберите ваш класс!", reply_markup=get_classes_keyboard())
    
    now = datetime.now()
    current_day = scheduler.days_mapping.get(now.weekday(), "Воскресенье")
    current_time = now.time()

    current_lesson, next_lesson = scheduler.get_lessons_for_time(user_class, current_day, current_time)

    response = f"🏫 Класс: {user_class}\n🕒 Время: {current_time.strftime('%H:%M')} ({current_day})\n\n"
    
    if current_lesson:
        response += f"📖 Сейчас идет: {current_lesson}\n"
    else:
        response += "📖 Сейчас идет: Перемена или уроков в это время нет\n"
        
    if next_lesson:
        response += f"➡️ Следующий урок: {next_lesson}"
    else:
        response += "➡️ Следующий урок: Больше уроков сегодня не будет!"
        
    await message.answer(response, parse_mode="Markdown")

# Кнопка 1: Сразу выводит расписание на текущий день без лишних вопросов
@router.message(F.text == "Расписание на сегодня")
async def day_schedule_today(message: Message):
    user_class = await db.get_user_class(message.from_user.id)
    if not user_class:return await message.answer("Сначала выберите ваш класс!", reply_markup=get_classes_keyboard())
    
    now = datetime.now()
    current_day = scheduler.days_mapping.get(now.weekday(), "Воскресенье")
    
    text = scheduler.get_full_day_schedule(user_class, current_day)
    await message.answer(text)

# Кнопка 2: Новая отдельная кнопка, которая предлагает выбрать конкретный день
@router.message(F.text == "Расписание на день")
async def day_schedule_prompt(message: Message):
    user_class = await db.get_user_class(message.from_user.id)
    if not user_class:
        return await message.answer("Сначала выберите ваш класс!", reply_markup=get_classes_keyboard())
    
    await message.answer(
        "Выберите интересующий день недели:",
        reply_markup=get_days_inline_keyboard()
    )

# Обработка кликов по инлайн-подсказкам дней недели
@router.callback_query(F.data.startswith("day_"))
async def process_day_callback(callback: CallbackQuery):
    user_class = await db.get_user_class(callback.from_user.id)
    if not user_class:
        await callback.answer("Ошибка: Класс не выбран. Нажмите /start", show_alert=True)
        return

    # Получаем название дня из callback_data (например "Понедельник" из "day_Понедельник")
    selected_day = callback.data.replace("day_", "")

    text = scheduler.get_full_day_schedule(user_class, selected_day)
    
    # Меняем текст сообщения с кнопками на само расписание
    await callback.message.edit_text(text)
    await callback.answer()

# Хэндлер для ручного ввода данных
@router.message(F.text)
async def handle_text(message: Message):
    text = message.text.strip()
    
    if text.upper() in [c.upper() for c in scheduler.get_all_classes()]:
        await db.set_user_class(message.from_user.id, text)
        await message.answer(f"Класс {text.upper()} успешно сохранен!", reply_markup=get_main_keyboard())
        return

    user_class = await db.get_user_class(message.from_user.id)
    if not user_class:
        return await message.answer("Сначала выберите ваш класс!", reply_markup=get_classes_keyboard())

    words = text.split()
    target_time_str = None
    target_day = None

    for word in words:
        word_clean = word.strip().capitalize()
        if word_clean in VALID_DAYS:
            target_day = word_clean
        elif ":" in word:
            target_time_str = word

    if target_time_str and not target_day:
        now = datetime.now()
        target_day = scheduler.days_mapping.get(now.weekday(), "Воскресенье")

    if target_time_str:
        try:
            target_time = datetime.strptime(target_time_str, "%H:%M").time()
            current_lesson, next_lesson = scheduler.get_lessons_for_time(user_class, target_day, target_time)
            
            response = f"🔍 Расписание для {user_class} на день: {target_day}, время: {target_time_str}:\n\n"
            if current_lesson:
                response += f"📖 Будет идти: {current_lesson}\n"
            else:
                response += "📖 В это время урока нет (перемена или свободное время)\n"
                
            if next_lesson:
                response += f"➡️ Ближайший следующий: {next_lesson}"
                
            await message.answer(response, parse_mode="Markdown")
            return
        except ValueError:
            await message.answer("Неверный формат времени. Пишите в формате ЧЧ:ММ (например, 14:20).")
            return

    await message.answer(
        "Не понимаю команду.\n\n"
        "Вы можете:\n"
        "• Использовать кнопки меню\n"
        "• Написать время: 14:20 (посмотрит на сегодня)\n"
        "• Написать время и день: 14:20 Вторник или Среда 09:00"
    )
