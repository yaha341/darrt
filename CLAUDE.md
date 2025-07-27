# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CodeAcademy Pro** - интерактивная IT академия для изучения различных языков программирования. Платформа предоставляет онлайн редактор кода с возможностью выполнения в реальном времени. Первый доступный курс - Dart, в планах добавление Python, JavaScript, Java, C#, Rust.

## Technology Stack

- **Backend**: Flask (Python) with REST API
- **Frontend**: HTML/CSS/JavaScript with CodeMirror editor
- **Code Execution**: Dart SDK with subprocess execution in temporary files
- **Styling**: Custom CSS with dark theme and responsive design

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run development server
python app.py

# The application will be available at http://localhost:5000
```

## Project Structure

```
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── templates/            
│   ├── base.html         # Base template with navigation
│   ├── index.html        # Landing page
│   └── lessons.html      # Interactive lessons page
├── static/
│   ├── css/
│   │   └── style.css     # Main stylesheet with dark theme
│   └── js/
│       └── app.js        # Frontend JavaScript functionality
└── CLAUDE.md             # This file
```

## Key Features

- **Interactive Code Editor**: CodeMirror with Dart syntax highlighting
- **Real-time Code Execution**: Server-side Dart code execution with security constraints
- **Lesson System**: Progressive learning with predefined code templates
- **Progress Tracking**: Client-side progress storage using localStorage
- **Responsive Design**: Works on desktop and mobile devices

## API Endpoints

- `GET /` - Landing page
- `GET /courses` - Courses selection page
- `GET /lessons` - Interactive Dart lessons interface  
- `GET /api/lessons` - Returns lesson data as JSON
- `POST /api/execute_dart` - Executes Dart code and returns output

## Security Considerations

- Code execution is limited to 10 seconds timeout
- Temporary files are automatically cleaned up
- Input validation on all API endpoints
- No persistent file storage for user code

## Adding New Lessons

Lessons are defined in the `/api/lessons` endpoint in `app.py`. Each lesson should include:
- `id`: Unique identifier
- `title`: Lesson title
- `description`: Brief description
- `code_template`: Starting code for the lesson
- `expected_output`: Expected result (optional)

## Prerequisites

- Python 3.7+
- Dart SDK installed and accessible via `dart` command
- Modern web browser with JavaScript enabled