# Bank SaaS — Корпоративный агрегатор банковских операций

Внутренний SaaS-инструмент для мониторинга банковских операций и балансов нескольких юридических лиц через единый Telegram-интерфейс. Работает в проде, используется командой директора и менеджеров.

---

## Содержание

- [Зачем это нужно](#зачем-это-нужно)
- [Основной функционал](#основной-функционал)
- [Архитектура](#архитектура)
- [Технологии](#технологии)
- [Структура проекта](#структура-проекта)
- [База данных](#база-данных)
- [Интеграции с банками](#интеграции-с-банками)
- [Управление доступом](#управление-доступом)
- [Установка и запуск](#установка-и-запуск)
- [Конфигурация](#конфигурация)
- [API](#api)
- [Разработка](#разработка)

---

## Зачем это нужно

Компания работает с несколькими юридическими лицами и двумя банками. Раньше директор и менеджеры заходили в каждый банк отдельно, вручную сверяли приходы и расходы, отслеживали контрагентов. Это занимало до 1-2 часов в день.

Сейчас весь финансовый мониторинг — в одном Telegram-боте: балансы, операции, контрагенты, статусы запросов.

---

## Основной функционал

### Для директора
- Просмотр текущих балансов по всем счетам (Точка + Сбербанк) одной кнопкой
- Разбивка входящих/исходящих по контрагентам за день
- Управление доступом менеджеров: одобрение/отказ заявок на отслеживание компаний
- Назначение менеджерам доступа к конкретным юридическим лицам
- Список всех менеджеров и их компаний

### Для менеджеров
- Запрос на отслеживание компании по ИНН (с согласованием директора)
- Просмотр операций по компании за 1 / 5 / 30 дней
- Итоги: приход, расход, детализация по операциям
- Отзыв своего доступа к компании

### Системные
- Автоматическая синхронизация операций каждые 5 минут
- Импорт выписок из 1С (формат Client-Bank, кодировка CP1251)
- Автоматическое создание карточек контрагентов из операций (через DaData)
- Определение внутренних переводов между своими юрлицами
- Защита от дублей на уровне базы данных

---

## Архитектура

```
┌───────────────────────────────────┐
│         Telegram Bot              │
│  (aiogram 3.4, роли: директор /   │
│   менеджер, FSM состояния)        │
└──────────────┬────────────────────┘
               │ HTTP + X-API-Key
               ▼
┌───────────────────────────────────┐
│        FastAPI Backend            │
│  /companies  /operations          │
│  /imports    /balances            │
│  /telegram   /bank-connections    │
└──────┬──────────────┬─────────────┘
       │              │
       ▼              ▼
┌────────────┐  ┌──────────────────────────┐
│ PostgreSQL │  │     APScheduler          │
│  16 tables │  │   каждые 5 минут:        │
│  Alembic   │  │   AccountSync →          │
│  migrations│  │   OperationSync          │
└────────────┘  └──────┬───────────────────┘
                       │
          ┌────────────┴─────────────┐
          ▼                          ▼
┌─────────────────┐      ┌─────────────────────┐
│   Точка API     │      │   Сбербанк API       │
│   OAuth 2.0     │      │   SSL-сертификат     │
│   REST          │      │   REST               │
└─────────────────┘      └─────────────────────┘
          │
          ▼
┌─────────────────┐
│   DaData API    │
│  (данные по ИНН)│
└─────────────────┘
```

**Паттерны:**
- **Adapter** — единый интерфейс для разных банков (`BankAdapterFactory`)
- **Service Layer** — бизнес-логика отделена от роутеров
- **Repository** — работа с БД через SQLAlchemy sessions
- **Scheduler** — фоновые задачи через APScheduler (в процессе)

---

## Технологии

| Компонент | Технология |
|-----------|-----------|
| Backend API | FastAPI 0.134, Python 3.11 |
| База данных | PostgreSQL 16 |
| ORM + миграции | SQLAlchemy 2.0, Alembic |
| Telegram Bot | aiogram 3.4 (async) |
| Планировщик | APScheduler 3.10 |
| Валидация | Pydantic 2.12 |
| HTTP клиент | httpx 0.27, requests 2.32 |
| Инфраструктура | Docker, Docker Compose |
| Данные по ИНН | DaData API |

---

## Структура проекта

```
bank-saas/
├── app/
│   ├── api/                    # FastAPI роутеры
│   │   ├── company_router.py
│   │   ├── bank_operation_router.py
│   │   ├── import_router.py
│   │   ├── balance_router.py
│   │   └── telegram_router.py  # 35+ эндпоинтов для бота
│   ├── models/                 # SQLAlchemy модели
│   │   ├── user.py
│   │   ├── company.py
│   │   ├── bank_account.py
│   │   ├── bank_operation.py
│   │   └── ...
│   ├── services/               # Бизнес-логика
│   │   ├── operation_sync_service.py   # Ядро синхронизации
│   │   ├── balance_service.py          # Агрегация балансов
│   │   ├── import_service.py           # Импорт выписок
│   │   ├── company_service.py          # Управление компаниями
│   │   └── sync_scheduler.py           # Фоновый планировщик
│   ├── integrations/
│   │   └── banks/
│   │       ├── adapter_factory.py      # Фабрика адаптеров банков
│   │       ├── tochka/                 # Интеграция с Точкой
│   │       │   ├── client.py           # OAuth 2.0 клиент
│   │       │   └── adapter.py
│   │       └── sber/                   # Интеграция со Сбером
│   │           ├── client.py           # SSL-cert клиент
│   │           └── adapter.py
│   ├── parsers/
│   │   └── kl_to_1c_parser.py         # Парсер Client-Bank выписок
│   ├── security/
│   │   └── api_key.py                 # API-key middleware
│   ├── config/
│   │   └── settings.py                # Pydantic Settings
│   └── main.py                        # Точка входа FastAPI
├── bot/
│   └── telegram_bot.py                # Telegram bot (aiogram)
├── migrations/
│   └── versions/                      # Alembic миграции
├── tests/                             # Ручные тесты и скрипты
├── certs/                             # SSL-сертификаты Сбербанка
├── logs/                              # Ротируемые JSON-логи синхронизации
├── docker-compose.yml
├── Dockerfile
├── Dockerfile.bot
├── requirements.txt
└── requirements_bot.txt
```

---

## База данных

15 таблиц PostgreSQL с полной системой внешних ключей и индексов.

```
users ──────────────── user_roles ── roles
  │                        │
  ├── telegram_accounts     │
  │                        │
  ├── user_companies ───────┤
  │                        │
  └── tracked_companies     │

companies ─────────────────┐
  │                        │
  ├── legal_entities        │
  │                        │
  ├── bank_connections      │
  │     └── bank_accounts   │
  │           └── bank_operations (с уникальным constraint на 6 полей)
  │
  └── operation_batches

manager_requests
user_registration_requests
```

**Защита от дублей** — уникальный индекс:
```sql
UNIQUE (company_id, document_number, document_type, operation_date, amount, direction)
```

Импорт использует `INSERT ... ON CONFLICT DO NOTHING` — быстро, без исключений.

---

## Интеграции с банками

### Точка (Open Banking API)
- Аутентификация: OAuth 2.0, Bearer token
- Автообновление токена при 401/403 через refresh_token
- Получение списка счетов + выписки по периоду
- Формат ответа: JSON (Data.Account, Amount.amount)

### Сбербанк (Fintech API)
- Аутентификация: SSL client certificate (cert.pem + key.pem)
- Получение сводки по дням + постраничные транзакции (100/страница)
- Итерация по датам в запрошенном диапазоне

### Логика синхронизации
- **Первая синхронизация**: lookback 90 дней
- **Инкрементная**: от `last_synced_at - 1 день` (перекрытие для надёжности)
- **Логи**: ротируемые JSON-файлы (max 5 файлов в `logs/`)

---

## Управление доступом

### Роли
| Роль | Возможности |
|------|-------------|
| `director` | Балансы всех счетов, управление менеджерами, назначение доступа к юрлицам |
| `manager` | Запрос доступа к компаниям, просмотр операций в рамках своих юрлиц |

### Workflow согласования
```
Менеджер вводит ИНН
    ↓
Создаётся ManagerRequest (status=pending)
    ↓
Директор получает уведомление в Telegram
    ↓
Директор одобряет ✅ или отклоняет ❌
    ↓
При одобрении создаётся TrackedCompany
```

### Регистрация пользователей
- Новый пользователь нажимает /start
- Создаётся UserRegistrationRequest (status=pending)
- Директор видит запрос, назначает доступ к юрлицам
- После одобрения — пользователь активен

### API-защита
- Все эндпоинты требуют заголовок `X-API-Key`
- Ключ задаётся через переменную окружения `INTERNAL_API_KEY`

---

## Установка и запуск

### Требования
- Docker + Docker Compose
- Токены Точки (OAuth 2.0)
- SSL-сертификат Сбербанка (опционально)
- Telegram Bot Token
- DaData API Key

### Шаги

1. **Клонировать репозиторий**
```bash
git clone <repo-url>
cd bank-saas
```

2. **Создать `.env` файл**
```bash
cp .env.example .env
# Заполнить все переменные (см. раздел Конфигурация)
```

3. **Добавить SSL-сертификаты Сбербанка** (если используется)
```
certs/cert.pem
certs/key.pem
```

4. **Запустить**
```bash
docker compose up -d
```

При старте автоматически:
- Применяются миграции БД (`alembic upgrade head`)
- Создаются роли (`seed_roles`)
- Запускается планировщик синхронизации

5. **Проверить работу**
```
http://localhost:8000/        # healthcheck
http://localhost:8000/docs    # Swagger UI
```

---

## Конфигурация

Файл `.env`:

```env
# База данных
DATABASE_URL=postgresql://bank_user:bank_pass@postgres:5432/bank_saas

# Точка
TOCHKA_CLIENT_ID=your_client_id
TOCHKA_CLIENT_SECRET=your_client_secret
TOCHKA_API_URL=https://enter.tochka.com/uapi
TOCHKA_TOKEN_URL=https://enter.tochka.com/connect/token

# Сбербанк
SBER_ACCESS_TOKEN=your_token
SBER_BOOTSTRAP_ACCOUNT=40702810XXXXXXXXXXXXXXXXX  # Номер счёта (API Сбера не возвращает список)

# Telegram
TELEGRAM_BOT_TOKEN=your_bot_token

# DaData
DADATA_API_KEY=your_key
DADATA_SECRET_KEY=your_secret

# Безопасность
INTERNAL_API_KEY=your_internal_key

# Режим
DEBUG=false
```

---

## API

FastAPI автоматически генерирует документацию:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### Основные группы эндпоинтов

| Префикс | Назначение |
|---------|-----------|
| `GET /` | Healthcheck + проверка БД |
| `/companies` | CRUD компаний |
| `/companies/{id}/operations` | Операции с фильтрами и сводками |
| `/bank-connections` | Регистрация банковских подключений |
| `/imports/bank-statement` | Загрузка выписки в формате 1С |
| `/sync/tochka` | Ручной запуск синхронизации |
| `/balances` | Текущие балансы + операции за день |
| `/telegram/*` | 35+ эндпоинтов для Telegram-бота |

---

## Разработка

### Запуск без Docker
```bash
# Backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Bot (в отдельном терминале)
pip install -r requirements_bot.txt
python -m bot.telegram_bot
```

### Миграции
```bash
# Создать новую миграцию после изменений моделей
alembic revision --autogenerate -m "описание изменений"

# Применить миграции
alembic upgrade head

# Проверить статус
alembic current
```

### Ручные тесты
```bash
# Проверить парсер 1С-выписок
python tests/test_parser.py

# Ручная синхронизация
python tests/manual_sync.py

# Тест Точка API
python tests/test_tochka_client.py

# Тест Сбербанк API
python tests/test_sber_client.py
```

### Просмотр базы данных
```bash
docker exec -it bank_postgres psql -U bank_user -d bank_saas
```

---

## Лицензия

Внутренний корпоративный инструмент. Не предназначен для публичного использования.
