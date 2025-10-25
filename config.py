import os

try:
    from secret import BOT_TOKEN as SECRET_BOT_TOKEN, SECRET_KEY as SECRET_SECRET_KEY
    BOT_TOKEN = SECRET_BOT_TOKEN
    SECRET_KEY = SECRET_SECRET_KEY
except ImportError:
    BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-secret-key-change-this-in-production')

