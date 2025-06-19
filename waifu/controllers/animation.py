import pygame
import logging
import config

class AnimationController:
    """Управляет загрузкой, выбором и отображением спрайтов."""

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.sprites = {}
        self.load_sprites()
        if not self.sprites:
            raise RuntimeError("Критическая ошибка: не удалось загрузить спрайты.")
        
        self.image_list = self.sprites['idle']['right'] # Default
        self.current_sprite_index = 0
        self.animation_timer = 0

    def load_sprites(self):
        """Загружает и масштабирует все спрайты из конфига."""
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
        """Создает словарь с кадрами для левого и правого направления."""
        return {
            "right": list(surfaces),
            "left": [pygame.transform.flip(s, True, False) for s in surfaces]
        }

    def update(self, delta_time, state, facing_direction):
        """Обновляет текущий кадр анимации."""
        self.image_list = self.sprites[state][facing_direction]
        self.animation_timer += delta_time
        if self.animation_timer > config.ANIMATION_INTERVAL:
            self.animation_timer = 0
            self.current_sprite_index = (self.current_sprite_index + 1) % len(self.image_list)
    
    def get_current_sprite(self):
        """Возвращает текущий спрайт для отрисовки."""
        return self.image_list[self.current_sprite_index] 