# -*- coding: utf-8 -*-

import pygame
import sys
import os
import logging
import config
import traceback
import uuid

try:
    import win32gui
    import win32con
    import win32api
    IS_WIN = sys.platform.startswith('win')
except ImportError:
    IS_WIN = False

from waifu.character import WaifuCharacter
from waifu.utils import check_for_updates, check_server_availability, LogstashHttpHandler

def main():
    """Основная функция приложения."""
    if not os.path.exists("assets"):
        logging.critical("Папка 'assets' не найдена! Запуск невозможен.")
        sys.exit(1)
    
    # Настройка логирования
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    client_id = str(uuid.uuid4())[:8]

    # Добавляем обработчик для отправки логов на сервер
    http_handler = LogstashHttpHandler(
        config.SERVER_URL, 
        client_id=client_id
    )
    logging.getLogger().addHandler(http_handler)

    check_for_updates()
    logging.info(f"Приложение запущено. Client ID: {client_id}")
    if not check_server_availability():
        logging.warning("Работа будет продолжена без отправки данных на сервер.")

    pygame.init()

    # --- Настройка окна Pygame ---
    screen = pygame.display.set_mode((config.SPRITE_WIDTH, config.SPRITE_HEIGHT), pygame.NOFRAME)
    TRANSPARENCY_COLOR = (255, 0, 255) # Magenta, используется как ключ прозрачности
    
    hwnd = None
    if IS_WIN:
        try:
            hwnd = pygame.display.get_wm_info()["window"]
            # Установка стилей окна: прозрачное, поверх всех окон, без иконки в таскбаре
            ex_style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            ex_style |= win32con.WS_EX_LAYERED | win32con.WS_EX_TOOLWINDOW
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, ex_style)
            
            win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*TRANSPARENCY_COLOR), 0, win32con.LWA_COLORKEY)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
        except Exception as e:
            logging.error(f"Не удалось настроить окно для Windows: {e}")

    try:
        character = WaifuCharacter(hwnd)
    except RuntimeError as e:
        logging.critical(str(e))
        pygame.quit()
        sys.exit(1)

    clock = pygame.time.Clock()
    running = True

    try:
        while running:
            delta_time = clock.tick(config.FPS)
            # --- Обработка событий ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                character.handle_event(event)

            # --- Обновление и отрисовка ---
            character.update(delta_time)
            
            screen.fill(TRANSPARENCY_COLOR)
            character.draw(screen)
            pygame.display.update()

            # Перемещение окна вслед за персонажем
            if IS_WIN and hwnd:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, int(character.x), int(character.y), 0, 0, win32con.SWP_NOSIZE)
    except KeyboardInterrupt:
        logging.info("Получено прерывание с клавиатуры (Ctrl+C). Завершение работы...")
        
    logging.info("Приложение Desktop Waifu завершило работу.")
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()

