"""
Flask backend для OmgtuParser с авторизацией.
"""

from flask import Flask, render_template, jsonify, request, session
import sys
import os
import traceback
from functools import wraps

# Добавляем родительскую директорию в путь
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from omgtu_interactive import OmgtuParser
from backend.db_manager import DatabaseManager

app = Flask(__name__,
            template_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates'),
            static_folder=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'))

app.secret_key = 'omgtu-schedule-secret-key-2026'

parser = OmgtuParser()
db = DatabaseManager()

# Мигрируем данные из JSON в БД (однократно)
db.migrate_from_json()


def apply_changes_to_schedule(schedule: list, group_id=None, teacher_id=None) -> list:
    """Наложить изменения из БД на расписание."""
    import json as json_mod
    
    result = []
    for lesson in schedule:
        l = dict(lesson)
        l["date"] = l.get("date", "").replace("-", ".")
        result.append(l)

    changes = db.get_all_changes(group_id=group_id, teacher_id=teacher_id)

    # Применяем переносы
    for change in changes.get("transfers", []):
        if group_id and change.get("group_id") != group_id:
            continue
        orig_date = change.get("original_date", "").replace("-", ".")
        orig_time_start = change.get("original_time", "").split(" - ")[0].strip()
        new_date = change.get("new_date", "").replace("-", ".")
        new_times = change.get("new_time", " - ").split(" - ")
        for lesson in result:
            if (lesson.get("date", "") == orig_date and
                    lesson.get("beginLesson", "") == orig_time_start):
                lesson["date"] = new_date
                lesson["beginLesson"] = new_times[0].strip() if len(new_times) > 0 else lesson["beginLesson"]
                lesson["endLesson"] = new_times[1].strip() if len(new_times) > 1 else lesson["endLesson"]
                if change.get("auditory"):
                    lesson["auditorium"] = change["auditory"]
                lesson["_changed"] = "перенос"

    # Применяем замены пар
    for change in changes.get("substitutions", []):
        if group_id and change.get("group_id") != group_id:
            continue
        orig_date = change.get("original_date", "").replace("-", ".")
        orig_time_start = change.get("original_time", "").split(" - ")[0].strip()
        
        if change.get("new_date") and change.get("new_time"):
            new_date = change.get("new_date", "").replace("-", ".")
            new_times = change.get("new_time", " - ").split(" - ")
            new_discipline = change.get("new_discipline", "")
            new_auditory = change.get("new_auditory", "")
            
            for lesson in result:
                if (lesson.get("date", "") == orig_date and
                        lesson.get("beginLesson", "") == orig_time_start):
                    lesson["date"] = new_date
                    lesson["beginLesson"] = new_times[0].strip() if len(new_times) > 0 else lesson["beginLesson"]
                    lesson["endLesson"] = new_times[1].strip() if len(new_times) > 1 else lesson["endLesson"]
                    if new_discipline:
                        lesson["discipline"] = new_discipline
                    if change.get("new_teacher"):
                        lesson["lecturer"] = change["new_teacher"]
                    if new_auditory:
                        lesson["auditorium"] = new_auditory
                    lesson["_changed"] = "замена пары"

    # Добавляем консультации
    for change in changes.get("consultations", []):
        if teacher_id and change.get("teacher_id") != teacher_id:
            continue
        if group_id and change.get("group_id") != group_id:
            continue
        times = change.get("time", " - ").split(" - ")
        result.append({
            "date": change.get("date", "").replace("-", "."),
            "beginLesson": times[0].strip() if len(times) > 0 else "",
            "endLesson": times[1].strip() if len(times) > 1 else "",
            "discipline": "Консультация",
            "kindOfWork": "Консультация",
            "lecturer": change.get("teacher", ""),
            "auditorium": change.get("auditory", ""),
            "building": "",
            "subGroup": change.get("group_name", ""),
            "_changed": "консультация"
        })

    # Добавляем пересдачи
    for change in changes.get("retakes", []):
        if group_id and change.get("group_id") != group_id:
            continue
        teachers_data = change.get("teachers", [])
        if isinstance(teachers_data, str):
            teachers_data = json_mod.loads(teachers_data)
        teacher_names = [t["name"] for t in teachers_data]
        if teacher_id:
            teacher_ids = [t.get("id") for t in teachers_data]
            if teacher_id not in teacher_ids:
                continue
        times = change.get("time", " - ").split(" - ")
        subtype = "Комиссионная пересдача" if change.get("subtype") == "commission" else "Пересдача"
        discipline = change.get("discipline", subtype)
        result.append({
            "date": change.get("date", "").replace("-", "."),
            "beginLesson": times[0].strip() if len(times) > 0 else "",
            "endLesson": times[1].strip() if len(times) > 1 else "",
            "discipline": discipline,
            "kindOfWork": subtype,
            "lecturer": ", ".join(teacher_names),
            "auditorium": change.get("auditory", ""),
            "building": "",
            "subGroup": change.get("group_name", ""),
            "_changed": "пересдача"
        })

    # Применяем отмены
    for change in changes.get("cancellations", []):
        if group_id and change.get("group_id") != group_id:
            continue
        orig_date = change.get("original_date", "").replace("-", ".")
        orig_time_start = change.get("original_time", "").split(" - ")[0].strip()
        for lesson in result:
            if (lesson.get("date", "") == orig_date and
                    lesson.get("beginLesson", "") == orig_time_start):
                lesson["_changed"] = "отмена"
                if change.get("reason"):
                    lesson["_cancel_reason"] = change["reason"]

    # Сортируем по дате и времени
    result.sort(key=lambda x: (x.get("date", ""), x.get("beginLesson", "")))
    return result


@app.errorhandler(Exception)
def handle_exception(e):
    """Глобальный обработчик ошибок — всегда возвращает JSON."""
    tb = traceback.format_exc()
    print(f"ERROR: {tb}")  # Логируем в консоль
    return jsonify({'error': str(e)}), 500


@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Endpoint не найден'}), 404


def require_teacher(f):
    """Декоратор: доступ только для преподавателей."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'role' not in session or session['role'] != 'teacher':
            return jsonify({'error': 'Доступ запрещён. Требуется авторизация преподавателя.'}), 403
        return f(*args, **kwargs)
    return decorated_function


# === Авторизация ===

@app.route('/login')
def login():
    """Страница входа."""
    return render_template('login.html')


@app.route('/api/login', methods=['POST'])
def api_login():
    """Вход в систему."""
    data = request.json
    role = data.get('role', '')
    
    if role == 'student':
        session['role'] = 'student'
        session['user'] = None
        return jsonify({'status': 'ok', 'role': 'student'})
    
    elif role == 'teacher':
        teacher_name = data.get('teacher_name', '').strip()
        if not teacher_name:
            return jsonify({'error': 'Введите ФИО преподавателя'}), 400
        
        # Ищем преподавателя через API
        try:
            resp = parser.session.get(
                f"{parser.BASE_URL}/search",
                params={"term": teacher_name, "type": "teacher"},
                timeout=10
            )
            results = [r for r in resp.json() if r.get("type") == "lecturer"]
            
            if not results:
                return jsonify({'error': 'Преподаватель не найден'}), 404
            
            # Берём первого найденного
            teacher = results[0]
            session['role'] = 'teacher'
            session['user'] = {
                'id': teacher['id'],
                'name': teacher['label']
            }
            return jsonify({
                'status': 'ok',
                'role': 'teacher',
                'user': session['user']
            })
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Неверная роль'}), 400


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Выход из системы."""
    session.clear()
    return jsonify({'status': 'ok'})


@app.route('/api/session', methods=['GET'])
def api_session():
    """Получить текущую сессию."""
    if 'role' not in session:
        return jsonify({'logged_in': False})
    
    return jsonify({
        'logged_in': True,
        'role': session['role'],
        'user': session.get('user')
    })


# === Страницы ===

@app.route('/')
def index():
    """Главная страница."""
    return render_template('index.html')


# === API endpoints (чтение — доступно всем) ===

@app.route('/api/search', methods=['POST'])
def search():
    """Поиск группы/преподавателя/аудитории."""
    data = request.json
    search_type = data.get('type', '')
    term = data.get('term', '')
    
    if not term:
        return jsonify({'error': 'Введите поисковый запрос'}), 400
    
    try:
        if search_type == 'group':
            resp = parser.session.get(
                f"{parser.BASE_URL}/search",
                params={"term": term, "type": "group"},
                timeout=10
            )
            results = resp.json()
        elif search_type == 'lecturer':
            resp = parser.session.get(
                f"{parser.BASE_URL}/search",
                params={"term": term, "type": "teacher"},
                timeout=10
            )
            results = [r for r in resp.json() if r.get("type") == "lecturer"]
        elif search_type == 'auditory':
            resp = parser.session.get(
                f"{parser.BASE_URL}/search",
                params={"term": term, "type": "auditory"},
                timeout=10
            )
            results = resp.json()
        else:
            return jsonify({'error': 'Неверный тип поиска'}), 400
        
        return jsonify(results)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedule/group/<int:group_id>', methods=['GET'])
def get_group_schedule(group_id):
    """Получить расписание группы."""
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    try:
        schedule = parser.get_group_schedule(group_id, date_from, date_to)
        # Применяем изменения из БД
        schedule = apply_changes_to_schedule(schedule, group_id=group_id)
        return jsonify(schedule)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedule/teacher/<int:teacher_id>', methods=['GET'])
def get_teacher_schedule(teacher_id):
    """Получить расписание преподавателя."""
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    try:
        schedule = parser.get_teacher_schedule(teacher_id, date_from, date_to)
        # Применяем изменения из БД
        schedule = apply_changes_to_schedule(schedule, teacher_id=teacher_id)
        return jsonify(schedule)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/schedule/auditory/<int:auditory_id>', methods=['GET'])
def get_auditory_schedule(auditory_id):
    """Получить расписание аудитории."""
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    try:
        schedule = parser.get_auditory_schedule(auditory_id, date_from, date_to)
        return jsonify(schedule)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/availability/teacher/<int:teacher_id>', methods=['GET'])
def check_teacher_availability(teacher_id):
    """Проверить доступность преподавателя."""
    date = request.args.get('date', '')
    time_start = request.args.get('time_start', '')
    time_end = request.args.get('time_end', '')
    
    available = parser.check_teacher_availability(teacher_id, date, time_start, time_end)
    return jsonify({'available': available})


@app.route('/api/availability/group/<int:group_id>', methods=['GET'])
def check_group_availability(group_id):
    """Проверить доступность группы."""
    date = request.args.get('date', '')
    time_start = request.args.get('time_start', '')
    time_end = request.args.get('time_end', '')
    subgroup = request.args.get('subgroup', '')
    
    available = parser.check_group_availability(group_id, date, time_start, time_end, subgroup)
    return jsonify({'available': available})


@app.route('/api/free-auditories', methods=['GET'])
def get_free_auditories():
    """Получить свободные аудитории на указанную дату/время."""
    date = request.args.get('date', '')
    time_start = request.args.get('time_start', '')
    time_end = request.args.get('time_end', '')
    
    if not date or not time_start or not time_end:
        return jsonify({'error': 'Нужны date, time_start, time_end'}), 400
    
    # Ищем все аудитории
    try:
        resp = parser.session.get(
            f"{parser.BASE_URL}/search",
            params={"term": "", "type": "auditory"},
            timeout=10
        )
        all_auditories = resp.json()
    except:
        return jsonify({'error': 'Не удалось получить список аудиторий'}), 500
    
    # Проверяем каждую на занятость
    free = []
    for aud in all_auditories:
        if parser.check_auditory_availability(aud['id'], date, time_start, time_end):
            free.append({'id': aud['id'], 'label': aud['label']})
    
    return jsonify(free)


@app.route('/api/availability/auditory/<int:auditory_id>', methods=['GET'])
def check_auditory_availability(auditory_id):
    """Проверить доступность аудитории."""
    date = request.args.get('date', '')
    time_start = request.args.get('time_start', '')
    time_end = request.args.get('time_end', '')
    
    available = parser.check_auditory_availability(auditory_id, date, time_start, time_end)
    return jsonify({'available': available})


@app.route('/api/free-slots', methods=['GET'])
def get_free_slots():
    """Получить свободные слоты."""
    teacher_id = request.args.get('teacher_id', type=int)
    group_id = request.args.get('group_id', type=int)
    date = request.args.get('date', '')
    subgroup = request.args.get('subgroup', '')
    
    if not teacher_id or not group_id or not date:
        return jsonify({'error': 'Необходимы teacher_id, group_id и date'}), 400
    
    slots = parser.get_free_slots(teacher_id, group_id, date, subgroup)
    return jsonify([{"start": s[0], "end": s[1]} for s in slots])


# === Изменения — только для преподавателей ===

@app.route('/api/changes', methods=['GET'])
def get_changes():
    """Получить все сохранённые изменения из БД."""
    group_id = request.args.get('group_id', type=int)
    teacher_id = request.args.get('teacher_id', type=int)
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    
    changes = db.get_all_changes(group_id=group_id, teacher_id=teacher_id)
    
    # Фильтруем консультации по датам если нужно
    if date_from or date_to:
        changes['consultations'] = db.get_consultations(
            teacher_id=teacher_id,
            date_from=date_from,
            date_to=date_to
        )
    
    return jsonify(changes)


@app.route('/api/transfer', methods=['POST'])
@require_teacher
def add_transfer():
    """Добавить перенос."""
    try:
        transfer = request.json
        if not transfer:
            return jsonify({'error': 'Нет данных'}), 400
        db.add_transfer(transfer)
        return jsonify({'status': 'ok', 'message': 'Перенос добавлен'})
    except Exception as e:
        print(f"TRANSFER ERROR: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/substitution', methods=['POST'])
@require_teacher
def add_substitution():
    """Добавить замену."""
    try:
        substitution = request.json
        if not substitution:
            return jsonify({'error': 'Нет данных'}), 400
        db.add_substitution(substitution)
        return jsonify({'status': 'ok', 'message': 'Замена добавлена'})
    except Exception as e:
        print(f"SUBSTITUTION ERROR: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/consultation', methods=['POST'])
@require_teacher
def add_consultation():
    """Добавить консультацию."""
    try:
        consultation = request.json
        if not consultation:
            return jsonify({'error': 'Нет данных'}), 400
        db.add_consultation(consultation)
        return jsonify({'status': 'ok', 'message': 'Консультация добавлена'})
    except Exception as e:
        print(f"CONSULTATION ERROR: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/retake', methods=['POST'])
@require_teacher
def add_retake():
    """Добавить пересдачу."""
    try:
        retake = request.json
        if not retake:
            return jsonify({'error': 'Нет данных'}), 400
        db.add_retake(retake)
        return jsonify({'status': 'ok', 'message': 'Пересдача добавлена'})
    except Exception as e:
        print(f"RETAKE ERROR: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/cancel', methods=['POST'])
@require_teacher
def add_cancel():
    """Отменить пару."""
    try:
        cancel = request.json
        if not cancel:
            return jsonify({'error': 'Нет данных'}), 400
        db.add_cancel(cancel)
        return jsonify({'status': 'ok', 'message': 'Пара отменена'})
    except Exception as e:
        print(f"CANCEL ERROR: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)
