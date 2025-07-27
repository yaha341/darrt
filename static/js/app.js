// Основные функции приложения

// Функция для выполнения Dart кода
async function runDartCode(code, outputElementId) {
    const outputEl = document.getElementById(outputElementId);
    const loadingEl = document.getElementById('loading');
    
    // Показываем индикатор загрузки
    if (loadingEl) {
        loadingEl.style.display = 'flex';
    }
    
    // Очищаем предыдущий вывод
    outputEl.innerHTML = '<div class="output-info">Выполнение кода...</div>';
    
    try {
        const response = await fetch('/api/execute_dart', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ code: code })
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (result.output) {
                outputEl.innerHTML = `<div class="output-success">${escapeHtml(result.output)}</div>`;
            } else {
                outputEl.innerHTML = '<div class="output-info">Код выполнен успешно (без вывода)</div>';
            }
            
            if (result.error) {
                outputEl.innerHTML += `<div class="output-warning">Предупреждения:\n${escapeHtml(result.error)}</div>`;
            }
        } else {
            outputEl.innerHTML = `<div class="output-error">Ошибка:\n${escapeHtml(result.error)}</div>`;
        }
        
    } catch (error) {
        outputEl.innerHTML = `<div class="output-error">Ошибка соединения: ${escapeHtml(error.message)}</div>`;
    } finally {
        // Скрываем индикатор загрузки
        if (loadingEl) {
            loadingEl.style.display = 'none';
        }
    }
}

// Функция для экранирования HTML
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Функция для форматирования времени выполнения
function formatExecutionTime(startTime) {
    const endTime = Date.now();
    const duration = endTime - startTime;
    return `Время выполнения: ${duration}ms`;
}

// Функция для сохранения кода в localStorage
function saveCodeToStorage(lessonId, code) {
    const key = `lesson_${lessonId}_code`;
    localStorage.setItem(key, code);
}

// Функция для загрузки кода из localStorage
function loadCodeFromStorage(lessonId) {
    const key = `lesson_${lessonId}_code`;
    return localStorage.getItem(key);
}

// Функция для отслеживания прогресса
function trackProgress(lessonId, completed = false) {
    // Сохраняем прогресс в localStorage как резервную копию
    if (typeof localStorage !== 'undefined') {
        const progressKey = 'lesson_progress';
        let progress = JSON.parse(localStorage.getItem(progressKey) || '{}');
        
        if (!progress[lessonId]) {
            progress[lessonId] = {
                started: new Date().toISOString(),
                completed: null,
                attempts: 0
            };
        }
        
        progress[lessonId].attempts += 1;
        
        if (completed) {
            progress[lessonId].completed = new Date().toISOString();
        }
        
        localStorage.setItem(progressKey, JSON.stringify(progress));
    }
    
    // Отправляем прогресс на сервер
    saveProgressToServer(lessonId, completed);
    
    updateProgressUI();
}

// Функция для сохранения прогресса на сервере
async function saveProgressToServer(lessonId, completed = false) {
    try {
        // В реальном приложении здесь будут реальные ID курса и урока
        const courseId = 'dart-basics'; // Пока фиксированное значение
        
        const response = await fetch('/api/save_progress', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                course_id: courseId,
                lesson_id: lessonId,
                completed: completed
            })
        });
        
        const result = await response.json();
        
        if (!result.success) {
            console.error('Ошибка сохранения прогресса:', result.error);
        }
    } catch (error) {
        console.error('Ошибка соединения при сохранении прогресса:', error);
    }
}

// Функция для получения прогресса с сервера
async function loadProgressFromServer() {
    try {
        const response = await fetch('/api/get_progress');
        const result = await response.json();
        
        if (result.success) {
            // Обновляем localStorage данными с сервера
            if (typeof localStorage !== 'undefined') {
                const progressKey = 'lesson_progress';
                const serverProgress = {};
                
                result.progress.forEach(item => {
                    serverProgress[item.lesson_id] = {
                        started: null, // У сервера нет этой информации
                        completed: item.completed_at,
                        attempts: 0 // У сервера нет этой информации
                    };
                });
                
                localStorage.setItem(progressKey, JSON.stringify(serverProgress));
            }
            
            return result.progress;
        } else {
            console.error('Ошибка загрузки прогресса:', result.error);
            return [];
        }
    } catch (error) {
        console.error('Ошибка соединения при загрузке прогресса:', error);
        return [];
    }
}

