# Desktop Waifu

Анимированный персонаж-компаньон для вашего рабочего стола, созданный с использованием Python и Pygame.

## Описание

Этот проект добавляет на ваш рабочий стол анимированную вайфу, которая живет своей жизнью: гуляет по окнам приложений, прыгает между ними и просто отдыхает. Приложение использует Pygame для создания прозрачного окна и анимаций, а также включает в себя серверную часть для сбора статистики о действиях персонажа.

## Ключевые технологии

*   **Клиент**: Python, Pygame, pywin32
*   **Сервер**: FastAPI, Docker, InfluxDB, Grafana
*   **Взаимодействие**: REST API, WebSockets

## Структура проекта

```
Waifu/
├── assets/                  # Спрайты персонажа
├── server/                  # Серверное приложение (FastAPI, Docker)
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── waifu/                   # Логика клиента
│   ├── __init__.py
│   ├── character.py         # Основной класс персонажа, AI
│   ├── physics.py           # Физический движок
│   ├── platform.py          # Класс для платформ (окон)
│   └── utils.py             # Вспомогательные функции
├── config.py                # Файл конфигурации
├── docker-compose.yml       # Файл для запуска сервера и баз данных
├── main_app.py              # Основной файл для запуска клиента
└── requirements.txt         # Зависимости клиента
```

---

## 🚀 Инструкция по запуску

Для полноценной работы необходим установленный Docker.

### Шаг 1: Запуск сервера

Серверная часть, база данных и система мониторинга запускаются одной командой с помощью Docker.

1.  Установите [Docker](https://www.docker.com/products/docker-desktop/) на вашу систему.
2.  Откройте терминал в корневой папке проекта и выполните команду:

    ```bash
    docker-compose up -d
    ```
    Эта команда в фоновом режиме скачает необходимые образы, соберет и запустит контейнеры с сервером, базой данных InfluxDB и Grafana для визуализации.

    *   **API-сервер** будет доступен по адресу `http://localhost:8000`.
    *   **Grafana** будет доступна по адресу `http://localhost:3000`.

### Шаг 2: Запуск клиента

Клиент — это само приложение с персонажем, которое вы увидите на рабочем столе.

1.  Убедитесь, что у вас установлен Python 3.8+
2.  Создайте виртуальное окружение и установите зависимости:
    ```bash
    # Для Windows
    python -m venv .venv
    .\.venv\Scripts\activate
    
    # Установка зависимостей
    pip install -r requirements.txt
    ```
3.  Запустите приложение:
    ```bash
    python main_app.py
    ```
После этого на вашем рабочем столе должен появиться анимированный персонаж. Он начнет взаимодействовать с окнами и отправлять данные о своих действиях на локальный сервер.

