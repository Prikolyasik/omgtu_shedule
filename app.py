"""
Точка входа для Vercel.
Импортирует Flask-приложение из backend/app.py.
"""
import os

# Сообщаем backend, что работаем на Vercel
os.environ['VERCEL'] = '1'

from backend.app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
