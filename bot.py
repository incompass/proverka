import asyncio
import random
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from config import BOT_TOKEN
import database

GROUPS = [
    "ИСиП25-1", "ИСиП25к", "МК23", "МНЭ25",
    "ОИБ25-1", "ОИБ25-2", "ОИБ25к", "ТЭС25", "ТЭС24",
    "УК25-1", "УК25-2", "УК25к",
    "ЭМ23", "ЭМ25", "ЭС25-1", "ЭС25-2", "ЭС24"
]

SUPER_ADMIN_ID = 5720640497
ADMIN_PASSWORD = "админ123"

class Registration(StatesGroup):
    waiting_for_group = State()
    waiting_for_fio = State()

class AdminRegistration(StatesGroup):
    waiting_for_role_choice = State()
    waiting_for_fio = State()
    waiting_for_group = State()
    waiting_for_confirmation = State()

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

def get_groups_keyboard(with_back=True):
    buttons = []
    row = []
    for i, group in enumerate(GROUPS):
        row.append(KeyboardButton(text=group))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    
    if with_back:
        buttons.append([KeyboardButton(text="◀️ Назад")])
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_role_choice_keyboard():
    keyboard = [
        [KeyboardButton(text="👨‍🏫 Учитель")],
        [KeyboardButton(text="👤 Ученик-админ")],
        [KeyboardButton(text="◀️ Отмена")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_profile_keyboard():
    keyboard = [[KeyboardButton(text="👤 Профиль")]]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

async def get_user_photo_url(user_id: int):
    """Получает URL фото профиля пользователя"""
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)
        if photos.total_count > 0:
            photo = photos.photos[0][-1]  # Берём самое большое фото
            file = await bot.get_file(photo.file_id)
            photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file.file_path}"
            return photo_url
    except Exception as e:
        print(f"Ошибка получения фото: {e}")
    return None

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    telegram_username = message.from_user.username
    telegram_name = message.from_user.full_name
    
    photo_url = await get_user_photo_url(telegram_id)
    has_premium = message.from_user.is_premium or False
    
    user = database.get_user_by_telegram(telegram_id)
    
    if user:
        database.update_user_profile(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            telegram_name=telegram_name,
            photo_url=photo_url,
            has_premium=has_premium
        )
        
        # Формируем сообщение в зависимости от роли
        greeting = f"👋 Привет, {user['first_name']}!\n\n"
        greeting += f"Ты уже зарегистрирован.\n"
        
        if user.get('role') == 'teacher':
            greeting += f"Роль: Учитель\n"
        elif user.get('is_admin'):
            greeting += f"Роль: Администратор\n"
            greeting += f"Группа: {user['group_name']}\n"
        else:
            greeting += f"Группа: {user['group_name']}\n"
        
        greeting += f"ФИО: {user['last_name']} {user['first_name']} {user['middle_name'] or ''}\n\n"
        greeting += f"Для входа на сайт перейди по ссылке:\n"
        
        if user.get('role') == 'teacher':
            greeting += f"👉 https://pashq.ru/rub"
        else:
            greeting += f"👉 https://pashq.ru/login"
        
        await message.answer(
            greeting,
            reply_markup=get_profile_keyboard()
        )
    else:
        await message.answer(
            "👋 Привет! Добро пожаловать в систему профилей НПЭК!\n\n"
            "Для регистрации выбери свою группу из списка ниже:",
            reply_markup=get_groups_keyboard()
        )
        await state.set_state(Registration.waiting_for_group)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "📖 Команды бота:\n\n"
        "/start - Регистрация или проверка профиля\n"
        "/help - Помощь\n\n"
        "Для входа на сайт используй систему авторизации через выбор группы и имени."
    )

