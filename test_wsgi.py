#!/usr/bin/env python3
"""
Тестовый WSGI файл для диагностики проблем на PythonAnywhere
Используйте этот файл временно для проверки настроек
"""

import sys
import os

# Информация для отладки
print("=== ДИАГНОСТИКА WSGI ===")
print(f"Python version: {sys.version}")
print(f"Current working directory: {os.getcwd()}")
print(f"Python path: {sys.path}")

# Путь к вашему проекту (ЗАМЕНИТЕ yourusername на ваше имя пользователя!)
project_home = '/home/yourusername/it_online'
print(f"Project home: {project_home}")
print(f"Project exists: {os.path.exists(project_home)}")

if project_home not in sys.path:
    sys.path = [project_home] + sys.path
    print("Added project to Python path")

# Переменные окружения
os.environ.setdefault('SECRET_KEY', 'test-secret-key')
os.environ.setdefault('DATABASE_URL', 'sqlite:///app.db')

# Проверка импорта
try:
    print("Attempting to import app...")
    from app import app as application
    print("✅ App imported successfully!")
    print(f"App name: {application.name}")
    print(f"App routes: {[rule.rule for rule in application.url_map.iter_rules()]}")
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    
    # Создаем простое тестовое приложение
    from flask import Flask
    application = Flask(__name__)
    
    @application.route('/')
    def test():
        return """
        <h1>🔧 WSGI Test Page</h1>
        <p>If you see this, WSGI is working but app import failed.</p>
        <p>Check the error logs for import details.</p>
        <p>Fix the import issue and replace this test WSGI file with the real one.</p>
        """
    
    print("Created test Flask app as fallback")

print("=== END ДИАГНОСТИКА ===")

if __name__ == "__main__":
    application.run(debug=True)