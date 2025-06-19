# -*- coding: utf-8 -*-
import random
import logging
import config

class AIController:
    """
    Управляет поведением персонажа, принимая решения о его действиях.
    """
    def __init__(self, character, physics):
        self.character = character
        self.physics = physics
        self.ai_timer = 0
    
    def update(self, delta_time):
        self.ai_timer += delta_time
        
        # AI принимает решение только если он на земле и у него нет текущей цели
        if self.physics.on_ground and self.character.target_x is None and self.character.pending_jump_platform is None:
            if self.ai_timer > (config.AI_UPDATE_INTERVAL * 1000):
                self.choose_new_action()
                self.ai_timer = 0
        
        # Логика движения к цели
        if self.character.target_x is not None:
            self.character.set_state("walk")
            move_direction = 1 if self.character.target_x > self.physics.x else -1
            self.physics.dx = config.WALK_SPEED * move_direction
            
            # Проверка прибытия в точку x
            if abs(self.character.target_x - self.physics.x) < config.WALK_SPEED:
                self.physics.x = self.character.target_x
                self.character.target_x = None
                self.physics.dx = 0
                
                # Если мы шли, чтобы прыгнуть, то прыгаем
                if self.character.pending_jump_platform:
                    self.character.jump_to_platform(
                        self.character.pending_jump_platform, 
                        self.character.pending_jump_x
                    )
                else:
                    self.character.set_state("idle")
        
        # Если стоим на земле без цели, то переходим в состояние покоя
        elif self.physics.on_ground:
            self.physics.dx = 0
            self.character.set_state("idle")

    def choose_new_action(self):
        if not self.physics.on_ground or not self.physics.current_platform:
            return

        current_platform = self.physics.current_platform
        
        # 1. Найти и оценить возможные прыжки
        possible_jumps = self.find_possible_jumps(current_platform)

        # 2. Принять решение
        # Сортируем прыжки по "стоимости" (расстоянию) и выбираем лучший
        if possible_jumps and random.random() < config.AI_JUMP_PROBABILITY:
            possible_jumps.sort(key=lambda j: j[0])
            best_jump = possible_jumps[0]
            _, target_platform, landing_x, takeoff_x = best_jump

            if config.DEBUG_LOGGING:
                logging.info(f"Решил прыгнуть с x={takeoff_x:.0f} на платформу Y={target_platform.top} в точку x={landing_x:.0f}")

            # Если до точки старта нужно идти, идем.
            if abs(self.physics.x - takeoff_x) > config.AI_WALK_TO_JUMP_THRESHOLD:
                 self.character.target_x = takeoff_x
                 self.character.pending_jump_platform = target_platform
                 self.character.pending_jump_x = landing_x
            else:
                 # Если уже на месте, прыгаем.
                 self.character.jump_to_platform(target_platform, landing_x)
            return

        # 3. Если не прыгаем, просто гуляем по текущей платформе
        if current_platform.width > self.character.width * 1.5:
            min_walk = max(current_platform.left, self.physics.x - config.AI_MAX_WALK_DISTANCE)
            max_walk = min(current_platform.right - self.character.width, self.physics.x + config.AI_MAX_WALK_DISTANCE)
            if max_walk > min_walk:
                self.character.target_x = random.uniform(min_walk, max_walk)
                if config.DEBUG_LOGGING:
                    logging.info(f"Решил прогуляться по текущей платформе до x={self.character.target_x:.0f}")

    def find_possible_jumps(self, current_platform):
        possible_jumps = []
        other_platforms = [p for p in self.character.platforms if p != current_platform and p.top > 0]

        for _ in range(config.AI_JUMP_ATTEMPTS):
            if not other_platforms: break
            
            target_platform = random.choice(other_platforms)
            landing_x = random.uniform(target_platform.left, target_platform.right - self.character.width)
            
            is_jumping_down = target_platform.top > current_platform.top
            
            path_is_clear = self.is_path_clear(current_platform, target_platform, landing_x, is_jumping_down)
            can_reach = self.can_reach_height(current_platform, target_platform)

            if path_is_clear and can_reach:
                takeoff_x = max(current_platform.left, min(landing_x, current_platform.right - self.character.width))
                walk_distance = abs(self.physics.x - takeoff_x)
                possible_jumps.append((walk_distance, target_platform, landing_x, takeoff_x))
        
        return possible_jumps

    def is_path_clear(self, current_platform, target_platform, landing_x, is_jumping_down):
        if is_jumping_down: return True

        # Прямоугольник, описывающий траекторию прыжка
        takeoff_x = max(current_platform.left, min(landing_x, current_platform.right - self.character.width))
        jump_left = min(self.physics.x, takeoff_x)
        jump_right = max(self.physics.x + self.character.width, takeoff_x + self.character.width)
        jump_top = target_platform.top
        jump_bottom = current_platform.top

        # Проверяем пересечение с другими платформами
        for p in self.character.platforms:
            if p == current_platform or p == target_platform:
                continue
            
            horizontal_overlap = max(jump_left, p.left) < min(jump_right, p.right)
            vertical_overlap = max(jump_top, p.top) < min(jump_bottom, p.bottom)

            if horizontal_overlap and vertical_overlap:
                return False
        return True

    def can_reach_height(self, current_platform, target_platform):
        if target_platform.top >= current_platform.top:
            return True # Всегда можно спрыгнуть вниз или на тот же уровень
        
        height_diff = current_platform.top - target_platform.top
        return height_diff <= config.JUMP_HEIGHT 