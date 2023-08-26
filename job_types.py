"""Описание классов для разных видов задач и вспомогательные функции.
Методы классов возвращают коретж из статуса и кода завершения"""
import os.path
import os
import subprocess
from http import HTTPStatus
from urllib.request import urlopen
from urllib.error import URLError
import logging
import json
import ssl

from settings_store import save_status
from data import Data


ssl._create_default_https_context = ssl._create_unverified_context


def run_command(command: str):
    """Запуск терминальных команд
    с помощью модуля subprocess"""
    command_list = command.split()
    with subprocess.Popen(
        command_list,
        stdout=subprocess.PIPE,
        universal_newlines=True,
    ) as process:
        output, _ = process.communicate()
        ret_code = process.returncode
    return output, ret_code


def analyze_json(resp_body: dict):
    """Функция, возвращающая название города и страны,
    извлеченные из json-файла"""
    try:
        city_name = resp_body['geo_object']['locality']['name']
    except KeyError:
        city_name = None
    try:
        country_name = resp_body['geo_object']['country']['name']
    except KeyError:
        country_name = None
    return city_name, country_name


class JobPrototype:
    """Прототип типитизированной задачи,
    хранящий статус и код"""
    def __init__(self):
        self.output = 'success'
        self.ret_code = 0


class JobWithFS(JobPrototype):
    """Описание класса для задач
    с файловой системой"""
    def create_file(self, filename: str):
        """Функция создания файла с помощью терминальной
        команды touch.
        Обрабатывает ситуацию уже существующего
        объекта с таким именем"""
        save_status('create file job is started')
        logging.info('create file')
        if os.path.exists(filename):
            self.output = f'CREATE FILE: {filename} is already exist'
            self.ret_code = 1
        else:
            self.output, self.ret_code = run_command(f'touch {filename}')
            super().__init__()
        return (self.output, self.ret_code)

    def create_dir(self, dirname: str):
        """Функция создания директории с помощью
        терминальной команды mkdir.
        Обрабатывает ситуацию уже существующего
        объекта с таким именем"""
        save_status('create dir job is started')
        logging.info('create dir')
        if os.path.exists(dirname):
            self.output = f'CREATE DIR: {dirname} is already exist'
            self.ret_code = 1
        else:
            self.output, self.ret_code = run_command(f'mkdir {dirname}')
            super().__init__()
        return (self.output, self.ret_code)

    def delete(self, name: str):
        """Функция удаления как файла, так и директории
        с помощью терминальной команды rm -rf.
        Обрабатывает ситуация отсутствия объекта
        с таким именем"""
        save_status('delete job is started')
        logging.info('delete file or dir')
        if os.path.exists(name):
            self.output, self.ret_code = run_command(f'rm -rf {name}')
            super().__init__()
        else:
            self.output = f'DELETE: {name} is not exist'
            self.ret_code = 1
        return (self.output, self.ret_code)

    def change_dir(self, dir_name: str, command: str):
        """Функция изменения директории и выполнения
        в ней указанной команды.
        Обрабатывает ситуацию отсутствия директории
        с таким именем"""
        save_status('change dir job is started')
        logging.info('change dir')
        command_list = command.split()
        if os.path.isdir(dir_name):
            with subprocess.Popen(
                command_list,
                cwd=dir_name,
                shell=True
            ) as process:
                self.output, _ = process.communicate()
                self.ret_code = process.returncode
            super().__init__()

        else:
            self.output = f'CHANGE: {dir_name} is not exist'
            self.ret_code = 1
        return (self.output, self.ret_code)


class JobWithFiles(JobPrototype):
    """Описание класса для задач с файлами"""
    def create_file(self, filename: str):
        """Функция создания файла с помощью инструментов Python.
        Обрабатывает ситуацию уже существующего
        объекта с таким именем"""
        save_status('create file job is started')
        logging.info('create file')
        if os.path.exists(filename):
            self.output = 'CREATE: file is already exist'
            self.ret_code = 1
        else:
            with open(filename, 'w') as _:
                logging.info(f'CREATE: {filename} is done')
            super().__init__()
        return (self.output, self.ret_code)

    def delete_file(self, filename: str):
        """Функция удаления файла с помощью инструментов Python.
        Обрабатывает ситуацию отстутствия
        файла с таким именем"""
        save_status('delete file job is started')
        logging.info('delete file')
        if os.path.isfile(filename):
            os.remove(filename)
            super().__init__()
        else:
            self.output = 'DELETE: file is not exist'
            self.ret_code = 1
        return (self.output, self.ret_code)

    def read_file(self, filename: str):
        """Функция-генератор чтения файла.
        Обрабатывает ситуацию отсутствия файла
        с таким имененем читаемого формата"""
        save_status('read file job is started')
        logging.info('read file')
        super().__init__()
        if os.path.isfile(filename):

            try:
                with open(filename) as file:
                    for row in file:
                        yield row
            except UnicodeDecodeError:
                self.output = 'READ: format file error'
                self.ret_code = 1
        else:
            self.output = 'READ: file is not exist'
            self.ret_code = 1
        return (self.output, self.ret_code)

    def write_file(self, filename: str, data: str, mode: str):
        """Функция записи в файл. Обрабатывает ошибку
        попытки записи в директорию"""
        save_status('write file job is started')
        logging.info('write file')
        super().__init__()
        try:
            with open(filename, mode) as file:
                file.write(data)
        except IsADirectoryError:
            self.output = 'WRITE: error'
            self.ret_code = 1
        return (self.output, self.ret_code)


class JobWithNet(JobPrototype):
    """Описание класса для задач с сетью"""
    def read_url(self, url: str):
        """Функция для получения данных по URL.
        В качестве примера анализатора данных
        используется фунция analyze_json.
        Обработанные данные записываются в файл"""
        save_status('read url job is started')
        data_dir = Data.data_dir

        if not os.path.exists(data_dir):
            data_dir = ''

        logging.info(f'read url {url}')
        super().__init__()

        try:
            with urlopen(url) as response:
                resp_body = response.read().decode('utf-8')
            resp_body_json = json.loads(resp_body)

            if response.status != HTTPStatus.OK:
                self.output = f'error during execute request. ' \
                    f'{resp_body.status}: {resp_body.reason}'
                self.ret_code = 1

            output = analyze_json(resp_body_json)
            city = output[0].upper()
            with open(f'{data_dir}{city}_data.txt', 'w') as output_file:
                output_file.write(f'{output[1]}\n')
        except (URLError, TypeError,
                json.decoder.JSONDecodeError, AttributeError):
            self.output = 'error'
            self.ret_code = 1
        return (self.output, self.ret_code)
