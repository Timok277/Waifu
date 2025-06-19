import logging
import sys
from screeninfo import get_monitors

import config
from ..platform import Platform
from ..utils import get_desktop_windows

# Зависимости для Windows-специфичных функций
try:
    import win32gui
    import pywintypes
    IS_WIN = sys.platform.startswith('win')
except ImportError:
    IS_WIN = False


class PlatformManager:
    """Управляет обнаружением и обновлением платформ (окон и мониторов)."""

    def __init__(self, character, hwnd):
        self.character = character
        self.hwnd = hwnd
        self.platforms = []
        self.monitors = []
        self.update_timer = 0
        self.update() # Первоначальное сканирование

    def update(self, delta_time=0):
        """Периодически обновляет список платформ."""
        self.update_timer += delta_time
        if self.update_timer > (config.PLATFORM_UPDATE_INTERVAL * 1000):
            self.scan_platforms()
            self.update_timer = 0

    def scan_platforms(self):
        """Сканирует окна и мониторы, чтобы создать платформы."""
        if not IS_WIN: return
        self.monitors = get_monitors()
        
        window_rects = get_desktop_windows()
        new_platforms = []
        
        for w_rect in window_rects:
            left, top, right, bottom = w_rect
            if (right - left) > 150 and (bottom - top) > 50:
                try:
                    if self.hwnd == win32gui.WindowFromPoint((left, top)):
                        continue
                except pywintypes.error:
                    pass 
                
                new_platform = Platform(left, top, right, top + 2)
                if new_platform not in new_platforms:
                    new_platforms.append(new_platform)

        for m in self.monitors:
            new_platform = Platform(m.x, m.y + m.height, m.x + m.width, m.y + m.height + 2)
            if new_platform not in new_platforms:
                new_platforms.append(new_platform)
                
        self.platforms = new_platforms 
        self.character.update_platforms_list(self.platforms)
        if config.DEBUG_LOGGING:
            logging.info(f"Обновлены платформы ({len(self.platforms)} шт).")

    def check_teleport_conditions(self):
        """Проверяет, не упал ли персонаж за пределы экрана."""
        if not self.monitors: return
        max_y = max(m.y + m.height for m in self.monitors)
        
        if self.character.y > max_y + 200:
            logging.warning("Персонаж упал за пределы экрана! Телепортация.")
            primary = next((m for m in self.monitors if m.is_primary), self.monitors[0])
            self.character.teleport(primary.x + primary.width / 2, primary.y + primary.height / 2) 