# ПРИОРИТЕТНЫЙ обработчик пароля админа - обрабатывается ПЕРЕД всеми состояниями!
@dp.message(F.text == ADMIN_PASSWORD)
async def admin_password_entered(message: Message, state: FSMContext):
    """Обработчик пароля 'админ123' для регистрации админов - работает в любом состоянии"""
    telegram_id = message.from_user.id
    
    # Проверяем, не зарегистрирован ли уже пользователь
    existing_user = database.get_user_by_telegram(telegram_id)
    if existing_user:
        await message.answer(
            "❌ Ты уже зарегистрирован в системе!\n"
            "Используй /start для просмотра профиля.",
            reply_markup=get_profile_keyboard()
        )
        return
    
    # Очищаем любое текущее состояние
    await state.clear()
    
    await message.answer(
        "🔑 Пароль принят!\n\n"
        "Выбери тип аккаунта:",
        reply_markup=get_role_choice_keyboard()
    )
    await state.set_state(AdminRegistration.waiting_for_role_choice)

# Обработчики состояний для обычной регистрации
@dp.message(Registration.waiting_for_group)
async def process_group(message: Message, state: FSMContext):
    # Проверка пароля админа ВНУТРИ обработчика состояния
    if message.text == ADMIN_PASSWORD:
        await admin_password_entered(message, state)
        return
    
    if message.text == "◀️ Назад":
        await state.clear()
        await message.answer(
            "❌ Регистрация отменена.\n\n"
            "Используй /start для начала регистрации.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if message.text not in GROUPS:
        await message.answer(
            "❌ Пожалуйста, выбери группу из списка кнопок ниже:",
            reply_markup=get_groups_keyboard()
        )
        return
    
    await state.update_data(group=message.text)
    back_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True
    )
    await message.answer(
        "✅ Группа выбрана!\n\n"
        "Теперь введи своё ФИО (Фамилия Имя Отчество) через пробел.\n"
        "Например: Иванов Иван Иванович\n\n"
        "Если нет отчества, просто напиши Фамилию и Имя.",
        reply_markup=back_keyboard
    )
    await state.set_state(Registration.waiting_for_fio)

@dp.message(Registration.waiting_for_fio)
async def process_fio(message: Message, state: FSMContext):
    # Проверка пароля админа ВНУТРИ обработчика состояния
    if message.text == ADMIN_PASSWORD:
        await admin_password_entered(message, state)
        return
    
    if message.text == "◀️ Назад":
        await message.answer(
            "Выбери свою группу из списка ниже:",
            reply_markup=get_groups_keyboard()
        )
        await state.set_state(Registration.waiting_for_group)
        return
    
    fio_parts = message.text.strip().split()
    
    if len(fio_parts) < 2:
        back_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
        await message.answer(
            "❌ Введи минимум Фамилию и Имя через пробел.\n"
            "Например: Иванов Иван",
            reply_markup=back_keyboard
        )
        return
    
    last_name = fio_parts[0]
    first_name = fio_parts[1]
    middle_name = fio_parts[2] if len(fio_parts) > 2 else None
    
    data = await state.get_data()
    group = data['group']
    
    telegram_id = message.from_user.id
    telegram_username = message.from_user.username
    telegram_name = message.from_user.full_name
    
    photo_url = await get_user_photo_url(telegram_id)
    has_premium = message.from_user.is_premium or False
    
    try:
        user_id = database.create_user(
            telegram_id=telegram_id,
            telegram_username=telegram_username,
            telegram_name=telegram_name,
            photo_url=photo_url,
            has_premium=has_premium,
            group_name=group,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name
        )
        
        full_name = f"{last_name} {first_name}"
        if middle_name:
            full_name += f" {middle_name}"
        
        await message.answer(
            f"✅ Регистрация завершена!\n\n"
            f"👤 {full_name}\n"
            f"🎓 Группа: {group}\n\n"
            f"Для входа на сайт перейди по ссылке:\n"
            f"👉 https://pashq.ru/login\n\n"
            f"Используй /start для проверки.",
            reply_markup=get_profile_keyboard()
        )
    except Exception as e:
        print(f"❌ Ошибка создания пользователя: {e}")
        await message.answer(
            "❌ Произошла ошибка при регистрации. Попробуй еще раз или обратись к администратору.\n\n"
            "Используй /start для проверки."
        )
    
    await state.clear()

