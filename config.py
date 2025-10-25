import os

# Приоритет: переменные окружения -> secret.py -> дефолтные значения
BOT_TOKEN = os.environ.get('BOT_TOKEN')
SECRET_KEY = os.environ.get('SECRET_KEY')

# Если переменные окружения не заданы, пытаемся загрузить из secret.py
if not BOT_TOKEN or not SECRET_KEY:
    try:
        from secret import BOT_TOKEN as SECRET_BOT_TOKEN, SECRET_KEY as SECRET_SECRET_KEY
        if not BOT_TOKEN:
            BOT_TOKEN = SECRET_BOT_TOKEN
        if not SECRET_KEY:
            SECRET_KEY = SECRET_SECRET_KEY
    except ImportError:
        pass

# Если всё ещё не заданы, используем дефолтные (только для разработки!)
if not BOT_TOKEN:
    BOT_TOKEN = 'YOUR_BOT_TOKEN_HERE'
if not SECRET_KEY:
    SECRET_KEY = 'default-secret-key-change-this-in-production'

