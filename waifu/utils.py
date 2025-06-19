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
import shutil
import tempfile
import platform

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
    """
    Проверяет наличие обновлений на GitHub, скачивает их и подготавливает
    скрипт для установки.
    """
    logging.info(f"Текущая версия: {config.CURRENT_VERSION}")
    try:
        # 1. Получаем информацию о последнем релизе
        api_url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest"
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release["tag_name"].lstrip('v')
        logging.info(f"Последняя версия на GitHub: {latest_version}")

        # 2. Сравниваем версии
        if latest_version > config.CURRENT_VERSION:
            logging.info("Доступна новая версия! Начинаю процесс обновления...")

            # 3. Находим ассет с клиентским архивом
            asset = next((a for a in latest_release['assets'] if a['name'] == 'Client.zip'), None)
            if not asset:
                logging.error("Не найден 'Client.zip' в последнем релизе.")
                return

            # 4. Скачиваем архив во временную папку
            temp_dir = tempfile.gettempdir()
            zip_path = os.path.join(temp_dir, "waifu_update.zip")
            logging.info(f"Скачиваю архив... {asset['browser_download_url']}")
            
            with requests.get(asset['browser_download_url'], stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            logging.info(f"Архив успешно скачан в: {zip_path}")
            
            # 5. Создаем и запускаем .bat скрипт для обновления
            app_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
            main_script_path = os.path.join(app_path, "main_app.py")
            pid = os.getpid()

            updater_script_path = os.path.join(temp_dir, "updater.bat")
            
            script_content = f"""
@echo off
echo Waiting for the application to close...
taskkill /PID {pid} /F > nul 2>&1
timeout /t 2 /nobreak > nul

echo Unpacking update...
tar -xf "{zip_path}" -C "{app_path}"

echo Relaunching application...
start "" pythonw "{main_script_path}"

echo Cleaning up...
del "{zip_path}"
del "%~f0"
"""
            with open(updater_script_path, "w") as f:
                f.write(script_content)

            logging.info("Запускаю скрипт обновления и закрываю приложение...")
            subprocess.Popen([updater_script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit()

        else:
            logging.info("У вас последняя версия.")

    except requests.RequestException as e:
        logging.error(f"Ошибка при проверке обновлений: {e}")
    except Exception as e:
        logging.error(f"Непредвиденная ошибка в процессе обновления: {e}", exc_info=True)

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
    Кастомный обработчик логов для отправки записей на HTTP эндпоинт (сервер).
    """
    def __init__(self, server_url, client_id):
        super().__init__()
        self.url = f"{server_url}/log"
        self.client_id = client_id

    def emit(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": self.format(record),
            "source": record.name,
            "client_id": self.client_id
        }
        try:
            # Используем timeout, чтобы не блокировать приложение надолго
            requests.post(self.url, json=log_entry, timeout=2)
        except requests.RequestException:
            # Не выводим ошибку, чтобы не попасть в бесконечный цикл логирования
            pass 