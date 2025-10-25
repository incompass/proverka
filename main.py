import threading
import asyncio
from app import app
import database
from bot import bot, dp

def run_flask():
    app.run(host='0.0.0.0', port=80, use_reloader=False)

async def run_bot():
    database.init_db()
    print("🤖 Telegram бот запускается...")
    await dp.start_polling(bot, skip_updates=True)

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Запуск системы НПЭК")
    print("=" * 50)
    
    database.init_db()
    print(f"✅ База данных инициализирована: {database.DATABASE}")
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    print("🌐 Flask сервер запущен")
    
    print("=" * 50)
    print("📱 Бот: @npeks_bot")
    print("🌍 Сайт: http://localhost:80")
    print("=" * 50)
    
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("\n⚠️ Система остановлена")

