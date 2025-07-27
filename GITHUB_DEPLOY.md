# 🚀 Деплой через GitHub на PythonAnywhere

## Шаг 1: Создание репозитория на GitHub

1. **Зайдите на GitHub** и создайте новый репозиторий
   - Имя: `codeacademy-pro` или любое другое
   - Описание: `Interactive Dart learning platform`
   - Публичный или приватный (на ваш выбор)
   - НЕ создавайте README.md (он уже есть)

2. **Скопируйте URL репозитория** (например: `https://github.com/username/codeacademy-pro.git`)

## Шаг 2: Загрузка кода на GitHub

**В командной строке (в папке проекта):**

```bash
# Добавляем remote origin
git remote add origin https://github.com/ВАШЕ_ИМЯ/НАЗВАНИЕ_РЕПО.git

# Отправляем код на GitHub
git branch -M main
git push -u origin main
```

## Шаг 3: Клонирование на PythonAnywhere

1. **Зайдите в консоль Bash** на PythonAnywhere

2. **Клонируйте репозиторий:**
```bash
cd ~
git clone https://github.com/ВАШЕ_ИМЯ/НАЗВАНИЕ_РЕПО.git
cd НАЗВАНИЕ_РЕПО
```

3. **Создайте виртуальное окружение:**
```bash
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

4. **Создайте .env файл для продакшена:**
```bash
cp .env.example .env
nano .env
```

Заполните:
```env
FLASK_ENV=production
SECRET_KEY=ваш-супер-секретный-ключ-измените-это
DATABASE_URL=sqlite:///app.db
DART_PATH=dart
```

## Шаг 4: Настройка Web App

1. **В разделе Web** → **Add a new web app**
   - Manual configuration
   - Python 3.10

2. **WSGI файл** (`/var/www/yourusername_pythonanywhere_com_wsgi.py`):
```python
import sys
import os

# Путь к проекту (ЗАМЕНИТЕ на ваш путь!)
project_home = '/home/yourusername/НАЗВАНИЕ_РЕПО'
if project_home not in sys.path:
    sys.path = [project_home] + sys.path

# Переменные окружения
os.environ.setdefault('SECRET_KEY', 'your-secret-key')
os.environ.setdefault('DATABASE_URL', 'sqlite:///app.db')

from app import app as application
```

3. **Virtualenv:** `/home/yourusername/НАЗВАНИЕ_РЕПО/venv`

4. **Static files:**
   - URL: `/static/`
   - Directory: `/home/yourusername/НАЗВАНИЕ_РЕПО/static/`

## Шаг 5: Инициализация базы данных

**В консоли Python на PythonAnywhere:**
```python
import os
os.chdir('/home/yourusername/НАЗВАНИЕ_РЕПО')

from app import app, db, init_achievements
with app.app_context():
    db.create_all()
    init_achievements()
    print("✅ База данных готова!")
```

## Шаг 6: Reload и тестирование

1. **Reload** в разделе Web
2. **Откройте сайт:** `yourusername.pythonanywhere.com`
3. **Проверьте функциональность**

## Обновление проекта

Когда внесете изменения в код:

**На локальной машине:**
```bash
git add .
git commit -m "Описание изменений"
git push origin main
```

**На PythonAnywhere:**
```bash
cd ~/НАЗВАНИЕ_РЕПО
git pull origin main
source venv/bin/activate
pip install -r requirements.txt  # если обновились зависимости

# Если обновились модели БД:
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
"
```

Затем **Reload** в Web разделе.

## Преимущества через Git:

✅ **Контроль версий** - отслеживание всех изменений  
✅ **Простые обновления** - один `git pull`  
✅ **Бэкапы** - код сохранен на GitHub  
✅ **Совместная работа** - можно работать в команде  
✅ **Откат изменений** - легко вернуться к предыдущей версии  

---

🎉 **Готово! Теперь ваша IT Академия работает через Git!**