import logging
import random
import math

import config

class AIController:
    """Управляет принятием решений и поведением персонажа."""

    def __init__(self, character, platforms):
        self.character = character
        self.physics = character.physics
        self.platforms = platforms
        self.ai_timer = 0
        self.target_x = None
        self.pending_jump_platform = None
        self.pending_jump_x = None

    def update(self, delta_time):
        """Обновляет состояние AI."""
        self.ai_timer += delta_time
        
        if self.physics.on_ground and self.target_x is None and self.pending_jump_platform is None:
            if self.ai_timer > (config.AI_UPDATE_INTERVAL * 1000):
                self.choose_new_action()
                self.ai_timer = 0
        
        if self.target_x is not None:
            self.character.set_state("walk")
            move_direction = 1 if self.target_x > self.physics.x else -1
            self.physics.dx = config.WALK_SPEED * move_direction
            
            if abs(self.target_x - self.physics.x) < config.WALK_SPEED:
                self.physics.x = self.target_x
                self.target_x = None
                self.physics.dx = 0
                if self.pending_jump_platform:
                    self.jump_to_platform(self.pending_jump_platform, self.pending_jump_x)
                else:
                    self.character.set_state("idle")
        elif self.physics.on_ground:
            self.physics.dx = 0
            self.character.set_state("idle")
    
    def reset_target(self):
        """Сбрасывает текущую цель AI."""
        self.ai_timer = 0
        self.target_x = None
        self.pending_jump_platform = None

    def choose_new_action(self):
        # ... (логика выбора действия)
        if not self.physics.on_ground or not self.physics.current_platform:
            return

        current_platform = self.physics.current_platform
        other_platforms = [
            p for p in self.platforms
            if p != current_platform and p.top > 0
        ]

        possible_jumps = self.evaluate_jumps(current_platform, other_platforms)

        if possible_jumps and random.random() < config.JUMP_CHANCE:
            possible_jumps.sort(key=lambda j: j[0])
            best_jump = possible_jumps[0]
            _, target_platform, landing_x, takeoff_x = best_jump

            if config.DEBUG_LOGGING:
                logging.info(f"Решил прыгнуть с x={takeoff_x:.0f} на платформу Y={target_platform.top} в точку x={landing_x:.0f}")

            if abs(self.physics.x - takeoff_x) > 5:
                self.target_x = takeoff_x
                self.pending_jump_platform = target_platform
                self.pending_jump_x = landing_x
            else:
                self.jump_to_platform(target_platform, landing_x)
        else:
            self.walk_on_platform(current_platform)

    def evaluate_jumps(self, current_platform, other_platforms):
        # ... (логика оценки прыжков)
        possible_jumps = []
        for _ in range(config.AI_JUMP_CANDIDATES):
            if not other_platforms: break
            
            target_platform = random.choice(other_platforms)
            landing_x = random.uniform(target_platform.left, target_platform.right - self.character.width)
            
            is_jumping_down = target_platform.top > current_platform.top

            path_is_clear = self.is_jump_path_clear(current_platform, target_platform)
            can_reach_height = is_jumping_down or (current_platform.top - target_platform.top) <= config.JUMP_HEIGHT

            if path_is_clear and can_reach_height:
                takeoff_x = max(current_platform.left, min(landing_x, current_platform.right - self.character.width))
                walk_distance = abs(self.physics.x - takeoff_x)
                possible_jumps.append((walk_distance, target_platform, landing_x, takeoff_x))
        return possible_jumps
    
    def is_jump_path_clear(self, current_platform, target_platform):
        """Проверяет, свободен ли путь для прыжка."""
        jump_left = min(self.physics.x, target_platform.left)
        jump_right = max(self.physics.x + self.character.width, target_platform.right)
        jump_top = target_platform.top
        jump_bottom = current_platform.top

        for p in self.platforms:
            if p == current_platform or p == target_platform:
                continue
            
            horizontal_overlap = max(jump_left, p.left) < min(jump_right, p.right)
            vertical_overlap = max(jump_top, p.top) < min(jump_bottom, p.bottom)

            if horizontal_overlap and vertical_overlap:
                return False
        return True

    def walk_on_platform(self, current_platform):
        """Выбирает случайную точку для прогулки на текущей платформе."""
        if current_platform.width > self.character.width * 1.5:
            min_walk = max(current_platform.left, self.physics.x - config.MAX_WALK_DISTANCE)
            max_walk = min(current_platform.right - self.character.width, self.physics.x + config.MAX_WALK_DISTANCE)
            if max_walk > min_walk:
                self.target_x = random.uniform(min_walk, max_walk)
                if config.DEBUG_LOGGING:
                    logging.info(f"Решил прогуляться по текущей платформе до x={self.target_x:.0f}")

    def jump_to_platform(self, target_platform, target_x):
        # ... (логика расчета и выполнения прыжка)
        if not self.physics.on_ground: return
        
        platform_to_jump_from = self.physics.current_platform
        self.pending_jump_platform = None
        self.pending_jump_x = None
        self.character.set_state("walk")

        optimal_landing_x = max(target_platform.left, min(target_x, target_platform.right - self.character.width))
        
        delta_x = optimal_landing_x - self.physics.x
        delta_y = (target_platform.top - self.character.height) - self.physics.y
        gravity = self.character.jump_gravity

        vy0 = 0
        time_to_target = 0

        if delta_y <= 0: # Прыжок вверх
            vy0 = -self.character.jump_velocity
            discriminant = vy0**2 + 2 * gravity * delta_y
            if discriminant < 0: return
            time_to_target = (-vy0 + math.sqrt(discriminant)) / gravity
        else: # Прыжок вниз
            if gravity > 0: time_to_target = math.sqrt(2 * delta_y / gravity)
        
        if time_to_target <= 0: return

        self.physics.dx = delta_x / time_to_target
        self.physics.dy = vy0 if delta_y <= 0 else 0
        self.physics.gravity_override = gravity
        self.physics.on_ground = False
        self.physics.platform_to_ignore = platform_to_jump_from
        self.physics.platform_to_jump_to = target_platform
        
        if config.DEBUG_LOGGING:
            logging.info(f"Прыгаю к ({optimal_landing_x:.0f}, {target_platform.top:.0f})! V=({self.physics.dx:.2f}, {self.physics.dy:.2f}), T~={time_to_target:.0f} кадров") 