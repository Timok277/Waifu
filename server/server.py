# -*- coding: utf-8 -*-
import uvicorn
from fastapi import FastAPI, status, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# --- 0. Загрузка конфигурации из .env файла ---
load_dotenv()

# --- 1. Настройка и конфигурация ---

# Конфигурация InfluxDB
INFLUX_URL = os.getenv("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN")
INFLUX_ORG = os.getenv("INFLUX_ORG")
INFLUX_BUCKET_STATUS = os.getenv("INFLUX_BUCKET_STATUS", "waifu_status")

# Конфигурация Logstash
LOGSTASH_HOST = os.getenv("LOGSTASH_HOST", "localhost")
LOGSTASH_PORT = int(os.getenv("LOGSTASH_PORT", 5959))

# --- 2. Настройка логирования ---
# Основной логгер для вывода в консоль
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Попытка настроить логгер для Logstash
try:
    import logstash_async.handler

    logstash_handler = logstash_async.handler.AsynchronousLogstashHandler(
        host=LOGSTASH_HOST,
        port=LOGSTASH_PORT,
        database_path='logstash_buffer.db' # Файл для буферизации логов
    )
    # Добавляем обработчик только к корневому логгеру для ошибок
    error_logger = logging.getLogger()
    error_logger.addHandler(logstash_handler)
    error_logger.setLevel(logging.ERROR)
    logger.info(f"Logstash handler configured for {LOGSTASH_HOST}:{LOGSTASH_PORT}")

except ImportError:
    logger.warning("`logstash_async` not installed. Skipping Logstash logging.")
    logstash_handler = None
except Exception as e:
    logger.error(f"Failed to configure Logstash handler: {e}")
    logstash_handler = None


# --- 3. Клиент InfluxDB ---
influx_client = None
influx_write_api = None
if all([INFLUX_URL, INFLUX_TOKEN, INFLUX_ORG]):
    try:
        from influxdb_client import InfluxDBClient, Point
        from influxdb_client.client.write_api import SYNCHRONOUS

        influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
        influx_write_api = influx_client.write_api(write_options=SYNCHRONOUS)
        logger.info(f"InfluxDB client configured for {INFLUX_URL}")
    except ImportError:
        logger.warning("`influxdb-client` not installed. Skipping InfluxDB integration.")
    except Exception as e:
        logger.error(f"Failed to configure InfluxDB client: {e}")
else:
    logger.warning("InfluxDB environment variables not set. Skipping InfluxDB integration.")

def get_influx_write_api():
    """Зависимость для предоставления API записи InfluxDB в эндпоинты."""
    if not influx_write_api:
        raise HTTPException(
            status_code=503, 
            detail="InfluxDB is not configured or available on the server."
        )
    return influx_write_api

# --- 4. Модели данных (Pydantic) ---
class WaifuStatus(BaseModel):
    timestamp: datetime
    action: str
    x: int
    y: int
    active_window_title: Optional[str] = None
    active_window_process: Optional[str] = None
    note: Optional[str] = None

class WaifuError(BaseModel):
    timestamp: datetime
    error_type: str
    message: str
    details: Optional[str] = None

# --- 5. Инициализация FastAPI ---
app = FastAPI(
    title="Desktop Waifu API",
    description="Сервер для сбора метрик и ошибок Desktop Waifu с интеграцией в InfluxDB и ELK.",
    version="2.0.0"
)

# --- 6. Эндпоинты ---

@app.get("/", summary="Проверка статуса сервера")
async def read_root():
    return {"status": "ok", "service": "Desktop Waifu Server is running"}

@app.post("/status", status_code=status.HTTP_202_ACCEPTED, summary="Прием и сохранение метрик персонажа")
async def post_status(
    status_update: WaifuStatus,
    write_api = Depends(get_influx_write_api)
):
    """
    Принимает метрики о состоянии персонажа и записывает их в InfluxDB.
    """
    logger.info(f"STATUS RECEIVED: {status_update.model_dump_json(indent=2)}")

    point = (
        Point("waifu_metrics")
        .tag("action", status_update.action)
        .field("x", status_update.x)
        .field("y", status_update.y)
        .field("active_window_title", str(status_update.active_window_title))
        .field("active_window_process", str(status_update.active_window_process))
        .time(status_update.timestamp)
    )

    try:
        write_api.write(bucket=INFLUX_BUCKET_STATUS, record=point)
        return {"message": "Status received and sent to InfluxDB"}
    except Exception as e:
        logger.error(f"Failed to write to InfluxDB: {e}")
        raise HTTPException(status_code=500, detail="Failed to write metrics to database.")


@app.post("/error", status_code=status.HTTP_202_ACCEPTED, summary="Прием и логирование ошибок")
async def post_error(error_report: WaifuError):
    """
    Принимает отчеты об ошибках и отправляет их в систему логирования (Logstash).
    """
    # Используем стандартный error logger, который мы настроили с Logstash
    error_message = f"CLIENT_ERROR: {error_report.error_type} - {error_report.message}"
    extra_data = {
        'error_details': error_report.model_dump()
    }
    logging.getLogger().error(error_message, extra=extra_data)
    
    return {"message": "Error report received and logged"}


# --- 7. Запуск сервера ---
if __name__ == "__main__":
    HOST_IP = "0.0.0.0"
    PORT = 8000

    logger.info(f"Starting server at http://{HOST_IP}:{PORT}")
    # Обратите внимание: uvicorn.run ожидает "путь.к.файлу:объект_app"
    uvicorn.run("server:app", host=HOST_IP, port=PORT, reload=True) 