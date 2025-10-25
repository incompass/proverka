from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
import secrets
import random
import asyncio
from config import SECRET_KEY
import database
import bot as telegram_bot

app = Flask(__name__)
app.secret_key = SECRET_KEY

database.init_db()

GROUPS = [
    "ИСиП25-1", "ИСиП25к", "МК23", "МНЭ25",
    "ОИБ25-1", "ОИБ25-2", "ОИБ25к", "ТЭС25", "ТЭС24",
    "УК25-1", "УК25-2", "УК25к",
    "ЭМ23", "ЭМ25", "ЭС25-1", "ЭС25-2", "ЭС24"
]

def get_cookie_id():
    if 'cookie_id' not in session:
        session['cookie_id'] = secrets.token_hex(16)
    return session['cookie_id']

def is_logged_in():
    return 'user_id' in session

def get_current_user():
    if 'user_id' in session:
        return database.get_user_by_id(session['user_id'])
    return None

def is_admin_or_teacher():
    """Проверяет, является ли пользователь админом или учителем"""
    if not is_logged_in():
        return False
    
    user = get_current_user()
    if not user:
        return False
    
    return user.get('is_admin') or user.get('role') == 'teacher'

def can_access_philosophy():
    """Проверяет, может ли пользователь получить доступ к дисциплине 'Основы философии'"""
    if not is_logged_in():
        return False
    
    user = get_current_user()
    if not user:
        return False
    
    # Админы и учителя имеют доступ ко всему
    if is_admin_or_teacher():
        return True
    
    # Доступ только для групп ЭС24 и ТЭС24
    allowed_groups = ['ЭС24', 'ТЭС24']
    return user.get('group_name') in allowed_groups

def get_doc_id_for_group(group_name):
    """Получает ID документа для конкретной группы"""
    # Группа 1: УК25к, ИСиП25-1, ЭМ23, МК23, ЭС25-1, ЭС25-2, УК25-2
    group1 = ['УК25к', 'ИСиП25-1', 'ЭМ23', 'МК23', 'ЭС25-1', 'ЭС25-2', 'УК25-2']
    doc1_id = '1NinpeaaHuRZtMvFWs3Wp3vXVPnzu05PDCoJhh5RnWYQ'
    
    # Группа 2: ОИБ25-1, ОИБ25-2, ОИБ25к, УК25-1, ИСиП25к, МНЭ25, ТЭС25, ЭМ25
    group2 = ['ОИБ25-1', 'ОИБ25-2', 'ОИБ25к', 'УК25-1', 'ИСиП25к', 'МНЭ25', 'ТЭС25', 'ЭМ25']
    doc2_id = '1DYEZFxMTJ9v76dWqkAy8vZ_A0n1EeZDtZCBcmcDoBIw'
    
    if group_name in group1:
        return doc1_id
    elif group_name in group2:
        return doc2_id
    else:
        return doc1_id  # По умолчанию

def get_obshchestvoznanie_access():
    """Возвращает информацию о доступе к Обществознанию и ссылку на документ"""
    if not is_logged_in():
        return None, None
    
    user = get_current_user()
    if not user:
        return None, None
    
    group = user.get('group_name')
    
    # Админы и учителя имеют доступ к документу своей группы (или к первому, если группы нет)
    if is_admin_or_teacher():
        doc_id = get_doc_id_for_group(group) if group else '1NinpeaaHuRZtMvFWs3Wp3vXVPnzu05PDCoJhh5RnWYQ'
        return True, doc_id
    
    # Группа 1: УК25к, ИСиП25-1, ЭМ23, МК23, ЭС25-1, ЭС25-2, УК25-2
    group1 = ['УК25к', 'ИСиП25-1', 'ЭМ23', 'МК23', 'ЭС25-1', 'ЭС25-2', 'УК25-2']
    doc1_id = '1NinpeaaHuRZtMvFWs3Wp3vXVPnzu05PDCoJhh5RnWYQ'
    
    # Группа 2: ОИБ25-1, ОИБ25-2, ОИБ25к, УК25-1, ИСиП25к, МНЭ25, ТЭС25, ЭМ25
    group2 = ['ОИБ25-1', 'ОИБ25-2', 'ОИБ25к', 'УК25-1', 'ИСиП25к', 'МНЭ25', 'ТЭС25', 'ЭМ25']
    doc2_id = '1DYEZFxMTJ9v76dWqkAy8vZ_A0n1EeZDtZCBcmcDoBIw'
    
    if group in group1:
        return True, doc1_id
    elif group in group2:
        return True, doc2_id
    else:
        return False, None

