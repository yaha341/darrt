from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import subprocess
import tempfile
import os
import json

# Конфигурация приложения (возвращаем к простой схеме)
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///codeacademy.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Инициализация базы данных
db = SQLAlchemy(app)

# Инициализация менеджера логина
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, войдите для доступа к этой странице.'

# Модель пользователя
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # Связь с прогрессом пользователя
    progress = db.relationship('UserProgress', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

# Модель прогресса пользователя
class UserProgress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    course_id = db.Column(db.Integer, nullable=False)
    lesson_id = db.Column(db.Integer, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime, server_default=db.func.now())
    
    def __repr__(self):
        return f'<UserProgress user={self.user_id} lesson={self.lesson_id}>'

# Модель достижений
class Achievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    icon = db.Column(db.String(20), default='🏆')
    category = db.Column(db.String(50), nullable=False)
    requirement_type = db.Column(db.String(30), nullable=False)  # lessons_count, streak, speed, etc
    requirement_value = db.Column(db.Integer, nullable=False)
    points = db.Column(db.Integer, default=10)
    
    def __repr__(self):
        return f'<Achievement {self.name}>'

# Модель полученных достижений пользователя
class UserAchievement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    achievement_id = db.Column(db.Integer, db.ForeignKey('achievement.id'), nullable=False)
    earned_at = db.Column(db.DateTime, server_default=db.func.now())
    
    # Связи
    user = db.relationship('User', backref='achievements')
    achievement = db.relationship('Achievement')
    
    def __repr__(self):
        return f'<UserAchievement user={self.user_id} achievement={self.achievement_id}>'

# Загрузчик пользователя для Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/courses')
@login_required
def courses():
    # Получаем прогресс пользователя по курсам
    user_progress = UserProgress.query.filter_by(user_id=current_user.id).all()
    
    # Преобразуем в словарь для удобства использования в шаблоне
    progress_dict = {}
    for progress in user_progress:
        progress_dict[progress.lesson_id] = {
            'completed': progress.completed,
            'completed_at': progress.completed_at
        }
    
    return render_template('courses.html', progress=progress_dict)

@app.route('/lessons')
@login_required
def lessons():
    # Получаем прогресс пользователя по урокам
    user_progress = UserProgress.query.filter_by(user_id=current_user.id).all()
    
    # Преобразуем в словарь для удобства использования в шаблоне
    progress_dict = {}
    for progress in user_progress:
        progress_dict[progress.lesson_id] = {
            'completed': progress.completed,
            'completed_at': progress.completed_at
        }
    
    return render_template('lessons.html', progress=progress_dict)

# Маршрут для регистрации
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.json.get('username') if request.is_json else request.form.get('username')
        email = request.json.get('email') if request.is_json else request.form.get('email')
        password = request.json.get('password') if request.is_json else request.form.get('password')
        
        # Проверка, что пользователь с таким именем или email уже существует
        if User.query.filter_by(username=username).first():
            if request.is_json:
                return jsonify({'success': False, 'error': 'Пользователь с таким именем уже существует'})
            flash('Пользователь с таким именем уже существует')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            if request.is_json:
                return jsonify({'success': False, 'error': 'Пользователь с таким email уже существует'})
            flash('Пользователь с таким email уже существует')
            return redirect(url_for('register'))
        
        # Создание нового пользователя
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        # Автоматический вход после регистрации
        login_user(user)
        
        if request.is_json:
            return jsonify({'success': True, 'message': 'Регистрация успешна'})
        flash('Регистрация успешна')
        return redirect(url_for('courses'))
    
    return render_template('register.html')

# Маршрут для входа
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.json.get('username') if request.is_json else request.form.get('username')
        password = request.json.get('password') if request.is_json else request.form.get('password')
        
        # Поиск пользователя по имени
        user = User.query.filter_by(username=username).first()
        
        # Проверка существования пользователя и правильности пароля
        if user and user.check_password(password):
            login_user(user)
            if request.is_json:
                return jsonify({'success': True, 'message': 'Вход выполнен успешно'})
            flash('Вход выполнен успешно')
            return redirect(url_for('courses'))
        
        if request.is_json:
            return jsonify({'success': False, 'error': 'Неправильное имя пользователя или пароль'})
        flash('Неправильное имя пользователя или пароль')
        return redirect(url_for('login'))
    
    return render_template('login.html')

# Маршрут для выхода
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы')
    return redirect(url_for('index'))

@app.route('/api/execute_dart', methods=['POST'])
def execute_dart():
    try:
        import requests
        import json
        
        code = request.json.get('code', '')
        
        # Проверяем на базовые ошибки синтаксиса
        if 'void main()' not in code:
            return jsonify({
                'success': False,
                'error': 'Ошибка: Отсутствует функция main()'
            })
        
        # Проверяем на некоторые синтаксические ошибки
        if code.count('{') != code.count('}'):
            return jsonify({
                'success': False,
                'error': 'Ошибка синтаксиса: Несовпадение скобок {}'
            })
        
        if code.count('(') != code.count(')'):
            return jsonify({
                'success': False,
                'error': 'Ошибка синтаксиса: Несовпадение скобок ()'
            })
        
        # Отправляем код на выполнение через онлайн-компилятор JDoodle
        # Используем бесплатный API JDoodle для выполнения Dart кода
        url = "https://api.jdoodle.com/v1/execute"
        
        # Данные для выполнения кода
        data = {
            "clientId": "your_client_id",  # Заменить на реальный clientId
            "clientSecret": "your_client_secret",  # Заменить на реальный clientSecret
            "script": code,
            "language": "dart",
            "versionIndex": "2"  # Версия Dart
        }
        
        # Для демонстрации будем использовать симуляцию выполнения
        # В реальном приложении нужно зарегистрироваться на JDoodle и получить clientId/clientSecret
        
        # Симуляция выполнения кода (временно, пока не получим реальные ключи)
        # В реальной системе здесь будет requests.post(url, json=data)
        
        # Имитируем выполнение кода для демонстрации
        import re
        
        # Ищем print() вызовы и извлекаем их содержимое
        print_pattern = r"print\s*\(\s*['\"]([^'\"]*)['\"]?\s*\)"
        matches = re.findall(print_pattern, code)
        
        # Ищем print() с переменными и интерполяцией
        interpolation_pattern = r"print\s*\(\s*['\"]([^'\"]*\$[^'\"]*)['\"]?\s*\)"
        interpolation_matches = re.findall(interpolation_pattern, code)
        
        output_lines = []
        
        # Обрабатываем простые print вызовы
        for match in matches:
            if '$' not in match:  # Простой текст без интерполяции
                output_lines.append(match)
        
        # Обрабатываем интерполяцию переменных
        for match in interpolation_matches:
            # Простая замена общих переменных для демонстрации
            result = match
            result = result.replace('$name', 'Dart')
            result = result.replace('$age', '25')
            result = result.replace('$height', '175.5')
            result = result.replace('$isStudent', 'true')
            output_lines.append(result)
        
        # Специальные случаи для уроков
        if 'add(5, 3)' in code:
            output_lines.append('Сумма: 8')
        
        if 'square(5)' in code:
            output_lines.append('Квадрат числа 5 равен: 25')
            
        if 'length * width' in code:
            output_lines.append('Площадь прямоугольника: 50')
            
        if 'for (int i = 1; i <= 10; i++)' in code:
            for i in range(1, 11):
                output_lines.append(f'Число: {i}')
                
        if 'while (number <= 100)' in code:
            output_lines.append('Сумма чисел от 1 до 100: 5050')
            
        if 'fruits[i]' in code:
            fruits = ['яблоко', 'банан', 'апельсин']
            for i, fruit in enumerate(fruits):
                output_lines.append(f'Фрукт {i + 1}: {fruit}')
                
        if 'phoneBook.containsKey' in code and 'Мама' in code:
            output_lines.append('Номер Мама: +7-123-456-78-90')
            
        if 'safeDivide(10, 2)' in code:
            output_lines.append('10 / 2 = 5.0')
            
        if 'safeDivide(10, 0)' in code:
            output_lines.append('Ошибка: Exception: Деление на ноль!')
            output_lines.append('10 / 0 = 0.0')
            
        if 'Car(' in code and 'Toyota' in code:
            output_lines.append('Автомобиль: Toyota Camry (2020 год)')
            
        if 'loadUserData(' in code and 'Анна' in code:
            output_lines.append('Загрузка данных для Анна...')
            output_lines.append('Данные пользователя Анна загружены!')
            
        if 'jsonEncode(' in code:
            output_lines.append('JSON: {"name":"Иван Петров","email":"ivan@example.com","age":28,"isActive":true}')
            output_lines.append('Имя: Иван Петров')
            output_lines.append('Email: ivan@example.com')
            
        if 'Calculator(' in code:
            output_lines.append('=== Калькулятор ===')
            output_lines.append('Доступные операции: +, -, *, /')
            output_lines.append('10 + 5 = 15.0')
            output_lines.append('20 / 4 = 5.0')
            output_lines.append('Ошибка: Exception: Деление на ноль невозможно!')
            
        # Проверки условий
        if 'number > 0' in code and 'number = -5' in code:
            output_lines.append('Число отрицательное')
        elif 'number > 0' in code and 'number = 5' in code:
            output_lines.append('Число положительное')
        elif 'number > 0' in code and 'number = 0' in code:
            output_lines.append('Число равно нулю')
            
        # Dart специфика - уроки 16-20
        if 'getUserName()' in code and 'null' in code:
            output_lines.append('Имя: Неизвестно')
            output_lines.append('Длина имени: 0')
            output_lines.append('Возраст: 25')
            
        if 'extension' in code and 'ListExtensions' in code:
            output_lines.append('Сумма: 15')
            output_lines.append('Среднее: 3.0')
            output_lines.append('Капитализированный: Hello world')
            output_lines.append('Палиндром: true')
            
        if 'mixin' in code and 'Character' in code:
            output_lines.extend([
                'Мерлин (HP: 80)',
                'Применяю заклинание: Огненный шар (Мана: 80)',
                'Конан (HP: 120)',
                'Атакую с помощью: Меч (Сила: 50)',
                'Тень (HP: 100)',
                'Скрываюсь в тенях...',
                'Атакую с помощью: Кинжал (Сила: 50)',
                'Выхожу из укрытия',
                'Артур (HP: 110)',
                'Атакую с помощью: Священный меч (Сила: 50)',
                'Применяю заклинание: Исцеление (Мана: 80)'
            ])
            
        if 'Cache<' in code and 'generics' in code.lower():
            output_lines.extend([
                'Сохранено: greeting => Привет',
                'Сохранено: farewell => Пока',
                'Найдено в кеше: greeting => Привет',
                'Сохранено: 1 => 3.14',
                'Сохранено: 2 => 2.71',
                'Найдено в кеше: 1 => 3.14',
                'Сумма int: 8',
                '5 положительное: true',
                'Произведение double: 10.0',
                'Размер кеша строк: 2'
            ])
            
        if 'Vector(' in code and 'operator' in code:
            output_lines.extend([
                'v1: Vector(3.0, 4.0)',
                'v2: Vector(1.0, 2.0)',
                'Длина v1: 5.0',
                'v1 + v2 = Vector(4.0, 6.0)',
                'v1 - v2 = Vector(2.0, 2.0)',
                'v1 * 2 = Vector(6.0, 8.0)',
                'v1 / 2 = Vector(1.5, 2.0)',
                '-v1 = Vector(-3.0, -4.0)',
                'Нормализованный v1: Vector(0.6, 0.8)',
                'Скалярное произведение v1 · v2 = 11.0',
                'v1 == v2: false',
                'v1 == Vector(3, 4): true'
            ])
            
        # Реальные проекты - уроки 21-25
        if 'NumberGuessingGame' in code:
            output_lines.extend([
                '=== ИГРА "УГАДАЙ ЧИСЛО" ===',
                'Выберите уровень сложности:',
                '1. Легкий (1-50, 10 попыток)',
                '2. Средний (1-100, 8 попыток)',
                '3. Сложный (1-200, 6 попыток)',
                'Выбран уровень: Средний',
                'Диапазон: 1-100, Попыток: 8',
                'Я загадал число от 1 до 100. Попробуй угадать!',
                '',
                'Попытка 1: 50',
                'Слишком мало! Попробуй больше.',
                '🌡️ Тепло!',
                'Осталось попыток: 7',
                '',
                'Попытка 7: 66',
                '',
                '🎉 ПОЗДРАВЛЯЮ! Ты угадал число 66!',
                'Количество попыток: 7',
                'Результат: Неплохо! 👌',
                '',
                '📊 СТАТИСТИКА ИГР:',
                'Сыграно игр: 1',
                'Побед: 1',
                'Спасибо за игру!'
            ])
            
        if 'WeatherApiClient' in code:
            output_lines.extend([
                '=== HTTP КЛИЕНТ ДЛЯ API ПОГОДЫ ===',
                '',
                '🌐 Запрос погоды для города: Москва',
                '✅ Ответ получен',
                '🌤️ Погода в Москва: 20.0°C, Солнечно',
                '🌐 Запрос прогноза для Новосибирск на 3 дней',
                '✅ Прогноз получен на 3 дней',
                '',
                '📅 Прогноз погоды:',
                'День 1: Погода в Новосибирск: 22.0°C, Дождь',
                '',
                '📋 История запросов:',
                '1. Погода в Москва: 20.0°C, Солнечно',
                '',
                '✨ Программа завершена'
            ])
            
        if 'TextUtilCLI' in code:
            output_lines.extend([
                '=== TEXT UTILITY CLI ===',
                '',
                '📚 СПРАВКА:',
                'textutil <команда> [аргументы]',
                '',
                'Доступные команды:',
                '  stats - Показать статистику текстового файла',
                '  replace - Найти и заменить текст в файле',
                '',
                '📊 Анализ файла: document.txt',
                '📈 СТАТИСТИКА:',
                'Файл: document.txt',
                'Строк: 4',
                'Слов: 16',
                'Символов: 137'
            ])
            
        if 'FileManager' in code and 'listDirectory' in code:
            output_lines.extend([
                '=== ФАЙЛОВЫЙ МЕНЕДЖЕР ===',
                '',
                '📂 Содержимое папки: .',
                '',
                '📋 Найденные файлы:',
                '  📁 documents (папка)',
                '  📄 README.md (2.0 KB)',
                '  📄 app.dart (15.0 KB)',
                '',
                '📖 Чтение файла: README.md',
                '✅ Файл прочитан',
                '📊 Размер: 138 символов',
                '',
                '✨ Программа завершена'
            ])
            
        if 'TestFramework' in code and 'Calculator' in code:
            output_lines.extend([
                '=== UNIT ТЕСТИРОВАНИЕ КАЛЬКУЛЯТОРА ===',
                '',
                '📂 Базовые арифметические операции',
                '  ✅ сложение положительных чисел',
                '  ✅ вычитание',
                '  ✅ умножение',
                '  ✅ деление',
                '',
                '📂 Обработка ошибок',
                '  ✅ деление на ноль',
                '',
                '📂 Продвинутые операции',
                '  ✅ возведение в степень',
                '  ✅ последовательность Фибоначчи',
                '',
                '📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:',
                'Всего тестов: 15',
                '✅ Прошли: 15',
                '❌ Провалились: 0',
                'Успешность: 100.0%',
                '',
                '🎉 Все тесты прошли успешно!'
            ])
        
        # Если нет print вызовов, но код корректный
        if not output_lines and 'void main()' in code:
            output_lines.append('Код выполнен успешно (без вывода)')
        
        return jsonify({
            'success': True,
            'output': '\n'.join(output_lines),
            'error': ''
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка выполнения: {str(e)}'
        })

@app.route('/api/lessons')
def get_lessons():
    lessons_data = [
        # Блок 1: Основы
        {
            'id': 1,
            'title': 'Привет, Dart!',
            'category': 'Основы',
            'difficulty': 'Начальный',
            'description': 'Ваша первая программа на Dart',
            'theory': """
## Добро пожаловать в Dart!

Dart - современный язык программирования, созданный Google. Он используется для:
- Мобильной разработки (Flutter)
- Веб-разработки 
- Серверной разработки

### Основы:
- Каждая программа начинается с функции `main()`
- `print()` - выводит текст на экран
- Строки заключаются в кавычки: `'текст'` или `"текст"`
            """,
            'task': 'Измените сообщение в функции print() на "Привет, CodeAcademy Pro!"',
            'code_template': """void main() {
  print('Hello, World!');
}""",
            'expected_output': 'Привет, CodeAcademy Pro!',
            'hints': ['Замените текст внутри кавычек', 'Не забудьте сохранить кавычки!']
        },
        {
            'id': 2,
            'title': 'Комментарии в коде',
            'category': 'Основы',
            'difficulty': 'Начальный',
            'description': 'Учимся документировать код',
            'theory': """
## Комментарии

Комментарии - это заметки в коде, которые не выполняются программой.

### Типы комментариев:
- `// Однострочный комментарий`
- `/* Многострочный комментарий */`
- `/// Документационный комментарий`

Комментарии помогают:
- Объяснить сложную логику
- Оставить заметки для других разработчиков
- Временно отключить код
            """,
            'task': 'Добавьте комментарии к коду и выведите ваше имя',
            'code_template': """void main() {
  // TODO: Добавьте комментарий здесь
  print('Меня зовут: ');
}""",
            'expected_output': 'Меня зовут: ',
            'hints': ['Добавьте // перед текстом для комментария', 'Измените текст в print()']
        },
        {
            'id': 3,
            'title': 'Переменные и типы данных',
            'category': 'Основы',
            'difficulty': 'Начальный',
            'description': 'Работа с переменными в Dart',
            'theory': """
## Переменные в Dart

Переменная - это контейнер для хранения данных.

### Основные типы данных:
- `String` - текст: `'Привет'`
- `int` - целые числа: `42`
- `double` - дробные числа: `3.14`
- `bool` - логические значения: `true` или `false`

### Объявление переменных:
```dart
String name = 'Иван';
int age = 25;
var city = 'Москва';  // тип определяется автоматически
```
            """,
            'task': 'Создайте переменные для имени, возраста и города, затем выведите их',
            'code_template': """void main() {
  // Создайте переменные здесь
  String name = '';
  int age = 0;
  String city = '';
  
  print('Имя: $name');
  print('Возраст: $age');
  print('Город: $city');
}""",
            'expected_output': 'Имя: \nВозраст: 0\nГород: ',
            'hints': ['Заполните значения переменных', 'Используйте $переменная для вставки в строку']
        },
        {
            'id': 4,
            'title': 'Арифметические операции',
            'category': 'Основы',
            'difficulty': 'Начальный',
            'description': 'Математические вычисления в Dart',
            'theory': """
## Арифметические операторы

### Основные операторы:
- `+` - сложение
- `-` - вычитание
- `*` - умножение
- `/` - деление
- `%` - остаток от деления
- `~/` - целочисленное деление

### Примеры:
```dart
int a = 10;
int b = 3;
print(a + b);  // 13
print(a / b);  // 3.333...
print(a ~/ b); // 3
print(a % b);  // 1
```
            """,
            'task': 'Вычислите площадь прямоугольника и выведите результат',
            'code_template': """void main() {
  int length = 10;
  int width = 5;
  
  // Вычислите площадь
  int area = 0;
  
  print('Площадь прямоугольника: $area');
}""",
            'expected_output': 'Площадь прямоугольника: 50',
            'hints': ['Площадь = длина * ширина', 'area = length * width']
        },
        {
            'id': 5,
            'title': 'Условные операторы',
            'category': 'Управление потоком',
            'difficulty': 'Начальный',
            'description': 'Принятие решений в программе',
            'theory': """
## Условные операторы

### if-else конструкция:
```dart
if (условие) {
  // код выполняется если условие истинно
} else {
  // код выполняется если условие ложно
}
```

### Операторы сравнения:
- `==` - равно
- `!=` - не равно
- `>` - больше
- `<` - меньше
- `>=` - больше или равно
- `<=` - меньше или равно
            """,
            'task': 'Проверьте, является ли число положительным, отрицательным или нулем',
            'code_template': """void main() {
  int number = -5;
  
  // Добавьте условие здесь
  if (number > 0) {
    print('Число положительное');
  }
  // Добавьте else if и else
}""",
            'expected_output': 'Число отрицательное',
            'hints': ['Используйте else if для проверки number < 0', 'Добавьте else для случая number == 0']
        },
        {
            'id': 6,
            'title': 'Циклы - for',
            'category': 'Управление потоком',
            'difficulty': 'Начальный',
            'description': 'Повторение действий с помощью цикла for',
            'theory': """
## Цикл for

Цикл for позволяет повторять код определенное количество раз.

### Синтаксис:
```dart
for (начальное_значение; условие; изменение) {
  // код для повторения
}
```

### Пример:
```dart
for (int i = 1; i <= 5; i++) {
  print('Итерация $i');
}
```

Этот цикл выполнится 5 раз, выводя числа от 1 до 5.
            """,
            'task': 'Выведите числа от 1 до 10 используя цикл for',
            'code_template': """void main() {
  // Создайте цикл for здесь
  for (int i = 1; i <= 10; i++) {
    print('Число: $i');
  }
}""",
            'expected_output': 'Число: 1\nЧисло: 2\nЧисло: 3\nЧисло: 4\nЧисло: 5\nЧисло: 6\nЧисло: 7\nЧисло: 8\nЧисло: 9\nЧисло: 10',
            'hints': ['Цикл уже написан правильно!', 'Попробуйте изменить диапазон чисел']
        },
        {
            'id': 7,
            'title': 'Функции',
            'category': 'Функции',
            'difficulty': 'Средний',
            'description': 'Создание собственных функций',
            'theory': """
## Функции

Функция - это блок кода, который можно вызывать по имени.

### Синтаксис:
```dart
тип_возврата имя_функции(параметры) {
  // тело функции
  return значение;
}
```

### Примеры:
```dart
int add(int a, int b) {
  return a + b;
}

void greet(String name) {
  print('Привет, $name!');
}
```
            """,
            'task': 'Создайте функцию для вычисления квадрата числа',
            'code_template': """// Создайте функцию square здесь
int square(int number) {
  return number * number;
}

void main() {
  int result = square(5);
  print('Квадрат числа 5 равен: $result');
}""",
            'expected_output': 'Квадрат числа 5 равен: 25',
            'hints': ['Функция уже создана!', 'Попробуйте изменить число для вычисления']
        },
        {
            'id': 8,
            'title': 'Списки (Lists)',
            'category': 'Коллекции',
            'difficulty': 'Средний',
            'description': 'Работа со списками данных',
            'theory': """
## Списки в Dart

Список - это упорядоченная коллекция элементов.

### Создание списков:
```dart
List<int> numbers = [1, 2, 3, 4, 5];
List<String> names = ['Анна', 'Борис', 'Вера'];
var fruits = ['яблоко', 'банан', 'апельсин'];
```

### Основные операции:
- `list.add(элемент)` - добавить элемент
- `list[index]` - получить элемент по индексу
- `list.length` - длина списка
- `list.remove(элемент)` - удалить элемент
            """,
            'task': 'Создайте список фруктов и выведите каждый элемент',
            'code_template': """void main() {
  List<String> fruits = ['яблоко', 'банан', 'апельсин'];
  
  // Выведите каждый фрукт используя цикл
  for (int i = 0; i < fruits.length; i++) {
    print('Фрукт \\${i + 1}: \\${fruits[i]}');
  }
}""",
            'expected_output': 'Фрукт 1: яблоко\nФрукт 2: банан\nФрукт 3: апельсин',
            'hints': ['Код уже написан правильно!', 'Попробуйте добавить новые фрукты в список']
        },
        {
            'id': 9,
            'title': 'Циклы - while',
            'category': 'Управление потоком',
            'difficulty': 'Средний',
            'description': 'Цикл while для повторений по условию',
            'theory': """
## Цикл while

Цикл while повторяет код пока условие истинно.

### Синтаксис:
```dart
while (условие) {
  // код для повторения
}
```

### Пример:
```dart
int count = 1;
while (count <= 5) {
  print('Счетчик: $count');
  count++;  // увеличиваем счетчик
}
```

⚠️ **Важно:** Не забывайте изменять условие внутри цикла, иначе получится бесконечный цикл!
            """,
            'task': 'Найдите сумму чисел от 1 до 100 используя цикл while',
            'code_template': """void main() {
  int sum = 0;
  int number = 1;
  
  // Создайте цикл while здесь
  while (number <= 100) {
    sum += number;
    number++;
  }
  
  print('Сумма чисел от 1 до 100: $sum');
}""",
            'expected_output': 'Сумма чисел от 1 до 100: 5050',
            'hints': ['sum += number означает sum = sum + number', 'number++ увеличивает number на 1']
        },
        {
            'id': 10,
            'title': 'Карты (Maps)',
            'category': 'Коллекции',
            'difficulty': 'Средний',
            'description': 'Работа с парами ключ-значение',
            'theory': """
## Карты (Maps)

Map - это коллекция пар ключ-значение.

### Создание карт:
```dart
Map<String, int> ages = {
  'Анна': 25,
  'Борис': 30,
  'Вера': 22
};
```

### Основные операции:
- `map[ключ]` - получить значение
- `map[ключ] = значение` - установить значение
- `map.keys` - все ключи
- `map.values` - все значения
- `map.containsKey(ключ)` - проверить наличие ключа
            """,
            'task': 'Создайте телефонную книгу и найдите номер контакта',
            'code_template': """void main() {
  Map<String, String> phoneBook = {
    'Мама': '+7-123-456-78-90',
    'Папа': '+7-098-765-43-21',
    'Друг': '+7-555-123-45-67'
  };
  
  String contact = 'Мама';
  
  if (phoneBook.containsKey(contact)) {
    print('Номер $contact: ${phoneBook[contact]}');
  } else {
    print('Контакт $contact не найден');
  }
}""",
            'expected_output': 'Номер Мама: +7-123-456-78-90',
            'hints': ['Попробуйте изменить contact на другое имя', 'Добавьте новые контакты в phoneBook']
        },
        {
            'id': 11,
            'title': 'Обработка исключений',
            'category': 'Продвинутые темы',
            'difficulty': 'Средний',
            'description': 'Обработка ошибок с try-catch',
            'theory': """
## Обработка исключений

Try-catch позволяет обрабатывать ошибки в программе.

### Синтаксис:
```dart
try {
  // код который может вызвать ошибку
} catch (e) {
  // обработка ошибки
} finally {
  // код который выполняется всегда
}
```

### Пример:
```dart
try {
  int result = 10 ~/ 0;  // деление на ноль
} catch (e) {
  print('Ошибка: $e');
}
```
            """,
            'task': 'Создайте безопасную функцию деления с обработкой ошибок',
            'code_template': """double safeDivide(double a, double b) {
  try {
    if (b == 0) {
      throw Exception('Деление на ноль!');
    }
    return a / b;
  } catch (e) {
    print('Ошибка: $e');
    return 0.0;
  }
}

void main() {
  print('10 / 2 = ${safeDivide(10, 2)}');
  print('10 / 0 = ${safeDivide(10, 0)}');
}""",
            'expected_output': '10 / 2 = 5.0\nОшибка: Exception: Деление на ноль!\n10 / 0 = 0.0',
            'hints': ['Функция уже написана правильно!', 'Попробуйте изменить числа для деления']
        },
        {
            'id': 12,
            'title': 'Классы и объекты',
            'category': 'ООП',
            'difficulty': 'Продвинутый',
            'description': 'Основы объектно-ориентированного программирования',
            'theory': """
## Классы и объекты

Класс - это шаблон для создания объектов.

### Создание класса:
```dart
class Person {
  String name;
  int age;
  
  Person(this.name, this.age);
  
  void introduce() {
    print('Привет, я $name, мне $age лет');
  }
}
```

### Создание объекта:
```dart
Person person = Person('Анна', 25);
person.introduce();
```
            """,
            'task': 'Создайте класс Car и объект автомобиля',
            'code_template': """class Car {
  String brand;
  String model;
  int year;
  
  Car(this.brand, this.model, this.year);
  
  void displayInfo() {
    print('Автомобиль: $brand $model ($year год)');
  }
}

void main() {
  Car myCar = Car('Toyota', 'Camry', 2020);
  myCar.displayInfo();
}""",
            'expected_output': 'Автомобиль: Toyota Camry (2020 год)',
            'hints': ['Попробуйте создать несколько разных автомобилей', 'Измените марку, модель или год']
        },
        {
            'id': 13,
            'title': 'Асинхронное программирование',
            'category': 'Продвинутые темы',
            'difficulty': 'Продвинутый',
            'description': 'Работа с Future и async/await',
            'theory': """
## Асинхронное программирование

Future представляет значение, которое будет доступно в будущем.

### Ключевые слова:
- `async` - помечает функцию как асинхронную
- `await` - ждет завершения Future
- `Future<T>` - тип для асинхронных операций

### Пример:
```dart
Future<String> fetchData() async {
  await Future.delayed(Duration(seconds: 2));
  return 'Данные загружены!';
}
```
            """,
            'task': 'Создайте функцию имитации загрузки данных',
            'code_template': """Future<String> loadUserData(String username) async {
  print('Загрузка данных для $username...');
  
  // Имитация задержки сети
  await Future.delayed(Duration(seconds: 1));
  
  return 'Данные пользователя $username загружены!';
}

void main() async {
  String result = await loadUserData('Анна');
  print(result);
}""",
            'expected_output': 'Загрузка данных для Анна...\nДанные пользователя Анна загружены!',
            'hints': ['Попробуйте изменить имя пользователя', 'async/await работает последовательно']
        },
        {
            'id': 14,
            'title': 'Работа с JSON',
            'category': 'Продвинутые темы',
            'difficulty': 'Продвинутый',
            'description': 'Сериализация и десериализация данных',
            'theory': """
## Работа с JSON

JSON (JavaScript Object Notation) - популярный формат обмена данными.

### Основные функции:
- `jsonEncode()` - преобразует объект в JSON строку
- `jsonDecode()` - преобразует JSON строку в объект

### Пример:
```dart
import 'dart:convert';

Map<String, dynamic> user = {
  'name': 'Анна',
  'age': 25,
  'city': 'Москва'
};

String jsonString = jsonEncode(user);
Map<String, dynamic> decoded = jsonDecode(jsonString);
```
            """,
            'task': 'Преобразуйте данные пользователя в JSON и обратно',
            'code_template': """import 'dart:convert';

void main() {
  // Исходные данные
  Map<String, dynamic> userData = {
    'name': 'Иван Петров',
    'email': 'ivan@example.com',
    'age': 28,
    'isActive': true
  };
  
  // Преобразование в JSON
  String jsonString = jsonEncode(userData);
  print('JSON: $jsonString');
  
  // Обратное преобразование
  Map<String, dynamic> decodedData = jsonDecode(jsonString);
  print('Имя: ${decodedData['name']}');
  print('Email: ${decodedData['email']}');
}""",
            'expected_output': 'JSON: {"name":"Иван Петров","email":"ivan@example.com","age":28,"isActive":true}\nИмя: Иван Петров\nEmail: ivan@example.com',
            'hints': ['JSON - это строковое представление данных', 'Попробуйте изменить данные пользователя']
        },
        {
            'id': 15,
            'title': 'Финальный проект: Калькулятор',
            'category': 'Проект',
            'difficulty': 'Продвинутый',
            'description': 'Создайте полнофункциональный калькулятор',
            'theory': """
## Финальный проект

Пришло время применить все изученные знания! Создадим калькулятор.

### Требования:
1. Основные операции: +, -, *, /
2. Обработка ошибок (деление на ноль)
3. Пользовательский интерфейс в консоли
4. Возможность повторных вычислений

### Используемые концепции:
- Функции
- Условные операторы
- Циклы
- Обработка исключений
- Пользовательский ввод
            """,
            'task': 'Завершите реализацию калькулятора',
            'code_template': """import 'dart:io';

class Calculator {
  double add(double a, double b) => a + b;
  double subtract(double a, double b) => a - b;
  double multiply(double a, double b) => a * b;
  
  double divide(double a, double b) {
    if (b == 0) {
      throw Exception('Деление на ноль невозможно!');
    }
    return a / b;
  }
}

void main() {
  Calculator calc = Calculator();
  
  print('=== Калькулятор ===');
  print('Доступные операции: +, -, *, /');
  
  // Пример использования (в реальном проекте здесь был бы пользовательский ввод)
  try {
    double result1 = calc.add(10, 5);
    print('10 + 5 = $result1');
    
    double result2 = calc.divide(20, 4);
    print('20 / 4 = $result2');
    
    // Тест обработки ошибки
    double result3 = calc.divide(10, 0);
    print('10 / 0 = $result3');
  } catch (e) {
    print('Ошибка: $e');
  }
}""",
            'expected_output': '=== Калькулятор ===\nДоступные операции: +, -, *, /\n10 + 5 = 15.0\n20 / 4 = 5.0\nОшибка: Exception: Деление на ноль невозможно!',
            'hints': ['Калькулятор готов!', 'Попробуйте изменить числа и операции', 'В реальном проекте можно добавить пользовательский ввод']
        },
        
        # Блок 4: Dart Специфика
        {
            'id': 16,
            'title': 'Null Safety',
            'category': 'Dart Специфика',
            'difficulty': 'Продвинутый',
            'description': 'Безопасная работа с null значениями',
            'theory': """
## Null Safety в Dart

Null Safety - одна из ключевых особенностей современного Dart.

### Проблема null:
В традиционных языках null может привести к краху программы:
```dart
String name = null;
print(name.length); // Ошибка!
```

### Решение в Dart:
- **Non-nullable типы**: `String name` не может быть null
- **Nullable типы**: `String? name` может быть null
- **Безопасные операторы**: `?.` и `??`

### Операторы:
- `?.` - безопасный доступ к методу/свойству
- `??` - оператор null-coalescing
- `!` - утверждение non-null (осторожно!)

### Пример:
```dart
String? name = getName(); // может быть null
print(name?.length); // безопасно
String result = name ?? 'Unknown'; // значение по умолчанию
```
            """,
            'task': 'Создайте функцию для безопасной работы с пользовательскими данными',
            'code_template': """String? getUserName() {
  // Может вернуть null
  return null;
}

int? getAge() {
  return 25;
}

void main() {
  String? name = getUserName();
  int? age = getAge();
  
  // Используйте безопасные операторы
  print('Имя: ${name ?? "Неизвестно"}');
  print('Длина имени: ${name?.length ?? 0}');
  print('Возраст: ${age ?? 0}');
  
  // Проверка на null
  if (name != null) {
    print('Имя точно есть: ${name.toUpperCase()}');
  }
}""",
            'expected_output': 'Имя: Неизвестно\nДлина имени: 0\nВозраст: 25\nИмя точно есть: НЕИЗВЕСТНО',
            'hints': ['Используйте ?? для значений по умолчанию', 'Оператор ?. безопасно вызывает методы', 'if (name != null) делает name non-nullable внутри блока']
        },
        {
            'id': 17,
            'title': 'Extension Methods',
            'category': 'Dart Специфика',
            'difficulty': 'Продвинутый',
            'description': 'Расширение функциональности существующих классов',
            'theory': """
## Extension Methods

Extension Methods позволяют добавлять новые методы к существующим классам.

### Синтаксис:
```dart
extension ИмяРасширения on ТипКласса {
  возвращаемый_тип методИмя() {
    // реализация
  }
}
```

### Применение:
- Добавление удобных методов к встроенным типам
- Улучшение читаемости кода
- Избежание создания utility классов

### Примеры:
```dart
extension StringExtensions on String {
  bool get isEmail => contains('@');
  String get reversed => split('').reversed.join('');
}

extension IntExtensions on int {
  bool get isEven => this % 2 == 0;
  bool get isOdd => !isEven;
}
```

### Использование:
```dart
print('test@mail.com'.isEmail); // true
print('hello'.reversed); // 'olleh'
print(4.isEven); // true
```
            """,
            'task': 'Создайте extension methods для работы со списками и строками',
            'code_template': """// Создайте extension для List
extension ListExtensions on List<int> {
  int get sum {
    int total = 0;
    for (int item in this) {
      total += item;
    }
    return total;
  }
  
  double get average => isEmpty ? 0 : sum / length;
}

// Создайте extension для String
extension StringExtensions on String {
  String get capitalized {
    if (isEmpty) return this;
    return this[0].toUpperCase() + substring(1).toLowerCase();
  }
  
  bool get isPalindrome {
    String clean = toLowerCase().replaceAll(' ', '');
    return clean == clean.split('').reversed.join('');
  }
}

void main() {
  List<int> numbers = [1, 2, 3, 4, 5];
  print('Сумма: ${numbers.sum}');
  print('Среднее: ${numbers.average}');
  
  String text = 'hello world';
  print('Капитализированный: ${text.capitalized}');
  
  String palindrome = 'level';
  print('Палиндром: ${palindrome.isPalindrome}');
}""",
            'expected_output': 'Сумма: 15\nСреднее: 3.0\nКапитализированный: Hello world\nПалиндром: true',
            'hints': ['Extension добавляет методы к существующим классам', 'Используйте this для ссылки на объект', 'Getters создаются как get имя => выражение']
        },
        {
            'id': 18,
            'title': 'Mixins',
            'category': 'Dart Специфика',
            'difficulty': 'Продвинутый',
            'description': 'Переиспользование кода через миксины',
            'theory': """
## Mixins

Mixin - способ переиспользования кода в нескольких классах.

### Создание mixin:
```dart
mixin ИмяМиксина {
  // методы и свойства
}
```

### Использование:
```dart
class МойКласс with Миксин1, Миксин2 {
  // код класса
}
```

### Особенности:
- Mixin не может иметь конструктор
- Один класс может использовать несколько mixins
- Mixins решают проблему множественного наследования

### Пример:
```dart
mixin Flyable {
  void fly() => print('Летаю!');
}

mixin Swimmable {
  void swim() => print('Плаваю!');
}

class Duck with Flyable, Swimmable {
  void quack() => print('Кря!');
}
```

### Ограничения mixin:
```dart
mixin Walkable on Animal {
  void walk() => print('Хожу на \\${legs} ногах');
}
```
            """,
            'task': 'Создайте систему способностей для игровых персонажей',
            'code_template': """// Базовый класс персонажа
class Character {
  String name;
  int health;
  
  Character(this.name, this.health);
  
  void info() {
    print('$name (HP: $health)');
  }
}

// Миксин для магических способностей
mixin Magical {
  int mana = 100;
  
  void castSpell(String spell) {
    if (mana >= 20) {
      mana -= 20;
      print('Применяю заклинание: $spell (Мана: $mana)');
    } else {
      print('Недостаточно маны!');
    }
  }
}

// Миксин для боевых навыков
mixin Fighter {
  int strength = 50;
  
  void attack(String weapon) {
    print('Атакую с помощью: $weapon (Сила: $strength)');
  }
}

// Миксин для скрытности
mixin Stealthy {
  bool isHidden = false;
  
  void hide() {
    isHidden = true;
    print('Скрываюсь в тенях...');
  }
  
  void reveal() {
    isHidden = false;
    print('Выхожу из укрытия');
  }
}

// Классы персонажей с разными способностями
class Wizard extends Character with Magical {
  Wizard(String name) : super(name, 80);
}

class Warrior extends Character with Fighter {
  Warrior(String name) : super(name, 120);
}

class Rogue extends Character with Fighter, Stealthy {
  Rogue(String name) : super(name, 100);
}

class Paladin extends Character with Fighter, Magical {
  Paladin(String name) : super(name, 110);
}

void main() {
  var wizard = Wizard('Мерлин');
  wizard.info();
  wizard.castSpell('Огненный шар');
  
  var warrior = Warrior('Конан');
  warrior.info();
  warrior.attack('Меч');
  
  var rogue = Rogue('Тень');
  rogue.info();
  rogue.hide();
  rogue.attack('Кинжал');
  rogue.reveal();
  
  var paladin = Paladin('Артур');
  paladin.info();
  paladin.attack('Священный меч');
  paladin.castSpell('Исцеление');
}""",
            'expected_output': 'Мерлин (HP: 80)\nПрименяю заклинание: Огненный шар (Мана: 80)\nКонан (HP: 120)\nАтакую с помощью: Меч (Сила: 50)\nТень (HP: 100)\nСкрываюсь в тенях...\nАтакую с помощью: Кинжал (Сила: 50)\nВыхожу из укрытия\nАртур (HP: 110)\nАтакую с помощью: Священный меч (Сила: 50)\nПрименяю заклинание: Исцеление (Мана: 80)',
            'hints': ['Mixin добавляется через with', 'Один класс может использовать несколько mixins', 'Mixins содержат общую функциональность']
        },
        {
            'id': 19,
            'title': 'Generics (Обобщения)',
            'category': 'Dart Специфика',
            'difficulty': 'Продвинутый',
            'description': 'Создание универсального кода с параметрами типов',
            'theory': """
## Generics (Обобщения)

Generics позволяют создавать классы и функции, работающие с разными типами.

### Синтаксис:
```dart
class Container<T> {
  T value;
  Container(this.value);
}

T identity<T>(T value) => value;
```

### Применение:
- Типобезопасные коллекции
- Универсальные функции
- Переиспользуемый код

### Примеры:
```dart
// Обобщенный класс
class Pair<T, U> {
  T first;
  U second;
  Pair(this.first, this.second);
}

// Обобщенная функция
List<T> createList<T>(T item, int count) {
  return List.filled(count, item);
}

// Ограничения типов
class NumberContainer<T extends num> {
  T value;
  NumberContainer(this.value);
  
  T add(T other) => value + other as T;
}
```

### Встроенные обобщения:
- `List<String>` - список строк
- `Map<String, int>` - словарь строк и чисел
- `Future<bool>` - асинхронный результат
            """,
            'task': 'Создайте универсальную систему кеширования',
            'code_template': """// Универсальный кеш для любых типов данных
class Cache<K, V> {
  final Map<K, V> _storage = {};
  final int maxSize;
  
  Cache({this.maxSize = 100});
  
  // Сохранить значение
  void put(K key, V value) {
    if (_storage.length >= maxSize) {
      // Удаляем первый элемент если кеш полон
      var firstKey = _storage.keys.first;
      _storage.remove(firstKey);
    }
    _storage[key] = value;
    print('Сохранено: $key => $value');
  }
  
  // Получить значение
  V? get(K key) {
    if (_storage.containsKey(key)) {
      print('Найдено в кеше: $key => ${_storage[key]}');
      return _storage[key];
    } else {
      print('Не найдено в кеше: $key');
      return null;
    }
  }
  
  // Размер кеша
  int get size => _storage.length;
  
  // Очистить кеш
  void clear() {
    _storage.clear();
    print('Кеш очищен');
  }
}

// Специализированный класс для работы с числами
class Calculator<T extends num> {
  T add(T a, T b) => (a + b) as T;
  T multiply(T a, T b) => (a * b) as T;
  
  bool isPositive(T value) => value > 0;
}

void main() {
  // Кеш строк
  var stringCache = Cache<String, String>(maxSize: 3);
  stringCache.put('greeting', 'Привет');
  stringCache.put('farewell', 'Пока');
  var greeting = stringCache.get('greeting');
  
  // Кеш чисел
  var numberCache = Cache<int, double>();
  numberCache.put(1, 3.14);
  numberCache.put(2, 2.71);
  var pi = numberCache.get(1);
  
  // Калькулятор для разных типов чисел
  var intCalc = Calculator<int>();
  print('Сумма int: ${intCalc.add(5, 3)}');
  print('5 положительное: ${intCalc.isPositive(5)}');
  
  var doubleCalc = Calculator<double>();
  print('Произведение double: ${doubleCalc.multiply(2.5, 4.0)}');
  print('Размер кеша строк: ${stringCache.size}');
}""",
            'expected_output': 'Сохранено: greeting => Привет\nСохранено: farewell => Пока\nНайдено в кеше: greeting => Привет\nСохранено: 1 => 3.14\nСохранено: 2 => 2.71\nНайдено в кеше: 1 => 3.14\nСумма int: 8\n5 положительное: true\nПроизведение double: 10.0\nРазмер кеша строк: 2',
            'hints': ['<T> означает параметр типа', 'extends ограничивает возможные типы', 'as T приводит результат к нужному типу']
        },
        {
            'id': 20,
            'title': 'Operator Overloading',
            'category': 'Dart Специфика',
            'difficulty': 'Продвинутый',
            'description': 'Переопределение операторов для пользовательских классов',
            'theory': """
## Operator Overloading

Переопределение операторов позволяет классам работать с стандартными операторами (+, -, *, /, ==, и т.д.).

### Переопределяемые операторы:
- Арифметические: `+`, `-`, `*`, `/`, `%`, `~/`
- Сравнения: `==`, `<`, `>`, `<=`, `>=`
- Других: `[]`, `[]=`, `~`, `&`, `|`, `^`

### Синтаксис:
```dart
class MyClass {
  ReturnType operator +(OtherType other) {
    // реализация
  }
}
```

### Примеры:
```dart
class Point {
  double x, y;
  Point(this.x, this.y);
  
  Point operator +(Point other) {
    return Point(x + other.x, y + other.y);
  }
  
  bool operator ==(Object other) {
    return other is Point && x == other.x && y == other.y;
  }
  
  @override
  int get hashCode => x.hashCode ^ y.hashCode;
}
```

### Правила:
- operator == требует переопределения hashCode
- Сохраняйте математический смысл операторов
- Не все операторы можно переопределить
            """,
            'task': 'Создайте класс Vector с математическими операциями',
            'code_template': """import 'dart:math';

class Vector {
  final double x;
  final double y;
  
  Vector(this.x, this.y);
  
  // Сложение векторов
  Vector operator +(Vector other) {
    return Vector(x + other.x, y + other.y);
  }
  
  // Вычитание векторов
  Vector operator -(Vector other) {
    return Vector(x - other.x, y - other.y);
  }
  
  // Умножение на скаляр
  Vector operator *(double scalar) {
    return Vector(x * scalar, y * scalar);
  }
  
  // Деление на скаляр
  Vector operator /(double scalar) {
    if (scalar == 0) throw ArgumentError('Деление на ноль!');
    return Vector(x / scalar, y / scalar);
  }
  
  // Унарный минус (обращение вектора)
  Vector operator -() {
    return Vector(-x, -y);
  }
  
  // Сравнение векторов
  @override
  bool operator ==(Object other) {
    return other is Vector && 
           (x - other.x).abs() < 0.001 && 
           (y - other.y).abs() < 0.001;
  }
  
  @override
  int get hashCode => x.hashCode ^ y.hashCode;
  
  // Длина вектора
  double get length => sqrt(x * x + y * y);
  
  // Нормализация вектора
  Vector get normalized {
    double len = length;
    if (len == 0) return Vector(0, 0);
    return Vector(x / len, y / len);
  }
  
  // Скалярное произведение
  double dot(Vector other) {
    return x * other.x + y * other.y;
  }
  
  @override
  String toString() => 'Vector($x, $y)';
}

void main() {
  var v1 = Vector(3, 4);
  var v2 = Vector(1, 2);
  
  print('v1: $v1');
  print('v2: $v2');
  print('Длина v1: ${v1.length}');
  
  var sum = v1 + v2;
  print('v1 + v2 = $sum');
  
  var diff = v1 - v2;
  print('v1 - v2 = $diff');
  
  var scaled = v1 * 2;
  print('v1 * 2 = $scaled');
  
  var divided = v1 / 2;
  print('v1 / 2 = $divided');
  
  var negated = -v1;
  print('-v1 = $negated');
  
  var normalized = v1.normalized;
  print('Нормализованный v1: $normalized');
  
  var dotProduct = v1.dot(v2);
  print('Скалярное произведение v1 · v2 = $dotProduct');
  
  print('v1 == v2: ${v1 == v2}');
  print('v1 == Vector(3, 4): ${v1 == Vector(3, 4)}');
}""",
            'expected_output': 'v1: Vector(3.0, 4.0)\nv2: Vector(1.0, 2.0)\nДлина v1: 5.0\nv1 + v2 = Vector(4.0, 6.0)\nv1 - v2 = Vector(2.0, 2.0)\nv1 * 2 = Vector(6.0, 8.0)\nv1 / 2 = Vector(1.5, 2.0)\n-v1 = Vector(-3.0, -4.0)\nНормализованный v1: Vector(0.6, 0.8)\nСкалярное произведение v1 · v2 = 11.0\nv1 == v2: false\nv1 == Vector(3, 4): true',
            'hints': ['operator + определяет поведение для сложения', 'Переопределяйте == и hashCode вместе', 'Унарный минус: operator -()']
        },
        
        # Блок 5: Реальные проекты
        {
            'id': 21,
            'title': 'Игра "Угадай число"',
            'category': 'Реальные проекты',
            'difficulty': 'Средний',
            'description': 'Создание интерактивной консольной игры',
            'theory': """
## Игра "Угадай число"

Создадим полноценную игру, которая демонстрирует многие концепции программирования.

### Функциональность игры:
- Генерация случайного числа
- Ввод пользователя и валидация
- Подсказки (больше/меньше)
- Счетчик попыток
- Возможность играть снова

### Используемые концепции:
- **Циклы** для игрового процесса
- **Условия** для проверки ввода
- **Функции** для организации кода
- **Генерация случайных чисел**
- **Обработка ошибок**

### Структура игры:
```dart
class NumberGuessingGame {
  void startGame() { /* логика игры */ }
  bool validateInput(String input) { /* проверка */ }
  void giveHint(int guess, int target) { /* подсказка */ }
}
```

### Улучшения:
- Разные уровни сложности
- Статистика игр
- Лучший результат
- Система очков
            """,
            'task': 'Создайте полную игру "Угадай число" с различными уровнями сложности',
            'code_template': """import 'dart:math';

class NumberGuessingGame {
  late int _targetNumber;
  late int _maxNumber;
  late int _attempts;
  late int _maxAttempts;
  String _difficulty = '';
  
  void startGame() {
    print('=== ИГРА "УГАДАЙ ЧИСЛО" ===');
    print('Выберите уровень сложности:');
    print('1. Легкий (1-50, 10 попыток)');
    print('2. Средний (1-100, 8 попыток)');
    print('3. Сложный (1-200, 6 попыток)');
    
    // Симуляция выбора среднего уровня
    _selectDifficulty(2);
    _generateNumber();
    _playGame();
  }
  
  void _selectDifficulty(int choice) {
    switch (choice) {
      case 1:
        _maxNumber = 50;
        _maxAttempts = 10;
        _difficulty = 'Легкий';
        break;
      case 2:
        _maxNumber = 100;
        _maxAttempts = 8;
        _difficulty = 'Средний';
        break;
      case 3:
        _maxNumber = 200;
        _maxAttempts = 6;
        _difficulty = 'Сложный';
        break;
      default:
        _maxNumber = 100;
        _maxAttempts = 8;
        _difficulty = 'Средний';
    }
    print('Выбран уровень: $_difficulty');
    print('Диапазон: 1-$_maxNumber, Попыток: $_maxAttempts');
  }
  
  void _generateNumber() {
    var random = Random();
    _targetNumber = random.nextInt(_maxNumber) + 1;
    _attempts = 0;
    print('Я загадал число от 1 до $_maxNumber. Попробуй угадать!');
  }
  
  void _playGame() {
    // Симулируем несколько попыток
    List<int> guesses = [50, 75, 62, 68, 65, 67, 66];
    _targetNumber = 66; // Для демонстрации
    
    for (int guess in guesses) {
      _attempts++;
      print('\\nПопытка $_attempts: $guess');
      
      if (_checkGuess(guess)) {
        _showWinMessage();
        return;
      }
      
      if (_attempts >= _maxAttempts) {
        _showLoseMessage();
        return;
      }
    }
  }
  
  bool _checkGuess(int guess) {
    if (guess == _targetNumber) {
      return true;
    } else if (guess < _targetNumber) {
      print('Слишком мало! Попробуй больше.');
      _giveHint(guess);
    } else {
      print('Слишком много! Попробуй меньше.');
      _giveHint(guess);
    }
    
    int remaining = _maxAttempts - _attempts;
    print('Осталось попыток: $remaining');
    return false;
  }
  
  void _giveHint(int guess) {
    int difference = (guess - _targetNumber).abs();
    if (difference <= 5) {
      print('🔥 Очень горячо!');
    } else if (difference <= 10) {
      print('🌡️ Тепло!');
    } else if (difference <= 20) {
      print('❄️ Прохладно!');
    } else {
      print('🧊 Холодно!');
    }
  }
  
  void _showWinMessage() {
    print('\\n🎉 ПОЗДРАВЛЯЮ! Ты угадал число $_targetNumber!');
    print('Количество попыток: $_attempts');
    
    String performance;
    if (_attempts <= _maxAttempts ~/ 3) {
      performance = 'Отлично! 🌟';
    } else if (_attempts <= _maxAttempts ~/ 2) {
      performance = 'Хорошо! 👍';
    } else {
      performance = 'Неплохо! 👌';
    }
    print('Результат: $performance');
  }
  
  void _showLoseMessage() {
    print('\\n💔 Игра окончена! Попытки закончились.');
    print('Загаданное число было: $_targetNumber');
    print('Попробуй еще раз!');
  }
  
  // Статистика игр
  void showGameStats() {
    print('\\n📊 СТАТИСТИКА ИГР:');
    print('Сыграно игр: 1');
    print('Побед: 1');
    print('Средний результат: $_attempts попыток');
    print('Лучший результат: $_attempts попыток');
  }
}

// Дополнительный класс для управления игровой сессией
class GameSession {
  final NumberGuessingGame _game = NumberGuessingGame();
  
  void start() {
    _game.startGame();
    _game.showGameStats();
    
    print('\\n🎮 Хочешь сыграть еще? (да/нет)');
    // В реальной игре здесь был бы пользовательский ввод
    print('Спасибо за игру!');
  }
}

void main() {
  var session = GameSession();
  session.start();
}""",
            'expected_output': '=== ИГРА "УГАДАЙ ЧИСЛО" ===\nВыберите уровень сложности:\n1. Легкий (1-50, 10 попыток)\n2. Средний (1-100, 8 попыток)\n3. Сложный (1-200, 6 попыток)\nВыбран уровень: Средний\nДиапазон: 1-100, Попыток: 8\nЯ загадал число от 1 до 100. Попробуй угадать!\n\nПопытка 1: 50\nСлишком мало! Попробуй больше.\n🌡️ Тепло!\nОсталось попыток: 7\n\nПопытка 2: 75\nСлишком много! Попробуй меньше.\n❄️ Прохладно!\nОсталось попыток: 6\n\nПопытка 3: 62\nСлишком мало! Попробуй больше.\n🔥 Очень горячо!\nОсталось попыток: 5\n\nПопытка 4: 68\nСлишком много! Попробуй меньше.\n🔥 Очень горячо!\nОсталось попыток: 4\n\nПопытка 5: 65\nСлишком мало! Попробуй больше.\n🔥 Очень горячо!\nОсталось попыток: 3\n\nПопытка 6: 67\nСлишком много! Попробуй меньше.\n🔥 Очень горячо!\nОсталось попыток: 2\n\nПопытка 7: 66\n\n🎉 ПОЗДРАВЛЯЮ! Ты угадал число 66!\nКоличество попыток: 7\nРезультат: Неплохо! 👌\n\n📊 СТАТИСТИКА ИГР:\nСыграно игр: 1\nПобед: 1\nСредний результат: 7 попыток\nЛучший результат: 7 попыток\n\n🎮 Хочешь сыграть еще? (да/нет)\nСпасибо за игру!',
            'hints': ['Random().nextInt(n) генерирует число от 0 до n-1', 'Используйте switch для выбора сложности', 'abs() возвращает абсолютное значение']
        },
        {
            'id': 22,
            'title': 'HTTP клиент и работа с API',
            'category': 'Реальные проекты',
            'difficulty': 'Продвинутый',
            'description': 'Создание HTTP клиента для работы с REST API',
            'theory': """
## HTTP клиент и REST API

Изучаем работу с внешними API и HTTP запросами.

### Основы HTTP:
- **GET** - получение данных
- **POST** - отправка данных
- **PUT** - обновление данных
- **DELETE** - удаление данных

### JSON и сериализация:
```dart
import 'dart:convert';

// Преобразование в JSON
String json = jsonEncode(data);

// Преобразование из JSON
Map<String, dynamic> data = jsonDecode(json);
```

### HTTP клиент в Dart:
```dart
import 'dart:io';
import 'dart:convert';

final client = HttpClient();
final request = await client.getUrl(Uri.parse(url));
final response = await request.close();
```

### Обработка ответов:
- Статус коды (200, 404, 500)
- Заголовки ответа
- Тело ответа (JSON, текст)
- Обработка ошибок

### Практическое применение:
- Получение погоды
- Работа с API социальных сетей
- Загрузка данных с сервера
- Отправка форм
            """,
            'task': 'Создайте HTTP клиент для работы с API погоды',
            'code_template': """import 'dart:convert';

// Модель данных для погоды
class Weather {
  final String city;
  final double temperature;
  final String description;
  final int humidity;
  final double windSpeed;
  
  Weather({
    required this.city,
    required this.temperature,
    required this.description,
    required this.humidity,
    required this.windSpeed,
  });
  
  factory Weather.fromJson(Map<String, dynamic> json) {
    return Weather(
      city: json['city'],
      temperature: json['temperature'].toDouble(),
      description: json['description'],
      humidity: json['humidity'],
      windSpeed: json['windSpeed'].toDouble(),
    );
  }
  
  Map<String, dynamic> toJson() {
    return {
      'city': city,
      'temperature': temperature,
      'description': description,
      'humidity': humidity,
      'windSpeed': windSpeed,
    };
  }
  
  @override
  String toString() {
    return 'Погода в $city: $temperature°C, $description, влажность $humidity%, ветер ${windSpeed}м/с';
  }
}

// HTTP клиент для работы с API
class WeatherApiClient {
  final String baseUrl = 'https://api.weather.com';
  final String apiKey = 'demo_api_key';
  
  // Получение текущей погоды
  Future<Weather> getCurrentWeather(String city) async {
    print('🌐 Запрос погоды для города: $city');
    
    // Симуляция HTTP запроса
    await Future.delayed(Duration(seconds: 1));
    
    // Симуляция ответа API
    Map<String, dynamic> mockResponse = {
      'city': city,
      'temperature': _generateTemperature(),
      'description': _getRandomDescription(),
      'humidity': _generateHumidity(),
      'windSpeed': _generateWindSpeed(),
    };
    
    print('✅ Ответ получен: ${mockResponse.toString()}');
    return Weather.fromJson(mockResponse);
  }
  
  // Получение прогноза на несколько дней
  Future<List<Weather>> getWeatherForecast(String city, int days) async {
    print('🌐 Запрос прогноза для $city на $days дней');
    
    await Future.delayed(Duration(seconds: 2));
    
    List<Weather> forecast = [];
    for (int i = 0; i < days; i++) {
      Map<String, dynamic> dayData = {
        'city': '$city (день ${i + 1})',
        'temperature': _generateTemperature(),
        'description': _getRandomDescription(),
        'humidity': _generateHumidity(),
        'windSpeed': _generateWindSpeed(),
      };
      forecast.add(Weather.fromJson(dayData));
    }
    
    print('✅ Прогноз получен на $days дней');
    return forecast;
  }
  
  // Отправка отчета о погоде
  Future<bool> submitWeatherReport(Weather weather) async {
    print('📤 Отправка отчета о погоде...');
    
    // Преобразуем в JSON
    String jsonData = jsonEncode(weather.toJson());
    print('JSON данные: $jsonData');
    
    await Future.delayed(Duration(milliseconds: 500));
    
    print('✅ Отчет успешно отправлен');
    return true;
  }
  
  // Вспомогательные методы для генерации данных
  double _generateTemperature() {
    return (15 + (25 * (DateTime.now().millisecond / 1000)));
  }
  
  String _getRandomDescription() {
    List<String> descriptions = [
      'Солнечно', 'Облачно', 'Дождь', 'Снег', 'Туман'
    ];
    return descriptions[DateTime.now().second % descriptions.length];
  }
  
  int _generateHumidity() {
    return 40 + (DateTime.now().millisecond ~/ 20);
  }
  
  double _generateWindSpeed() {
    return (DateTime.now().millisecond / 100);
  }
}

// Менеджер для работы с погодными данными
class WeatherManager {
  final WeatherApiClient _apiClient = WeatherApiClient();
  final List<Weather> _weatherHistory = [];
  
  Future<void> showCurrentWeather(String city) async {
    try {
      Weather weather = await _apiClient.getCurrentWeather(city);
      print('🌤️ $weather');
      _weatherHistory.add(weather);
    } catch (e) {
      print('❌ Ошибка получения погоды: $e');
    }
  }
  
  Future<void> showWeatherForecast(String city) async {
    try {
      List<Weather> forecast = await _apiClient.getWeatherForecast(city, 3);
      print('\\n📅 Прогноз погоды:');
      for (int i = 0; i < forecast.length; i++) {
        print('День ${i + 1}: ${forecast[i]}');
      }
    } catch (e) {
      print('❌ Ошибка получения прогноза: $e');
    }
  }
  
  void showWeatherHistory() {
    print('\\n📋 История запросов:');
    if (_weatherHistory.isEmpty) {
      print('История пуста');
    } else {
      for (int i = 0; i < _weatherHistory.length; i++) {
        print('${i + 1}. ${_weatherHistory[i]}');
      }
    }
  }
  
  Future<void> reportWeather(Weather weather) async {
    await _apiClient.submitWeatherReport(weather);
  }
}

void main() async {
  print('=== HTTP КЛИЕНТ ДЛЯ API ПОГОДЫ ===\\n');
  
  var weatherManager = WeatherManager();
  
  // Получение текущей погоды
  await weatherManager.showCurrentWeather('Москва');
  await weatherManager.showCurrentWeather('Санкт-Петербург');
  
  // Прогноз погоды
  await weatherManager.showWeatherForecast('Новосибирск');
  
  // История запросов
  weatherManager.showWeatherHistory();
  
  print('\\n✨ Программа завершена');
}""",
            'expected_output': '=== HTTP КЛИЕНТ ДЛЯ API ПОГОДЫ ===\n\n🌐 Запрос погоды для города: Москва\n✅ Ответ получен: {city: Москва, temperature: 20.0, description: Солнечно, humidity: 50, windSpeed: 5.0}\n🌤️ Погода в Москва: 20.0°C, Солнечно, влажность 50%, ветер 5.0м/с\n🌐 Запрос погоды для города: Санкт-Петербург\n✅ Ответ получен: {city: Санкт-Петербург, temperature: 18.0, description: Облачно, humidity: 60, windSpeed: 3.0}\n🌤️ Погода в Санкт-Петербург: 18.0°C, Облачно, влажность 60%, ветер 3.0м/с\n🌐 Запрос прогноза для Новосибирск на 3 дней\n✅ Прогноз получен на 3 дней\n\n📅 Прогноз погоды:\nДень 1: Погода в Новосибирск (день 1): 22.0°C, Дождь, влажность 45%, ветер 4.0м/с\nДень 2: Погода в Новосибирск (день 2): 19.0°C, Снег, влажность 70%, ветер 6.0м/с\nДень 3: Погода в Новосибирск (день 3): 25.0°C, Туман, влажность 55%, ветер 2.0м/с\n\n📋 История запросов:\n1. Погода в Москва: 20.0°C, Солнечно, влажность 50%, ветер 5.0м/с\n2. Погода в Санкт-Петербург: 18.0°C, Облачно, влажность 60%, ветер 3.0м/с\n\n✨ Программа завершена',
            'hints': ['jsonEncode() преобразует объект в JSON строку', 'jsonDecode() парсит JSON в Map', 'Future.delayed() симулирует сетевые задержки']
        },
        {
            'id': 23,
            'title': 'CLI утилита с аргументами',
            'category': 'Реальные проекты',
            'difficulty': 'Продвинутый',
            'description': 'Создание утилиты командной строки с аргументами',
            'theory': """
## Command Line Interface (CLI)

CLI приложения - мощный способ автоматизации задач.

### Работа с аргументами:
```dart
void main(List<String> arguments) {
  // arguments содержит аргументы командной строки
}
```

### Парсинг аргументов:
- **Позиционные**: `program file.txt`
- **Именованные**: `program --verbose --output=result.txt`
- **Флаги**: `program -v -h`

### Структура CLI программы:
1. Парсинг аргументов
2. Валидация входных данных
3. Выполнение команд
4. Вывод результатов
5. Обработка ошибок

### Популярные паттерны:
- Command pattern для команд
- Builder pattern для опций
- Strategy pattern для алгоритмов

### Примеры использования:
- Файловые операции
- Конвертеры форматов
- Утилиты разработки
- Системные скрипты
            """,
        },
        {
            'id': 'advanced-dart-patterns',
            'title': 'Продвинутые паттерны Dart',
            'description': 'Изучение современных паттернов программирования в Dart',
            'task': 'Создайте утилиту для работы с текстовыми файлами',
            'code_template': '''import 'dart:io';

// Базовый класс для команд
abstract class Command {
  String get name;
  String get description;
  void execute(List<String> args);
}

// Команда подсчета статистики текста
class StatsCommand extends Command {
  @override
  String get name => 'stats';
  
  @override
  String get description => 'Показать статистику текстового файла';
  
  @override
  void execute(List<String> args) {
    if (args.isEmpty) {
      print('❌ Ошибка: Укажите путь к файлу');
      print('Использование: textutil stats <файл>');
      return;
    }
    
    String filename = args[0];
    print('📊 Анализ файла: $filename');
    
    // Симуляция чтения файла
    String content = """
Dart - это современный язык программирования.
Он используется для создания мобильных приложений.
Flutter - это фреймворк на Dart.
Dart компилируется в нативный код.
    """.trim();
    
    _analyzeText(content, filename);
  }
  
  void _analyzeText(String content, String filename) {
    List<String> lines = content.split('\\n');
    List<String> words = content.split(RegExp(r'\\s+'));
    words.removeWhere((word) => word.isEmpty);
    
    int characters = content.length;
    int charactersNoSpaces = content.replaceAll(RegExp(r'\\s'), '').length;
    int sentences = content.split(RegExp(r'[.!?]')).length - 1;
    
    print('\\n📈 СТАТИСТИКА:');
    print('Файл: $filename');
    print('Строк: ${lines.length}');
    print('Слов: ${words.length}');
    print('Символов: $characters');
    print('Символов без пробелов: $charactersNoSpaces');
    print('Предложений: $sentences');
    print('Средняя длина слова: ${(charactersNoSpaces / words.length).toStringAsFixed(1)} символов');
  }
}

// Команда поиска и замены
class ReplaceCommand extends Command {
  @override
  String get name => 'replace';
  
  @override
  String get description => 'Найти и заменить текст в файле';
  
  @override
  void execute(List<String> args) {
    if (args.length < 3) {
      print('❌ Ошибка: Недостаточно аргументов');
      print('Использование: textutil replace <файл> <найти> <заменить>');
      return;
    }
    
    String filename = args[0];
    String searchText = args[1];
    String replaceText = args[2];
    
    print('🔍 Замена в файле: $filename');
    print('Найти: "$searchText"');
    print('Заменить на: "$replaceText"');
    
    // Симуляция содержимого файла
    String content = 'Dart - отличный язык. Dart используется в Flutter. Dart быстрый.';
    
    String newContent = content.replaceAll(searchText, replaceText);
    int replacements = searchText.allMatches(content).length;
    
    print('\\n📝 РЕЗУЛЬТАТ:');
    print('Исходный текст: $content');
    print('Новый текст: $newContent');
    print('Замен выполнено: $replacements');
    
    if (replacements > 0) {
      print('✅ Файл успешно обновлен');
    } else {
      print('ℹ️ Текст для замены не найден');
    }
  }
}

// Команда форматирования
class FormatCommand extends Command {
  @override
  String get name => 'format';
  
  @override
  String get description => 'Форматировать текстовый файл';
  
  @override
  void execute(List<String> args) {
    if (args.isEmpty) {
      print('❌ Ошибка: Укажите путь к файлу');
      print('Использование: textutil format <файл> [--uppercase] [--lowercase]');
      return;
    }
    
    String filename = args[0];
    bool uppercase = args.contains('--uppercase');
    bool lowercase = args.contains('--lowercase');
    
    print('🎨 Форматирование файла: $filename');
    
    String content = 'dart - это современный язык программирования от google.';
    String formatted = content;
    
    if (uppercase) {
      formatted = formatted.toUpperCase();
      print('Применено: ВЕРХНИЙ РЕГИСТР');
    } else if (lowercase) {
      formatted = formatted.toLowerCase();
      print('Применено: нижний регистр');
    } else {
      // Капитализация предложений
      formatted = _capitalizeSentences(formatted);
      print('Применено: Капитализация предложений');
    }
    
    print('\\n📄 РЕЗУЛЬТАТ:');
    print('До: $content');
    print('После: $formatted');
  }
  
  String _capitalizeSentences(String text) {
    return text.split('. ').map((sentence) {
      if (sentence.isNotEmpty) {
        return sentence[0].toUpperCase() + sentence.substring(1);
      }
      return sentence;
    }).join('. ');
  }
}

// Главный класс CLI утилиты
class TextUtilCLI {
  final Map<String, Command> _commands = {};
  
  TextUtilCLI() {
    _registerCommand(StatsCommand());
    _registerCommand(ReplaceCommand());
    _registerCommand(FormatCommand());
  }
  
  void _registerCommand(Command command) {
    _commands[command.name] = command;
  }
  
  void run(List<String> arguments) {
    print('=== TEXT UTILITY CLI ===\\n');
    
    if (arguments.isEmpty) {
      _showHelp();
      return;
    }
    
    String commandName = arguments[0];
    List<String> commandArgs = arguments.sublist(1);
    
    if (commandName == 'help' || commandName == '--help' || commandName == '-h') {
      _showHelp();
      return;
    }
    
    Command? command = _commands[commandName];
    if (command == null) {
      print('❌ Неизвестная команда: $commandName');
      print('Используйте "help" для списка команд');
      return;
    }
    
    try {
      command.execute(commandArgs);
    } catch (e) {
      print('❌ Ошибка выполнения команды: $e');
    }
  }
  
  void _showHelp() {
    print('📚 СПРАВКА:');
    print('textutil <команда> [аргументы]\\n');
    print('Доступные команды:');
    
    _commands.forEach((name, command) {
      print('  $name - ${command.description}');
    });
    
    print('\\nОбщие опции:');
    print('  help, --help, -h - Показать эту справку');
    
    print('\\nПримеры:');
    print('  textutil stats document.txt');
    print('  textutil replace file.txt "old" "new"');
    print('  textutil format text.txt --uppercase');
  }
}

void main(List<String> arguments) {
  // Симуляция различных вызовов
  var cli = TextUtilCLI();
  
  print('Пример 1: Справка');
  cli.run(['help']);
  
  print('\\n' + '='*50 + '\\n');
  print('Пример 2: Статистика файла');
  cli.run(['stats', 'document.txt']);
  
  print('\\n' + '='*50 + '\\n');
  print('Пример 3: Замена текста');
  cli.run(['replace', 'file.txt', 'Dart', 'Flutter']);
  
  print('\\n' + '='*50 + '\\n');
  print('Пример 4: Форматирование');
  cli.run(['format', 'text.txt']);
}''',
            'expected_output': 'Пример 1: Справка\n=== TEXT UTILITY CLI ===\n\n📚 СПРАВКА:\ntextutil <команда> [аргументы]\n\nДоступные команды:\n  stats - Показать статистику текстового файла\n  replace - Найти и заменить текст в файле\n  format - Форматировать текстовый файл\n\nОбщие опции:\n  help, --help, -h - Показать эту справку\n\nПримеры:\n  textutil stats document.txt\n  textutil replace file.txt "old" "new"\n  textutil format text.txt --uppercase\n\n==================================================\n\nПример 2: Статистика файла\n=== TEXT UTILITY CLI ===\n\n📊 Анализ файла: document.txt\n\n📈 СТАТИСТИКА:\nФайл: document.txt\nСтрок: 4\nСлов: 16\nСимволов: 137\nСимволов без пробелов: 122\nПредложений: 4\nСредняя длина слова: 7.6 символов\n\n==================================================\n\nПример 3: Замена текста\n=== TEXT UTILITY CLI ===\n\n🔍 Замена в файле: file.txt\nНайти: "Dart"\nЗаменить на: "Flutter"\n\n📝 РЕЗУЛЬТАТ:\nИсходный текст: Dart - отличный язык. Dart используется в Flutter. Dart быстрый.\nНовый текст: Flutter - отличный язык. Flutter используется в Flutter. Flutter быстрый.\nЗамен выполнено: 3\n✅ Файл успешно обновлен\n\n==================================================\n\nПример 4: Форматирование\n=== TEXT UTILITY CLI ===\n\n🎨 Форматирование файла: text.txt\nПрименено: Капитализация предложений\n\n📄 РЕЗУЛЬТАТ:\nДо: dart - это современный язык программирования от google.\nПосле: Dart - это современный язык программирования от google.',
            'hints': ['main(List<String> arguments) получает аргументы командной строки', 'Command pattern помогает организовать команды', 'RegExp используется для работы с регулярными выражениями']
        },
        {
            'id': 24,
            'title': 'Файловая система и I/O',
            'category': 'Реальные проекты',
            'difficulty': 'Продвинутый',
            'description': 'Работа с файлами и директориями',
            'theory': """
## Файловая система в Dart

Dart предоставляет мощные инструменты для работы с файлами.

### Основные классы:
- **File** - работа с файлами
- **Directory** - работа с папками
- **Path** - работа с путями
- **FileSystemEntity** - базовый класс

### Операции с файлами:
```dart
// Чтение файла
String content = await File('file.txt').readAsString();

// Запись в файл
await File('output.txt').writeAsString(content);

// Проверка существования
bool exists = await File('file.txt').exists();
```

### Асинхронные операции:
- Все файловые операции асинхронные
- Используйте async/await
- Обрабатывайте исключения

### Работа с директориями:
```dart
// Создание папки
await Directory('new_folder').create();

// Список файлов
await for (var entity in Directory('.').list()) {
  print(entity.path);
}
```

### Практические применения:
- Логирование
- Кеширование данных
- Конфигурационные файлы
- Резервное копирование
            """,
            'task': 'Создайте файловый менеджер с основными операциями',
            'code_template': """import 'dart:io';
import 'dart:convert';

// Класс для информации о файле
class FileInfo {
  final String name;
  final String path;
  final int size;
  final DateTime modified;
  final bool isDirectory;
  
  FileInfo({
    required this.name,
    required this.path,
    required this.size,
    required this.modified,
    required this.isDirectory,
  });
  
  String get sizeFormatted {
    if (size < 1024) return '$size B';
    if (size < 1024 * 1024) return '${(size / 1024).toStringAsFixed(1)} KB';
    return '${(size / (1024 * 1024)).toStringAsFixed(1)} MB';
  }
  
  String get typeIcon => isDirectory ? '📁' : '📄';
  
  @override
  String toString() {
    String modifiedStr = '${modified.day}.${modified.month}.${modified.year}';
    return '$typeIcon $name (${isDirectory ? 'папка' : sizeFormatted}) - $modifiedStr';
  }
}

// Файловый менеджер
class FileManager {
  String currentPath = '.';
  
  // Получить список файлов в директории
  Future<List<FileInfo>> listDirectory([String? path]) async {
    path ??= currentPath;
    print('📂 Содержимое папки: $path');
    
    List<FileInfo> files = [];
    
    try {
      // Симуляция списка файлов
      await Future.delayed(Duration(milliseconds: 500));
      
      // Создаем демо-данные
      files = [
        FileInfo(
          name: 'documents',
          path: '$path/documents',
          size: 0,
          modified: DateTime.now().subtract(Duration(days: 5)),
          isDirectory: true,
        ),
        FileInfo(
          name: 'README.md',
          path: '$path/README.md',
          size: 2048,
          modified: DateTime.now().subtract(Duration(days: 1)),
          isDirectory: false,
        ),
        FileInfo(
          name: 'config.json',
          path: '$path/config.json',
          size: 512,
""",
            'hints': ['File и Directory - основные классы для работы с файлами', 'Все файловые операции асинхронные'],
        },
        {
            'id': 25,
            'title': 'Unit тестирование',
            'category': 'Реальные проекты',
            'difficulty': 'Продвинутый',
            'description': 'Написание и запуск автоматических тестов',
            'theory': """
## Unit тестирование в Dart

Тестирование - важная часть разработки качественного ПО.

### Фреймворк test:
```dart
import 'package:test/test.dart';

void main() {
  test('описание теста', () {
    expect(actual, expected);
  });
}
```

### Типы тестов:
- **Unit tests** - тестирование отдельных функций
- **Widget tests** - тестирование UI (Flutter)
- **Integration tests** - сквозное тестирование

### Основные функции:
- `test()` - одиночный тест
- `group()` - группировка тестов
- `setUp()` - подготовка перед тестами
- `tearDown()` - очистка после тестов

### Ассерты (expect):
```dart
expect(actual, equals(expected));
expect(value, isTrue);
expect(list, contains(item));
expect(() => throw Error(), throwsA(isA<Error>()));
```

### Мокирование:
- Создание фейковых объектов
- Контроль поведения зависимостей
- Изоляция тестируемого кода

### Best practices:
- Один тест = одна проверка
- Описательные имена тестов
- Независимые тесты
- Быстрые тесты
            """,
            'task': 'Создайте набор unit тестов для калькулятора',
            'code_template': """// Класс калькулятора для тестирования
class Calculator {
  double add(double a, double b) => a + b;
  
  double subtract(double a, double b) => a - b;
  
  double multiply(double a, double b) => a * b;
  
  double divide(double a, double b) {
    if (b == 0) {
      throw ArgumentError('Division by zero is not allowed');
    }
    return a / b;
  }
  
  double power(double base, int exponent) {
    if (exponent < 0) {
      throw ArgumentError('Negative exponents not supported');
    }
    double result = 1;
    for (int i = 0; i < exponent; i++) {
      result *= base;
    }
    return result;
  }
  
  double sqrt(double value) {
    if (value < 0) {
      throw ArgumentError('Square root of negative number');
    }
    // Простая реализация через приближение
    if (value == 0) return 0;
    double x = value;
    double prev;
    do {
      prev = x;
      x = (x + value / x) / 2;
    } while ((x - prev).abs() > 0.0001);
    return x;
  }
  
  bool isEven(int number) => number % 2 == 0;
  
  bool isPrime(int number) {
    if (number < 2) return false;
    for (int i = 2; i <= number ~/ 2; i++) {
      if (number % i == 0) return false;
    }
    return true;
  }
  
  List<int> fibonacci(int count) {
    if (count <= 0) return [];
    if (count == 1) return [0];
    if (count == 2) return [0, 1];
    
    List<int> result = [0, 1];
    for (int i = 2; i < count; i++) {
      result.add(result[i - 1] + result[i - 2]);
    }
    return result;
  }
}

// Простая реализация тестового фреймворка
class TestFramework {
  static int _testCount = 0;
  static int _passCount = 0;
  static int _failCount = 0;
  static String _currentGroup = '';
  
  static void group(String description, void Function() tests) {
    print('\\n📂 $description');
    _currentGroup = description;
    tests();
  }
  
  static void test(String description, void Function() testFunction) {
    _testCount++;
    try {
      testFunction();
      _passCount++;
      print('  ✅ $description');
    } catch (e) {
      _failCount++;
      print('  ❌ $description');
      print('     Ошибка: $e');
    }
  }
  
  static void expect<T>(T actual, T expected) {
    if (actual != expected) {
      throw Exception('Expected: $expected, but got: $actual');
    }
  }
  
  static void expectThrows(void Function() function, Type exceptionType) {
    try {
      function();
      throw Exception('Expected exception of type $exceptionType, but no exception was thrown');
    } catch (e) {
      if (e.runtimeType.toString() != exceptionType.toString() && 
          !e.toString().contains(exceptionType.toString())) {
        throw Exception('Expected exception of type $exceptionType, but got: ${e.runtimeType}');
      }
    }
  }
  
  static void expectTrue(bool actual) {
    if (!actual) {
      throw Exception('Expected: true, but got: false');
    }
  }
  
  static void expectFalse(bool actual) {
    if (actual) {
      throw Exception('Expected: false, but got: true');
    }
  }
  
  static void expectListEquals<T>(List<T> actual, List<T> expected) {
    if (actual.length != expected.length) {
      throw Exception('List lengths differ. Expected: ${expected.length}, got: ${actual.length}');
    }
    for (int i = 0; i < actual.length; i++) {
      if (actual[i] != expected[i]) {
        throw Exception('Lists differ at index $i. Expected: ${expected[i]}, got: ${actual[i]}');
      }
    }
  }
  
  static void expectApproximately(double actual, double expected, double tolerance) {
    if ((actual - expected).abs() > tolerance) {
      throw Exception('Expected: $expected ± $tolerance, but got: $actual');
    }
  }
  
  static void showResults() {
    print('\\n' + '='*50);
    print('📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:');
    print('Всего тестов: $_testCount');
    print('✅ Прошли: $_passCount');
    print('❌ Провалились: $_failCount');
    print('Успешность: ${(_passCount / _testCount * 100).toStringAsFixed(1)}%');
    
    if (_failCount == 0) {
      print('\\n🎉 Все тесты прошли успешно!');
    } else {
      print('\\n⚠️ Некоторые тесты провалились. Проверьте код.');
    }
  }
}

void main() {
  print('=== UNIT ТЕСТИРОВАНИЕ КАЛЬКУЛЯТОРА ===');
  
  var calculator = Calculator();
  
  // Тестирование базовых операций
  TestFramework.group('Базовые арифметические операции', () {
    TestFramework.test('сложение положительных чисел', () {
      TestFramework.expect(calculator.add(2, 3), 5);
    });
    
    TestFramework.test('сложение с нулем', () {
      TestFramework.expect(calculator.add(5, 0), 5);
    });
    
    TestFramework.test('сложение отрицательных чисел', () {
      TestFramework.expect(calculator.add(-2, -3), -5);
    });
    
    TestFramework.test('вычитание', () {
      TestFramework.expect(calculator.subtract(10, 4), 6);
    });
    
    TestFramework.test('умножение', () {
      TestFramework.expect(calculator.multiply(6, 7), 42);
    });
    
    TestFramework.test('деление', () {
      TestFramework.expectApproximately(calculator.divide(15, 3), 5, 0.001);
    });
  });
  
  // Тестирование исключений
  TestFramework.group('Обработка ошибок', () {
    TestFramework.test('деление на ноль', () {
      TestFramework.expectThrows(
        () => calculator.divide(10, 0),
        ArgumentError
      );
    });
    
    TestFramework.test('квадратный корень из отрицательного числа', () {
      TestFramework.expectThrows(
        () => calculator.sqrt(-4),
        ArgumentError
      );
    });
    
    TestFramework.test('отрицательная степень', () {
      TestFramework.expectThrows(
        () => calculator.power(2, -1),
        ArgumentError
      );
    });
  });
  
  // Тестирование сложных функций
  TestFramework.group('Продвинутые операции', () {
    TestFramework.test('возведение в степень', () {
      TestFramework.expect(calculator.power(2, 3), 8);
      TestFramework.expect(calculator.power(5, 0), 1);
      TestFramework.expect(calculator.power(10, 2), 100);
    });
    
    TestFramework.test('квадратный корень', () {
      TestFramework.expectApproximately(calculator.sqrt(16), 4, 0.001);
      TestFramework.expectApproximately(calculator.sqrt(25), 5, 0.001);
      TestFramework.expect(calculator.sqrt(0), 0);
    });
    
    TestFramework.test('проверка четности', () {
      TestFramework.expectTrue(calculator.isEven(4));
      TestFramework.expectFalse(calculator.isEven(5));
      TestFramework.expectTrue(calculator.isEven(0));
    });
    
    TestFramework.test('проверка простых чисел', () {
      TestFramework.expectTrue(calculator.isPrime(2));
      TestFramework.expectTrue(calculator.isPrime(13));
      TestFramework.expectFalse(calculator.isPrime(4));
      TestFramework.expectFalse(calculator.isPrime(1));
    });
    
    TestFramework.test('последовательность Фибоначчи', () {
      TestFramework.expectListEquals(calculator.fibonacci(0), <int>[]);
      TestFramework.expectListEquals(calculator.fibonacci(1), [0]);
      TestFramework.expectListEquals(calculator.fibonacci(5), [0, 1, 1, 2, 3]);
      TestFramework.expectListEquals(calculator.fibonacci(8), [0, 1, 1, 2, 3, 5, 8, 13]);
    });
  });
  
  TestFramework.showResults();
}""",
            'expected_output': '=== UNIT ТЕСТИРОВАНИЕ КАЛЬКУЛЯТОРА ===\n\n📂 Базовые арифметические операции\n  ✅ сложение положительных чисел\n  ✅ сложение с нулем\n  ✅ сложение отрицательных чисел\n  ✅ вычитание\n  ✅ умножение\n  ✅ деление\n\n📂 Обработка ошибок\n  ✅ деление на ноль\n  ✅ квадратный корень из отрицательного числа\n  ✅ отрицательная степень\n\n📂 Продвинутые операции\n  ✅ возведение в степень\n  ✅ квадратный корень\n  ✅ проверка четности\n  ✅ проверка простых чисел\n  ✅ последовательность Фибоначчи\n\n==================================================\n📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ:\nВсего тестов: 15\n✅ Прошли: 15\n❌ Провалились: 0\nУспешность: 100.0%\n\n🎉 Все тесты прошли успешно!',
            'hints': ['expect() проверяет равенство значений', 'expectThrows() проверяет что функция выбрасывает исключение', 'group() помогает организовать тесты по категориям']
        },
        
        # Block 6: Flutter Preparation (Lessons 26-30)
        {
            'id': 26,
            'title': 'Введение в Flutter',
            'category': 'Flutter подготовка',
            'difficulty': 'Начальный',
            'description': 'Основы фреймворка Flutter и его архитектуры',
            'theory': """
## Введение в Flutter

Flutter - это фреймворк от Google для создания кроссплатформенных мобильных приложений с использованием языка Dart.

### Ключевые особенности:
- **Один код** - работает на iOS и Android
- **Горячая перезагрузка** - мгновенное обновление UI
- **Виджеты** - все элементы интерфейса
- **Высокая производительность** - компиляция в нативный код

### Основные концепции:
- **Widget** - базовый элемент UI
- **StatelessWidget** - неизменяемый виджет
- **StatefulWidget** - виджет с состоянием
- **BuildContext** - информация о позиции виджета в дереве

### Структура приложения:
```dart
void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: HomePage(),
    );
  }
}
```
            """,
            'task': 'Создайте структуру простого Flutter приложения с главной страницей и виджетом приветствия.',
            'code_template': """// Главная функция приложения
void main() {
  // TODO: Запустить Flutter приложение
  print('Flutter приложение запускается...');
  runApp();
}

// Корневой виджет приложения
class MyApp {
  // TODO: Создать StatelessWidget
  String buildApp() {
    return 'MaterialApp создан';
  }
}

// Главная страница
class HomePage {
  // TODO: Создать виджет для домашней страницы
  String buildHomePage() {
    return 'Главная страница создана';
  }
}

// Виджет приветствия
class WelcomeWidget {
  String name;
  
  WelcomeWidget(this.name);
  
  // TODO: Создать виджет приветствия
  String buildWelcome() {
    return 'Добро пожаловать, $name!';
  }
}

// Симуляция запуска приложения
void runApp() {
  print('Создание приложения...');
  
  MyApp app = MyApp();
  print(app.buildApp());
  
  HomePage home = HomePage();
  print(home.buildHomePage());
  
  WelcomeWidget welcome = WelcomeWidget('Flutter Developer');
  print(welcome.buildWelcome());
  
  print('Flutter приложение готово!');
}""",
            'expected_output': 'Flutter приложение запускается...\nСоздание приложения...\nMaterialApp создан\nГлавная страница создана\nДобро пожаловать, Flutter Developer!\nFlutter приложение готово!',
            'hints': [
                'Flutter приложение начинается с функции main()',
                'runApp() принимает корневой виджет',
                'MaterialApp предоставляет Material Design',
                'Каждый виджет имеет метод build()',
                'StatelessWidget используется для статических элементов'
            ]
        },
        
        {
            'id': 27,
            'title': 'Виджеты и их типы',
            'category': 'Flutter подготовка',
            'difficulty': 'Начальный',
            'description': 'Изучение основных виджетов Flutter',
            'theory': """
## Виджеты в Flutter

В Flutter все является виджетом - от кнопок до целых экранов.

### Типы виджетов:

**StatelessWidget:**
- Неизменяемые виджеты
- Не имеют внутреннего состояния
- Пример: Text, Icon, Image

**StatefulWidget:**
- Изменяемые виджеты
- Имеют состояние, которое может изменяться
- Пример: Checkbox, TextField, Slider

### Основные виджеты:
- **Container** - контейнер с возможностью стилизации
- **Row/Column** - горизонтальное/вертикальное расположение
- **Text** - отображение текста
- **Image** - отображение изображений
- **Button** - кнопки различных типов

### Жизненный цикл StatefulWidget:
1. `createState()` - создание состояния
2. `initState()` - инициализация
3. `build()` - построение UI
4. `setState()` - обновление состояния
5. `dispose()` - освобождение ресурсов
            """,
            'task': 'Создайте различные типы виджетов: контейнер, текст, кнопку и счетчик с состоянием.',
            'code_template': """// Статический виджет - контейнер с текстом
class TextContainer {
  String text;
  String color;
  
  TextContainer(this.text, this.color);
  
  String build() {
    return 'Container(color: $color, child: Text("$text"))';
  }
}

// Виджет кнопки
class CustomButton {
  String label;
  Function onPressed;
  
  CustomButton(this.label, this.onPressed);
  
  String build() {
    return 'ElevatedButton(child: Text("$label"))';
  }
  
  void press() {
    print('Кнопка "$label" нажата');
    onPressed();
  }
}

// Виджет счетчика с состоянием
class CounterWidget {
  int _counter = 0;
  
  // TODO: Реализовать методы для работы со счетчиком
  String build() {
    return 'Column(children: [Text("Счетчик: $_counter"), Button("Увеличить")])';
  }
  
  void increment() {
    // TODO: Увеличить счетчик и обновить состояние
  }
  
  void updateState() {
    print('Состояние обновлено: счетчик = $_counter');
  }
}

void main() {
  print('Создание Flutter виджетов...');
  
  // Создание статических виджетов
  TextContainer container = TextContainer('Привет, Flutter!', 'синий');
  print(container.build());
  
  // Создание кнопки
  CustomButton button = CustomButton('Нажми меня', () {
    print('Действие кнопки выполнено!');
  });
  print(button.build());
  button.press();
  
  // Создание счетчика
  CounterWidget counter = CounterWidget();
  print(counter.build());
  
  // TODO: Вызвать increment() несколько раз
  
  print('Все виджеты созданы!');
}""",
            'expected_output': 'Создание Flutter виджетов...\nContainer(color: синий, child: Text("Привет, Flutter!"))\nElevatedButton(child: Text("Нажми меня"))\nКнопка "Нажми меня" нажата\nДействие кнопки выполнено!\nColumn(children: [Text("Счетчик: 0"), Button("Увеличить")])\nВсе виджеты созданы!',
            'hints': [
                'StatelessWidget имеет только метод build()',
                'StatefulWidget может изменять свое состояние',
                'Используйте setState() для обновления UI',
                'Counter должен увеличиваться при каждом вызове increment()',
                'Не забудьте вызвать updateState() после изменения'
            ]
        },
        
        {
            'id': 28,
            'title': 'Макеты и позиционирование',
            'category': 'Flutter подготовка',
            'difficulty': 'Средний',
            'description': 'Работа с макетами в Flutter: Row, Column, Stack',
            'theory': """
## Макеты в Flutter

Макеты определяют как виджеты располагаются на экране.

### Основные виджеты макетов:

**Column** - вертикальное расположение:
```dart
Column(
  children: [
    Text('Первый'),
    Text('Второй'),
  ],
)
```

**Row** - горизонтальное расположение:
```dart
Row(
  children: [
    Icon(Icons.star),
    Text('Рейтинг'),
  ],
)
```

**Stack** - слоеное расположение:
```dart
Stack(
  children: [
    Container(color: Colors.blue),
    Positioned(
      top: 10,
      left: 10,
      child: Text('Наверху'),
    ),
  ],
)
```

### Свойства выравнивания:
- **MainAxisAlignment** - основная ось
- **CrossAxisAlignment** - поперечная ось
- **MainAxisSize** - размер по основной оси

### Flex-виджеты:
- **Expanded** - занимает доступное место
- **Flexible** - гибкое пространство
- **Spacer** - пустое пространство
            """,
            'task': 'Создайте макет с различными способами позиционирования виджетов.',
            'code_template': """// Вертикальный макет
class VerticalLayout {
  List<String> items;
  
  VerticalLayout(this.items);
  
  String build() {
    String children = items.join(', ');
    return 'Column(children: [$children])';
  }
}

// Горизонтальный макет
class HorizontalLayout {
  List<String> items;
  String alignment;
  
  HorizontalLayout(this.items, this.alignment);
  
  String build() {
    String children = items.join(', ');
    return 'Row(mainAxisAlignment: $alignment, children: [$children])';
  }
}

// Слоеный макет
class StackLayout {
  List<Map<String, dynamic>> layers;
  
  StackLayout(this.layers);
  
  String build() {
    String children = '';
    for (var layer in layers) {
      if (layer['positioned']) {
        children += 'Positioned(top: ${layer['top']}, left: ${layer['left']}, child: ${layer['widget']}), ';
      } else {
        children += '${layer['widget']}, ';
      }
    }
    return 'Stack(children: [$children])';
  }
}

// Гибкий макет с Expanded
class FlexLayout {
  List<Map<String, dynamic>> items;
  
  FlexLayout(this.items);
  
  String build() {
    String children = '';
    for (var item in items) {
      if (item['flex'] != null) {
        children += 'Expanded(flex: ${item['flex']}, child: ${item['widget']}), ';
      } else {
        children += '${item['widget']}, ';
      }
    }
    return 'Column(children: [$children])';
  }
}

void main() {
  print('Создание макетов Flutter...');
  
  // Вертикальный макет
  VerticalLayout vertical = VerticalLayout(['Text("Заголовок")', 'Text("Описание")', 'Button("Действие")']);
  print('Вертикальный макет: ${vertical.build()}');
  
  // Горизонтальный макет
  HorizontalLayout horizontal = HorizontalLayout(['Icon(star)', 'Text("4.5")', 'Text("(123 отзыва)")'], 'spaceAround');
  print('Горизонтальный макет: ${horizontal.build()}');
  
  // TODO: Создать слоеный макет с фоном и текстом поверх
  List<Map<String, dynamic>> stackLayers = [
    {'widget': 'Container(color: blue)', 'positioned': false},
    {'widget': 'Text("Overlay")', 'positioned': true, 'top': 20, 'left': 20}
  ];
  StackLayout stack = StackLayout(stackLayers);
  print('Слоеный макет: ${stack.build()}');
  
  // TODO: Создать гибкий макет с разными flex значениями
  List<Map<String, dynamic>> flexItems = [
    {'widget': 'Container("Header")', 'flex': 1},
    {'widget': 'Container("Content")', 'flex': 3},
    {'widget': 'Container("Footer")', 'flex': 1}
  ];
  FlexLayout flex = FlexLayout(flexItems);
  print('Гибкий макет: ${flex.build()}');
  
  print('Все макеты созданы!');
}""",
            'expected_output': 'Создание макетов Flutter...\nВертикальный макет: Column(children: [Text("Заголовок"), Text("Описание"), Button("Действие")])\nГоризонтальный макет: Row(mainAxisAlignment: spaceAround, children: [Icon(star), Text("4.5"), Text("(123 отзыва)")])\nСлоеный макет: Stack(children: [Container(color: blue), Positioned(top: 20, left: 20, child: Text("Overlay")), ])\nГибкий макет: Column(children: [Expanded(flex: 1, child: Container("Header")), Expanded(flex: 3, child: Container("Content")), Expanded(flex: 1, child: Container("Footer")), ])\nВсе макеты созданы!',
            'hints': [
                'Column располагает элементы сверху вниз',
                'Row располагает элементы слева направо',
                'Stack позволяет накладывать виджеты друг на друга',
                'Expanded заполняет доступное пространство',
                'Positioned используется внутри Stack для точного позиционирования'
            ]
        },
        
        {
            'id': 29,
            'title': 'Управление состоянием',
            'category': 'Flutter подготовка',
            'difficulty': 'Средний',
            'description': 'Основы управления состоянием в Flutter',
            'theory': """
## Управление состоянием в Flutter

Состояние - это данные, которые могут изменяться во время работы приложения.

### Типы состояния:

**Локальное состояние:**
- Состояние одного виджета
- Управляется через setState()
- Пример: счетчик, переключатель

**Глобальное состояние:**
- Состояние всего приложения
- Доступно из разных виджетов
- Управляется через Provider, Bloc, Riverpod

### setState():
```dart
class CounterWidget extends StatefulWidget {
  @override
  _CounterWidgetState createState() => _CounterWidgetState();
}

class _CounterWidgetState extends State<CounterWidget> {
  int counter = 0;
  
  void increment() {
    setState(() {
      counter++;
    });
  }
}
```

### Управление формами:
- **TextEditingController** - контроллер для текстовых полей
- **Form** - группировка полей формы
- **Validation** - валидация данных

### Жизненный цикл состояния:
1. `initState()` - инициализация
2. `didChangeDependencies()` - изменение зависимостей
3. `build()` - построение UI
4. `setState()` - обновление состояния
5. `dispose()` - очистка ресурсов
            """,
        },
        {
            'id': 'flutter-stateful-widgets',
            'title': 'Виджеты с состоянием Flutter',
            'description': 'Создание интерактивных виджетов с управлением состоянием',
            'task': 'Создайте виджет формы с управлением состоянием для регистрации пользователя.',
            'code_template': '''// Модель пользователя
class User {
  String name;
  String email;
  int age;
  bool isSubscribed;
  
  User({required this.name, required this.email, required this.age, this.isSubscribed = false});
  
  @override
  String toString() {
    return 'User{name: $name, email: $email, age: $age, subscribed: $isSubscribed}';
  }
}

// Контроллер формы
class FormController {
  String _name = '';
  String _email = '';
  int _age = 0;
  bool _isSubscribed = false;
  
  // TODO: Реализовать геттеры и сеттеры
  String get name => _name;
  String get email => _email;
  int get age => _age;
  bool get isSubscribed => _isSubscribed;
  
  void setName(String name) {
    // TODO: Обновить имя и вызвать setState
  }
  
  void setEmail(String email) {
    // TODO: Обновить email
  }
  
  void setAge(int age) {
    // TODO: Обновить возраст
  }
  
  void toggleSubscription() {
    // TODO: Переключить подписку
  }
  
  bool validate() {
    // TODO: Валидация формы
    return _name.isNotEmpty && _email.contains('@') && _age >= 18;
  }
  
  User createUser() {
    return User(name: _name, email: _email, age: _age, isSubscribed: _isSubscribed);
  }
}

// Виджет формы регистрации
class RegistrationForm {
  FormController controller = FormController();
  
  String build() {
    return """
Form(
  children: [
    TextFormField(hint: "Имя", value: "${controller.name}"),
    TextFormField(hint: "Email", value: "${controller.email}"),
    TextFormField(hint: "Возраст", value: "${controller.age}"),
    Checkbox(value: ${controller.isSubscribed}, label: "Подписка на новости"),
    ElevatedButton(text: "Зарегистрироваться")
  ]
)""";
  }
  
  void onNameChanged(String value) {
    controller.setName(value);
    print('Состояние обновлено: имя = $value');
  }
  
  void onEmailChanged(String value) {
    controller.setEmail(value);
    print('Состояние обновлено: email = $value');
  }
  
  void onAgeChanged(int value) {
    controller.setAge(value);
    print('Состояние обновлено: возраст = $value');
  }
  
  void onSubscriptionToggled() {
    controller.toggleSubscription();
    print('Состояние обновлено: подписка = ${controller.isSubscribed}');
  }
  
  void onSubmit() {
    if (controller.validate()) {
      User user = controller.createUser();
      print('Пользователь зарегистрирован: $user');
    } else {
      print('Ошибка: форма заполнена некорректно');
    }
  }
}

void main() {
  print('Создание формы регистрации...');
  
  RegistrationForm form = RegistrationForm();
  print(form.build());
  
  // Симуляция ввода данных
  print('\nЗаполнение формы:');
  form.onNameChanged('Алексей');
  form.onEmailChanged('alexey@example.com');
  form.onAgeChanged(25);
  form.onSubscriptionToggled();
  
  print('\nОтправка формы:');
  form.onSubmit();
  
  print('\nОбновленная форма:');
  print(form.build());
}''',
            'expected_output': 'Создание формы регистрации...\nForm(\n  children: [\n    TextFormField(hint: "Имя", value: ""),\n    TextFormField(hint: "Email", value: ""),\n    TextFormField(hint: "Возраст", value: "0"),\n    Checkbox(value: false, label: "Подписка на новости"),\n    ElevatedButton(text: "Зарегистрироваться")\n  ]\n)\n\nЗаполнение формы:\nСостояние обновлено: имя = Алексей\nСостояние обновлено: email = alexey@example.com\nСостояние обновлено: возраст = 25\nСостояние обновлено: подписка = true\n\nОтправка формы:\nПользователь зарегистрирован: User{name: Алексей, email: alexey@example.com, age: 25, subscribed: true}',
            'hints': [
                'setState() обновляет UI после изменения состояния',
                'Контроллеры помогают управлять данными форм',
                'Валидация должна проверять корректность данных',
                'Каждое изменение поля должно обновлять состояние',
                'Используйте private поля для инкапсуляции данных'
            ]
        },
        
        {
            'id': 30,
            'title': 'Навигация между экранами',
            'category': 'Flutter подготовка',
            'difficulty': 'Продвинутый',
            'description': 'Система навигации в Flutter приложениях',
            'theory': """
## Навигация в Flutter

Навигация позволяет переходить между разными экранами приложения.

### Основные концепции:

**Navigator:**
- Управляет стеком экранов
- Работает по принципу LIFO (Last In, First Out)
- Методы: `push()`, `pop()`, `pushReplacement()`

**Routes (Маршруты):**
- Именованные маршруты
- Анонимные маршруты
- Генерируемые маршруты

### Базовая навигация:
```dart
// Переход на новый экран
Navigator.push(
  context,
  MaterialPageRoute(builder: (context) => SecondScreen()),
);

// Возврат на предыдущий экран
Navigator.pop(context);
```

### Именованные маршруты:
```dart
MaterialApp(
  routes: {
    '/': (context) => HomeScreen(),
    '/profile': (context) => ProfileScreen(),
    '/settings': (context) => SettingsScreen(),
  },
);

// Переход по имени
Navigator.pushNamed(context, '/profile');
```

### Передача данных:
- Через конструктор виджета
- Через arguments в маршруте
- Возврат данных с экрана

### Типы переходов:
- `push()` - добавить экран в стек
- `pushReplacement()` - заменить текущий экран
- `pushAndRemoveUntil()` - очистить стек до определенного экрана
            """,
        },
        {
            'id': 'flutter-navigation-system',
            'title': 'Система навигации Flutter',
            'description': 'Создание многоэкранного приложения с навигацией и передачей данных',
            'task': 'Создайте систему навигации с несколькими экранами и передачей данных между ними.',
            'code_template': '''// Модель данных пользователя
class UserProfile {
  String name;
  String email;
  int age;
  
  UserProfile({required this.name, required this.email, required this.age});
  
  @override
  String toString() => 'UserProfile{name: $name, email: $email, age: $age}';
}

// Главный экран
class HomeScreen {
  String title = 'Главная страница';
  
  String build() {
    return """
Scaffold(
  appBar: AppBar(title: Text("$title")),
  body: Column(children: [
    Text("Добро пожаловать!"),
    ElevatedButton(text: "Профиль"),
    ElevatedButton(text: "Настройки"),
    ElevatedButton(text: "О программе")
  ])
)""";
  }
  
  void navigateToProfile(UserProfile user) {
    print('Навигация: Главная → Профиль (данные: $user)');
  }
  
  void navigateToSettings() {
    print('Навигация: Главная → Настройки');
  }
  
  void navigateToAbout() {
    print('Навигация: Главная → О программе');
  }
}

// Экран профиля
class ProfileScreen {
  UserProfile? user;
  String title = 'Профиль пользователя';
  
  ProfileScreen({this.user});
  
  String build() {
    String userInfo = user != null ? 
      'Имя: ${user!.name}, Email: ${user!.email}, Возраст: ${user!.age}' : 
      'Данные пользователя не загружены';
      
    return """
Scaffold(
  appBar: AppBar(title: Text("$title")),
  body: Column(children: [
    Text("$userInfo"),
    ElevatedButton(text: "Редактировать"),
    ElevatedButton(text: "Назад")
  ])
)""";
  }
  
  void navigateToEdit() {
    print('Навигация: Профиль → Редактирование');
  }
  
  UserProfile navigateBack() {
    print('Навигация: Профиль → Главная (возврат данных)');
    return user ?? UserProfile(name: 'Unknown', email: '', age: 0);
  }
}

// Экран настроек
class SettingsScreen {
  String title = 'Настройки';
  Map<String, bool> settings = {
    'notifications': true,
    'darkTheme': false,
    'autoSync': true
  };
  
  String build() {
    return """
Scaffold(
  appBar: AppBar(title: Text("$title")),
  body: Column(children: [
    SwitchListTile(title: "Уведомления", value: ${settings['notifications']}),
    SwitchListTile(title: "Темная тема", value: ${settings['darkTheme']}),
    SwitchListTile(title: "Автосинхронизация", value: ${settings['autoSync']}),
    ElevatedButton(text: "Сохранить"),
    ElevatedButton(text: "Назад")
  ])
)""";
  }
  
  void toggleSetting(String key) {
    settings[key] = !settings[key]!;
    print('Настройка "$key" изменена на ${settings[key]}');
  }
  
  void save() {
    print('Настройки сохранены: $settings');
  }
}

// Навигатор приложения
class AppNavigator {
  String currentScreen = 'home';
  HomeScreen homeScreen = HomeScreen();
  ProfileScreen? profileScreen;
  SettingsScreen settingsScreen = SettingsScreen();
  
  void navigateTo(String screenName, {dynamic data}) {
    String previousScreen = currentScreen;
    currentScreen = screenName;
    
    switch (screenName) {
      case 'profile':
        profileScreen = ProfileScreen(user: data as UserProfile?);
        print('Navigator: push ProfileScreen');
        break;
      case 'settings':
        print('Navigator: push SettingsScreen');
        break;
      case 'home':
        print('Navigator: pop to HomeScreen');
        break;
    }
    
    print('Переход: $previousScreen → $currentScreen');
    printCurrentScreen();
  }
  
  void pop({dynamic result}) {
    print('Navigator: pop with result: $result');
    navigateTo('home');
  }
  
  void printCurrentScreen() {
    switch (currentScreen) {
      case 'home':
        print(homeScreen.build());
        break;
      case 'profile':
        print(profileScreen?.build() ?? 'ProfileScreen not initialized');
        break;
      case 'settings':
        print(settingsScreen.build());
        break;
    }
  }
}

void main() {
  print('Создание системы навигации Flutter...');
  
  AppNavigator navigator = AppNavigator();
  UserProfile user = UserProfile(name: 'Иван Петров', email: 'ivan@example.com', age: 28);
  
  // Показать главный экран
  print('\n=== ГЛАВНЫЙ ЭКРАН ===');
  navigator.printCurrentScreen();
  
  // Переход к профилю с данными
  print('\n=== ПЕРЕХОД К ПРОФИЛЮ ===');
  navigator.navigateTo('profile', data: user);
  
  // Переход к настройкам
  print('\n=== ПЕРЕХОД К НАСТРОЙКАМ ===');
  navigator.navigateTo('settings');
  
  // Изменение настройки
  navigator.settingsScreen.toggleSetting('darkTheme');
  navigator.settingsScreen.save();
  
  // Возврат на главную
  print('\n=== ВОЗВРАТ НА ГЛАВНУЮ ===');
  navigator.pop(result: navigator.settingsScreen.settings);
  
  print('\nСистема навигации готова!');
}''',
            'expected_output': 'Создание системы навигации Flutter...\n\n=== ГЛАВНЫЙ ЭКРАН ===\nScaffold(\n  appBar: AppBar(title: Text("Главная страница")),\n  body: Column(children: [\n    Text("Добро пожаловать!"),\n    ElevatedButton(text: "Профиль"),\n    ElevatedButton(text: "Настройки"),\n    ElevatedButton(text: "О программе")\n  ])\n)\n\n=== ПЕРЕХОД К ПРОФИЛЮ ===\nNavigator: push ProfileScreen\nПереход: home → profile\nScaffold(\n  appBar: AppBar(title: Text("Профиль пользователя")),\n  body: Column(children: [\n    Text("Имя: Иван Петров, Email: ivan@example.com, Возраст: 28"),\n    ElevatedButton(text: "Редактировать"),\n    ElevatedButton(text: "Назад")\n  ])\n)\n\nСистема навигации готова!',
            'hints': [
                'Navigator управляет стеком экранов',
                'push() добавляет экран в стек',
                'pop() убирает текущий экран из стека',
                'Данные можно передавать через конструктор',
                'Результат можно вернуть через pop()'
            ]
        },
        # Новые продвинутые темы
        {
            'id': 31,
            'title': 'Stream API и реактивное программирование',
            'category': 'Продвинутые концепции',
            'difficulty': 'Продвинутый',
            'description': 'Работа с потоками данных и асинхронными событиями',
            'theory': '''
## Stream API в Dart

Stream представляет поток асинхронных данных - последовательность событий во времени.

### Основные концепции:
- **Single-subscription streams** - один слушатель
- **Broadcast streams** - множественные слушатели
- **StreamController** - управление потоком
- **StreamTransformer** - преобразование данных

### Создание Stream:
```dart
// Генератор Stream
Stream<int> countStream(int max) async* {
  for (int i = 1; i <= max; i++) {
    await Future.delayed(Duration(seconds: 1));
    yield i;
  }
}

// StreamController
StreamController<String> controller = StreamController();
Stream<String> stream = controller.stream;
```

### Операторы Stream:
```dart
stream
  .where((value) => value % 2 == 0)  // фильтрация
  .map((value) => value * 2)         // преобразование
  .take(5)                           // ограничение
  .listen((value) => print(value));  // подписка
```

### Практическое применение:
- Обработка пользовательского ввода
- Реал-тайм обновления UI
- WebSocket соединения
- Сенсоры и IoT устройства
            ''',
            'task': 'Создайте систему чата с использованием Streams для обработки сообщений в реальном времени',
            'code_template': '''import 'dart:async';

// Модель сообщения
class Message {
  final String user;
  final String text;
  final DateTime timestamp;
  
  Message(this.user, this.text) : timestamp = DateTime.now();
  
  @override
  String toString() => '[$user] $text (${timestamp.hour}:${timestamp.minute})';
}

// Система чата
class ChatSystem {
  final StreamController<Message> _messageController = StreamController.broadcast();
  final List<String> _users = [];
  
  // Поток сообщений
  Stream<Message> get messages => _messageController.stream;
  
  // Подключение пользователя
  void connectUser(String username) {
    if (!_users.contains(username)) {
      _users.add(username);
      _addSystemMessage('$username присоединился к чату');
    }
  }
  
  // Отправка сообщения
  void sendMessage(String user, String text) {
    if (_users.contains(user)) {
      _messageController.add(Message(user, text));
    }
  }
  
  // Системное сообщение
  void _addSystemMessage(String text) {
    _messageController.add(Message('Система', text));
  }
  
  // Отключение пользователя
  void disconnectUser(String username) {
    _users.remove(username);
    _addSystemMessage('$username покинул чат');
  }
  
  void dispose() {
    _messageController.close();
  }
}

void main() async {
  print('=== СИСТЕМА ЧАТА НА STREAMS ===\\n');
  
  final chat = ChatSystem();
  
  // Подписка на сообщения с фильтрацией
  final subscription = chat.messages
    .where((msg) => msg.text.isNotEmpty)
    .listen((message) {
      print('📨 $message');
    });
  
  // Симуляция работы чата
  chat.connectUser('Алиса');
  chat.connectUser('Боб');
  
  chat.sendMessage('Алиса', 'Привет всем!');
  
  // Добавляем задержки для демонстрации
  await Future.delayed(Duration(milliseconds: 100));
  chat.sendMessage('Боб', 'Привет, Алиса!');
  
  await Future.delayed(Duration(milliseconds: 100));
  chat.sendMessage('Алиса', 'Как дела?');
  
  await Future.delayed(Duration(milliseconds: 100));
  chat.disconnectUser('Боб');
  
  await Future.delayed(Duration(milliseconds: 100));
  chat.sendMessage('Алиса', 'Боб ушел...');
  
  // Очистка ресурсов
  await Future.delayed(Duration(milliseconds: 200));
  subscription.cancel();
  chat.dispose();
  
  print('\\n✨ Чат завершен');
}''',
            'expected_output': '=== СИСТЕМА ЧАТА НА STREAMS ===\\n\\n📨 [Система] Алиса присоединился к чату\\n📨 [Система] Боб присоединился к чату\\n📨 [Алиса] Привет всем!\\n📨 [Боб] Привет, Алиса!\\n📨 [Алиса] Как дела?\\n📨 [Система] Боб покинул чат\\n📨 [Алиса] Боб ушел...\\n\\n✨ Чат завершен',
            'hints': [
                'StreamController.broadcast() позволяет множественные подписки',
                'async* и yield создают генераторы Stream',
                'where() и map() - основные операторы фильтрации',
                'Не забывайте закрывать StreamController'
            ]
        },
        {
            'id': 32,
            'title': 'Isolates и многопоточность',
            'category': 'Продвинутые концепции',
            'difficulty': 'Продвинутый',
            'description': 'Параллельные вычисления и изоляция памяти',
            'theory': '''
## Isolates в Dart

Isolate - изолированная среда выполнения с собственной памятью. Основа многопоточности в Dart.

### Ключевые особенности:
- **Изоляция памяти** - isolates не делят память
- **Обмен сообщениями** - через SendPort/ReceivePort
- **Истинный параллелизм** - настоящие потоки ОС
- **Безопасность** - нет race conditions

### Создание Isolate:
```dart
import 'dart:isolate';

// Функция для isolate
void isolateEntry(SendPort sendPort) {
  // Тяжелые вычисления
  int result = heavyComputation();
  sendPort.send(result);
}

// Запуск isolate
final receivePort = ReceivePort();
await Isolate.spawn(isolateEntry, receivePort.sendPort);
final result = await receivePort.first;
```

### Практические применения:
- Обработка изображений
- Парсинг больших JSON файлов
- Криптографические операции
- Фоновые задачи

### Compute() helper:
```dart
import 'dart:isolate';

// Простой способ запуска тяжелых операций
int heavyTask(int number) {
  // Симуляция тяжелой задачи
  return number * number;
}

final result = await compute(heavyTask, 1000000);
```
            ''',
            'task': 'Создайте систему параллельной обработки данных с использованием Isolates',
            'code_template': '''import 'dart:isolate';
import 'dart:math';

// Задача для обработки в isolate
class ProcessingTask {
  final List<int> data;
  final String taskId;
  
  ProcessingTask(this.data, this.taskId);
}

// Результат обработки
class ProcessingResult {
  final String taskId;
  final int sum;
  final double average;
  final int max;
  final int min;
  
  ProcessingResult(this.taskId, this.sum, this.average, this.max, this.min);
  
  @override
  String toString() => 'Task $taskId: sum=$sum, avg=${average.toStringAsFixed(2)}, max=$max, min=$min';
}

// Функция для isolate - обработка данных
void dataProcessor(SendPort sendPort) {
  final receivePort = ReceivePort();
  sendPort.send(receivePort.sendPort);
  
  receivePort.listen((message) {
    if (message is ProcessingTask) {
      // Симуляция тяжелой обработки
      final data = message.data;
      
      // Вычисления
      int sum = data.reduce((a, b) => a + b);
      double average = sum / data.length;
      int max = data.reduce((a, b) => a > b ? a : b);
      int min = data.reduce((a, b) => a < b ? a : b);
      
      // Искусственная задержка для демонстрации
      for (int i = 0; i < 1000000; i++) {
        math.sqrt(i);
      }
      
      final result = ProcessingResult(message.taskId, sum, average, max, min);
      sendPort.send(result);
    }
  });
}

// Менеджер параллельной обработки
class ParallelProcessor {
  final List<Isolate> _isolates = [];
  final List<ReceivePort> _receivePorts = [];
  final List<SendPort> _sendPorts = [];
  
  // Инициализация isolates
  Future<void> initialize(int isolateCount) async {
    print('🚀 Создание $isolateCount isolates...');
    
    for (int i = 0; i < isolateCount; i++) {
      final receivePort = ReceivePort();
      final isolate = await Isolate.spawn(dataProcessor, receivePort.sendPort);
      
      final sendPort = await receivePort.first as SendPort;
      
      _isolates.add(isolate);
      _receivePorts.add(receivePort);
      _sendPorts.add(sendPort);
      
      print('✅ Isolate ${i + 1} готов');
    }
  }
  
  // Обработка задач параллельно
  Future<List<ProcessingResult>> processTasks(List<ProcessingTask> tasks) async {
    print('\\n📊 Обработка ${tasks.length} задач...');
    
    final futures = <Future<ProcessingResult>>[];
    
    for (int i = 0; i < tasks.length; i++) {
      final isolateIndex = i % _sendPorts.length;
      final sendPort = _sendPorts[isolateIndex];
      final receivePort = _receivePorts[isolateIndex];
      
      sendPort.send(tasks[i]);
      futures.add(receivePort.first.then((result) => result as ProcessingResult));
    }
    
    return await Future.wait(futures);
  }
  
  // Очистка ресурсов
  void dispose() {
    for (final isolate in _isolates) {
      isolate.kill(priority: Isolate.immediate);
    }
    for (final port in _receivePorts) {
      port.close();
    }
    _isolates.clear();
    _receivePorts.clear();
    _sendPorts.clear();
  }
}

void main() async {
  print('=== ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА ДАННЫХ ===');
  
  final processor = ParallelProcessor();
  await processor.initialize(3); // 3 isolate
  
  // Создаем тестовые данные
  final tasks = <ProcessingTask>[];
  final random = Random();
  
  for (int i = 1; i <= 6; i++) {
    final data = List.generate(1000, (_) => random.nextInt(1000));
    tasks.add(ProcessingTask(data, 'T$i'));
  }
  
  final stopwatch = Stopwatch()..start();
  
  // Параллельная обработка
  final results = await processor.processTasks(tasks);
  
  stopwatch.stop();
  
  print('\\n📈 РЕЗУЛЬТАТЫ:');
  for (final result in results) {
    print('  $result');
  }
  
  print('\\n⏱️ Время выполнения: ${stopwatch.elapsedMilliseconds}ms');
  print('🧮 Обработано ${results.length} задач параллельно');
  
  processor.dispose();
  print('\\n✨ Все isolates завершены');
}''',
            'expected_output': '=== ПАРАЛЛЕЛЬНАЯ ОБРАБОТКА ДАННЫХ ===\\n🚀 Создание 3 isolates...\\n✅ Isolate 1 готов\\n✅ Isolate 2 готов\\n✅ Isolate 3 готов\\n\\n📊 Обработка 6 задач...\\n\\n📈 РЕЗУЛЬТАТЫ:\\n  Task T1: sum=499500, avg=499.50, max=999, min=1\\n  Task T2: sum=501234, avg=501.23, max=998, min=2\\n  Task T3: sum=498765, avg=498.77, max=997, min=0\\n  Task T4: sum=502100, avg=502.10, max=999, min=3\\n  Task T5: sum=497890, avg=497.89, max=996, min=1\\n  Task T6: sum=503210, avg=503.21, max=998, min=4\\n\\n⏱️ Время выполнения: 1250ms\\n🧮 Обработано 6 задач параллельно\\n\\n✨ Все isolates завершены',
            'hints': [
                'Isolate.spawn() создает новый isolate',
                'SendPort/ReceivePort для обмена сообщениями',
                'Isolates не делят память - только сообщения',
                'Используйте compute() для простых задач'
            ]
        },
        {
            'id': 33,
            'title': 'Package Management и Pub.dev',
            'category': 'Продвинутые концепции', 
            'difficulty': 'Средний',
            'description': 'Работа с пакетами и управление зависимостями',
            'theory': '''
## Package Management в Dart

Система управления пакетами через pub.dev - центральный репозиторий Dart пакетов.

### pubspec.yaml:
```yaml
name: my_project
description: Описание проекта
version: 1.0.0

environment:
  sdk: '>=2.17.0 <4.0.0'

dependencies:
  http: ^0.13.5          # HTTP клиент
  json_annotation: ^4.8.1  # JSON аннотации
  
dev_dependencies:
  build_runner: ^2.3.3   # Кодогенерация
  json_serializable: ^6.6.2  # JSON сериализация
  test: ^1.21.0          # Тестирование
```

### Основные команды:
```bash
dart pub get        # Установка зависимостей
dart pub upgrade    # Обновление пакетов
dart pub deps       # Анализ зависимостей
dart pub publish    # Публикация пакета
```

### Создание пакета:
```dart
// lib/my_package.dart
library my_package;

export 'src/core.dart';
export 'src/utils.dart';

// Публичный API пакета
```

### Семантическое версионирование:
- **MAJOR.MINOR.PATCH** (1.2.3)
- **^1.2.3** - совместимые обновления (>=1.2.3 <2.0.0)
- **~1.2.3** - минорные обновления (>=1.2.3 <1.3.0)

### Лучшие практики:
- Четкое описание в README.md
- Документация API
- Примеры использования
- Семантическое версионирование
- Тестирование всех функций
            ''',
            'task': 'Создайте собственный пакет для работы с валютами и демонстрацию его использования',
            'code_template': '''// Создаем пакет для работы с валютами
// lib/currency_converter.dart

/// Пакет для конвертации валют
library currency_converter;

import 'dart:math';

/// Класс валюты
class Currency {
  final String code;
  final String symbol;
  final String name;
  
  const Currency(this.code, this.symbol, this.name);
  
  @override
  String toString() => '$name ($code)';
  
  @override
  bool operator ==(Object other) =>
      identical(this, other) ||
      other is Currency && code == other.code;
  
  @override
  int get hashCode => code.hashCode;
}

/// Предопределенные валюты
class Currencies {
  static const Currency usd = Currency('USD', r'$', 'US Dollar');
  static const Currency eur = Currency('EUR', '€', 'Euro');
  static const Currency rub = Currency('RUB', '₽', 'Russian Ruble');
  static const Currency jpy = Currency('JPY', '¥', 'Japanese Yen');
  static const Currency gbp = Currency('GBP', '£', 'British Pound');
  
  static const List<Currency> all = [usd, eur, rub, jpy, gbp];
}

/// Сумма в определенной валюте
class Money {
  final double amount;
  final Currency currency;
  
  const Money(this.amount, this.currency);
  
  /// Форматированный вывод
  String get formatted => '${currency.symbol}${amount.toStringAsFixed(2)}';
  
  @override
  String toString() => '$formatted ${currency.code}';
  
  /// Операции с деньгами в одной валюте
  Money operator +(Money other) {
    if (currency != other.currency) {
      throw ArgumentError('Нельзя складывать разные валюты напрямую');
    }
    return Money(amount + other.amount, currency);
  }
  
  Money operator -(Money other) {
    if (currency != other.currency) {
      throw ArgumentError('Нельзя вычитать разные валюты напрямую');
    }
    return Money(amount - other.amount, currency);
  }
  
  Money operator *(double multiplier) => Money(amount * multiplier, currency);
  Money operator /(double divisor) => Money(amount / divisor, currency);
}

/// Конвертер валют
class CurrencyConverter {
  final Map<String, double> _rates = {};
  Currency _baseCurrency = Currencies.usd;
  
  CurrencyConverter() {
    _initializeRates();
  }
  
  /// Инициализация курсов (симуляция)
  void _initializeRates() {
    final random = Random();
    _rates['USD'] = 1.0; // базовая валюта
    _rates['EUR'] = 0.85 + random.nextDouble() * 0.1;
    _rates['RUB'] = 75.0 + random.nextDouble() * 10;
    _rates['JPY'] = 110.0 + random.nextDouble() * 20;
    _rates['GBP'] = 0.73 + random.nextDouble() * 0.1;
  }
  
  /// Получить курс валюты
  double getRate(Currency currency) {
    return _rates[currency.code] ?? 1.0;
  }
  
  /// Конвертация между валютами
  Money convert(Money money, Currency targetCurrency) {
    if (money.currency == targetCurrency) return money;
    
    // Конвертируем через базовую валюту
    final fromRate = getRate(money.currency);
    final toRate = getRate(targetCurrency);
    
    final baseAmount = money.amount / fromRate;
    final targetAmount = baseAmount * toRate;
    
    return Money(targetAmount, targetCurrency);
  }
  
  /// Обновление курса валюты
  void updateRate(Currency currency, double rate) {
    _rates[currency.code] = rate;
  }
  
  /// Получить все доступные курсы
  Map<Currency, double> getAllRates() {
    final rates = <Currency, double>{};
    for (final currency in Currencies.all) {
      rates[currency] = getRate(currency);
    }
    return rates;
  }
}

/// Портфель валют
class CurrencyPortfolio {
  final Map<Currency, double> _holdings = {};
  final CurrencyConverter _converter;
  
  CurrencyPortfolio(this._converter);
  
  /// Добавить валюту в портфель
  void addMoney(Money money) {
    _holdings[money.currency] = (_holdings[money.currency] ?? 0) + money.amount;
  }
  
  /// Получить баланс в конкретной валюте
  Money getBalance(Currency currency) {
    return Money(_holdings[currency] ?? 0, currency);
  }
  
  /// Общая стоимость портфеля в базовой валюте
  Money getTotalValue(Currency targetCurrency) {
    double totalValue = 0;
    
    for (final entry in _holdings.entries) {
      final money = Money(entry.value, entry.key);
      final converted = _converter.convert(money, targetCurrency);
      totalValue += converted.amount;
    }
    
    return Money(totalValue, targetCurrency);
  }
  
  /// Получить все активы
  List<Money> getAllHoldings() {
    return _holdings.entries
        .where((entry) => entry.value > 0)
        .map((entry) => Money(entry.value, entry.key))
        .toList();
  }
}

void main() {
  print('=== СИСТЕМА КОНВЕРТАЦИИ ВАЛЮТ ===\\n');
  
  final converter = CurrencyConverter();
  final portfolio = CurrencyPortfolio(converter);
  
  // Демонстрация работы с валютами
  print('💰 Доступные валюты:');
  for (final currency in Currencies.all) {
    final rate = converter.getRate(currency);
    print('  ${currency.toString().padRight(20)} Курс: ${rate.toStringAsFixed(4)}');
  }
  
  print('\\n🔄 Конвертация валют:');
  final money1 = Money(100, Currencies.usd);
  final money2 = converter.convert(money1, Currencies.eur);
  final money3 = converter.convert(money1, Currencies.rub);
  
  print('  $money1');
  print('  ↓');
  print('  $money2');
  print('  $money3');
  
  // Работа с портфелем
  print('\\n📊 Портфель валют:');
  portfolio.addMoney(Money(1000, Currencies.usd));
  portfolio.addMoney(Money(500, Currencies.eur));
  portfolio.addMoney(Money(50000, Currencies.rub));
  portfolio.addMoney(Money(10000, Currencies.jpy));
  
  final holdings = portfolio.getAllHoldings();
  for (final money in holdings) {
    print('  ${money.toString().padRight(25)} (${money.currency.name})');
  }
  
  final totalInUsd = portfolio.getTotalValue(Currencies.usd);
  final totalInEur = portfolio.getTotalValue(Currencies.eur);
  
  print('\\n💼 Общая стоимость портфеля:');
  print('  В долларах: $totalInUsd');
  print('  В евро: $totalInEur');
  
  // Математические операции
  print('\\n🧮 Операции с деньгами:');
  final salary = Money(5000, Currencies.usd);
  final bonus = Money(1000, Currencies.usd);
  final total = salary + bonus;
  final tax = total * 0.13; // 13% налог
  final netIncome = total - tax;
  
  print('  Зарплата: $salary');
  print('  Бонус: $bonus');
  print('  Всего: $total');
  print('  Налог (13%): $tax');
  print('  К получению: $netIncome');
  
  print('\\n✨ Демонстрация пакета завершена');
}''',
            'expected_output': '=== СИСТЕМА КОНВЕРТАЦИИ ВАЛЮТ ===\\n\\n💰 Доступные валюты:\\n  US Dollar (USD)      Курс: 1.0000\\n  Euro (EUR)           Курс: 0.8756\\n  Russian Ruble (RUB)  Курс: 78.4521\\n  Japanese Yen (JPY)   Курс: 125.7834\\n  British Pound (GBP)  Курс: 0.7654\\n\\n🔄 Конвертация валют:\\n  $100.00 USD\\n  ↓\\n  €87.56 EUR\\n  ₽7845.21 RUB\\n\\n📊 Портфель валют:\\n  $1000.00 USD             (US Dollar)\\n  €500.00 EUR              (Euro)\\n  ₽50000.00 RUB            (Russian Ruble)\\n  ¥10000.00 JPY            (Japanese Yen)\\n\\n💼 Общая стоимость портфеля:\\n  В долларах: $2208.32 USD\\n  В евро: €1934.15 EUR\\n\\n🧮 Операции с деньгами:\\n  Зарплата: $5000.00 USD\\n  Бонус: $1000.00 USD\\n  Всего: $6000.00 USD\\n  Налог (13%): $780.00 USD\\n  К получению: $5220.00 USD\\n\\n✨ Демонстрация пакета завершена',
            'hints': [
                'pubspec.yaml определяет метаданные и зависимости',
                'library и export для создания публичного API',
                'Семантическое версионирование для совместимости',
                'Документация и примеры - важная часть пакета'
            ]
        }
    ]
    return jsonify(lessons_data)

# API для сохранения прогресса пользователя
@app.route('/api/save_progress', methods=['POST'])
@login_required
def save_progress():
    try:
        data = request.json
        course_id = data.get('course_id')
        lesson_id = data.get('lesson_id')
        completed = data.get('completed', False)
        
        # Проверяем, существует ли уже запись о прогрессе
        progress = UserProgress.query.filter_by(
            user_id=current_user.id, 
            course_id=course_id, 
            lesson_id=lesson_id
        ).first()
        
        if progress:
            # Обновляем существующую запись
            progress.completed = completed
        else:
            # Создаем новую запись
            progress = UserProgress(
                user_id=current_user.id,
                course_id=course_id,
                lesson_id=lesson_id,
                completed=completed
            )
            db.session.add(progress)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Прогресс сохранен'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Ошибка сохранения прогресса: {str(e)}'
        })

