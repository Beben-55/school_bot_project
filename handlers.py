from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from datetime import datetime
from zoneinfo import ZoneInfo
import logging
import os

from database import db
from config import settings
from schedule import ScheduleManager

logger = logging.getLogger(name)
router = Router()
scheduler = ScheduleManager(settings.SCHEDULE_FILE)

# Список доступных дней для валидации ввода
VALID_DAYS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

# Принудительный часовой пояс (берется из переменной TZ в Railway или ставится Москва по умолчанию)
TIMEZONE = ZoneInfo(os.getenv("TZ", "Europe/Moscow"))

# Главная панель кнопок внизу экрана (теперь 4 кнопки, включая "Учителя")
def get_main_keyboard() -> ReplyKeyboardMarkup:
    kb = [
        [KeyboardButton(text="Что сейчас?"), KeyboardButton(text="Расписание на сегодня")],
        [KeyboardButton(text="Расписание на день"), KeyboardButton(text="Учителя")],
        [KeyboardButton(text="Сменить класс")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# Перенесли выбор класса на прикрепленные (Inline) кнопки в сообщении
def get_classes_inline_keyboard() -> InlineKeyboardMarkup:
    classes = scheduler.get_all_classes()
    if not classes:
        return InlineKeyboardMarkup(inline_keyboard=[[]])
    
    buttons = [InlineKeyboardButton(text=c, callback_data=f"select_class_{c}") for c in classes]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(inline_keyboard=rows)

# Прикрепленные кнопки выбора дней недели
def get_days_inline_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="Понедельник", callback_data="day_Понедельник"), InlineKeyboardButton(text="Вторник", callback_data="day_Вторник")],
        [InlineKeyboardButton(text="Среда", callback_data="day_Среда"), InlineKeyboardButton(text="Четверг", callback_data="day_Четверг")],
        [InlineKeyboardButton(text="Пятница", callback_data="day_Пятница"), InlineKeyboardButton(text="Суббота", callback_data="day_Суббота")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Прикрепленные кнопки предметов для выбранного класса
def get_subjects_inline_keyboard(school_class: str) -> InlineKeyboardMarkup:
    subjects = scheduler.get_subjects_for_class(school_class)
    buttons = [InlineKeyboardButton(text=sub, callback_data=f"teacher_for_{sub}") for sub in subjects]
    rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 Привет! Я бот-расписание.\nВыберите ваш класс из списка ниже:",
        reply_markup=get_classes_inline_keyboard()
    )

@router.message(F.text == "Сменить класс")
async def change_class(message: Message):
    await message.answer("Выберите ваш класс из списка ниже:", reply_markup=get_classes_inline_keyboard())

# Обработка выбора класса через инлайн-кнопку
@router.callback_query(F.data.startswith("select_class_"))
async def process_class_selection(callback: CallbackQuery):
    selected_class = callback.data.replace("select_class_", "")
    await db.set_user_class(callback.from_user.id, selected_class)
    
    await callback.message.delete() # Удаляем сообщение со списком классов, чтобы не занимать экран
    await callback.message.answer(
        f"✅ Класс {selected_class} успешно сохранен! Используйте меню для работы.",
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(F.text == "Что сейчас?")
async def what_is_now(message: Message):
    user_class = await db.get_user_class(message.from_user.id)
    if not user_class:
        return await message.answer("Сначала выберите ваш класс!", reply_markup=get_main_keyboard())
    
    now = datetime.now(TIMEZONE)
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

@router.message(F.text == "Расписание на сегодня")
async def day_schedule_today(message: Message):
    user_class = await db.get_user_class(message.from_user.id)
    if not user_class:
        return await message.answer("Сначала выберите ваш класс!")
    
    now = datetime.now(TIMEZONE)
    current_day = scheduler.days_mapping.get(now.weekday(), "Воскресенье")
    text = scheduler.get_full_day_schedule(user_class, current_day)
    await message.answer(text)

@router.message(F.text == "Расписание на день")
async def day_schedule_prompt(message: Message):
    user_class = await db.get_user_class(message.from_user.id)
    if not user_class:
        return await message.answer("Сначала выберите ваш класс!")
    
    await message.answer("Выберите интересующий день недели:", reply_markup=get_days_inline_keyboard())

@router.callback_query(F.data.startswith("day_"))
async def process_day_callback(callback: CallbackQuery):
    user_class = await db.get_user_class(callback.from_user.id)
    selected_day = callback.data.replace("day_", "")
    text = scheduler.get_full_day_schedule(user_class, selected_day)
    await callback.message.edit_text(text)
    await callback.answer()

# Новая логика: Обработка нажатия кнопки "Учителя"
@router.message(F.text == "Учителя")
async def teachers_prompt(message: Message):
    user_class = await db.get_user_class(message.from_user.id)
    if not user_class:
        return await message.answer("Сначала выберите ваш класс!")
    
    await message.answer(
        f"Выберите предмет класса {user_class}, чтобы узнать учителя:",
        reply_markup=get_subjects_inline_keyboard(user_class)
    )

# Обработка нажатия на инлайн-кнопку конкретного предмета
@router.callback_query(F.data.startswith("teacher_for_"))
async def process_teacher_callback(callback: CallbackQuery):
    user_class = await db.get_user_class(callback.from_user.id)
    subject = callback.data.replace("teacher_for_", "")
    teacher = scheduler.get_teacher_for_subject(user_class, subject)
    
    await callback.message.edit_text(
        f"📖 Предмет: {subject}\n👤 Преподаватель: {teacher}\n\n*(Вы можете выбрать другой предмет кнопкой «Учителя» в меню)*",
        parse_mode="Markdown"
    )
    await callback.answer()

@router.message(F.text)
async def handle_text(message: Message):
    text = message.text.strip()
    user_class = await db.get_user_class(message.from_user.id)
    if not user_class:
        return await message.answer("Сначала выберите ваш класс через команду /start")

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
        now = datetime.now(TIMEZONE)
        target_day = scheduler.days_mapping.get(now.weekday(), "Воскресенье")

    if target_time_str:
        try:
            target_time = datetime.strptime(target_time_str, "%H:%M").time()
            current_lesson, next_lesson = scheduler.get_lessons_for_time(user_class, target_day, target_time)
            
            response = f"🔍 Расписание для {user_class} на день: {target_day}, время: {target_time_str}:\n\n"
            if current_lesson:
                response += f"📖 Будет идти: {current_lesson}\n"
            else:
                response += "📖 В это время урока нет\n"
            if next_lesson:
                response += f"➡️ Ближайший следующий: {next_lesson}"
            await message.answer(response, parse_mode="Markdown")
            return
        except ValueError:
            await message.answer("Неверный формат времени. Пишите ЧЧ:ММ (например, 14:20).")
            return

    await message.answer("Используйте кнопки меню для управления ботом или введите время (например 12:30).")