@app.context_processor
def inject_user():
    user = get_current_user()
    has_obsh_access = False
    has_phil_access = False
    
    if user:
        # Проверка доступа к обществознанию
        has_obsh_access, _ = get_obshchestvoznanie_access()
        has_obsh_access = has_obsh_access or False
        
        # Проверка доступа к философии
        has_phil_access = can_access_philosophy()
    
    return {
        'user': user,
        'has_obsh_access': has_obsh_access,
        'has_phil_access': has_phil_access
    }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/info')
def info():
    return render_template('info.html')

@app.route('/profile')
def profile():
    if not is_logged_in():
        return redirect(url_for('login'))
    
    user = database.get_user_by_id(session['user_id'])
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    return render_template('profile.html', user=user)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        return redirect(url_for('profile'))
    
    cookie_id = get_cookie_id()
    
    if database.is_cookie_blocked(cookie_id):
        return render_template('blocked.html')
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'select_group':
            group = request.form.get('group')
            if group in GROUPS:
                session['selected_group'] = group
                users = database.get_users_by_group(group)
                return render_template('login.html', groups=GROUPS, step='select_user', 
                                     selected_group=group, users=users)
        
        elif action == 'select_user':
            user_id = request.form.get('user_id')
            user = database.get_user_by_id(int(user_id))
            
            if user:
                code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
                database.create_login_code(user['id'], code)
                
                try:
                    success = telegram_bot.send_login_code_sync(user['telegram_id'], code)
                    
                    if success:
                        session['login_user_id'] = user['id']
                        return render_template('login.html', groups=GROUPS, step='enter_code', 
                                             user=user)
                    else:
                        return render_template('login.html', groups=GROUPS, step='select_user',
                                             selected_group=session.get('selected_group'),
                                             users=database.get_users_by_group(session.get('selected_group')),
                                             error='Ошибка отправки кода. Проверь токен бота.')
                except Exception as e:
                    print(f"❌ Критическая ошибка отправки кода: {e}")
                    import traceback
                    traceback.print_exc()
                    return render_template('login.html', groups=GROUPS, step='select_user',
                                         selected_group=session.get('selected_group'),
                                         users=database.get_users_by_group(session.get('selected_group')),
                                         error=f'Ошибка отправки кода: {str(e)}')
        
        elif action == 'verify_code':
            code = request.form.get('code')
            user_id = session.get('login_user_id')
            
            if database.verify_code(user_id, code):
                database.reset_failed_attempts(cookie_id, user_id)
                session['user_id'] = user_id
                session.permanent = True
                return redirect(url_for('profile'))
            else:
                attempts = database.increment_failed_attempts(cookie_id, user_id)
                
                if attempts >= 3:
                    database.block_cookie(cookie_id)
                    return redirect(url_for('blocked'))
                
                user = database.get_user_by_id(user_id)
                return render_template('login.html', groups=GROUPS, step='enter_code',
                                     user=user, error=f'Неверный код. Осталось попыток: {3 - attempts}')
    
    return render_template('login.html', groups=GROUPS, step='select_group')

@app.route('/blocked')
def blocked():
    return render_template('blocked.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/rub', methods=['GET', 'POST'])
def rub_login():
    """Секретная страница для входа только учителей (не учеников-админов)"""
    if is_logged_in():
        user = get_current_user()
        if user and user.get('role') == 'teacher':
            return redirect(url_for('profile'))
    
    cookie_id = get_cookie_id()
    
    if database.is_cookie_blocked(cookie_id):
        return redirect(url_for('blocked'))
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'select_user':
            user_id = request.form.get('user_id')
            user = database.get_user_by_id(int(user_id))
            
            # Только учителя могут входить через /rub
            if user and user.get('role') == 'teacher':
                code = ''.join([str(random.randint(0, 9)) for _ in range(4)])
                database.create_login_code(user['id'], code)
                
                try:
                    success = telegram_bot.send_login_code_sync(user['telegram_id'], code)
                    if success:
                        session['login_user_id'] = user['id']
                        session['selected_group'] = user.get('group_name')
                        return render_template('rub.html', step='enter_code', user=user)
                    else:
                        return render_template('rub.html', step='select_user',
                                             users=database.get_teachers(),
                                             error='Ошибка отправки кода. Проверь токен бота.')
                except Exception as e:
                    print(f"❌ Ошибка отправки кода: {e}")
                    return render_template('rub.html', step='select_user',
                                         users=database.get_teachers(),
                                         error=f'Ошибка отправки кода: {str(e)}')
        
        elif action == 'verify_code':
            code = request.form.get('code')
            user_id = session.get('login_user_id')
            
            if database.verify_code(user_id, code):
                database.reset_failed_attempts(cookie_id, user_id)
                session['user_id'] = user_id
                session.pop('login_user_id', None)
                return redirect(url_for('profile'))
            else:
                attempts = database.increment_failed_attempts(cookie_id, user_id)
                if attempts >= 3:
                    database.block_cookie(cookie_id)
                    return redirect(url_for('blocked'))
                
                user = database.get_user_by_id(user_id)
                return render_template('rub.html', step='enter_code',
                                     user=user, error=f'Неверный код. Осталось попыток: {3 - attempts}')
    
    users = database.get_teachers()
    return render_template('rub.html', step='select_user', users=users)