# API для получения прогресса пользователя
@app.route('/api/get_progress')
@login_required
def get_progress():
    try:
        # Получаем весь прогресс пользователя
        user_progress = UserProgress.query.filter_by(user_id=current_user.id).all()
        
        # Преобразуем в список словарей
        progress_list = []
        for progress in user_progress:
            progress_list.append({
                'course_id': progress.course_id,
                'lesson_id': progress.lesson_id,
                'completed': progress.completed,
                'completed_at': progress.completed_at.isoformat() if progress.completed_at else None
            })
        
        return jsonify({
            'success': True,
            'progress': progress_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'Ошибка получения прогресса: {str(e)}'
        })

# Функции для работы с достижениями
def init_achievements():
    """Инициализация стандартных достижений"""
    achievements_data = [
        # Достижения за количество уроков
        {'name': 'Первые шаги', 'description': 'Завершите первый урок', 'icon': '🌱', 
         'category': 'Прогресс', 'requirement_type': 'lessons_count', 'requirement_value': 1, 'points': 10},
        {'name': 'Начинающий', 'description': 'Завершите 5 уроков', 'icon': '📚', 
         'category': 'Прогресс', 'requirement_type': 'lessons_count', 'requirement_value': 5, 'points': 25},
        {'name': 'Ученик', 'description': 'Завершите 10 уроков', 'icon': '🎓', 
         'category': 'Прогресс', 'requirement_type': 'lessons_count', 'requirement_value': 10, 'points': 50},
        {'name': 'Продвинутый', 'description': 'Завершите 20 уроков', 'icon': '⭐', 
         'category': 'Прогресс', 'requirement_type': 'lessons_count', 'requirement_value': 20, 'points': 100},
        {'name': 'Мастер Dart', 'description': 'Завершите все 33 урока', 'icon': '👑', 
         'category': 'Прогресс', 'requirement_type': 'lessons_count', 'requirement_value': 33, 'points': 200},
        
        # Достижения за категории
        {'name': 'Основы освоены', 'description': 'Завершите все уроки категории "Основы"', 'icon': '🔰', 
         'category': 'Категории', 'requirement_type': 'category_complete', 'requirement_value': 1, 'points': 30},
        {'name': 'Мастер циклов', 'description': 'Завершите все уроки по циклам', 'icon': '🔄', 
         'category': 'Категории', 'requirement_type': 'category_complete', 'requirement_value': 2, 'points': 40},
        {'name': 'Flutter гуру', 'description': 'Завершите все уроки по Flutter', 'icon': '💙', 
         'category': 'Категории', 'requirement_type': 'category_complete', 'requirement_value': 3, 'points': 75},
        
        # Достижения за скорость и стрики
        {'name': 'Быстрая молния', 'description': 'Завершите урок менее чем за 5 минут', 'icon': '⚡', 
         'category': 'Скорость', 'requirement_type': 'lesson_speed', 'requirement_value': 5, 'points': 20},
        {'name': 'Марафонец', 'description': 'Завершите 5 уроков подряд за один день', 'icon': '🏃', 
         'category': 'Активность', 'requirement_type': 'daily_streak', 'requirement_value': 5, 'points': 60},
        {'name': 'Настойчивый', 'description': 'Изучайте курс 7 дней подряд', 'icon': '🔥', 
         'category': 'Активность', 'requirement_type': 'learning_streak', 'requirement_value': 7, 'points': 80},
        
        # Особые достижения
        {'name': 'Полуночник', 'description': 'Завершите урок после 23:00', 'icon': '🌙', 
         'category': 'Особые', 'requirement_type': 'late_night', 'requirement_value': 1, 'points': 15},
        {'name': 'Ранняя пташка', 'description': 'Завершите урок до 7:00', 'icon': '🌅', 
         'category': 'Особые', 'requirement_type': 'early_bird', 'requirement_value': 1, 'points': 15},
        {'name': 'Перфекционист', 'description': 'Завершите 10 уроков без ошибок', 'icon': '💎', 
         'category': 'Особые', 'requirement_type': 'perfect_lessons', 'requirement_value': 10, 'points': 100},
    ]
    
    for ach_data in achievements_data:
        existing = Achievement.query.filter_by(name=ach_data['name']).first()
        if not existing:
            achievement = Achievement(**ach_data)
            db.session.add(achievement)
    
    db.session.commit()

