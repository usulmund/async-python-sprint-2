"""Описание класса Job и вспомогательные функции"""
from typing import Callable, Any
from time import sleep, monotonic
from datetime import datetime
import types
from threading import current_thread
import logging

from settings_store import save_status


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
                logging.info(f'READ RESULT: {check_is_empty}')
            except StopIteration:
                save_status('read fail')
                logging.error(f'READ FAIL {arg}')
                break
            logging.info(f'READ SUCCESS {arg}')
            save_status('read success')

            for line in output:
                logging.info(f'READ RESULT: {line}')
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
    is_pause - на паузе,
    is_stop - принудительная остановка,
    is_end - задача завершена,
    is_successful - задача завершилась успешно."""
    def __init__(
            self,
            target: Callable, args: Any = None,
            start_at="", max_working_time: int = -1,
            tries: int = 1, dependencies=()):

        self.__args = args or ()
        self.__func = target
        self.__is_pause = False
        self.__is_stop = False
        try:
            self.__start_at = datetime.strptime(
                start_at,
                "%Y-%m-%d %H:%M:%S"
            )
        except (ValueError, TypeError):
            self.__start_at = datetime.now()
        self.__max_working_time = max_working_time
        self.__tries = tries

        self.__dependencies: tuple[Job] = dependencies

        self.is_successful = False
        self.is_end = False
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
        is_dependencies_successful = True
        is_dependencies_end = True
        for job in self.__dependencies:
            is_dependencies_successful &= job.is_successful
            is_dependencies_end &= job.is_end

        return is_dependencies_successful, is_dependencies_end

    def wait_start_time(self):
        """Метод для ожидания время запуска"""
        while datetime.now() < self.__start_at:
            sleep(0.01)

    def wait_dependencies(self):
        """Метод для ожидания выполенния задач-зависимостей.
        В случае фейла зависимостей перезапускает их.
        Возвращает статус успешности задач-зависимостей"""
        is_dependencies_successful, is_dependencies_end = self.check_deps()
        save_status(
            f'is dependencies successful = {is_dependencies_successful}\n'
            f'is dependencies ended = {is_dependencies_end}'
        )
        while not is_dependencies_end:
            sleep(0.1)
            is_dependencies_successful, is_dependencies_end = self.check_deps()

        if not is_dependencies_successful:
            save_status(f'{self.__dependencies} restart')
            for job in self.__dependencies:
                job.run()

        is_dependencies_successful, is_dependencies_end = self.check_deps()
        while not is_dependencies_end:
            sleep(0.1)
            is_dependencies_successful, is_dependencies_end = self.check_deps()
        return is_dependencies_successful

    def check_timout(self, start_time):
        """Метод, проверяющий выход за заданную границу времени"""
        if self.__max_working_time != -1:
            is_have_timeout = True
        else:
            is_have_timeout = False
        try:
            spend_time = monotonic() - start_time
        except TypeError:
            spend_time = 0

        limit = self.__max_working_time
        is_time_end = is_have_timeout and (spend_time > limit)
        return is_time_end

    def do_job(self):
        """Метод с учетом количества попыток выполняет основную задачу.
        В корутину отправлятся аргументы для выполения.
        В случае таймаута задача завершается.
        Сохраняется статус завершения и выполенности задачи"""
        num_of_tries = 0
        while num_of_tries < self.__tries and not self.is_successful:
            coroutine = catch_arg(self.__func)
            start_time = monotonic()
            coroutine.send(None)
            cur_thread = current_thread()

            num_of_tries += 1
            logging.info(
                f'{cur_thread} tries to get {self}: try {num_of_tries}.'
            )

            self.is_successful = True
            save_status(f'job is successful = {self.is_successful}')

            for arg in self.__args:
                while self.__is_pause:
                    save_status(f'job {self} on pause')
                    sleep(0.01)

                is_time_end = self.check_timout(start_time)
                if self.__is_stop or is_time_end:
                    save_status(f'job {self} is stop')
                    break

                try:
                    coroutine.send(arg)
                    self.is_successful &= True
                except StopIteration:
                    self.is_successful &= False
                    save_status(f'job {self} is fail')
                    logging.error(f'FAIL: {self}')

    def run(self):
        """Метод для запуска задачи.
        Ожидает время до запуска и успешное завершение задач зависимостей.
        В случае успеха-задач зависмостей запускает основную задачу"""
        self.wait_start_time()
        is_dependencies_successful = self.wait_dependencies()

        if not is_dependencies_successful:
            self.is_successful = False
            save_status(f'job {self} is fail')
            logging.error(f'FAIL: {self}')
        else:
            save_status(
                f'is dependencies successful = {is_dependencies_successful}'
            )
            self.do_job()
        self.is_end = True
        logging.info(f'END: {self}')
        save_status(f'END JOB: {self}')

    def pause(self, is_pause=True):
        """Метод, определяющий статус пауза"""
        self.__is_pause = is_pause

    def stop(self):
        """Метод, определяющий статус стоп"""
        self.__is_stop = True