@dp.message(AdminRegistration.waiting_for_role_choice)
async def process_role_choice(message: Message, state: FSMContext):
    """Обработчик выбора роли (учитель/ученик-админ)"""
    if message.text == "◀️ Отмена":
        await state.clear()
        await message.answer(
            "❌ Регистрация отменена.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    if message.text == "👨‍🏫 Учитель":
        await state.update_data(role="teacher", is_admin=False, group_name=None)
        back_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
        await message.answer(
            "👨‍🏫 Регистрация учителя\n\n"
            "Введи своё ФИО (Фамилия Имя Отчество) через пробел.\n"
            "Например: Иванов Иван Иванович\n\n"
            "Если нет отчества, просто напиши Фамилию и Имя.",
            reply_markup=back_keyboard
        )
        await state.set_state(AdminRegistration.waiting_for_fio)
    
    elif message.text == "👤 Ученик-админ":
        await state.update_data(role="student", is_admin=True)
        await message.answer(
            "👤 Регистрация ученика-админа\n\n"
            "Выбери свою группу из списка ниже:",
            reply_markup=get_groups_keyboard()
        )
        await state.set_state(AdminRegistration.waiting_for_group)
    
    else:
        await message.answer(
            "❌ Выбери один из вариантов:",
            reply_markup=get_role_choice_keyboard()
        )

@dp.message(AdminRegistration.waiting_for_group)
async def process_admin_group(message: Message, state: FSMContext):
    """Обработчик выбора группы для ученика-админа"""
    if message.text == "◀️ Назад":
        await message.answer(
            "Выбери тип аккаунта:",
            reply_markup=get_role_choice_keyboard()
        )
        await state.set_state(AdminRegistration.waiting_for_role_choice)
        return
    
    if message.text not in GROUPS:
        await message.answer(
            "❌ Пожалуйста, выбери группу из списка кнопок ниже:",
            reply_markup=get_groups_keyboard()
        )
        return
    
    await state.update_data(group_name=message.text)
    back_keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="◀️ Назад")]],
        resize_keyboard=True
    )
    await message.answer(
        "✅ Группа выбрана!\n\n"
        "Теперь введи своё ФИО (Фамилия Имя Отчество) через пробел.\n"
        "Например: Иванов Иван Иванович\n\n"
        "Если нет отчества, просто напиши Фамилию и Имя.",
        reply_markup=back_keyboard
    )
    await state.set_state(AdminRegistration.waiting_for_fio)