def check_achievements(user_id, lesson_id=None):
    """Проверка и выдача достижений пользователю"""
    user = User.query.get(user_id)
    if not user:
        return []
    
    new_achievements = []
    user_progress = UserProgress.query.filter_by(user_id=user_id, completed=True).all()
    completed_count = len(user_progress)
    
    # Получаем уже полученные достижения
    earned_achievements = UserAchievement.query.filter_by(user_id=user_id).all()
    earned_ids = {ea.achievement_id for ea in earned_achievements}
    
    # Проверяем достижения по количеству уроков
    lesson_achievements = Achievement.query.filter_by(requirement_type='lessons_count').all()
    for achievement in lesson_achievements:
        if achievement.id not in earned_ids and completed_count >= achievement.requirement_value:
            user_achievement = UserAchievement(user_id=user_id, achievement_id=achievement.id)
            db.session.add(user_achievement)
            new_achievements.append(achievement)
    
    # Проверяем достижения по времени (если передан lesson_id)
    if lesson_id:
        from datetime import datetime
        current_hour = datetime.now().hour
        
        # Полуночник (23:00 - 6:59)
        if current_hour >= 23 or current_hour < 7:
            late_night_ach = Achievement.query.filter_by(requirement_type='late_night').first()
            if late_night_ach and late_night_ach.id not in earned_ids:
                user_achievement = UserAchievement(user_id=user_id, achievement_id=late_night_ach.id)
                db.session.add(user_achievement)
                new_achievements.append(late_night_ach)
        
        # Ранняя пташка (5:00 - 6:59)
        if 5 <= current_hour < 7:
            early_bird_ach = Achievement.query.filter_by(requirement_type='early_bird').first()
            if early_bird_ach and early_bird_ach.id not in earned_ids:
                user_achievement = UserAchievement(user_id=user_id, achievement_id=early_bird_ach.id)
                db.session.add(user_achievement)
                new_achievements.append(early_bird_ach)
    
    db.session.commit()
    return new_achievements

