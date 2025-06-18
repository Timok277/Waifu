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

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_json(self, data: dict):
        message = json.dumps(data)
        for connection in self.active_connections:
            await connection.send_text(message)

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

# --- Маршруты ---
@app.get("/", response_class=HTMLResponse)
async def get_root(request: Request):
    """Отдает главную страницу с логами."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket для отправки логов и событий на фронтенд."""
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text() # Просто держим соединение
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("Клиент WebSocket отключился.")

@app.post("/status")
async def receive_status(payload: StatusPayload, request: Request):
    """Принимает данные о состоянии от клиента."""
    client_host = request.client.host if request.client else "unknown"
    
    log_msg = f"Статус: {payload.action}, Процесс: {payload.active_window_process}"
    logger.info(log_msg)
    await manager.broadcast_json({"type": "log", "message": {"level": "INFO", "text": log_msg}})
    await manager.broadcast_json({"type": "connection", "message": {"event": "status", "client": client_host}})

    if not write_api:
        error_msg = "InfluxDB не настроен на сервере."
        logger.error(error_msg)
        await manager.broadcast_json({"type": "log", "message": {"level": "ERROR", "text": error_msg}})
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
        await manager.broadcast_json({"type": "log", "message": {"level": "ERROR", "text": error_msg}})
        return {"status": "error", "message": str(e)}

@app.post("/error")
async def receive_error(request: Request, payload: Dict):
    """Принимает отчеты об ошибках от клиента."""
    client_host = request.client.host if request.client else "unknown"
    error_msg = f"Ошибка от клиента {client_host}: {json.dumps(payload)}"
    logger.error(error_msg)
    
    await manager.broadcast_json({"type": "log", "message": {"level": "ERROR", "text": error_msg}})
    await manager.broadcast_json({"type": "connection", "message": {"event": "error", "client": client_host}})
    
    return {"status": "logged"}

@app.get("/health")
def health_check():
    """Проверка доступности сервера и InfluxDB."""
    if influx_client and influx_client.ping():
        return {"status": "ok", "influxdb": "connected"}
    return {"status": "ok", "influxdb": "disconnected"}

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False) 