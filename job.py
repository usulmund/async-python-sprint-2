"""Описание класса Job и вспомогательные функции"""
from typing import Callable
from time import sleep, monotonic
from datetime import datetime
import types
from threading import current_thread
import logging

from settings_store import save_status
from data import Data

DATA_DIR = Data.data_dir
CITIES = Data.cities


def catch_arg(func: Callable):
    """Функция-корутина, принимает функцию, которая будет вызвана.
    Оператор yield отлавливает аргументы функции в виде значения
    либо кортежа в зависимости от количества параметров func.
    output является либо кортежем из статуса и кода завершения,
    либо генератором.
    В случае генератора проверяем его на непустоту попыткой next.
    В случае с кортежем проверяем код завершения"""
    while True:
        arg = yield
        if isinstance(arg, tuple):
            output = func(*arg)
        else:
            output = func(arg)

        if isinstance(output, types.GeneratorType):
            try:
                check_is_empty = next(output)
                print(check_is_empty)
            except StopIteration:
                save_status('read fail')
                logging.error(f"READ FAIL {arg}")
                break
            logging.info(f"READ SUCCESS {arg}")
            save_status('read success')

            for line in output:
                print(line, end='')
        else:
            save_status(output[0])

        if not isinstance(output, types.GeneratorType) and output[1] != 0:
            logging.error(f'FAIL: {func}')
            save_status('fail')
            break


class Job:
    """Описания класса, реализующего выполнение задачи.
    Аргументы: функция для выполенения,
    аргументы функции (можно задать пул аргументов
    для последовательного выполнения target с каждым аргументом),
    время запуска, таймаут работы, количество попыток запуска,
    зависимости от других задач.
    Дополнительные поля, описывающие состояние задачи:
    isPause - на паузе,
    isStop - принудительная остановка,
    isEnd - задача завершена,
    isSuccessful - задача завершилась успешно."""
    def __init__(
            self,
            target: Callable, args=None,
            start_at="", max_working_time=-1,
            tries=1, dependencies=[]):

        self.__args = args or ()
        self.__func = target
        self.__isPause = False
        self.__isStop = False
        try:
            if isinstance(start_at, str):
                self.__start_at = datetime.strptime(
                    start_at,
                    "%Y-%m-%d %H:%M:%S"
                )
            else:
                self.__start_at = start_at
        except ValueError:
            self.__start_at = datetime.now()
        self.__max_working_time = max_working_time
        self.__tries = tries

        self.__dependencies: list[Job] = dependencies

        self.isSuccessful = False
        self.isEnd = False
        save_status(
            f'\n[NEW JOB: {self}]\n'
            f'agrs = {self.__args}\n'
            f'start at {self.__start_at}\n'
            f'max working time = {self.__max_working_time}\n'
            f'tries = {self.__tries}\n'
            f'dependencies: {self.__dependencies}'
        )

    def check_deps(self):
        """Метод, вовзращающий статус задач-зависимостей:
        успешны и завершены"""
        isDependenciesSuccessful = True
        isDependenciesEnded = True
        for job in self.__dependencies:
            isDependenciesSuccessful &= job.isSuccessful
            isDependenciesEnded &= job.isEnd

        return isDependenciesSuccessful, isDependenciesEnded

    def wait_start_time(self):
        """Метод для ожидания время запуска"""
        while datetime.now() < self.__start_at:
            sleep(0.01)

    def wait_dependencies(self):
        """Метод для ожидания выполенния задач-зависимостей.
        В случае фейла зависимостей перезапускает их.
        Возвращает статус успешности задач-зависимостей"""
        isDependenciesSuccessful, isDependenciesEnded = self.check_deps()
        save_status(
            f'is dependencies successful = {isDependenciesSuccessful}\n'
            f'is dependencies ended = {isDependenciesEnded}'
        )
        while not isDependenciesEnded:
            sleep(0.1)
            isDependenciesSuccessful, isDependenciesEnded = self.check_deps()

        if not isDependenciesSuccessful:
            save_status(f'{self.__dependencies} restart')
            for job in self.__dependencies:
                job.run()

        isDependenciesSuccessful, isDependenciesEnded = self.check_deps()
        while not isDependenciesEnded:
            sleep(0.1)
            isDependenciesSuccessful, isDependenciesEnded = self.check_deps()
        return isDependenciesSuccessful

    def check_timout(self, start_time):
        """Метод, проверяющий выход за заданную границу времени"""
        if self.__max_working_time != -1:
            isHaveTimeout = True
        else:
            isHaveTimeout = False
        try:
            spend_time = monotonic() - start_time
        except TypeError:
            spend_time = 0

        limit = self.__max_working_time
        isTimeEnd = isHaveTimeout and (spend_time > limit)
        return isTimeEnd

    def run(self):
        """Метод для запуска задачи.
        Ожидает время до запуска и успешное завершение задач зависимостей.
        В случае успеха-задач зависмостей запускает основную задачу
        с учетом количества попыток.
        В корутину отправлятся аргументы для выполения.
        В случае таймаута задача завершается.
        Сохраняется статус завершения и выполенности задачи"""
        self.wait_start_time()
        isDependenciesSuccessful = self.wait_dependencies()

        if isDependenciesSuccessful:
            save_status(
                f'is dependencies successful = {isDependenciesSuccessful}'
            )
            num_of_tries = 0
            while num_of_tries < self.__tries and not self.isSuccessful:
                coroutine = catch_arg(self.__func)
                start_time = monotonic()
                coroutine.send(None)
                cur_thread = current_thread()

                num_of_tries += 1
                logging.info(
                    f'{cur_thread} tries to get {self}: try {num_of_tries}.'
                )

                self.isSuccessful = True
                save_status(f'job is successful = {self.isSuccessful}')

                for arg in self.__args:
                    while self.__isPause:
                        save_status(f'job {self} on pause')
                        sleep(0.01)

                    isTimeEnd = self.check_timout(start_time)
                    if self.__isStop or isTimeEnd:
                        save_status(f'job {self} is stop')
                        break

                    try:
                        coroutine.send(arg)
                        self.isSuccessful &= True
                    except StopIteration:
                        self.isSuccessful &= False
                        save_status(f'job {self} is fail')
                        logging.error(f'FAIL: {self}')
        else:
            self.isSuccessful = False
            save_status(f'job {self} is fail')
            logging.error(f'FAIL: {self}')

        self.isEnd = True
        logging.info(f'END: {self}')
        save_status(f'END JOB: {self}')

    def pause(self, isPause=True):
        """Метод, определяющий статус пауза"""
        self.__isPause = isPause

    def stop(self):
        """Метод, определяющий статус стоп"""
        self.__isStop = True
