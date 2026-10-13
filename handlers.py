return await message.answer("Сначала выберите ваш класс!", reply_markup=get_classes_keyboard())
    
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