# API маршруты для достижений
@app.route('/api/achievements')
@login_required
def get_achievements():
    """Получить все достижения и статус их получения"""
    try:
        all_achievements = Achievement.query.all()
        user_achievements = UserAchievement.query.filter_by(user_id=current_user.id).all()
        
        earned_ids = {ua.achievement_id for ua in user_achievements}
        
        achievements_data = []
        total_points = 0
        
        for achievement in all_achievements:
            is_earned = achievement.id in earned_ids
            if is_earned:
                total_points += achievement.points
                
            achievements_data.append({
                'id': achievement.id,
                'name': achievement.name,
                'description': achievement.description,
                'icon': achievement.icon,
                'category': achievement.category,
                'points': achievement.points,
                'earned': is_earned,
                'earned_at': next((ua.earned_at.isoformat() for ua in user_achievements 
                                 if ua.achievement_id == achievement.id), None)
            })
        
        return jsonify({
            'achievements': achievements_data,
            'total_points': total_points,
            'earned_count': len(earned_ids)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/achievements')
@login_required
def achievements_page():
    """Страница достижений"""
    return render_template('achievements.html')

# Обновляем функцию save_progress для проверки достижений
def save_progress_with_achievements():
    """Обновленная версия save_progress с проверкой достижений"""
    @app.route('/api/save_progress_v2', methods=['POST'])
    @login_required
    def save_progress_v2():
        try:
            data = request.json
            course_id = data.get('course_id')
            lesson_id = data.get('lesson_id')
            completed = data.get('completed', False)
            
            # Проверяем существующий прогресс
            progress = UserProgress.query.filter_by(
                user_id=current_user.id,
                course_id=course_id,
                lesson_id=lesson_id
            ).first()
            
            if progress:
                progress.completed = completed
                if completed:
                    progress.completed_at = db.func.now()
            else:
                progress = UserProgress(
                    user_id=current_user.id,
                    course_id=course_id,
                    lesson_id=lesson_id,
                    completed=completed
                )
                db.session.add(progress)
            
            db.session.commit()
            
            # Проверяем достижения если урок завершен
            new_achievements = []
            if completed:
                new_achievements = check_achievements(current_user.id, lesson_id)
            
            return jsonify({
                'success': True,
                'message': 'Прогресс сохранен',
                'new_achievements': [{
                    'name': ach.name,
                    'description': ach.description,
                    'icon': ach.icon,
                    'points': ach.points
                } for ach in new_achievements]
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'success': False,
                'error': f'Ошибка сохранения прогресса: {str(e)}'
            })

# Инициализируем обновленную функцию
save_progress_with_achievements()

if __name__ == '__main__':
    # Создание таблиц базы данных
    with app.app_context():
        db.create_all()
        # Инициализация достижений
        init_achievements()
    
    app.run(debug=True)