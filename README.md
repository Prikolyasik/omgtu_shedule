# Расписание ОмГТУ — Веб-приложение

Интерактивное веб-приложение для управления расписанием ОмГТУ.

## Возможности

- 🔍 **Поиск расписания** — по группе, преподавателю, аудитории
- 📅 **Просмотр расписания** — с фильтрацией по датам
- 🔄 **Перенос пар** — с автоматическим подбором свободных слотов
- 👤 **Замена преподавателя** — с проверкой занятости
- 💬 **Консультации** — запись на консультации
- 📝 **Пересдачи** — обычные и комиссионные
- ✅ **Проверка доступности** — аудиторий, групп, преподавателей

## Установка и запуск

### Локальный запуск

#### 1. Установка зависимостей

```bash
pip install -r requirements.txt
```

#### 2. Запуск сервера

```bash
python backend\app.py
```

#### 3. Открыть в браузере

Перейдите по адресу: http://127.0.0.1:5000

### Деплой на PythonAnywhere (бесплатно, навсегда)

#### 1. Зарегистрируйся

Перейди на [pythonanywhere.com](https://www.pythonanywhere.com) и создай бесплатный аккаунт.

#### 2. Клонируй репозиторий

Открой **Bash-консоль** в PythonAnywhere и выполни:

```bash
git clone https://github.com/твой-username/omgtu_schedule.git
cd omgtu_schedule
pip3 install --user -r requirements.txt
```

#### 3. Настрой веб-приложение

1. Перейди во вкладку **Web** → **Add a new web app**
2. Выбери **Manual configuration** → **Python 3.10+**
3. В настройках укажи:
   - **Source code:** `/home/твой-username/omgtu_schedule/backend/app.py`
   - **Working directory:** `/home/твой-username/omgtu_schedule`
4. В разделе **WSGI configuration file** найди строку с `application =` и замени на:

```python
import sys
path = '/home/твой-username/omgtu_schedule'
if path not in sys.path:
    sys.path.append(path)

from backend.app import app as application
```

5. Нажми **Reload**

#### 4. Готово!

Твоё приложение доступно по адресу: `https://твой-username.pythonanywhere.com`

#### Обновление кода

```bash
cd ~/omgtu_schedule
git pull
# Перезагрузи веб-апп из вкладки Web → Reload
```

> **SQLite на PythonAnywhere:** база данных хранится в файловой системе и **не удаляется** при перезагрузках. Данные сохраняются.

### Деплой на Vercel

Проект настроен для деплоя на Vercel:

1. Установите Vercel CLI: `npm i -g vercel`
2. Войдите в аккаунт: `vercel login`
3. Задеплойте: `vercel`

Vercel автоматически найдёт файл `app.py` в корне как точку входа Flask-приложения.

> **⚠️ Важно:** На бесплатном тарифе Vercel база данных хранится в `/tmp` и **очищается** при каждом холодном старте (бездействии сервера). Это означает, что все пользовательские изменения (переносы, замены, консультации) будут потеряны. Vercel подходит для демонстрации, но не для постоянного использования.

## Структура проекта

```
omgtu_schedule/
├── backend/
│   ├── app.py              # Flask backend с API endpoints
│   └── db_manager.py       # Работа с базой данных
├── templates/
│   └── index.html          # Основной HTML шаблон
├── static/
│   ├── logo.png            # Логотип
│   ├── css/
│   │   └── style.css       # Стили интерфейса
│   └── js/
│       └── main.js         # Клиентская логика (AJAX, модалки)
├── omgtu_interactive.py    # Оригинальный парсер расписания
├── requirements.txt        # Зависимости Python
└── README.md               # Этот файл
```

> **Примечание:** Файлы `schedule.db` и `schedule_changes.json` генерируются автоматически при работе приложения и не хранятся в репозитории.

## Используемые технологии

- **Backend**: Python + Flask
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **UI фреймворк**: Bootstrap 5.3
- **Иконки**: Bootstrap Icons
- **API**: rasp.omgtu.ru (официальный API ОмГТУ)

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/search` | Поиск группы/преподавателя/аудитории |
| GET | `/api/schedule/group/<id>` | Расписание группы |
| GET | `/api/schedule/teacher/<id>` | Расписание преподавателя |
| GET | `/api/schedule/auditory/<id>` | Расписание аудитории |
| GET | `/api/free-slots` | Свободные слоты для переноса |
| GET | `/api/changes` | Все сохранённые изменения |
| POST | `/api/transfer` | Добавить перенос |
| POST | `/api/substitution` | Добавить замену |
| POST | `/api/consultation` | Добавить консультацию |
| POST | `/api/retake` | Добавить пересдачу |
