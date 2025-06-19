import os
import logging
import json
from datetime import datetime
from typing import List, Dict

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from influxdb_client import InfluxDBClient, Point, WriteOptions
from influxdb_client.client.write_api import SYNCHRONOUS
from dotenv import load_dotenv

# --- Загрузка конфигурации ---
load_dotenv()

# --- Настройка логирования ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- FastAPI приложение ---
app = FastAPI(
    title="Waifu Server",
    description="Сервер для сбора статистики от Desktop Waifu.",
    version="1.0.0"
)

# --- Настройка шаблонов ---
templates = Jinja2Templates(directory="templates")

# --- Менеджер WebSocket соединений ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        # Отправляем историю при подключении к странице логов
        for log in log_history:
            try:
                await websocket.send_text(json.dumps(log))
            except Exception:
                # Клиент мог отключиться, пока мы слали историю
                break

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

# --- Глобальное хранилище логов и менеджер WebSocket ---
log_history = []
manager = ConnectionManager()

# --- InfluxDB ---
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")

try:
    influx_client = InfluxDBClient(url=INFLUXDB_URL, token=INFLUXDB_TOKEN, org=INFLUXDB_ORG)
    write_api = influx_client.write_api(write_options=SYNCHRONOUS)
    query_api = influx_client.query_api()
    logger.info(f"Успешное подключение к InfluxDB: {INFLUXDB_URL}")
except Exception as e:
    logger.error(f"Не удалось подключиться к InfluxDB: {e}")
    influx_client = None
    write_api = None

# --- Модели данных (Pydantic) ---
class StatusPayload(BaseModel):
    timestamp: datetime
    action: str
    x: int
    y: int
    active_window_title: str
    active_window_process: str

# --- HTTP Эндпоинты ---
@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    """Отдает главную страницу (в будущем может быть дашборд)."""
    return templates.TemplateResponse("index.html", {"request": request, "log_count": len(log_history)})

@app.get("/logs", response_class=HTMLResponse)
async def get_logs_page(request: Request):
    """Отдает страницу для просмотра логов в реальном времени."""
    return templates.TemplateResponse("logs.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket для отправки логов и событий на фронтенд."""
    await manager.connect(websocket)
    try:
        while True:
            # Просто держим соединение открытым
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Client disconnected from websocket")

@app.post("/status")
async def receive_status(payload: StatusPayload, request: Request):
    """Принимает данные о состоянии от клиента."""
    client_host = request.client.host if request.client else "unknown"
    
    log_msg = f"Статус: {payload.action}, Процесс: {payload.active_window_process}"
    logger.info(log_msg)
    await manager.broadcast(log_msg)
    await manager.broadcast(f"Connection event: status, client: {client_host}")

    if not write_api:
        error_msg = "InfluxDB не настроен на сервере."
        logger.error(error_msg)
        await manager.broadcast(error_msg)
        await manager.broadcast(f"Connection event: error, client: {client_host}")
        return {"status": "error", "message": error_msg}

    try:
        point = Point("waifu_status") \
            .tag("action", payload.action) \
            .tag("process", payload.active_window_process) \
            .field("x", payload.x) \
            .field("y", payload.y) \
            .field("window_title", payload.active_window_title) \
            .time(payload.timestamp)
        
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=point)
        return {"status": "success"}

    except Exception as e:
        error_msg = f"Ошибка записи в InfluxDB: {e}"
        logger.error(error_msg)
        await manager.broadcast(error_msg)
        await manager.broadcast(f"Connection event: error, client: {client_host}")
        return {"status": "error", "message": str(e)}

@app.post("/error")
async def receive_error(request: Request, payload: Dict):
    """Принимает отчеты об ошибках от клиента."""
    client_host = request.client.host if request.client else "unknown"
    error_msg = f"Ошибка от клиента {client_host}: {json.dumps(payload)}"
    logger.error(error_msg)
    
    await manager.broadcast(error_msg)
    await manager.broadcast(f"Connection event: error, client: {client_host}")
    
    return {"status": "logged"}

@app.get("/health")
def health_check():
    """Проверка доступности сервера и InfluxDB."""
    if influx_client and influx_client.ping():
        return {"status": "ok", "influxdb": "connected"}
    return {"status": "ok", "influxdb": "disconnected"}

@app.post("/log")
async def receive_log(log_entry: dict):
    """
    Принимает запись лога, добавляет в историю и транслирует по WebSocket.
    """
    log_history.append(log_entry)
    # Ограничиваем историю, чтобы не переполнять память
    if len(log_history) > config.MAX_LOG_HISTORY:
        log_history.pop(0)
    
    # В broadcast передаем JSON-строку
    await manager.broadcast(json.dumps(log_entry))
    return {"status": "log_received"}

if __name__ == '__main__':
    # Запуск uvicorn для асинхронного FastAPI
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000, debug=False) 