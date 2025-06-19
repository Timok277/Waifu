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
import tkinter as tk
import tkinter.messagebox as messagebox

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
    Проверяет наличие новой версии на GitHub и предлагает обновиться.
    Скачивает .exe и запускает .bat скрипт для его замены.
    """
    logging.info("Проверка обновлений...")
    try:
        api_url = f"https://api.github.com/repos/{config.GITHUB_REPO}/releases/latest"
        response = requests.get(api_url, timeout=5)
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release["tag_name"].lstrip('v')

        if parse_version(latest_version) > parse_version(config.CURRENT_VERSION):
            logging.info(f"Найдена новая версия: {latest_version}")
            
            # Ищем .exe файл в ассетах релиза
            asset_url = None
            asset_name = ""
            for asset in latest_release.get("assets", []):
                if asset["name"].startswith("Waifu-Client-") and asset["name"].endswith(".exe"):
                    asset_url = asset["browser_download_url"]
                    asset_name = asset["name"]
                    break
            
            if not asset_url:
                logging.error("В последнем релизе не найден .exe файл для обновления.")
                return

            # Спрашиваем пользователя, хочет ли он обновиться
            root = tk.Tk()
            root.withdraw()
            if not messagebox.askyesno(
                "Доступно обновление",
                f"Доступна новая версия {latest_version}. Хотите обновиться?"
            ):
                logging.info("Пользователь отказался от обновления.")
                return

            logging.info(f"Скачивание {asset_name}...")
            update_exe_path = os.path.join(os.getcwd(), "update.exe")
            
            with requests.get(asset_url, stream=True) as r:
                r.raise_for_status()
                with open(update_exe_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
            
            logging.info("Скачивание завершено. Создание скрипта обновления...")

            # Получаем имя текущего исполняемого файла
            current_exe_name = os.path.basename(sys.executable)

            # Создаем .bat файл для обновления
            updater_script_path = os.path.join(os.getcwd(), "updater.bat")
            with open(updater_script_path, "w") as f:
                f.write(f"""
@echo off
echo Ожидание закрытия приложения...
timeout /t 3 /nobreak > nul
taskkill /IM "{current_exe_name}" /F > nul
echo Замена файлов...
del "{current_exe_name}"
rename "update.exe" "{current_exe_name}"
echo Запуск новой версии...
start "" "{current_exe_name}"
echo Удаление скрипта обновления...
del "%~f0"
                """.strip())

            # Запускаем .bat и выходим
            logging.info("Запуск скрипта обновления и выход из приложения...")
            subprocess.Popen([updater_script_path], creationflags=subprocess.CREATE_NEW_CONSOLE)
            sys.exit()

        else:
            logging.info("У вас установлена последняя версия.")

    except requests.RequestException as e:
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