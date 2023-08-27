"""Описание класса с данными"""
from pydantic import BaseModel


class Data(BaseModel):
    """Класс, хранящий констатные значания.
    Среди них:
    data_dir - директория для хранения данных json-анализатора,
    logging_file - файл для хранения логов,
    statuses_file - файл для хранения статусов задач,
    cities - набор данных для анализатора.
    """
    data_dir: str = 'cities_data_dir/'
    logging_file: str = 'app-log.log'
    status_file: str = 'STATUSES.txt'
    cities: dict = {
        "MOSCOW":
        "https://code.s3.yandex.net/async-module/moscow-response.json",
        "PARIS":
        "https://code.s3.yandex.net/async-module/paris-response.json",
        "LONDON":
        "https://code.s3.yandex.net/async-module/london-response.json",
        "BERLIN":
        "https://code.s3.yandex.net/async-module/berlin-response.json",
        "BEIJING":
        "https://code.s3.yandex.net/async-module/beijing-response.json",
        "KAZAN":
        "https://code.s3.yandex.net/async-module/kazan-response.json",
        "SPETERSBURG":
        "https://code.s3.yandex.net/async-module/spetersburg-response.json",
        "VOLGOGRAD":
        "https://code.s3.yandex.net/async-module/volgograd-response.json",
        "NOVOSIBIRSK":
        "https://code.s3.yandex.net/async-module/novosibirsk-response.json",
        "KALININGRAD":
        "https://code.s3.yandex.net/async-module/kaliningrad-response.json",
        "ABUDHABI":
        "https://code.s3.yandex.net/async-module/abudhabi-response.json",
        "WARSZAWA":
        "https://code.s3.yandex.net/async-module/warszawa-response.json",
        "BUCHAREST":
        "https://code.s3.yandex.net/async-module/bucharest-response.json",
        "ROMA":
        "https://code.s3.yandex.net/async-module/roma-response.json",
        "CAIRO":
        "https://code.s3.yandex.net/async-module/cairo-response.json",
        "GIZA":
        "https://code.s3.yandex.net/async-module/giza-response.json",
        "MADRID":
        "https://code.s3.yandex.net/async-module/madrid-response.json",
        "TORONTO":
        "https://code.s3.yandex.net/async-module/toronto-response.json",
    }
