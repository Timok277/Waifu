# Desktop Waifu v2.0

Анимированный персонаж-компаньон для вашего рабочего стола, теперь с расширенными возможностями мониторинга, аналитики и развертывания.

![Desktop Waifu - Спрайт Сидя](https://r2.flowith.net/files/o/1750000420473-anime_girl_waifu_sitting_transparent_background_index_2@1024x1536.png)
![Desktop Waifu - Спрайт Ходьбы 2](https://r2.flowith.net/files/o/1750000406880-anime_girl_walking_animation_frame_index_1@1024x1536.png)
![Desktop Waifu - Спрайт Покоя](https://r2.flowith.net/files/o/1750000401036-anime_waifu_idle_pose_transparent_background_index_3@1024x1536.png)

## Описание проекта

Проект "Desktop Waifu" — это десктопное приложение, которое добавляет анимированного персонажа на ваш рабочий стол. Персонаж может перемещаться по окнам и взаимодействовать с ними.

**Версия 2.0** переводит проект на новый уровень: серверная часть теперь контейнеризирована с помощью Docker, а данные (метрики и ошибки) отправляются в специализированные системы: Time-Series базу данных (InfluxDB) и систему управления логами (например, стек ELK). Это обеспечивает масштабируемость, надежность и открывает широкие возможности для анализа.

## Новые возможности v2.0

*   **📈 Надежное хранение данных**: Метрики о действиях персонажа сохраняются в InfluxDB, а ошибки — в Elasticsearch (через Logstash).
*   **🐳 Простое развертывание**: Вся серверная инфраструктура (API, InfluxDB, Grafana) запускается одной командой с помощью Docker Compose.
*   **📊 Готовность к аналитике**: Собранные данные можно визуализировать в Grafana (для метрик) или Kibana (для логов), создавая дашборды для отслеживания трендов.
*   **⚙️ Автоматизация CI/CD**: Добавлен GitHub Action для автоматического обновления Pull Request'ов, что упрощает процесс разработки.

## Структура проекта

```
Waifu/
├── .github/
│   └── workflows/
│       └── autoupdate.yaml  # GitHub Action для авто-обновления PR
├── assets/                  # Спрайты персонажа
├── server/                  # Серверное приложение
│   ├── .env.example         # Пример файла с переменными окружения
│   ├── Dockerfile           # Dockerfile для сборки образа сервера
│   ├── requirements.txt     # Зависимости сервера
│   └── server.py            # Код сервера (FastAPI, InfluxDB, Logstash)
├── main_app.py              # Основное приложение клиента (Tkinter)
├── requirements.txt         # Зависимости клиента
├── docker-compose.yml       # Файл для запуска всех сервисов
└── README.md                # Этот файл
```

---

## 🚀 Инструкция по запуску

### Шаг 1: Настройка серверной части

Сервер и сервисы мониторинга запускаются с помощью Docker.

1.  **Установите Docker и Docker Compose.**
    Если они у вас не установлены, следуйте официальным инструкциям:
    *   [Установить Docker](https://docs.docker.com/get-docker/)
    *   [Установить Docker Compose](https://docs.docker.com/compose/install/)

2.  **Настройте переменные окружения.**
    В директории `server/` переименуйте файл `.env.example` в `.env`. Откройте его и укажите свои данные. **Это самый важный шаг.**

    Содержимое `server/.env`:
    ```ini
    # --- InfluxDB Configuration ---
    # Эти переменные используются и для первоначальной настройки InfluxDB в Docker
    DOCKER_INFLUXDB_INIT_MODE=setup
    DOCKER_INFLUXDB_INIT_USERNAME=your_admin_user # Придумайте имя пользователя
    DOCKER_INFLUXDB_INIT_PASSWORD=your_secure_password # Придумайте надежный пароль
    DOCKER_INFLUXDB_INIT_ORG=my-org # Название вашей организации
    DOCKER_INFLUXDB_INIT_BUCKET=waifu_status # Название "базы данных" для метрик
    DOCKER_INFLUXDB_INIT_ADMIN_TOKEN=your_super_secret_admin_token # Придумайте токен администратора

    # --- Переменные для подключения сервера к InfluxDB ---
    # URL вашего InfluxDB инстанса (оставляем как есть для Docker)
    INFLUX_URL=http://influxdb:8086
    # Токен доступа (должен совпадать с DOCKER_INFLUXDB_INIT_ADMIN_TOKEN)
    INFLUX_TOKEN=${DOCKER_INFLUXDB_INIT_ADMIN_TOKEN}
    # Название организации (должно совпадать с DOCKER_INFLUXDB_INIT_ORG)
    INFLUX_ORG=${DOCKER_INFLUXDB_INIT_ORG}
    # Название bucket (должно совпадать с DOCKER_INFLUXDB_INIT_BUCKET)
    INFLUX_BUCKET_STATUS=${DOCKER_INFLUXDB_INIT_BUCKET}

    # --- Logstash Configuration (опционально) ---
    LOGSTASH_HOST=localhost
    LOGSTASH_PORT=5959
    ```

3.  **Запустите всё одной командой.**
    Откройте терминал в корневой папке проекта (где находится `docker-compose.yml`) и выполните:
    ```bash
    docker-compose up -d --build
    ```
    Эта команда скачает образы, соберет контейнер для сервера и запустит все сервисы в фоновом режиме.

### Шаг 2: Настройка и запуск клиента

Клиент (`main_app.py`) — это десктопное приложение, которое вы запускаете на своем ПК.

1.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```
2.  **Настройте адрес сервера:**
    В файле `main_app.py` найдите строку `SERVER_URL`. Если вы запускаете Docker на той же машине, оставьте `http://localhost:8000`. Если Docker запущен на другой машине в вашей сети, укажите ее IP-адрес.
    ```python
    # main_app.py
    SERVER_URL = "http://localhost:8000"
    ```
3.  **Запустите приложение:**
    ```bash
    python main_app.py
    ```
    Теперь персонаж должен появиться на вашем рабочем столе и отправлять данные на сервер.

---

## 📈 Просмотр данных в Grafana

1.  Откройте Grafana в браузере: `http://localhost:3000`.
2.  Войдите с логином `admin` и паролем `admin`. Grafana предложит сменить пароль.
3.  **Подключите InfluxDB как источник данных:**
    *   Перейдите в `Connections -> Data sources -> Add data source`.
    *   Выберите `InfluxDB`.
    *   В настройках:
        *   Query Language: `Flux`
        *   URL: `http://influxdb:8086`
        *   Organization: Укажите ваш `INFLUX_ORG` из `.env` файла.
        *   Token: Укажите ваш `INFLUX_TOKEN` из `.env` файла.
    *   Нажмите `Save & Test`. Должно появиться сообщение об успехе.
4.  **Создайте дашборд:**
    *   Перейдите в `Dashboards -> New Dashboard`.
    *   Создайте панели, используя ваш источник данных InfluxDB и bucket `waifu_status`.

Примеры панелей:

*   **Карта активности**: Тепловая карта (Heatmap) или график рассеивания (Scatter plot) с координатами `x` и `y`.
*   **Анализ действий**: Круговая диаграмма (Pie chart), показывающая распределение состояний (`idle`, `walk`, `sit`).
*   **Активность по приложениям**: Гистограмма (Bar chart), показывающая количество взаимодействий с каждым приложением.

## 🤝 Автоматизация CI/CD (GitHub Actions)

В репозитории настроен рабочий процесс **Auto Update** (`.github/workflows/autoupdate.yaml`). Он автоматически обновляет все активные Pull Request'ы последними изменениями из `main` (или `master`) ветки. Это помогает поддерживать PR в актуальном состоянии и избегать конфликтов слияния. Никаких дополнительных действий для его работы не требуется.

## ⚙️ Финальный шаг: Отправка кода в ваш репозиторий

Теперь, когда все настроено локально, отправьте код в ваш GitHub репозиторий.

1.  **Инициализируйте Git (если еще не сделали):**
    ```bash
    git init
    ```
2.  **Добавьте репозиторий как удаленный:**
    ```bash
    git remote add origin https://github.com/Timok277/Waifu.git
    ```
3.  **Добавьте, закоммитьте и отправьте все файлы:**
    ```bash
    git add .
    git commit -m "feat: Implement client auto-update and update docs"
    git push -u origin main
    ```

После этого **GitHub Action для авто-обновления PR** будет активен в вашем репозитории.

## ⚙️ Автообновление клиента

В приложение встроена система автоматического обновления.

### Как это работает?

1.  При каждом запуске `main_app.py` проверяет страницу **Releases** вашего GitHub-репозитория.
2.  Он сравнивает свою `CURRENT_VERSION` с версией последнего релиза.
3.  Если доступна новая версия, он скачивает ассет с именем `client.zip`, автоматически устанавливает его и перезапускается.

### Как выпустить новую версию?

Чтобы пользователи получили обновление, вы должны создать новый релиз на GitHub:

1.  **Подготовьте файлы**: Внесите все необходимые изменения в код клиента (`main_app.py`, `assets/` и т.д.). **Не забудьте увеличить номер `CURRENT_VERSION` в `main_app.py`!**
2.  **Создайте архив**: Выделите все файлы и папки, относящиеся к клиенту (`main_app.py`, `requirements.txt`, папка `assets`), и создайте из них **ZIP-архив с именем `client.zip`**.
3.  **Создайте новый релиз на GitHub**:
    *   Перейдите в ваш репозиторий `https://github.com/Timok277/Waifu` и откройте вкладку `Releases` (справа).
    *   Нажмите **"Draft a new release"**.
    *   В поле **"Tag version"** введите номер новой версии, например, `v2.0.1`. Он должен совпадать с `CURRENT_VERSION` в коде (можно с префиксом `v`).
    *   Дайте релизу название и описание.
    *   В разделе **"Attach binaries by dropping them here or selecting them"** загрузите ваш архив `client.zip`.
    *   Нажмите **"Publish release"**.

Готово! При следующем запуске старые клиенты автоматически обновятся до этой версии.

