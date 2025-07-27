#!/usr/bin/env python3
"""
Правильный WSGI файл для PythonAnywhere
Скопируйте содержимое в /var/www/va12a_pythonanywhere_com_wsgi.py
"""

import sys
import os

# Путь к вашему проекту (ЗАМЕНИТЕ на правильный путь!)
project_home = '/home/Va12A/it_online'  # Измените если папка называется по-другому

# Добавляем проект в Python path
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Переменные окружения
os.environ.setdefault('SECRET_KEY', 'your-production-secret-key-change-this')
os.environ.setdefault('DATABASE_URL', 'sqlite:///app.db')

# Импорт приложения
try:
    from app import app as application
    print(f"✅ Flask app loaded successfully: {application.name}")
except ImportError as e:
    print(f"❌ Failed to import app: {e}")
    # Создаем простое приложение для отладки
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def error_page():
        return f'''
        <h1>Import Error</h1>
        <p>Failed to import the main application.</p>
        <p>Error: {e}</p>
        <p>Check the error logs and file paths.</p>
        <p>Project path: {project_home}</p>
        <p>Python path: {sys.path}</p>
        '''

# Убираем активацию виртуального окружения из WSGI файла
# Виртуальное окружение настраивается в Web interface: Web → Virtualenv

if __name__ == "__main__":
    application.run()