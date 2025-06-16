# Использовать официальный образ Python
FROM python:3.9-slim

# Установить рабочую директорию
WORKDIR /app

# Скопировать файл с зависимостями
COPY requirements.txt .

# Установить зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Скопировать код приложения
COPY . .

# Открыть порт 8000
EXPOSE 8000

# Запустить сервер при старте контейнера
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"] 