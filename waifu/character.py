# -*- coding: utf-8 -*-
import pygame
import logging
import sys
from datetime import datetime

import config
from .physics import PhysicsController
from .utils import send_to_server
from .controllers.ai import AIController
from .controllers.animation import AnimationController
from .controllers.input import InputHandler
from .controllers.platform import PlatformManager

import pygetwindow
import psutil

try:
    import win32process
    IS_WIN = sys.platform.startswith('win')
except ImportError:
    IS_WIN = False

class WaifuCharacter:
    """
    Основной класс-оркестратор, управляющий всеми аспектами персонажа,
    делегируя задачи специализированным контроллерам.
    """
    def __init__(self, hwnd=None):
        self.width, self.height = config.SPRITE_WIDTH, config.SPRITE_HEIGHT
        self.hwnd = hwnd

        self.physics = PhysicsController(self.width, self.height)
        self.animation = AnimationController(self.width, self.height)
        self.platform_manager = PlatformManager(self, self.hwnd)
        self.ai = AIController(self, self.platform_manager.platforms)
        self.input = InputHandler(self, self.hwnd)
        
        # Параметры для прыжков, которые нужны разным контроллерам
        time_to_apex = config.TIME_TO_JUMP_APEX * config.FPS
        self.jump_gravity = (2 * config.JUMP_HEIGHT) / (time_to_apex**2)
        self.jump_velocity = self.jump_gravity * time_to_apex

        self.state = "idle"
        self.facing_direction = "right"
        
        if config.DEBUG_LOGGING:
            logging.info("Инициализация персонажа и всех контроллеров завершена.")
        
    @property
    def x(self): return self.physics.x
    @property
    def y(self): return self.physics.y

    def update(self, delta_time):
        self.platform_manager.update(delta_time)
        self.input.update()
        
        if not self.input.is_mouse_dragging:
            self.ai.update(delta_time)
        
        # Определение направления до обновления физики
        if self.physics.dx > 0.1: self.facing_direction = "right"
        elif self.physics.dx < -0.1: self.facing_direction = "left"
            
        self.physics.update(self.platform_manager.platforms)
        self.platform_manager.check_teleport_conditions()
        self.animation.update(delta_time, self.state, self.facing_direction)

    def draw(self, screen):
        current_sprite = self.animation.get_current_sprite()
        screen.blit(current_sprite, (0, 0))

    def handle_event(self, event):
        self.input.handle_event(event)

    def set_state(self, new_state):
        if self.state == new_state: return
        self.state = new_state
        self.animation.animation_timer = 0
        self.animation.current_sprite_index = 0
        self.send_status_to_server(new_state)

    def send_status_to_server(self, action):
        try:
            active_win = pygetwindow.getActiveWindow()
            if active_win and active_win._hWnd and IS_WIN:
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
            "x": int(self.x), "y": int(self.y),
            "active_window_title": active_window_title,
            "active_window_process": process_name
        }
        send_to_server(f"{config.SERVER_URL}/status", payload)

    def update_platforms_list(self, new_platforms):
        """Обновляет список платформ в AI контроллере."""
        self.ai.platforms = new_platforms

    def teleport(self, x, y):
        """Телепортирует персонажа в заданные координаты."""
        self.physics.x, self.physics.y = x, y
        self.physics.dx, self.physics.dy = 0, 0