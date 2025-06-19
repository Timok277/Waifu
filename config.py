# -*- coding: utf-8 -*-

# --- Конфигурация Сервера ---
SERVER_URL = "http://26.186.125.19:8000"
STATUS_ENDPOINT = f"{SERVER_URL}/status"
ERROR_ENDPOINT = f"{SERVER_URL}/error"
LOG_ENDPOINT = f"{SERVER_URL}/log"

# --- Целевые Окна ---
# Используются для определения, где персонаж будет "сидеть"
TARGET_WINDOW_TITLES = ["Visual Studio Code", "Visual Studio"]
TARGET_WINDOW_PROCESSES = ["Code.exe", "devenv.exe"]

# --- Пути к Спрайтам ---
SPRITE_PATHS = {
    "idle": "assets/anime_waifu_idle_pose_transparent_background_index_3.png",
    "walk1": "assets/anime_girl_walking_animation_frame_index_0.png",
    "walk2": "assets/anime_girl_walking_animation_frame_index_1.png",
    "sit": "assets/anime_girl_waifu_sitting_transparent_background_index_2.png",
}

# --- Параметры Персонажа ---
SPRITE_WIDTH, SPRITE_HEIGHT = 150, 200

# --- Настройки Pygame ---
FPS = 60

# --- Интервалы (в миллисекундах) ---
ANIMATION_INTERVAL = 150
PHYSICS_INTERVAL = 50 
CURSOR_CHECK_INTERVAL = 200 
STATUS_SEND_INTERVAL = 5000 

# --- Физические Константы ---
WALK_SPEED = 2
JUMP_POWER = 12
GRAVITY = 0.98
TERMINAL_VELOCITY = 10
CURSOR_EVADE_DISTANCE = 50

# --- Новые параметры для управляемого прыжка ---
JUMP_HEIGHT = 1100
TIME_TO_JUMP_APEX = 0.7

# --- Поведение AI ---
AI_UPDATE_INTERVAL = 3.0       # Как часто AI принимает решения (в секундах)
PLATFORM_UPDATE_INTERVAL = 2.0 # Как часто сканировать окна на рабочем столе
AI_JUMP_PROBABILITY = 0.4      # Вероятность того, что AI решит прыгнуть, если есть куда
AI_JUMP_ATTEMPTS = 10          # Сколько вариантов для прыжка AI пытается найти
AI_WALK_TO_JUMP_THRESHOLD = 5  # Расстояние в пикселях, которое считается "прибытием" в точку для прыжка
AI_MAX_WALK_DISTANCE = 400     # Максимальное расстояние, на которое AI гуляет по платформе

# --- Конфигурация Обновлений ---
CURRENT_VERSION = "2.1.3.9" # Текущая версия приложения
GITHUB_REPO = "Timok277/Waifu" # Путь к репозиторию

# --- Отладка ---
DEBUG_LOGGING = False # Включить для вывода подробных логов состояния в консоль 

# --- Физика и движение ---
MAX_FALL_SPEED = 25 
MAX_HORIZONTAL_SPEED = 25 # Ограничиваем максимальную скорость по горизонтали
DRAG_INERTIA_FACTOR = 0.25 # Коэффициент инерции после перетаскивания мышью

# --- Сервер ---
MAX_LOG_HISTORY = 200 # Максимальное количество логов, хранимых на сервере
