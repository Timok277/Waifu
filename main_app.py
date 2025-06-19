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
from waifu.utils import check_for_updates, check_server_availability, ServerLogHandler

def main(client_id):
    """Основная функция приложения."""
    logging.info(f"Приложение запущено. Версия {config.VERSION}. Client ID: {client_id}")
    
    if not os.path.exists("assets"):
        logging.critical("Папка 'assets' не найдена! Запуск невозможен.")
        if IS_WIN:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, "Папка 'assets' не найдена!\n\nПрограмма не может запуститься без своих ресурсов.\nУбедитесь, что 'assets' находится рядом с .exe файлом.", "Waifu Error", 0x10)
        sys.exit(1)

    check_for_updates()
    
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
    except Exception as e:
        logging.critical(f"Не удалось инициализировать персонажа: {e}", exc_info=True)
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
    log_file_path = "app.log"
    client_id = str(uuid.uuid4())[:8]

    # --- Настройка логирования ---
    # Создаем файловый обработчик, который будет ловить ВСЕ сообщения
    file_handler = logging.FileHandler(log_file_path, mode='w', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG) # Ловим все, от DEBUG и выше
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Настраиваем базовую конфигурацию логирования, которая будет использовать наш файловый обработчик
    logging.basicConfig(
        level=logging.DEBUG, # Устанавливаем самый низкий уровень, чтобы всё шло в обработчики
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[file_handler] # Передаем сюда файловый обработчик
    )

    # Добавляем обработчик для отправки логов на сервер, если включено
    if config.ENABLE_LOGGING_TO_SERVER:
        try:
            server_handler = ServerLogHandler(client_id=client_id)
            server_handler.setLevel(logging.INFO) # На сервер шлем только INFO и выше
            logging.getLogger().addHandler(server_handler)
        except Exception as e:
            logging.error(f"Не удалось создать обработчик логов для сервера: {e}")
    
    try:
        main(client_id=client_id)
    except Exception as e:
        # Это глобальный перехватчик на случай, если что-то пойдет не так до основного цикла
        logging.critical("Критическая неперехваченная ошибка в приложении:", exc_info=True)
        if IS_WIN:
            import ctypes
            # Формируем сообщение для пользователя
            error_message = f"Произошла критическая ошибка:\n\n{e}\n\nПожалуйста, проверьте файл app.log для получения полной информации."
            ctypes.windll.user32.MessageBoxW(0, error_message, "Waifu Error", 0x10 | 0x40000) # MB_ICONERROR | MB_TOPMOST
        sys.exit(1)

