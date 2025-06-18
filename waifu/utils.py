# -*- coding: utf-8 -*-

import logging
import requests
import webbrowser
import sys
import os
import config
from PIL import Image
import pygame
import pygetwindow
import psutil
import random
import math
from datetime import datetime
import zipfile
import subprocess
import threading
from packaging.version import parse as parse_version

# --- Новая зависимость для get_desktop_windows ---
try:
    import win32gui
    import win32process
    import win32con
    import pywintypes
    IS_WIN = sys.platform.startswith('win')
except ImportError:
    IS_WIN = False


def get_desktop_windows():
    """
    Возвращает список видимых окон на рабочем столе в формате (x, y, w, h),
    отсортированный по Z-порядку (от верхнего к нижнему).
    Работает только под Windows.
    """
    if not IS_WIN:
        return []

    windows = []
    def _enum_cb(hwnd, results):
        if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd) != '':
            # Пропускаем окна с определенными стилями, которые не являются "настоящими" окнами
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE)
            if not (style & win32con.WS_CAPTION): # Пропускаем окна без заголовка
                 return True
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            if ex_style & win32con.WS_EX_TOOLWINDOW: # Пропускаем "инструментальные" окна
                return True

            rect = win32gui.GetWindowRect(hwnd)
            if (rect[2] - rect[0]) > 0 and (rect[3] - rect[1]) > 0:
                results.append((hwnd, rect))
        return True

    temp_windows = []
    win32gui.EnumWindows(_enum_cb, temp_windows)

    # Сортировка по Z-order. Более "высокие" окна (ближе к пользователю) идут первыми.
    # Мы итерируемся от самого верхнего окна вниз.
    hwnd = win32gui.GetTopWindow(None)
    while hwnd:
        for h, rect in temp_windows:
            if h == hwnd:
                windows.append(rect)
                break
        hwnd = win32gui.GetWindow(hwnd, win32con.GW_HWNDNEXT)
        
    return windows

def scale_image(image, scale_factor):
    """Масштабирует изображение в scale_factor раз с использованием smoothscale для лучшего качества."""
    new_size = (int(image.get_width() * scale_factor), int(image.get_height() * scale_factor))
    return pygame.transform.smoothscale(image, new_size)

def check_for_updates():
    """Проверяет наличие обновлений на GitHub и запускает процесс обновления."""
    logging.info(f"Текущая версия: {config.CURRENT_VERSION}. Проверка обновлений...")
    try:
        api_url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release["tag_name"].lstrip('v')
        
        logging.info(f"Последняя версия на GitHub: {latest_version}")
        
        if parse_version(latest_version) > parse_version(config.CURRENT_VERSION):
            logging.info("Доступна новая версия! Начинаю обновление.")
            
            # Ищем ассет с именем Client.zip
            asset_to_download = None
            for asset in latest_release.get("assets", []):
                if asset["name"] == "Client.zip":
                    asset_to_download = asset
                    break
            
            if not asset_to_download:
                logging.error("Не найден 'Client.zip' в последнем релизе. Обновление невозможно.")
                return

            download_url = asset_to_download["browser_download_url"]
            logging.info(f"Скачивание архива Client.zip из {download_url}...")
            update_zip_path = "Client.zip"
            with requests.get(download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(update_zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            update_dir = "update_temp"
            if os.path.exists(update_dir):
                import shutil
                shutil.rmtree(update_dir)
            
            with zipfile.ZipFile(update_zip_path, 'r') as zip_ref:
                # Архив Client.zip не имеет корневой папки, извлекаем его содержимое в update_dir
                zip_ref.extractall(update_dir)
            
            # Создаем .bat скрипт, который дождется завершения, скопирует файлы и перезапустится.
            updater_script_path = "updater.bat"
            with open(updater_script_path, "w", encoding="utf-8") as f:
                f.write(f"""
@echo off
chcp 65001 > nul
echo.
echo ===============================================
echo      Updating Waifu to version {latest_version}
echo ===============================================
echo.
echo Please do not close this window.
echo The application will restart automatically.
echo.
echo --^> Waiting for application to exit (5 seconds)...
timeout /t 5 /nobreak > nul
echo --^> Step 1/3: Copying new files...
robocopy "{update_dir}" . /E /IS /IT /MOVE /NFL /NDL /NJH /NJS /nc /ns /np
if %errorlevel% geq 8 (
    echo.
    echo [ERROR] File copy failed. Update cannot continue.
    robocopy . "{update_dir}" /E /MOVE > nul
    pause
    exit /b %errorlevel%
)
echo --^> Step 2/3: Cleaning up...
rd /s /q "{update_dir}"
del "{update_zip_path}"
echo --^> Step 3/3: Restarting application...
echo.
echo Update complete!
start "" "{sys.executable}" main_app.py
del "%~f0"
""")
            
            subprocess.Popen([updater_script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            logging.info("Запущен скрипт обновления. Приложение будет закрыто.")
            sys.exit(0)
            
        else:
            logging.info("У вас последняя версия приложения.")
            
    except requests.exceptions.RequestException as e:
        logging.error(f"Не удалось проверить обновления: {e}")
    except Exception as e:
        logging.error(f"Произошла ошибка во время процесса обновления: {e}")

def check_server_availability():
    try:
        requests.get(config.SERVER_URL, timeout=2)
        logging.info("Сервер доступен.")
        return True
    except (requests.ConnectionError, requests.Timeout):
        logging.error(f"Сервер {config.SERVER_URL} недоступен.")
    return False

def send_to_server(endpoint: str, data: dict):
    def _send():
        try:
            requests.post(endpoint, json=data, timeout=3)
        except requests.exceptions.RequestException:
            pass 
    threading.Thread(target=_send, daemon=True).start() 

class LogstashHttpHandler(logging.Handler):
    """
    Кастомный обработчик логов, который отправляет каждую запись
    в виде JSON на указанный HTTP-эндпоинт.
    """
    def __init__(self, url, method='POST'):
        super().__init__()
        self.url = url
        self.method = method

    def emit(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": self.format(record),
            "source": record.name
        }
        
        def _send_log():
            try:
                requests.post(self.url, json=log_entry, timeout=2)
            except requests.exceptions.RequestException:
                # В случае ошибки просто игнорируем, чтобы не зациклиться
                pass

        # Отправляем в отдельном потоке, чтобы не блокировать основное приложение
        threading.Thread(target=_send_log, daemon=True).start() 