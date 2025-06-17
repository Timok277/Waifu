# -*- coding: utf-8 -*-

import tkinter as tk
from PIL import Image, ImageTk
import pygetwindow
import psutil
import requests
import time
import random
import threading
from datetime import datetime
import sys
import logging
import os
import ctypes
import math
from screeninfo import get_monitors
import subprocess
import zipfile
from packaging.version import parse as parse_version

try:
    import win32gui
    import win32process
    import pywintypes
    IS_WIN = sys.platform.startswith('win')
except ImportError:
    IS_WIN = False

# --- Настройка Логирования ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)

# --- Конфигурация ---
SERVER_URL = "http://26.186.125.19:8000"
STATUS_ENDPOINT = f"{SERVER_URL}/status"
ERROR_ENDPOINT = f"{SERVER_URL}/error"

TARGET_WINDOW_TITLES = ["Visual Studio Code", "Visual Studio"]
TARGET_WINDOW_PROCESSES = ["Code.exe", "devenv.exe"]

SPRITE_PATHS = {
    "idle": "assets/anime_waifu_idle_pose_transparent_background_index_3.png",
    "walk1": "assets/anime_girl_walking_animation_frame_index_0.png",
    "walk2": "assets/anime_girl_walking_animation_frame_index_1.png",
    "sit": "assets/anime_girl_waifu_sitting_transparent_background_index_2.png",
}

SPRITE_WIDTH, SPRITE_HEIGHT = 150, 200
ANIMATION_INTERVAL = 150
MOVEMENT_INTERVAL = 16  # ~60 FPS
PHYSICS_INTERVAL = 50 
CURSOR_CHECK_INTERVAL = 200 
STATUS_SEND_INTERVAL = 5000 

# Физические константы
WALK_SPEED = 2.5
JUMP_POWER = 15
GRAVITY = 0.8
TERMINAL_VELOCITY = 20
CURSOR_EVADE_DISTANCE = 50

# --- Конфигурация Обновлений ---
CURRENT_VERSION = "2.0.5" # Текущая версия приложения
GITHUB_REPO = "Timok277/Waifu" # Путь к вашему репозиторию

