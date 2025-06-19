import pygame
import sys
import config

# Зависимости для Windows-специфичных функций
try:
    import win32gui
    IS_WIN = sys.platform.startswith('win')
except ImportError:
    IS_WIN = False

class InputHandler:
    """Обрабатывает ввод от пользователя (мышь, клавиатура)."""

    def __init__(self, character, hwnd):
        self.character = character
        self.physics = character.physics
        self.hwnd = hwnd
        
        self.is_mouse_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.last_drag_dx = 0
        self.last_drag_dy = 0
    
    def handle_event(self, event):
        """Обрабатывает события Pygame."""
        if not IS_WIN: return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.start_drag(event)
        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.stop_drag()
        elif event.type == pygame.MOUSEMOTION:
            self.on_drag(event)

    def start_drag(self, event):
        """Начинает перетаскивание персонажа."""
        mouse_x, mouse_y = event.pos
        char_rect = pygame.Rect(0, 0, self.character.width, self.character.height)
        if char_rect.collidepoint(mouse_x, mouse_y):
            self.is_mouse_dragging = True
            self.physics.on_ground = False
            self.character.ai.reset_target() # Сбрасываем цель AI при начале перетаскивания
            
            win_x, win_y = win32gui.GetWindowRect(self.hwnd)[:2]
            cursor_x, cursor_y = win32gui.GetCursorPos()
            self.drag_offset_x = cursor_x - win_x
            self.drag_offset_y = cursor_y - win_y

    def stop_drag(self):
        """Заканчивает перетаскивание и придает инерцию."""
        if self.is_mouse_dragging:
            self.is_mouse_dragging = False
            # Применяем инерцию
            self.physics.dx = self.last_drag_dx * config.DRAG_INERTIA_FACTOR
            self.physics.dy = self.last_drag_dy * config.DRAG_INERTIA_FACTOR

    def on_drag(self, event):
        """Обновляет позицию персонажа во время перетаскивания."""
        if self.is_mouse_dragging:
            cursor_x, cursor_y = win32gui.GetCursorPos()
            new_win_x = cursor_x - self.drag_offset_x
            new_win_y = cursor_y - self.drag_offset_y
            
            # Сохраняем последние смещения для расчета инерции
            self.last_drag_dx = new_win_x - self.physics.x
            self.last_drag_dy = new_win_y - self.physics.y

            self.physics.x = new_win_x
            self.physics.y = new_win_y
            self.physics.dx = 0
            self.physics.dy = 0
            
            # Определяем направление взгляда
            if self.last_drag_dx > 0.1: self.character.facing_direction = "right"
            elif self.last_drag_dx < -0.1: self.character.facing_direction = "left"
            self.last_drag_dx = 0 # Сбрасываем, чтобы избежать "залипания" направления

    def update(self):
        """Вызывается в основном цикле для обновления состояния, не связанного с событиями."""
        # Можно использовать для будущих проверок, например, удержания клавиш
        pass 