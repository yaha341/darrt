# 🚀 Инструкция по деплою на PythonAnywhere

## Подготовка к деплою

### 1. Создайте аккаунт на PythonAnywhere
- Зарегистрируйтесь на [pythonanywhere.com](https://www.pythonanywhere.com)
- Выберите подходящий план (Beginner план бесплатный)

### 2. Подготовьте файлы проекта
Убедитесь, что у вас есть все необходимые файлы:
```
it_online/
├── app.py
├── wsgi.py
├── config.py
├── requirements.txt
├── .env.example
├── templates/
├── static/
└── DEPLOYMENT.md
```

## Загрузка проекта

### Способ 1: Через Git (рекомендуется)

1. **Создайте репозиторий на GitHub** и загрузите туда весь проект

2. **В консоли PythonAnywhere** клонируйте репозиторий:
```bash
cd ~
git clone https://github.com/yourusername/it_online.git
cd it_online
```

### Способ 2: Через загрузку файлов

1. Зайдите в **Files** на PythonAnywhere
2. Создайте папку `it_online` в домашней директории
3. Загрузите все файлы проекта

## Настройка окружения

### 1. Создайте виртуальное окружение
```bash
cd ~/it_online
python3.10 -m venv venv
source venv/bin/activate
```

### 2. Установите зависимости
```bash
pip install -r requirements.txt
```

### 3. Создайте файл .env
```bash
cp .env.example .env
nano .env
```

Заполните переменные:
```env
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-here-change-this
DATABASE_URL=sqlite:///app.db
DART_PATH=/usr/bin/dart
```

### 4. Установите Dart SDK (если нужно)
```bash
# Проверьте, есть ли Dart
which dart

# Если нет, установите:
cd ~
wget https://storage.googleapis.com/dart-archive/channels/stable/release/latest/sdk/dartsdk-linux-x64-release.zip
unzip dartsdk-linux-x64-release.zip
export PATH="$PATH:$HOME/dart-sdk/bin"
echo 'export PATH="$PATH:$HOME/dart-sdk/bin"' >> ~/.bashrc
```

## Настройка веб-приложения

### 1. Создайте Web App
- Перейдите в раздел **Web** в панели PythonAnywhere
- Нажмите **Add a new web app**
- Выберите **Manual configuration**
- Выберите **Python 3.10**

### 2. Настройте WSGI файл
Отредактируйте WSGI файл (обычно `/var/www/yourusername_pythonanywhere_com_wsgi.py`):

```python
import sys
import os

# Путь к вашему проекту
project_home = '/home/yourusername/it_online'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Переменные окружения
os.environ.setdefault('SECRET_KEY', 'your-secret-key-change-this')
os.environ.setdefault('DATABASE_URL', 'sqlite:///app.db')

# ВАЖНО: Импорт приложения
from app import app as application

# Для отладки - проверьте что приложение импортировалось
print("Flask app imported successfully")
print(f"App name: {application.name}")
```

**Внимание:** Убедитесь что:
1. Путь `project_home` правильный (замените `yourusername` на ваше имя пользователя)
2. Виртуальное окружение настроено в разделе Web → Virtualenv
3. После изменений обязательно нажмите **Reload** в разделе Web

### 3. Настройте виртуальное окружение
В разделе **Web** → **Virtualenv**:
```
/home/yourusername/it_online/venv
```

### 4. Настройте статические файлы
В разделе **Static files**:
- URL: `/static/`
- Directory: `/home/yourusername/it_online/static/`

## Инициализация базы данных

### 1. Откройте консоль Python в PythonAnywhere
```python
import os
os.chdir('/home/yourusername/it_online')

from app import app, db
with app.app_context():
    db.create_all()
    print("База данных создана!")
```

### 2. Проверьте создание достижений
```python
from app import init_achievements
init_achievements()
print("Достижения инициализированы!")
```

## Запуск и тестирование

### 1. Перезагрузите веб-приложение
- В разделе **Web** нажмите **Reload**

### 2. Откройте ваш сайт
- Перейдите по адресу `yourusername.pythonanywhere.com`

### 3. Проверьте функциональность
- ✅ Регистрация пользователей
- ✅ Вход в систему  
- ✅ Просмотр курсов
- ✅ Выполнение уроков Dart
- ✅ Система достижений

## Устранение проблем

### Частые ошибки:

**1. Показывает "Hello from Flask!" вместо сайта**
```python
# В WSGI файле проверьте:
# 1. Правильный ли путь к проекту
project_home = '/home/ВАШЕИМЯ/it_online'  # Замените ВАШЕИМЯ

# 2. Правильный ли импорт
from app import app as application  # именно так!

# 3. Нажмите Reload в Web разделе после изменений
```

**2. Ошибка импорта модулей**
```bash
# Проверьте пути в WSGI файле
# Убедитесь что виртуальное окружение настроено в Web → Virtualenv
# Путь должен быть: /home/ВАШЕИМЯ/it_online/venv
```

**2. Ошибка с базой данных**
```bash
# Проверьте права доступа к файлу БД
chmod 666 ~/it_online/app.db
```

**3. Dart код не выполняется**
```bash
# Проверьте установку Dart
which dart
# Обновите путь в .env файле
```

**4. Статические файлы не загружаются**
- Проверьте настройки Static files в Web разделе
- Убедитесь что путь к папке static правильный

### Просмотр логов ошибок:
- В разделе **Web** → **Log files**
- Посмотрите **Error log** для диагностики проблем

## Обновление проекта

### Через Git:
```bash
cd ~/it_online
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
```

### Перезагрузка:
- В разделе **Web** нажмите **Reload**

## Дополнительные настройки

### 1. Домен (для платных планов)
- В разделе **Web** можете настроить собственный домен

### 2. HTTPS
- PythonAnywhere автоматически предоставляет HTTPS

### 3. MySQL база данных (для платных планов)
```python
# В config.py обновите DATABASE_URL:
DATABASE_URL=mysql+pymysql://username:password@username.mysql.pythonanywhere-services.com/username$dbname
```

## Поддержка

При возникновении проблем:
1. Проверьте логи ошибок
2. Обратитесь к [документации PythonAnywhere](https://help.pythonanywhere.com)
3. Используйте форум PythonAnywhere для получения помощи

---

🎉 **Поздравляем! Ваша IT Академия готова к использованию!**