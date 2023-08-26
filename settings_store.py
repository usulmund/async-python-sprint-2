"""Функции для настройки логировани и сохранения статусов"""
import logging

from data import Data

STATUS_FILE = Data.status_file


def set_logging():
    """Устанавливает настройки логирования"""
    logging.basicConfig(
        level=logging.DEBUG,
        filename=Data.logging_file,
        filemode='w',
        format='%(asctime)s: %(name)s - %(levelname)s - %(message)s'
    )


def clear_status_file():
    """Очищает хранилище статусов и пишет в него хэдер"""
    with open(STATUS_FILE, 'w') as file:
        file.write('\t\t____STATUSES____\t\t')


def save_status(status: str):
    """Сохраняет заданный статус в файл"""
    with open(STATUS_FILE, 'a') as file:
        file.write(f'{status}\n')
