# 🍽️ Foodgram | Социальная сеть для гурманов

**Добро пожаловать в кулинарную вселенную!**  
Foodgram — это твоя цифровая кухня, где можно делиться рецептами, находить вдохновение и создавать идеальные списки покупок.  

---

## 🌟 Ключевые возможности
- **Публикация рецептов** с фото и детальным описанием
- **Избранное** — сохраняй рецепты в личную коллекцию
- **Подписки** на любимых авторов

---

## ⚙️ Технологический стек
| Категория              | Технологии                          |
|------------------------|-------------------------------------|
| **Backend**            | Python 3, Django REST Framework     |
| **Frontend**           | React                               |
| **База данных**        | PostgreSQL                          |
| **Инфраструктура**     | Docker, Nginx, Gunicorn             |

---

## 🚀 Быстрый старт: развертывание за 5 минут

### Предварительные условия
- Установленные **Docker** и **Docker Compose**
- Клонированный репозиторий

```bash
git clone https://github.com/khaustovdn/foodgram-st Foodgram
cd Foodgram/infra
```

### 1. Настройка окружения
Создайте `.env` файл и заполните по шаблону:
```bash
# PostgreSQL
POSTGRES_DB=your_db_name
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_strong_password
DB_HOST=db
DB_PORT=5432

# Django
SECRET_KEY=your_django_secret_key
DEBUG=False  # Для продакшена
```

### 2. Запуск проекта
Собираем и запускаем контейнеры:
```bash
docker-compose.exe up -d --no-deps --build
```

### 3. Инициализация проекта
```bash
# Подготавливаем миграции
docker-compose.exe exec backend python manage.py makemigrations

# Применяем миграции
docker-compose.exe exec backend python manage.py migrate

# Создаем суперпользователя
docker-compose.exe exec backend python manage.py createsuperuser

# Загружаем ингредиенты
docker-compose.exe exec backend python manage.py loaddata ingredients_fixture.json

# Собираем статику
docker-compose.exe exec backend python manage.py collectstatic --noinput
```

### 🔄 Сброс окружения
Полная остановка проекта с удалением **всех данных** (контейнеры, тома, сети):
```bash
docker compose down -v
```
> ⚠️ Важно: Эта команда удалит все ваши данные БД! Используйте только при необходимости полного сброса.

### ☢️ Атомная очистка
Полная очистка Docker-системы (**удаляет всё**):
```bash
docker system prune -af --volumes
```

---

## 🔗 Основные эндпоинты
| Назначение                           | URL                               |
|--------------------------------------|-----------------------------------|
| **Главная страница**                 | `http://localhost:8000/`          |
| **Админ-панель**                     | `http://localhost:8000/admin/`    |
| **Интерактивная документация API**   | `http://localhost:8000/api/docs/` |
| **API Endpoint**                     | `http://localhost:8000/api/`      |

---

## 🎉 Готово! Foodgram запущен!