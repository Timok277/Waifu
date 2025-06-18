# -*- coding: utf-8 -*-
import pygame
import logging
import random
import os
import math
import sys
from datetime import datetime

import config
from .physics import PhysicsController
from .platform import Platform
from .utils import get_desktop_windows, scale_image, send_to_server
from screeninfo import get_monitors
import pygetwindow
import psutil

# Зависимости для Windows-специфичных функций
try:
    import win32gui
    import win32process
    import pywintypes
    IS_WIN = sys.platform.startswith('win')
except ImportError:
    IS_WIN = False

class WaifuCharacter:
    """
    Основной класс, управляющий персонажем, его логикой, физикой и отображением.
    Версия 3.0: Полный рефакторинг для стабильности и чистоты кода.
    """
    def __init__(self, hwnd=None):
        self.width, self.height = config.SPRITE_WIDTH, config.SPRITE_HEIGHT
        self.hwnd = hwnd

        self.sprites = {}
        self.load_sprites()
        if not self.sprites:
            raise RuntimeError("Критическая ошибка: не удалось загрузить спрайты.")
        
        self.physics = PhysicsController(self.width, self.height)
        self.platforms = []
        self.update_platforms() 
        
        time_to_apex_in_frames = config.TIME_TO_JUMP_APEX * config.FPS
        self.jump_gravity = (2 * config.JUMP_HEIGHT) / (time_to_apex_in_frames**2)
        self.jump_velocity = self.jump_gravity * time_to_apex_in_frames
        if config.DEBUG_LOGGING:
            logging.info(f"Физика прыжка (на кадр): g={self.jump_gravity:.2f}, v0={self.jump_velocity:.2f}")

        self.state = "idle"
        self.facing_direction = "right"
        self.image_list = self.sprites['idle'][self.facing_direction]
        self.current_sprite_index = 0
        self.animation_timer = 0
        self.ai_timer = 0
        self.platforms_update_timer = 0
        self.target_x = None
        self.pending_jump_platform = None
        self.pending_jump_x = None
        
        self.is_mouse_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.last_drag_dx = 0
        self.last_drag_dy = 0
        
        if config.DEBUG_LOGGING:
            logging.info("Инициализация персонажа завершена.")
        
    @property
    def x(self): return self.physics.x
    @property
    def y(self): return self.physics.y

    def update(self, delta_time):
        self.platforms_update_timer += delta_time
        if self.platforms_update_timer > (config.PLATFORM_UPDATE_INTERVAL * 1000):
            self.update_platforms()
            self.platforms_update_timer = 0
            
        if self.is_mouse_dragging:
            if self.last_drag_dx > 0.1: self.facing_direction = "right"
            elif self.last_drag_dx < -0.1: self.facing_direction = "left"
            self.last_drag_dx = 0 # Сбрасываем, чтобы избежать "залипания" направления
            
            self.ai_timer = 0
            self.target_x = None
            self.pending_jump_platform = None
        else:
            self.update_ai(delta_time)
            # Определяем направление ДО обновления физики, т.к. физика может сбросить dx
            if self.physics.dx > 0.1: self.facing_direction = "right"
            elif self.physics.dx < -0.1: self.facing_direction = "left"
            
        self.physics.update(self.platforms)
        self.check_teleport_conditions()
        self.update_animation(delta_time)

    def draw(self, screen):
        current_sprite = self.image_list[self.current_sprite_index]
        screen.blit(current_sprite, (0, 0))

    def handle_event(self, event):
        if not IS_WIN: return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x, mouse_y = event.pos
            char_rect = pygame.Rect(0, 0, self.width, self.height)
            if char_rect.collidepoint(mouse_x, mouse_y):
                self.is_mouse_dragging = True
                self.physics.on_ground = False
                win_x, win_y = win32gui.GetWindowRect(self.hwnd)[:2]
                cursor_x, cursor_y = win32gui.GetCursorPos()
                self.drag_offset_x = cursor_x - win_x
                self.drag_offset_y = cursor_y - win_y

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_mouse_dragging:
                self.is_mouse_dragging = False
                self.physics.dx = self.last_drag_dx * 0.25 # Уменьшаем инерцию в 4 раза
                self.physics.dy = self.last_drag_dy * 0.25

        elif event.type == pygame.MOUSEMOTION:
            if self.is_mouse_dragging:
                cursor_x, cursor_y = win32gui.GetCursorPos()
                new_win_x = cursor_x - self.drag_offset_x
                new_win_y = cursor_y - self.drag_offset_y
                
                self.last_drag_dx = new_win_x - self.physics.x
                self.last_drag_dy = new_win_y - self.physics.y

                self.physics.x = new_win_x
                self.physics.y = new_win_y
                self.physics.dx = 0
                self.physics.dy = 0

    def update_ai(self, delta_time):
        self.ai_timer += delta_time
        
        if self.physics.on_ground and self.target_x is None and self.pending_jump_platform is None:
            if self.ai_timer > (config.AI_UPDATE_INTERVAL * 1000):
                self.choose_new_action()
                self.ai_timer = 0
        
        if self.target_x is not None:
            self.set_state("walk")
            move_direction = 1 if self.target_x > self.physics.x else -1
            self.physics.dx = config.WALK_SPEED * move_direction
            
            if abs(self.target_x - self.physics.x) < config.WALK_SPEED:
                self.physics.x = self.target_x
                self.target_x = None
                self.physics.dx = 0
                if self.pending_jump_platform:
                    self.jump_to_platform(self.pending_jump_platform, self.pending_jump_x)
                else:
                    self.set_state("idle")
        elif self.physics.on_ground:
            self.physics.dx = 0
            self.set_state("idle")

    def choose_new_action(self):
        # --- Логика выбора действия на основе видимых платформ ---
        if not self.physics.on_ground or not self.physics.current_platform:
            return

        current_platform = self.physics.current_platform
        
        # 1. Найти и оценить возможные прыжки
        possible_jumps = []
        # Отфильтровываем платформы, которые находятся выше Y=0, чтобы не прыгать за экран.
        other_platforms = [
            p for p in self.platforms 
            if p != current_platform and p.top > 0
        ]

        # Проверяем до 10 случайных целей, чтобы найти лучшую
        for _ in range(10):
            if not other_platforms: break
            
            target_platform = random.choice(other_platforms)
            # Выбираем случайную точку приземления
            landing_x = random.uniform(target_platform.left, target_platform.right - self.width)
            
            is_jumping_down = target_platform.top > current_platform.top

            # 1. Проверка на препятствия сверху (физическое перекрытие пути)
            path_is_clear = True
            if not is_jumping_down:
                # Примерная траектория прыжка (прямоугольник)
                takeoff_x = max(current_platform.left, min(landing_x, current_platform.right - self.width))
                jump_left = min(self.physics.x, takeoff_x)
                jump_right = max(self.physics.x + self.width, takeoff_x + self.width)
                jump_top = target_platform.top
                jump_bottom = current_platform.top

                for p in self.platforms:
                    if p == current_platform or p == target_platform:
                        continue
                    
                    # Полная проверка на пересечение прямоугольников: прыжковой зоны и платформы p
                    horizontal_overlap = max(jump_left, p.left) < min(jump_right, p.right)
                    vertical_overlap = max(jump_top, p.top) < min(jump_bottom, p.bottom)

                    if horizontal_overlap and vertical_overlap:
                        path_is_clear = False
                        break
            
            # 2. Проверка возможности самого прыжка (достаточно ли силы)
            can_reach_height = False
            if is_jumping_down:
                can_reach_height = True # Всегда можно спрыгнуть вниз
            else: # Прыжок вверх
                height_diff = current_platform.top - target_platform.top
                if height_diff <= config.JUMP_HEIGHT:
                    can_reach_height = True

            if path_is_clear and can_reach_height:
                # Рассчитываем точку старта на текущей платформе
                takeoff_x = max(current_platform.left, min(landing_x, current_platform.right - self.width))
                walk_distance = abs(self.physics.x - takeoff_x)
                possible_jumps.append((walk_distance, target_platform, landing_x, takeoff_x))

        # 2. Принять решение
        # Сортируем прыжки по "стоимости" (расстоянию) и выбираем лучший
        # Уменьшаем вероятность прыжка до 40%, чтобы она больше ходила
        if possible_jumps and random.random() < 0.4:
            possible_jumps.sort(key=lambda j: j[0])
            best_jump = possible_jumps[0]
            _, target_platform, landing_x, takeoff_x = best_jump

            if config.DEBUG_LOGGING:
                logging.info(f"Решил прыгнуть с x={takeoff_x:.0f} на платформу Y={target_platform.top} в точку x={landing_x:.0f}")

            # Если до точки старта нужно идти, идем.
            if abs(self.physics.x - takeoff_x) > 5:
                 self.target_x = takeoff_x
                 self.pending_jump_platform = target_platform
                 self.pending_jump_x = landing_x
            else:
                 # Если уже на месте, прыгаем.
                 self.jump_to_platform(target_platform, landing_x)
            return

        # 3. Если не прыгаем, просто гуляем по текущей платформе, но недалеко
        if current_platform.width > self.width * 1.5:
            # Выбираем точку в радиусе 400 пикселей от текущего положения
            min_walk = max(current_platform.left, self.physics.x - 400)
            max_walk = min(current_platform.right - self.width, self.physics.x + 400)
            if max_walk > min_walk:
                self.target_x = random.uniform(min_walk, max_walk)
                if config.DEBUG_LOGGING:
                    logging.info(f"Решил прогуляться по текущей платформе до x={self.target_x:.0f}")

    def jump_to_platform(self, target_platform, target_x):
        if not self.physics.on_ground: return
        
        platform_to_jump_from = self.physics.current_platform
        self.pending_jump_platform = None
        self.pending_jump_x = None
        self.set_state("walk")

        optimal_landing_x = max(target_platform.left, min(target_x, target_platform.right - self.width))
        
        delta_x = optimal_landing_x - self.physics.x
        delta_y = (target_platform.top - self.height) - self.physics.y
        gravity = self.jump_gravity

        vy0 = 0
        time_to_target = 0

        if delta_y <= 0: # Прыжок вверх или на тот же уровень
            vy0 = -self.jump_velocity
            
            discriminant = vy0**2 + 2 * gravity * delta_y
            if discriminant < 0:
                if config.DEBUG_LOGGING: logging.error("Невозможно совершить прыжок вверх: цель недостижима.")
                return

            time_to_target = (-vy0 + math.sqrt(discriminant)) / gravity
            if time_to_target <= 0:
                 if config.DEBUG_LOGGING: logging.error("Невозможно совершить прыжок вверх: время отрицательное.")
                 return

            self.physics.dx = delta_x / time_to_target
            self.physics.dy = vy0

        else: # Прыжок вниз
            vy0 = 0 # Начинаем падение
            
            if gravity > 0:
                time_to_target = math.sqrt(2 * delta_y / gravity)
                if time_to_target > 0:
                    self.physics.dx = delta_x / time_to_target
            self.physics.dy = vy0
        
        if time_to_target <= 0:
            if config.DEBUG_LOGGING: logging.error(f"Не удалось рассчитать время прыжка.")
            return

        self.physics.gravity_override = gravity
        self.physics.on_ground = False
        self.physics.platform_to_ignore = platform_to_jump_from
        self.physics.platform_to_jump_to = target_platform
        
        if config.DEBUG_LOGGING:
            logging.info(f"Прыгаю к ({optimal_landing_x:.0f}, {target_platform.top:.0f})! V=({self.physics.dx:.2f}, {self.physics.dy:.2f}), T~={time_to_target:.0f} кадров")

    def set_state(self, new_state):
        if self.state == new_state: return
        self.state = new_state
        # Сброс анимации при смене состояния
        self.animation_timer = 0
        self.current_sprite_index = 0

        # --- Отправка статуса на сервер ---
        try:
            active_win = pygetwindow.getActiveWindow()
            if active_win and active_win._hWnd:
                pid = win32process.GetWindowThreadProcessId(active_win._hWnd)[1]
                process_name = psutil.Process(pid).name()
                active_window_title = active_win.title
                active_window_process = process_name
            else:
                active_window_title = "Unknown"
                active_window_process = "Unknown"
        except Exception:
             active_window_title = "Unknown"
             active_window_process = "Unknown"

        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": new_state,
            "x": int(self.physics.x),
            "y": int(self.physics.y),
            "active_window_title": active_window_title,
            "active_window_process": active_window_process
        }
        send_to_server(f"{config.SERVER_URL}/status", payload)

    def update_animation(self, delta_time):
        # 1. Выбираем правильный список кадров для текущего состояния и направления
        self.image_list = self.sprites[self.state][self.facing_direction]

        # 2. Обновляем кадр анимации по таймеру
        self.animation_timer += delta_time
        if self.animation_timer > config.ANIMATION_INTERVAL:
            self.animation_timer = 0
            self.current_sprite_index = (self.current_sprite_index + 1) % len(self.image_list)

    def load_sprites(self):
        try:
            raw_images = {name: pygame.image.load(path).convert_alpha() for name, path in config.SPRITE_PATHS.items()}
            scaled_images = {name: pygame.transform.smoothscale(img, (self.width, self.height)) for name, img in raw_images.items()}
            self.sprites = {
                "idle": self.prepare_sprite_set(scaled_images["idle"]),
                "walk": self.prepare_sprite_set(scaled_images["walk1"], scaled_images["walk2"]),
                "sit": self.prepare_sprite_set(scaled_images["sit"]),
            }
        except Exception as e:
            logging.critical(f"Ошибка загрузки спрайтов: {e}")

    def prepare_sprite_set(self, *surfaces):
        return {
            "right": list(surfaces),
            "left": [pygame.transform.flip(s, True, False) for s in surfaces]
        }
        
    def update_platforms(self):
        if not IS_WIN: return
        self.monitors = get_monitors()
        
        # get_desktop_windows() теперь возвращает окна, отсортированные по Z-order (сверху вниз)
        window_rects = get_desktop_windows()
        
        # Окна идут первыми, так как они "выше" в Z-порядке
        new_platforms = []
        
        for w_rect in window_rects:
            left, top, right, bottom = w_rect
            width = right - left
            height = bottom - top

            if width > 150 and height > 50:
                # Пропускаем собственное окно приложения
                try:
                    if self.hwnd == win32gui.WindowFromPoint((left, top)):
                        continue
                except pywintypes.error:
                    pass 
                
                # Добавляем верхнюю грань окна как платформу. Высота 2 пикселя для корректной детекции.
                new_platform = Platform(left, top, right, top + 2)
                if new_platform not in new_platforms:
                    new_platforms.append(new_platform)

        # Затем добавляем мониторы как самые нижние платформы
        for m in self.monitors:
            new_platform = Platform(m.x, m.y + m.height, m.x + m.width, m.y + m.height + 2)
            if new_platform not in new_platforms:
                new_platforms.append(new_platform)
                
        self.platforms = new_platforms 
        if config.DEBUG_LOGGING:
            logging.info(f"Обновлены платформы ({len(new_platforms)} шт). Z-Order (сверху вниз):")
            for i, p in enumerate(self.platforms):
                logging.info(f"  {i+1}. Y={p.top} | L={p.left}, R={p.right}")

    def check_teleport_conditions(self):
        if not self.monitors: return
        max_y = max(m.y + m.height for m in self.monitors)
        
        if self.physics.y > max_y + 200:
            logging.warning("Персонаж упал за пределы экрана! Телепортация.")
            primary = next((m for m in self.monitors if m.is_primary), self.monitors[0])
            self.physics.x = primary.x + primary.width / 2
            self.physics.y = primary.y + primary.height / 2
            self.physics.dx, self.physics.dy = 0, 0