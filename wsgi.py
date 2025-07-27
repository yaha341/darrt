#!/usr/bin/env python3
"""
WSGI конфигурация для PythonAnywhere
"""

import sys
import os

# Добавляем путь к проекту
project_home = '/home/yourusername/it_online'  # Замените на ваш путь
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Установка переменных окружения для продакшена
os.environ.setdefault('SECRET_KEY', 'your-secret-key-here-change-this')
os.environ.setdefault('DATABASE_URL', 'sqlite:///app.db')

# Импорт приложения
from app import app as application

if __name__ == "__main__":
    application.run()