@app.route('/conf')
def conf():
    from datetime import datetime
    return render_template('conf.html', current_date=datetime.now().strftime('%d.%m.%Y'))

@app.route('/o')
def obshchestvoznanie():
    has_access, doc_id = get_obshchestvoznanie_access()
    if has_access is None:
        return render_template('blocked.html',
                             title='Необходима авторизация',
                             message='Для доступа к дисциплине "Обществознание" необходимо войти в систему')
    elif not has_access:
        return render_template('blocked.html',
                             title='Доступ ограничен',
                             message='Дисциплина "Обществознание" недоступна для вашей группы')
    
    # Для админов и учителей показываем выбор группы
    if is_admin_or_teacher():
        # Все группы, у которых есть Обществознание
        all_groups = [
            'ИСиП25-1', 'ИСиП25к', 'МК23', 'МНЭ25',
            'ОИБ25-1', 'ОИБ25-2', 'ОИБ25к',
            'ТЭС25', 'УК25-1', 'УК25-2', 'УК25к',
            'ЭМ23', 'ЭМ25', 'ЭС25-1', 'ЭС25-2'
        ]
        # Сортируем в алфавитном порядке
        all_groups.sort()
        return render_template('obshchestvoznanie_select_group.html', 
                             all_groups=all_groups)
    
    return render_template('obshchestvoznanie.html')

@app.route('/o/group/<group_name>')
def obshchestvoznanie_for_group(group_name):
    """Страница обществознания для конкретной группы (для админов/учителей)"""
    if not is_admin_or_teacher():
        return render_template('blocked.html',
                             title='Доступ ограничен',
                             message='Эта страница доступна только администраторам и учителям')
    
    # Сохраняем выбранную группу в сессию
    session['selected_group_obsh'] = group_name
    return render_template('obshchestvoznanie.html', selected_group=group_name)

@app.route('/o/document')
def obshchestvoznanie_document():
    has_access, doc_id = get_obshchestvoznanie_access()
    if has_access is None:
        return render_template('blocked.html',
                             title='Необходима авторизация',
                             message='Для доступа к дисциплине "Обществознание" необходимо войти в систему')
    elif not has_access:
        return render_template('blocked.html',
                             title='Доступ ограничен',
                             message='Дисциплина "Обществознание" недоступна для вашей группы')
    
    # Для админов/учителей проверяем выбранную группу
    if is_admin_or_teacher() and 'selected_group_obsh' in session:
        selected_group = session['selected_group_obsh']
        doc_id = get_doc_id_for_group(selected_group)
    
    document_url = f'https://docs.google.com/document/d/{doc_id}'
    return render_template('obshchestvoznanie_document.html', document_url=document_url)

@app.route('/o/fullscreen')
def obshchestvoznanie_fullscreen():
    has_access, doc_id = get_obshchestvoznanie_access()
    if has_access is None:
        return render_template('blocked.html',
                             title='Необходима авторизация',
                             message='Для доступа к дисциплине "Обществознание" необходимо войти в систему')
    elif not has_access:
        return render_template('blocked.html',
                             title='Доступ ограничен',
                             message='Дисциплина "Обществознание" недоступна для вашей группы')
    
    # Для админов/учителей проверяем выбранную группу
    if is_admin_or_teacher() and 'selected_group_obsh' in session:
        selected_group = session['selected_group_obsh']
        doc_id = get_doc_id_for_group(selected_group)
    
    iframe_url = f'https://docs.google.com/document/d/{doc_id}/preview'
    return render_template('obshchestvoznanie_fullscreen.html', iframe_url=iframe_url)

@app.route('/of')
def osnovy_filosofii():
    if not can_access_philosophy():
        return render_template('blocked.html', 
                             title='Доступ ограничен',
                             message='Дисциплина "Основы философии" доступна только для групп ЭС24 и ТЭС24')
    return render_template('philosophy.html')

@app.route('/of/document')
def philosophy_document():
    if not can_access_philosophy():
        return render_template('blocked.html', 
                             title='Доступ ограничен',
                             message='Дисциплина "Основы философии" доступна только для групп ЭС24 и ТЭС24')
    return render_template('philosophy_document.html')

@app.route('/of/fullscreen')
def philosophy_fullscreen():
    if not can_access_philosophy():
        return render_template('blocked.html', 
                             title='Доступ ограничен',
                             message='Дисциплина "Основы философии" доступна только для групп ЭС24 и ТЭС24')
    return render_template('philosophy_fullscreen.html')


if __name__ == '__main__':
    database.init_db()
    app.run(host='0.0.0.0', port=80)
