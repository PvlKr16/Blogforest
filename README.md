# BlogForest 🌿

Веб-приложение для блогов на Django + PostgreSQL.

## Стек

- **Backend**: Django 4.2, PostgreSQL
- **Frontend**: адаптивный HTML/CSS (без JS-фреймворков)
- **Дизайн**: мягкая палитра зелёный · серый · коричневый, шрифты Lora + Source Serif 4

## Функциональность

- Регистрация и аутентификация по email + паролю
- Открытые и закрытые блоги
- Управление участниками: добавить, удалить, покинуть блог
- Любой участник может писать посты
- Посты: заголовок, текст, обложка (до 5 МБ), прикреплённые файлы (до 10 МБ каждый)
- Теги и категории, поиск по постам
- Комментарии
- Профили пользователей
- Django Admin панель

---

## Быстрый старт

### 1. Клонировать / распаковать проект

```bash
cd blogforest
```

### 2. Создать виртуальное окружение и установить зависимости

```bash
python -m venv venv
source venv/bin/activate        # Linux/macOS
# venv\Scripts\activate          # Windows

pip install -r requirements.txt
```

### 3. Настроить переменные окружения

```bash
cp .env.example .env
# Отредактируйте .env: SECRET_KEY, DB_NAME, DB_USER, DB_PASSWORD
```

### 4. Создать базу данных PostgreSQL

```sql
CREATE DATABASE blogdb;
CREATE USER bloguser WITH PASSWORD 'blogpassword';
GRANT ALL PRIVILEGES ON DATABASE blogdb TO bloguser;
```

### 5. Применить миграции

```bash
python manage.py migrate
```

### 6. Создать суперпользователя (для Admin)

```bash
python manage.py createsuperuser
```

### 7. Запустить сервер

```bash
python manage.py runserver
```

Открыть в браузере: [http://127.0.0.1:8000](http://127.0.0.1:8000)

Admin панель: [http://127.0.0.1:8000/admin](http://127.0.0.1:8000/admin)

---

## Структура проекта

```
blogforest/
├── blogproject/          # Настройки Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── blogapp/              # Основное приложение
│   ├── models.py         # Blog, Post, PostFile, Comment, Tag
│   ├── views.py          # Все представления
│   ├── urls.py           # URL-маршруты
│   ├── forms.py          # Формы
│   ├── admin.py          # Admin-конфигурация
│   ├── templates/        # HTML-шаблоны
│   └── static/           # CSS
├── media/                # Загруженные файлы (создаётся автоматически)
├── manage.py
├── requirements.txt
└── .env.example
```

## Лимиты файлов

| Тип          | Лимит   |
|--------------|---------|
| Обложка блога   | 5 МБ |
| Изображение поста | 5 МБ |
| Прикреплённый файл | 10 МБ |

Лимиты изменяются в `blogproject/settings.py`:
```python
MAX_UPLOAD_SIZE = 10 * 1024 * 1024   # 10 МБ
MAX_IMAGE_SIZE  =  5 * 1024 * 1024   #  5 МБ
```
