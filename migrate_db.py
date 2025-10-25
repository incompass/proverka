import database

print("Запуск миграции базы данных...")

try:
    with database.get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'telegram_username' not in columns:
            print("Добавляем новые колонки...")
            cursor.execute('ALTER TABLE users ADD COLUMN telegram_username TEXT')
            cursor.execute('ALTER TABLE users ADD COLUMN telegram_name TEXT')
            cursor.execute('ALTER TABLE users ADD COLUMN photo_url TEXT')
            cursor.execute('ALTER TABLE users ADD COLUMN has_premium BOOLEAN DEFAULT 0')
            cursor.execute('ALTER TABLE users ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
            conn.commit()
            print("✅ Миграция завершена успешно!")
        else:
            print("✅ База данных уже актуальна!")
            
except Exception as e:
    print(f"❌ Ошибка миграции: {e}")
    print("Если база данных новая, это нормально - просто запусти приложение.")

