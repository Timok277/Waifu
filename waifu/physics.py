# -*- coding: utf-8 -*-

import logging
import config

class PhysicsController:
    """
    Управляет всей физикой персонажа.
    Версия 5.0: Поддержка управляемой параболы прыжка через gravity_override.
    """
    def __init__(self, char_width, char_height):
        self.x = 500
        self.y = 500
        self.dx = 0
        self.dy = 0
        
        self.on_ground = False
        self.was_on_ground = False
        self.current_platform = None
        
        self.char_width = char_width
        self.char_height = char_height
        
        self.gravity_override = None # Позволяет временно менять гравитацию для прыжка
        self.platform_to_ignore = None
        self.platform_to_jump_to = None

    def update(self, platforms):
        self.was_on_ground = self.on_ground
        
        if self.on_ground:
            self.platform_to_ignore = None
            self.platform_to_jump_to = None
        
        # --- Основной цикл обновления физики ---
        # 1. Применяем гравитацию (если не в прыжке со своей гравитацией)
        if self.gravity_override is None:
            self.dy += config.GRAVITY
        else:
            self.dy += self.gravity_override

        # 2. Ограничиваем максимальную скорость падения
        if self.dy > config.MAX_FALL_SPEED:
            self.dy = config.MAX_FALL_SPEED
        
        # 3. Ограничиваем максимальную горизонтальную скорость
        if abs(self.dx) > config.MAX_HORIZONTAL_SPEED:
            self.dx = config.MAX_HORIZONTAL_SPEED * (1 if self.dx > 0 else -1)
        
        next_x = self.x + self.dx
        next_y = self.y + self.dy
        
        # 4. Ищем самую высокую платформу, на которую мы МОЖЕМ приземлиться
        best_platform = None
        
        # Падаем вниз или движемся горизонтально (dy >= 0)
        if self.dy >= 0:
            potential_grounds = []
            
            for p in platforms:
                if p == self.platform_to_ignore:
                    continue
                # Проверяем горизонтальное пересечение
                if max(next_x, p.left) < min(next_x + self.char_width, p.right):
                    # Персонаж должен пересечь верхнюю грань платформы за этот кадр
                    if (self.y + self.char_height) <= p.top + 1 and (next_y + self.char_height) >= p.top:
                        potential_grounds.append(p)
            
            if potential_grounds:
                # Выбираем самую высокую из возможных платформ (с наименьшим Y)
                best_platform = min(potential_grounds, key=lambda p: p.top)
        
        # NEW: Проверка столкновения с потолком (когда прыгаем вверх)
        else: # self.dy < 0
            potential_ceilings = []
            for p in platforms:
                 if p == self.platform_to_ignore or p == self.platform_to_jump_to:
                    continue
                 # Проверяем горизонтальное пересечение
                 if max(next_x, p.left) < min(next_x + self.char_width, p.right):
                    # Персонаж должен пересечь нижнюю грань платформы за этот кадр
                    if self.y >= p.bottom and next_y <= p.bottom:
                        potential_ceilings.append(p)
            
            if potential_ceilings:
                # Выбираем самый низкий потолок, в который врезались
                best_ceiling = max(potential_ceilings, key=lambda p: p.bottom)
                self.y = best_ceiling.bottom
                self.dy = 0 # Обнуляем скорость, чтобы начать падать
                # self.platform_to_ignore = None # НЕ СБРАСЫВАЕМ! Иначе сразу приземлимся на исходную.
                self.platform_to_jump_to = None

        # 5. Обрабатываем столкновение или его отсутствие
        if best_platform:
            # СТОЛКНОВЕНИЕ: Приземляемся
            self.y = best_platform.top - self.char_height
            self.dy = 0
            self.dx *= 0.1 # Friction on landing
            self.on_ground = True
            self.current_platform = best_platform
            self.gravity_override = None
            if config.DEBUG_LOGGING and not self.was_on_ground:
                logging.info(f"Приземлился на платформу Y={best_platform.top}")
            
            # Применяем горизонтальное движение и СРАЗУ ограничиваемся краями новой платформы
            self.x = next_x
            self.x = max(self.current_platform.left, min(self.x, self.current_platform.right - self.char_width))
            
            # Сбрасываем горизонтальную скорость ПОСЛЕ приземления
            self.dx = 0
        else:
            # СТОЛКНОВЕНИЯ НЕТ: Мы в воздухе
            if self.on_ground:
                logging.info("Сошел с края платформы.")
            
            self.on_ground = False
            self.current_platform = None
            self.x = next_x
            self.y = next_y 