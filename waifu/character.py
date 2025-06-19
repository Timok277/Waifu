# -*- coding: utf-8 -*-
import pygame
import logging
import math
import sys
from datetime import datetime

import config
from .physics import PhysicsController
from .platform import Platform
from .utils import get_desktop_windows, send_to_server
from .ai import AIController
from .animation import AnimationController
from .input import InputHandler

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
    Основной класс, управляющий персонажем.
    Координирует работу физического движка, AI, анимации и обработки ввода.
    """
    def __init__(self, hwnd=None):
        self.width, self.height = config.SPRITE_WIDTH, config.SPRITE_HEIGHT
        self.hwnd = hwnd

        self.physics = PhysicsController(self.width, self.height)
        self.animation_controller = AnimationController(self.width, self.height)
        self.input_handler = InputHandler(self, self.physics)
        self.ai_controller = AIController(self, self.physics)
        
        self.platforms = []
        self.monitors = []
        self.update_platforms() 
        
        self.jump_gravity, self.jump_velocity = self.calculate_jump_physics()
        
        self.state = "idle"
        self.facing_direction = "right"
        self.platforms_update_timer = 0
        
        # AI-related state
        self.target_x = None
        self.pending_jump_platform = None
        self.pending_jump_x = None
        
        # Input-related state
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
            
        # Обновление AI только если персонажа не таскают мышкой
        if not self.input_handler.is_mouse_dragging:
            self.ai_controller.update(delta_time)
        else:
            # Обновляем направление при перетаскивании
            if self.last_drag_dx > 0.1: self.facing_direction = "right"
            elif self.last_drag_dx < -0.1: self.facing_direction = "left"
            self.last_drag_dx = 0
            
        # Определяем направление на основе движения
        if self.physics.dx > 0.1: self.facing_direction = "right"
        elif self.physics.dx < -0.1: self.facing_direction = "left"
            
        self.physics.update(self.platforms)
        self.check_teleport_conditions()
        self.animation_controller.update_animation(delta_time, self.state, self.facing_direction)

    def draw(self, screen):
        current_sprite = self.animation_controller.get_current_sprite()
        screen.blit(current_sprite, (0, 0))

    def handle_event(self, event):
        self.input_handler.handle_event(event)

    def calculate_jump_physics(self):
        time_to_apex_in_frames = config.TIME_TO_JUMP_APEX * config.FPS
        jump_gravity = (2 * config.JUMP_HEIGHT) / (time_to_apex_in_frames**2)
        jump_velocity = jump_gravity * time_to_apex_in_frames
        if config.DEBUG_LOGGING:
            logging.info(f"Физика прыжка (на кадр): g={jump_gravity:.2f}, v0={jump_velocity:.2f}")
        return jump_gravity, jump_velocity

    def jump_to_platform(self, target_platform, target_x):
        if not self.physics.on_ground: return
        
        platform_to_jump_from = self.physics.current_platform
        self.reset_ai_targets()
        self.set_state("walk") # Анимация ходьбы/прыжка

        optimal_landing_x = max(target_platform.left, min(target_x, target_platform.right - self.width))
        
        delta_x = optimal_landing_x - self.physics.x
        delta_y = (target_platform.top - self.height) - self.physics.y
        gravity = self.jump_gravity

        time_to_target = 0
        vy0 = 0

        if delta_y <= 0: # Прыжок вверх
            vy0 = -self.jump_velocity
            discriminant = vy0**2 + 2 * gravity * delta_y
            if discriminant >= 0:
                time_to_target = (-vy0 + math.sqrt(discriminant)) / gravity
        else: # Прыжок вниз
            if gravity > 0:
                time_to_target = math.sqrt(2 * delta_y / gravity)
        
        if time_to_target <= 0:
            if config.DEBUG_LOGGING: logging.error("Не удалось рассчитать время прыжка.")
            return

        self.physics.dx = delta_x / time_to_target
        self.physics.dy = vy0
        self.physics.gravity_override = gravity
        self.physics.on_ground = False
        self.physics.platform_to_ignore = platform_to_jump_from
        self.physics.platform_to_jump_to = target_platform
        
        if config.DEBUG_LOGGING:
            logging.info(f"Прыгаю к ({optimal_landing_x:.0f}, {target_platform.top:.0f})! V=({self.physics.dx:.2f}, {self.physics.dy:.2f}), T~={time_to_target:.0f} кадров")
    
    def reset_ai_targets(self):
        """Сбрасывает цели AI, используется при перехвате управления."""
        self.target_x = None
        self.pending_jump_platform = None
        self.pending_jump_x = None
        self.ai_controller.ai_timer = 0

    def set_state(self, new_state):
        if self.state == new_state: return
        
        previous_state = self.state
        self.state = new_state
        
        # Сброс таймера анимации при смене состояния, если это не просто продолжение движения
        if not (previous_state.startswith("walk") and new_state.startswith("walk")):
             self.animation_controller.animation_timer = 0
             self.animation_controller.current_sprite_index = 0

        # --- Отправка статуса на сервер ---
        self.send_status_to_server(new_state)

    def send_status_to_server(self, action):
        try:
            active_win = pygetwindow.getActiveWindow()
            if active_win and active_win._hWnd:
                pid = win32process.GetWindowThreadProcessId(active_win._hWnd)[1]
                process_name = psutil.Process(pid).name()
                active_window_title = active_win.title
            else:
                active_window_title = "Unknown"
                process_name = "Unknown"
        except Exception:
             active_window_title = "Unknown"
             process_name = "Unknown"

        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "x": int(self.physics.x),
            "y": int(self.physics.y),
            "active_window_title": active_window_title,
            "active_window_process": process_name
        }
        send_to_server(f"{config.SERVER_URL}/status", payload)
        
    def update_platforms(self):
        if not IS_WIN: return
        self.monitors = get_monitors()
        
        window_rects = get_desktop_windows()
        new_platforms = []
        
        for w_rect in window_rects:
            left, top, right, bottom = w_rect
            if (right - left) > 150 and (bottom - top) > 50:
                try:
                    if self.hwnd and self.hwnd == win32gui.WindowFromPoint((left, top)):
                        continue
                except pywintypes.error: pass
                
                new_platform = Platform(left, top, right, top + 2)
                if new_platform not in new_platforms:
                    new_platforms.append(new_platform)

        for m in self.monitors:
            new_platform = Platform(m.x, m.y + m.height, m.x + m.width, m.y + m.height + 2)
            if new_platform not in new_platforms:
                new_platforms.append(new_platform)
                
        self.platforms = new_platforms 
        if config.DEBUG_LOGGING:
            logging.info(f"Обновлены платформы ({len(self.platforms)} шт).")

    def check_teleport_conditions(self):
        if not self.monitors: return
        max_y = max(m.y + m.height for m in self.monitors)
        
        if self.physics.y > max_y + 200:
            logging.warning("Персонаж упал за пределы экрана! Телепортация.")
            primary = next((m for m in self.monitors if m.is_primary), self.monitors[0])
            self.physics.x = primary.x + primary.width / 2
            self.physics.y = primary.y + primary.height / 2
            self.physics.dx, self.physics.dy = 0, 0