// Функция для обновления UI прогресса
function updateProgressUI() {
    // Сначала пытаемся получить прогресс с сервера, переданный через HTML
    let initialServerProgress = [];
    const progressDataElement = document.getElementById('server-progress-data');
    if (progressDataElement) {
        try {
            initialServerProgress = JSON.parse(progressDataElement.textContent);
        } catch (e) {
            console.error('Ошибка парсинга данных прогресса:', e);
        }
    }
    
    // Обновляем отображение прогресса в UI с начальными данными
    updateProgressElements(initialServerProgress);
    
    // Затем пытаемся загрузить актуальный прогресс с сервера
    loadProgressFromServer().then(serverProgress => {
        updateProgressElements(serverProgress);
    });
}

// Вспомогательная функция для обновления элементов прогресса
function updateProgressElements(serverProgress) {
    const progressElements = document.querySelectorAll('[data-lesson-id]');
    progressElements.forEach(el => {
        const lessonId = el.getAttribute('data-lesson-id');
        
        // Проверяем прогресс на сервере
        const serverLessonProgress = serverProgress.find(item => item.lesson_id === lessonId);
        if (serverLessonProgress && serverLessonProgress.completed) {
            el.classList.add('completed');
            return;
        }
        
        // Если на сервере нет прогресса, проверяем localStorage
        if (typeof localStorage !== 'undefined') {
            const progressKey = 'lesson_progress';
            const localProgress = JSON.parse(localStorage.getItem(progressKey) || '{}');
            if (localProgress[lessonId] && localProgress[lessonId].completed) {
                el.classList.add('completed');
            }
        }
    });
}

// Функция для проверки правильности кода
function checkCodeCorrectness(output, expectedOutput) {
    if (!expectedOutput) return true;
    
    // Простая проверка соответствия вывода
    const cleanOutput = output.trim().replace(/\s+/g, ' ');
    const cleanExpected = expectedOutput.trim().replace(/\s+/g, ' ');
    
    return cleanOutput === cleanExpected;
}

// Функция для показа подсказок
function showHint(message, type = 'info') {
    const hintEl = document.createElement('div');
    hintEl.className = `hint hint-${type}`;
    hintEl.textContent = message;
    
    document.body.appendChild(hintEl);
    
    // Автоматически скрываем через 5 секунд
    setTimeout(() => {
        if (hintEl.parentNode) {
            hintEl.parentNode.removeChild(hintEl);
        }
    }, 5000);
}

// Функция для добавления горячих клавиш
function setupKeyboardShortcuts() {
    document.addEventListener('keydown', function(event) {
        // Ctrl+Enter или Cmd+Enter для запуска кода
        if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
            event.preventDefault();
            const runButton = document.getElementById('run-code') || document.getElementById('run-demo');
            if (runButton) {
                runButton.click();
            }
        }
        
        // Ctrl+R или Cmd+R для сброса кода
        if ((event.ctrlKey || event.metaKey) && event.key === 'r') {
            event.preventDefault();
            const resetButton = document.getElementById('reset-code');
            if (resetButton) {
                resetButton.click();
            }
        }
    });
}

// Функция для инициализации приложения
function initializeApp() {
    setupKeyboardShortcuts();
    updateProgressUI();
    
    // Добавляем CSS для прогресса и подсказок
    const style = document.createElement('style');
    style.textContent = `
        .lesson-started::before {
            content: "🔄 ";
        }
        
        .lesson-completed::before {
            content: "✅ ";
        }
        
        .hint {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 20px;
            border-radius: 6px;
            color: white;
            font-weight: 500;
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
        }
        
        .hint-info {
            background-color: #0969da;
        }
        
        .hint-success {
            background-color: #1a7f37;
        }
        
        .hint-warning {
            background-color: #9a6700;
        }
        
        .hint-error {
            background-color: #d1242f;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
        
        .output-success {
            color: #3fb950;
        }
        
        .output-error {
            color: #f85149;
        }
        
        .output-warning {
            color: #d29922;
        }
        
        .output-info {
            color: #58a6ff;
        }
    `;
    document.head.appendChild(style);
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', initializeApp);