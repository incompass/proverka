import sqlite3
import json
import os
from datetime import datetime, timedelta
from contextlib import contextmanager

DATA_DIR = '/data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

DATABASE = os.path.join(DATA_DIR, 'npek.db')

@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                telegram_username TEXT,
                telegram_name TEXT,
                photo_url TEXT,
                has_premium BOOLEAN DEFAULT 0,
                group_name TEXT,
                last_name TEXT NOT NULL,
                first_name TEXT NOT NULL,
                middle_name TEXT,
                role TEXT DEFAULT 'student',
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS login_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP NOT NULL,
                used BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS blocked_cookies (
                cookie_id TEXT PRIMARY KEY,
                blocked_until TIMESTAMP NOT NULL
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS failed_attempts (
                cookie_id TEXT,
                user_id INTEGER,
                attempts INTEGER DEFAULT 0,
                last_attempt TIMESTAMP,
                PRIMARY KEY (cookie_id, user_id)
            )
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS pending_registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                telegram_username TEXT,
                telegram_name TEXT,
                photo_url TEXT,
                has_premium BOOLEAN DEFAULT 0,
                group_name TEXT,
                last_name TEXT NOT NULL,
                first_name TEXT NOT NULL,
                middle_name TEXT,
                role TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                confirmation_code TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()

def create_user(telegram_id, group_name, last_name, first_name, middle_name=None, 
                telegram_username=None, telegram_name=None, photo_url=None, has_premium=False,
                role='student', is_admin=False):
    with get_db() as conn:
        cursor = conn.execute(
            '''INSERT INTO users (telegram_id, telegram_username, telegram_name, photo_url, has_premium,
                                  group_name, last_name, first_name, middle_name, role, is_admin) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (telegram_id, telegram_username, telegram_name, photo_url, has_premium,
             group_name, last_name, first_name, middle_name, role, is_admin)
        )
        conn.commit()
        return cursor.lastrowid

def update_user_profile(telegram_id, telegram_username=None, telegram_name=None, 
                       photo_url=None, has_premium=False):
    with get_db() as conn:
        conn.execute(
            '''UPDATE users 
               SET telegram_username = ?, telegram_name = ?, photo_url = ?, 
                   has_premium = ?, updated_at = CURRENT_TIMESTAMP
               WHERE telegram_id = ?''',
            (telegram_username, telegram_name, photo_url, has_premium, telegram_id)
        )
        conn.commit()

def get_user_by_telegram(telegram_id):
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,)).fetchone()
        return dict(user) if user else None

def get_user_by_id(user_id):
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        return dict(user) if user else None

def get_users_by_group(group_name):
    with get_db() as conn:
        users = conn.execute(
            'SELECT id, last_name, first_name FROM users WHERE group_name = ? ORDER BY last_name, first_name',
            (group_name,)
        ).fetchall()
        return [dict(user) for user in users]

def create_login_code(user_id, code):
    expires_at = datetime.now() + timedelta(minutes=5)
    with get_db() as conn:
        conn.execute(
            'INSERT INTO login_codes (user_id, code, expires_at) VALUES (?, ?, ?)',
            (user_id, code, expires_at)
        )
        conn.commit()

def verify_code(user_id, code):
    with get_db() as conn:
        result = conn.execute(
            '''SELECT * FROM login_codes 
               WHERE user_id = ? AND code = ? AND used = 0 AND expires_at > ?''',
            (user_id, code, datetime.now())
        ).fetchone()
        
        if result:
            conn.execute('UPDATE login_codes SET used = 1 WHERE id = ?', (result['id'],))
            conn.commit()
            return True
        return False

def is_cookie_blocked(cookie_id):
    with get_db() as conn:
        result = conn.execute(
            'SELECT * FROM blocked_cookies WHERE cookie_id = ? AND blocked_until > ?',
            (cookie_id, datetime.now())
        ).fetchone()
        return result is not None

def block_cookie(cookie_id):
    blocked_until = datetime.now() + timedelta(minutes=10)
    with get_db() as conn:
        conn.execute(
            'INSERT OR REPLACE INTO blocked_cookies (cookie_id, blocked_until) VALUES (?, ?)',
            (cookie_id, blocked_until)
        )
        conn.commit()

def increment_failed_attempts(cookie_id, user_id):
    with get_db() as conn:
        result = conn.execute(
            'SELECT attempts FROM failed_attempts WHERE cookie_id = ? AND user_id = ?',
            (cookie_id, user_id)
        ).fetchone()
        
        if result:
            new_attempts = result['attempts'] + 1
            conn.execute(
                'UPDATE failed_attempts SET attempts = ?, last_attempt = ? WHERE cookie_id = ? AND user_id = ?',
                (new_attempts, datetime.now(), cookie_id, user_id)
            )
        else:
            new_attempts = 1
            conn.execute(
                'INSERT INTO failed_attempts (cookie_id, user_id, attempts, last_attempt) VALUES (?, ?, ?, ?)',
                (cookie_id, user_id, new_attempts, datetime.now())
            )
        
        conn.commit()
        return new_attempts

def reset_failed_attempts(cookie_id, user_id):
    with get_db() as conn:
        conn.execute(
            'DELETE FROM failed_attempts WHERE cookie_id = ? AND user_id = ?',
            (cookie_id, user_id)
        )
        conn.commit()

def create_pending_registration(telegram_id, last_name, first_name, middle_name, role, is_admin,
                                group_name=None, telegram_username=None, telegram_name=None, 
                                photo_url=None, has_premium=False):
    """Создает ожидающую регистрацию"""
    import random
    confirmation_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    with get_db() as conn:
        conn.execute(
            '''INSERT OR REPLACE INTO pending_registrations 
               (telegram_id, telegram_username, telegram_name, photo_url, has_premium,
                group_name, last_name, first_name, middle_name, role, is_admin, confirmation_code)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (telegram_id, telegram_username, telegram_name, photo_url, has_premium,
             group_name, last_name, first_name, middle_name, role, is_admin, confirmation_code)
        )
        conn.commit()
    return confirmation_code

def get_pending_registration(telegram_id):
    """Получает ожидающую регистрацию по telegram_id"""
    with get_db() as conn:
        pending = conn.execute(
            'SELECT * FROM pending_registrations WHERE telegram_id = ?',
            (telegram_id,)
        ).fetchone()
        return dict(pending) if pending else None

def confirm_pending_registration(telegram_id, confirmation_code):
    """Подтверждает регистрацию и создает пользователя"""
    with get_db() as conn:
        pending = conn.execute(
            'SELECT * FROM pending_registrations WHERE telegram_id = ? AND confirmation_code = ?',
            (telegram_id, confirmation_code)
        ).fetchone()
        
        if not pending:
            return False
        
        # Создаем пользователя
        create_user(
            telegram_id=pending['telegram_id'],
            group_name=pending['group_name'],
            last_name=pending['last_name'],
            first_name=pending['first_name'],
            middle_name=pending['middle_name'],
            telegram_username=pending['telegram_username'],
            telegram_name=pending['telegram_name'],
            photo_url=pending['photo_url'],
            has_premium=pending['has_premium'],
            role=pending['role'],
            is_admin=pending['is_admin']
        )
        
        # Удаляем ожидающую регистрацию
        conn.execute('DELETE FROM pending_registrations WHERE telegram_id = ?', (telegram_id,))
        conn.commit()
        return True

def delete_pending_registration(telegram_id):
    """Удаляет ожидающую регистрацию"""
    with get_db() as conn:
        conn.execute('DELETE FROM pending_registrations WHERE telegram_id = ?', (telegram_id,))
        conn.commit()

def get_teachers_and_admins():
    """Получает всех учителей и админов для страницы /rub"""
    with get_db() as conn:
        users = conn.execute(
            '''SELECT id, last_name, first_name, middle_name, role, is_admin, group_name 
               FROM users 
               WHERE role = "teacher" OR is_admin = 1
               ORDER BY role DESC, last_name, first_name'''
        ).fetchall()
        return [dict(user) for user in users]

def get_teachers():
    """Получает только учителей (не учеников-админов) для страницы /rub"""
    with get_db() as conn:
        users = conn.execute(
            '''SELECT id, last_name, first_name, middle_name, role, is_admin, group_name 
               FROM users 
               WHERE role = "teacher"
               ORDER BY last_name, first_name'''
        ).fetchall()
        return [dict(user) for user in users]