@dp.message(AdminRegistration.waiting_for_fio)
async def process_admin_fio(message: Message, state: FSMContext):
    """Обработчик ввода ФИО для админа/учителя"""
    if message.text == "◀️ Назад":
        data = await state.get_data()
        role = data.get('role')
        
        if role == "teacher":
            await message.answer(
                "Выбери тип аккаунта:",
                reply_markup=get_role_choice_keyboard()
            )
            await state.set_state(AdminRegistration.waiting_for_role_choice)
        else:  # student admin
            await message.answer(
                "Выбери свою группу из списка ниже:",
                reply_markup=get_groups_keyboard()
            )
            await state.set_state(AdminRegistration.waiting_for_group)
        return
    
    fio_parts = message.text.strip().split()
    
    if len(fio_parts) < 2:
        back_keyboard = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="◀️ Назад")]],
            resize_keyboard=True
        )
        await message.answer(
            "❌ Введи минимум Фамилию и Имя через пробел.\n"
            "Например: Иванов Иван",
            reply_markup=back_keyboard
        )
        return
    
    last_name = fio_parts[0]
    first_name = fio_parts[1]
    middle_name = fio_parts[2] if len(fio_parts) > 2 else None
    
    data = await state.get_data()
    role = data.get('role')
    is_admin = data.get('is_admin')
    group_name = data.get('group_name')
    
    telegram_id = message.from_user.id
    telegram_username = message.from_user.username
    telegram_name = message.from_user.full_name
    photo_url = await get_user_photo_url(telegram_id)
    has_premium = message.from_user.is_premium or False
    
    # Создаем ожидающую регистрацию
    confirmation_code = database.create_pending_registration(
        telegram_id=telegram_id,
        last_name=last_name,
        first_name=first_name,
        middle_name=middle_name,
        role=role,
        is_admin=is_admin,
        group_name=group_name,
        telegram_username=telegram_username,
        telegram_name=telegram_name,
        photo_url=photo_url,
        has_premium=has_premium
    )
    
    # Отправляем код главному админу
    role_text = "👨‍🏫 Учитель" if role == "teacher" else "👤 Ученик-админ"
    group_text = f"\n👥 Группа: {group_name}" if group_name else ""
    
    try:
        await bot.send_message(
            SUPER_ADMIN_ID,
            f"🔔 Новая заявка на регистрацию!\n\n"
            f"Тип: {role_text}\n"
            f"👤 ФИО: {last_name} {first_name} {middle_name or ''}{group_text}\n"
            f"🆔 Telegram ID: {telegram_id}\n"
            f"📱 Username: @{telegram_username or 'нет'}\n\n"
            f"🔑 Код подтверждения: `{confirmation_code}`\n\n"
            f"Для подтверждения отправь этот код пользователю."
        )
        
        await message.answer(
            f"✅ Заявка отправлена!\n\n"
            f"Попроси код подтверждения у главного админа и введи его здесь.\n\n"
            f"Код состоит из 6 цифр.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.set_state(AdminRegistration.waiting_for_confirmation)
        
    except Exception as e:
        print(f"❌ Ошибка отправки сообщения главному админу: {e}")
        await message.answer(
            "❌ Ошибка отправки заявки. Попробуй позже или обратись к администратору.",
            reply_markup=ReplyKeyboardRemove()
        )
        await state.clear()

@dp.message(AdminRegistration.waiting_for_confirmation)
async def process_confirmation_code(message: Message, state: FSMContext):
    """Обработчик кода подтверждения от главного админа"""
    confirmation_code = message.text.strip()
    telegram_id = message.from_user.id
    
    if len(confirmation_code) != 6 or not confirmation_code.isdigit():
        await message.answer(
            "❌ Код должен состоять из 6 цифр. Попробуй еще раз."
        )
        return
    
    # Проверяем и подтверждаем регистрацию
    success = database.confirm_pending_registration(telegram_id, confirmation_code)
    
    if success:
        user = database.get_user_by_telegram(telegram_id)
        
        if user['role'] == "teacher":
            await message.answer(
                f"✅ Регистрация подтверждена!\n\n"
                f"Ты зарегистрирован как учитель.\n\n"
                f"🌐 Войти на сайт:\n"
                f"https://pashq.ru/rub\n\n"
                f"Используй /start для просмотра профиля.",
                reply_markup=get_profile_keyboard()
            )
        else:  # student admin
            await message.answer(
                f"✅ Регистрация подтверждена!\n\n"
                f"Ты зарегистрирован как ученик-администратор.\n\n"
                f"🌐 Войти на сайт:\n"
                f"https://pashq.ru/login\n\n"
                f"(вход через обычную систему для учеников)\n\n"
                f"Используй /start для просмотра профиля.",
                reply_markup=get_profile_keyboard()
            )
        
        # Уведомляем главного админа
        try:
            role_text = "учителя" if user['role'] == "teacher" else "ученика-админа"
            await bot.send_message(
                SUPER_ADMIN_ID,
                f"✅ Регистрация подтверждена!\n\n"
                f"Тип: {role_text}\n"
                f"👤 {user['last_name']} {user['first_name']} {user.get('middle_name') or ''}\n"
                f"🆔 ID: {telegram_id}"
            )
        except:
            pass
        
        await state.clear()
    else:
        await message.answer(
            "❌ Неверный код подтверждения. Попробуй еще раз или обратись к администратору."
        )

@dp.message(F.text == "👤 Профиль")
async def show_profile(message: Message):
    telegram_id = message.from_user.id
    user = database.get_user_by_telegram(telegram_id)
    
    if not user:
        await message.answer(
            "❌ Ты еще не зарегистрирован!\n\n"
            "Используй /start для регистрации.",
            reply_markup=ReplyKeyboardRemove()
        )
        return
    
    # Обновляем фото при просмотре профиля
    photo_url = await get_user_photo_url(telegram_id)
    has_premium = message.from_user.is_premium or False
    
    if photo_url:
        database.update_user_profile(
            telegram_id=telegram_id,
            telegram_username=message.from_user.username,
            telegram_name=message.from_user.full_name,
            photo_url=photo_url,
            has_premium=has_premium
        )
        user = database.get_user_by_telegram(telegram_id)  # Обновляем данные
    
    profile_text = f"👤 *Мой профиль*\n\n"
    profile_text += f"🆔 ID: `{user['telegram_id']}`\n"
    
    if user.get('telegram_username'):
        profile_text += f"📱 Username: @{user['telegram_username']}\n"
    
    if user.get('telegram_name'):
        profile_text += f"✏️ Имя в Telegram: {user['telegram_name']}\n"
    
    # Определяем заголовок в зависимости от роли
    if user.get('role') == 'teacher':
        profile_text += f"\n👨‍🏫 *Данные учителя:*\n"
    elif user.get('is_admin'):
        profile_text += f"\n👑 *Данные администратора:*\n"
    else:
        profile_text += f"\n👨‍🎓 *Данные студента:*\n"
    
    profile_text += f"📝 Фамилия: {user['last_name']}\n"
    profile_text += f"📝 Имя: {user['first_name']}\n"
    
    if user.get('middle_name'):
        profile_text += f"📝 Отчество: {user['middle_name']}\n"
    
    if user.get('group_name'):
        profile_text += f"🎓 Группа: *{user['group_name']}*\n"
    
    # Показываем статус для админов и учителей
    if user.get('is_admin'):
        profile_text += f"💼 Статус: *Администратор*\n"
    elif user.get('role') == 'teacher':
        profile_text += f"💼 Статус: *Учитель*\n"
    
    if user.get('has_premium'):
        profile_text += f"\n⭐ Telegram Premium\n"
    
    # Разные ссылки для входа в зависимости от роли
    profile_text += f"\n🌐 Войти на сайт:\n"
    if user.get('role') == 'teacher':
        profile_text += f"https://pashq.ru/rub"
    else:
        profile_text += f"https://pashq.ru/login"
    
    if user.get('photo_url'):
        try:
            from aiogram.types import URLInputFile
            photo = URLInputFile(user['photo_url'])
            await message.answer_photo(
                photo=photo,
                caption=profile_text,
                parse_mode="Markdown",
                reply_markup=get_profile_keyboard()
            )
        except Exception as e:
            print(f"Ошибка отправки фото: {e}")
            await message.answer(
                profile_text,
                parse_mode="Markdown",
                reply_markup=get_profile_keyboard()
            )
    else:
        await message.answer(
            profile_text,
            parse_mode="Markdown",
            reply_markup=get_profile_keyboard()
        )

def send_login_code_sync(telegram_id: int, code: str):
    """Синхронная функция для отправки кода"""
    try:
        import requests
        from config import BOT_TOKEN
        
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": telegram_id,
            "text": f"🔐 Код для входа на сайт:\n\n*{code}*\n\nКод действителен 5 минут.\nУ тебя есть 3 попытки ввода.",
            "parse_mode": "Markdown"
        }
        
        response = requests.post(url, json=data, timeout=5)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка отправки кода: {e}")
        return False

async def send_login_code(telegram_id: int, code: str):
    """Асинхронная обертка"""
    return send_login_code_sync(telegram_id, code)

async def main():
    database.init_db()
    print("✅ База данных инициализирована")
    print("🤖 Бот запущен")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