# --- Вспомогательные функции ---
def check_for_updates():
    """Проверяет наличие обновлений на GitHub и запускает процесс обновления."""
    logging.info(f"Текущая версия: {CURRENT_VERSION}. Проверка обновлений...")
    try:
        api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        latest_release = response.json()
        latest_version = latest_release["tag_name"].lstrip('v')
        
        logging.info(f"Последняя версия на GitHub: {latest_version}")

        if parse_version(latest_version) > parse_version(CURRENT_VERSION):
            logging.info("Доступна новая версия! Начинаю обновление.")
            
            download_url = latest_release.get("zipball_url")
            if not download_url:
                logging.error("Не найден URL для скачивания исходного кода (zipball_url) в релизе.")
                return

            # Скачать архив
            logging.info(f"Скачивание архива с исходным кодом из {download_url}...")
            update_zip_path = "update_source.zip"
            with requests.get(download_url, stream=True, timeout=30) as r:
                r.raise_for_status()
                with open(update_zip_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # Распаковать архив
            update_dir = "update_temp"
            if os.path.exists(update_dir):
                import shutil
                shutil.rmtree(update_dir)
            
            with zipfile.ZipFile(update_zip_path, 'r') as zip_ref:
                # Архив от GitHub содержит одну папку с исходниками, нам нужно ее имя
                root_folder_in_zip = zip_ref.namelist()[0]
                zip_ref.extractall(update_dir)
            
            source_path = os.path.join(update_dir, root_folder_in_zip)

            # Создать и запустить скрипт обновления
            updater_script_path = "updater.bat"
            with open(updater_script_path, "w", encoding="utf-8") as f:
                f.write(f"""
@echo off
rem Switch to a unicode codepage to handle all paths, just in case.
chcp 65001 > nul

rem Clean up junk files from previous failed updates, if they exist
if exist Step del Step > nul 2>&1
if exist Waiting del Waiting > nul 2>&1

echo.
echo ===============================================
echo      Updating Waifu to version {latest_version}
echo ===============================================
echo.
echo Please do not close this window.
echo The application will restart automatically.
echo.

rem Wait for the main application to close completely
echo --^> Waiting for application to exit...
timeout /t 5 /nobreak > nul

rem Copy new files, overwriting old ones.
rem Robocopy is used as a more robust replacement for xcopy.
rem /E    :: copy subdirectories, including empty ones.
rem /IS   :: include same files (overwrite).
rem /IT   :: include "tweaked" files (essential for overwrite).
rem /NFL /NDL /NJH /NJS /nc /ns /np :: Suppress Robocopy's own logging for a cleaner output.
echo --^> Step 1/3: Copying new files...
robocopy "{source_path}" . /E /IS /IT /NFL /NDL /NJH /NJS /nc /ns /np

rem Check if Robocopy was successful. Exit codes >= 8 are errors.
if %errorlevel% geq 8 (
    echo.
    echo [ERROR] File copy failed. Update cannot continue.
    echo Please try running the application again.
    echo Robocopy exit code: %errorlevel%
    pause
    exit /b %errorlevel%
)

rem Clean up temporary files
echo --^> Step 2/3: Cleaning up temporary files...
rd /s /q "{update_dir}"
del "{update_zip_path}"

rem Restart the application
echo --^> Step 3/3: Restarting application...
echo.
echo Update complete!
start "" "{sys.executable}" main_app.py

rem Self-delete the updater script
del "%~f0"
""")
            
            # Запускаем батник и выходим
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
        requests.get(SERVER_URL, timeout=2)
        logging.info("Сервер доступен.")
        return True
    except (requests.ConnectionError, requests.Timeout):
        logging.error(f"Сервер {SERVER_URL} недоступен.")
        return False

def send_to_server(endpoint: str, data: dict):
    def _send():
        try:
            requests.post(endpoint, json=data, timeout=3)
        except requests.exceptions.RequestException:
            pass 
    threading.Thread(target=_send, daemon=True).start()

# --- Класс Платформы ---
class Platform:
    def __init__(self, left, top, right, bottom, is_target=False):
        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom
        self.is_target = is_target

    @property
    def width(self):
        return self.right - self.left
        
    def __eq__(self, other):
        if not isinstance(other, Platform):
            return NotImplemented
        return (self.left == other.left and
                self.top == other.top and
                self.right == other.right and
                self.bottom == other.bottom)

# --- Класс Персонажа ---
class WaifuCharacter:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.width, self.height = SPRITE_WIDTH, SPRITE_HEIGHT
        self.is_windows = IS_WIN

        # Состояние
        self.state = "idle"
        self.x, self.y = 100, 100
        self.dx, self.dy = 0, 0
        self.target_x = None
        self.on_ground = False
        self.facing_direction = 'right'
        self.pending_jump_platform = None
        self.current_platform = None 
        self.last_platform = None 
        self.decision_cooldown = 0
        
        # Взаимодействие
        self.is_dragging = False
        self._drag_data = {'x': 0, 'y': 0}

        # Спрайты и таймеры
        self.sprites = {}
        self.current_sprite_index = 0
        self._timers = {}

        # Платформы
        self.platforms = []
        
        self.setup_window()
        self.load_sprites()

        if self.sprites:
            self.sprite_item = self.canvas.create_image(0, 0, anchor=tk.NW)
            self.bind_events()
            logging.info("Инициализация персонажа завершена.")
        else:
            self.sprite_item = None
            logging.error("Инициализация провалена: спрайты не загружены.")

    def setup_window(self):
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        transparency_color = '#ff00ff'
        
        self.canvas = tk.Canvas(self.root, width=self.width, height=self.height, bg=transparency_color, highlightthickness=0)
        self.canvas.pack()

        try:
            if self.is_windows:
                self.root.wm_attributes('-transparentcolor', transparency_color)
            else:
                self.root.attributes('-alpha', 0.99)
        except tk.TclError:
            logging.warning("Прозрачность не поддерживается.")
        

    def bind_events(self):
        self.canvas.bind("<ButtonPress-1>", self.start_drag)
        self.canvas.bind("<ButtonRelease-1>", self.stop_drag)
        self.canvas.bind("<B1-Motion>", self.do_drag)

    def load_sprites(self):
        try:
            pil_images = {name: Image.open(path).resize((self.width, self.height), Image.Resampling.LANCZOS) 
                          for name, path in SPRITE_PATHS.items()}

            self.sprites = {
                "idle": self.prepare_sprite_set(pil_images["idle"]),
                "walk": self.prepare_sprite_set(pil_images["walk1"], pil_images["walk2"]),
                "sit": self.prepare_sprite_set(pil_images["sit"]),
            }
            logging.info("Спрайты успешно загружены.")
        except Exception as e:
            logging.critical(f"Ошибка загрузки спрайтов: {e}")
            self.sprites = {}

    def prepare_sprite_set(self, *pil_imgs):
        right_imgs = [ImageTk.PhotoImage(img) for img in pil_imgs]
        left_imgs = [ImageTk.PhotoImage(img.transpose(Image.FLIP_LEFT_RIGHT)) for img in pil_imgs]
        return {"right": right_imgs, "left": left_imgs}

    def run(self):
        if not self.sprites:
            self.root.after(100, self.on_close)
            return
        
        self.schedule_task('animation', ANIMATION_INTERVAL, self.update_animation)
        self.schedule_task('physics', MOVEMENT_INTERVAL, self.update_physics)
        self.schedule_task('platforms', PHYSICS_INTERVAL, self.update_platforms)
        self.schedule_task('cursor_check', CURSOR_CHECK_INTERVAL, self.check_cursor)
        self.schedule_task('status_send', STATUS_SEND_INTERVAL, self.send_status)
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def schedule_task(self, name, interval, func):
        """Рекурсивно планирует вызов функции."""
        func()
        self._timers[name] = self.root.after(interval, lambda: self.schedule_task(name, interval, func))

    # --- Логика обновления ---
    def update_animation(self):
        if self.is_dragging: return

        if self.state == "sit":
             anim_state = "sit"
        elif not self.on_ground:
            anim_state = "walk"
        elif self.dx == 0 and self.dy == 0:
            anim_state = "idle"
        else:
            anim_state = "walk"
        
        if self.state != anim_state:
            self.set_state(anim_state)
        
        state_sprites = self.sprites.get(self.state, self.sprites["idle"])
        direction_sprites = state_sprites.get(self.facing_direction, state_sprites["right"])
        
        self.current_sprite_index = (self.current_sprite_index + 1) % len(direction_sprites)
        current_image = direction_sprites[self.current_sprite_index]
        self.canvas.itemconfig(self.sprite_item, image=current_image)

    def update_physics(self):
        if self.is_dragging: return

        if self.dx > 0: self.facing_direction = 'right'
        elif self.dx < 0: self.facing_direction = 'left'

        # --- Логика на земле ---
        if self.on_ground:
            self.decision_cooldown = max(0, self.decision_cooldown - 1)
            self.dy = 0 

            # --- ИИ: Принятие решений ---
            if self.target_x is None and self.pending_jump_platform is None and self.decision_cooldown <= 0:
                
                # 1. Приоритет: Найти и сесть на целевое окно
                target_platforms = [p for p in self.platforms if p.is_target]
                if target_platforms and self.current_platform not in target_platforms:
                    self.target_x = target_platforms[0].left + 10 # Идем к левому краю
                    logging.info("Нашел целевое окно, иду к нему!")
                elif self.current_platform and self.current_platform.is_target:
                    self.dx = 0
                    self.set_state("sit")
                
                # 2. Решить прыгнуть
                elif len(self.platforms) > 1 and random.random() < 0.02 and self.state != 'sit':
                    valid_choices = [p for p in self.platforms if p != self.current_platform and p != self.last_platform and p.top < self.y]
                    if valid_choices:
                        target_platform = random.choice(valid_choices)
                        if self.current_platform:
                            target_center_x = target_platform.left + (target_platform.right - target_platform.left) / 2
                            jump_off_x = target_center_x - self.width / 2
                            self.target_x = max(self.current_platform.left, min(jump_off_x, self.current_platform.right - self.width))
                            self.pending_jump_platform = target_platform
                            logging.info(f"Решил прыгнуть на y={target_platform.top}. Иду к x={self.target_x:.0f}.")
                
                # 3. Решить погулять
                elif random.random() < 0.02 and self.state != 'sit':
                    if self.current_platform:
                        platform_width = self.current_platform.right - self.current_platform.left
                        if platform_width > self.width:
                            self.target_x = random.randint(int(self.current_platform.left), int(self.current_platform.left + platform_width - self.width))
                
                # 4. Решить подпрыгнуть на месте
                elif self.target_x is None and random.random() < 0.005 and self.state != 'sit':
                    self.jump()
            
            # --- Движение ---
            if self.target_x is not None:
                if abs(self.target_x - self.x) < WALK_SPEED:
                    self.x = self.target_x
                    self.target_x = None
                    self.dx = 0
                    if self.pending_jump_platform:
                        self.jump_to_platform(self.pending_jump_platform)
                        self.pending_jump_platform = None
                else:
                    self.dx = WALK_SPEED if self.target_x > self.x else -WALK_SPEED
            elif self.state != 'sit':
                self.dx = 0
        
        # --- Логика в воздухе ---
        else: 
            self.dy += GRAVITY
            self.dy = min(self.dy, TERMINAL_VELOCITY)

        # --- Перемещение и коллизии (всегда) ---
        self.x += self.dx
        self.y += self.dy
        self.check_ground_collision()
        
        self.move_window(self.x, self.y)

    def check_ground_collision(self):
        next_foot_y = self.y + self.dy + self.height
        center_x = self.x + self.width / 2

        candidate_platforms = [p for p in self.platforms if p.left <= center_x <= p.right]
        
        ground = None
        for p in candidate_platforms:
            is_above = (self.y + self.height) <= p.top + 1
            if is_above:
                if ground is None or p.top < ground.top:
                    ground = p

        if ground:
            if next_foot_y >= ground.top:
                is_new_landing = not self.on_ground
                self.y = ground.top - self.height
                self.dy = 0

                if is_new_landing:
                    self.last_platform = self.current_platform
                    self.decision_cooldown = random.randint(100, 250) 
                    self.dx = 0 
                
                self.current_platform = ground
                self.on_ground = True
                return

        self.on_ground = False
        self.current_platform = None # Если мы в воздухе, у нас нет текущей платформы

    def update_platforms(self):
        new_platforms = []
        for m in get_monitors():
            platform = Platform(m.x, m.y + m.height, m.x + m.width, m.y + m.height + 1)
            new_platforms.append(platform)
            
        if not self.is_windows:
            for w in pygetwindow.getAllWindows():
                 if w.visible and not w.isMinimized and w.title and w.width > 150 and w.height > 50:
                    is_target = any(t in w.title for t in TARGET_WINDOW_TITLES)
                    platform = Platform(w.left, w.top, w.left + w.width, w.top + 1, is_target=is_target)
                    new_platforms.append(platform)
            self.platforms = sorted(new_platforms, key=lambda p: p.top)
            return

        # --- Логика с Z-Order для Windows ---
        hwnds = []
        win32gui.EnumWindows(lambda hwnd, hwnds: hwnds.append(hwnd), [])
        
        all_windows = []
        for h in hwnds:
            try:
                if win32gui.IsWindowVisible(h) and win32gui.GetWindowText(h):
                    w = pygetwindow.Win32Window(h)
                    if w.visible and not w.isMinimized and w.title and w.width > 150 and w.height > 50:
                        all_windows.append(w)
            except (pygetwindow.PyGetWindowException, pywintypes.error):
                continue
        
        unoccluded_windows = []
        for i, w_current in enumerate(all_windows):
            is_occluded = False
            for j in range(i):
                w_occluder = all_windows[j]
                
                overlap_x = max(0, min(w_current.right, w_occluder.right) - max(w_current.left, w_occluder.left))
                overlap_y = max(0, min(w_current.bottom, w_occluder.bottom) - max(w_current.top, w_occluder.top))
                
                if overlap_x * overlap_y > 0.7 * (w_current.width * w_current.height):
                    is_occluded = True
                    break
            
            if not is_occluded:
                unoccluded_windows.append(w_current)
                
        for w in unoccluded_windows:
            is_target = False
            # Проверяем, является ли окно целевым
            try:
                _, pid = win32process.GetWindowThreadProcessId(w._hWnd)
                p = psutil.Process(pid)
                proc_name = p.name()
                is_target = proc_name in TARGET_WINDOW_PROCESSES or any(t in w.title for t in TARGET_WINDOW_TITLES)
            except (psutil.NoSuchProcess, psutil.AccessDenied, pywintypes.error):
                is_target = any(t in w.title for t in TARGET_WINDOW_TITLES)
            
            platform = Platform(w.left, w.top, w.left + w.width, w.top + 1, is_target=is_target)
            new_platforms.append(platform)

        self.platforms = sorted(new_platforms, key=lambda p: p.top)

    # --- Интерактивность ---
    def check_cursor(self):
        if self.is_dragging or not self.on_ground or self.state == 'sit': return
        
        cursor_x, cursor_y = self.root.winfo_pointerxy()
        dist = math.hypot(cursor_x - (self.x + self.width / 2), cursor_y - (self.y + self.height / 2))

        if dist < CURSOR_EVADE_DISTANCE:
            logging.info("Курсор слишком близко! Убегаю.")
            if self.current_platform:
                if cursor_x > self.x + self.width / 2: 
                    self.target_x = self.current_platform.left
                else: 
                    self.target_x = self.current_platform.right - self.width

    def jump_to_platform(self, target_platform):
        if not self.on_ground: return

        delta_y = self.y - (target_platform.top - self.height)
        if delta_y <= 0: 
            self.pending_jump_platform = None
            return
            
        required_power = math.sqrt(2 * GRAVITY * delta_y) * 1.05
        self.dy = -min(required_power, JUMP_POWER * 2.5)

        time_to_peak = -self.dy / GRAVITY
        time_in_air_approx = time_to_peak * 2
        if time_in_air_approx <= 0:
            self.pending_jump_platform = None
            return

        target_center_x = target_platform.left + (target_platform.right - target_platform.left) / 2
        delta_x = (target_center_x - self.width / 2) - self.x
        self.dx = delta_x / time_in_air_approx
        
        self.on_ground = False
        logging.info(f"Прыгаю! Цель y={target_platform.top}, V=({self.dx:.2f}, {self.dy:.2f}), T~={time_in_air_approx*MOVEMENT_INTERVAL/1000:.2f}с")

    def jump(self):
        if self.on_ground:
            self.dy = -JUMP_POWER
            self.on_ground = False

    def start_drag(self, event):
        self.is_dragging = True
        self.set_state("idle")
        self._drag_data['x'] = event.x
        self._drag_data['y'] = event.y

    def stop_drag(self, event):
        self.is_dragging = False
        self.x = self.root.winfo_x()
        self.y = self.root.winfo_y()
        self.dy = 2 
        self.on_ground = False
        self.target_x = None
        self.dx = 0

    def do_drag(self, event):
        if not self.is_dragging: return
        new_x = self.root.winfo_x() + (event.x - self._drag_data['x'])
        new_y = self.root.winfo_y() + (event.y - self._drag_data['y'])
        self.move_window(new_x, new_y)

    # --- Управление и прочее ---
    def set_state(self, new_state):
        if self.state != new_state:
            self.state = new_state
            self.current_sprite_index = 0

    def move_window(self, x, y):
        self.root.geometry(f'{self.width}x{self.height}+{int(x)}+{int(y)}')

    def send_status(self):
        active_window = pygetwindow.getActiveWindow()
        process_name = None
        if active_window:
            try:
                if self.is_windows:
                    import win32process
                    import win32gui
                    hwnd = active_window._hWnd
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    p = psutil.Process(pid)
                    process_name = p.name()
                else: 
                    process_name = "N/A"
            except (psutil.NoSuchProcess, psutil.AccessDenied, AttributeError, ImportError, pywintypes.error):
                process_name = "N/A"

        send_to_server(STATUS_ENDPOINT, {
            "timestamp": datetime.now().isoformat(),
            "action": self.state, 
            "x": int(self.x),
            "y": int(self.y),
            "active_window_title": active_window.title if active_window else "None",
            "active_window_process": process_name
        })

    def on_close(self):
        logging.info("Завершение работы персонажа.")
        for timer_id in self._timers.values():
            self.root.after_cancel(timer_id)
        self.root.destroy()

# --- Основная Точка Входа ---
if __name__ == "__main__":
    if not os.path.exists("assets"):
        logging.critical("Папка 'assets' не найдена! Запуск невозможен.")
        sys.exit(1)

    # Перед запуском основного приложения проверяем обновления
    check_for_updates()

    logging.info("Запуск приложения Desktop Waifu.")
    if not check_server_availability():
        logging.warning("Работа будет продолжена без отправки данных на сервер.")

    root = tk.Tk()
    character = WaifuCharacter(root)
    character.run()
    root.mainloop()
    logging.info("Приложение Desktop Waifu завершило работу.")

