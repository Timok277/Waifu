# -*- coding: utf-8 -*-
import pygame
import config

try:
    import win32gui
    IS_WIN = True
except ImportError:
    IS_WIN = False

class InputHandler:
    """
    Обрабатывает ввод пользователя (в основном, перетаскивание мышью).
    """
    def __init__(self, character, physics):
        self.character = character
        self.physics = physics
        self.is_mouse_dragging = False
        self.drag_offset_x = 0
        self.drag_offset_y = 0

    def handle_event(self, event):
        if not IS_WIN: return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mouse_x, mouse_y = event.pos
            char_rect = pygame.Rect(0, 0, self.character.width, self.character.height)
            if char_rect.collidepoint(mouse_x, mouse_y):
                self.is_mouse_dragging = True
                self.physics.on_ground = False
                win_x, win_y = win32gui.GetWindowRect(self.character.hwnd)[:2]
                cursor_x, cursor_y = win32gui.GetCursorPos()
                self.drag_offset_x = cursor_x - win_x
                self.drag_offset_y = cursor_y - win_y
                # Сбрасываем AI цели при начале перетаскивания
                self.character.reset_ai_targets()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_mouse_dragging:
                self.is_mouse_dragging = False
                self.physics.dx = self.character.last_drag_dx * config.DRAG_INERTIA_FACTOR
                self.physics.dy = self.character.last_drag_dy * config.DRAG_INERTIA_FACTOR

        elif event.type == pygame.MOUSEMOTION:
            if self.is_mouse_dragging:
                cursor_x, cursor_y = win32gui.GetCursorPos()
                new_win_x = cursor_x - self.drag_offset_x
                new_win_y = cursor_y - self.drag_offset_y
                
                self.character.last_drag_dx = new_win_x - self.physics.x
                self.character.last_drag_dy = new_win_y - self.physics.y

                self.physics.x = new_win_x
                self.physics.y = new_win_y
                self.physics.dx = 0
                self.physics.dy = 0 