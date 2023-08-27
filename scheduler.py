"""Описание класса Scheduler"""
from queue import Queue
from threading import Thread
import queue
from time import sleep
import logging

from job import Job
from settings_store import set_logging, clear_status_file, save_status

set_logging()
clear_status_file()


class Scheduler:
    """Класс принимает аргументом
    количество одновременно выполняющихся задач.
    Дополнительные поля:
    очередь задач, потоки, статусы стоп и рестарт"""
    def __init__(self, pool_size: int = 10):

        self.__pool_size = pool_size
        self.__jobs_queue: Queue = Queue()
        self.__threads: list[Thread] = []
        self.__isStop = False
        self.__isRestart = False
        save_status(
            f'\n[NEW SCHEDULER: {self}]\n'
            f'pool size = {self.__pool_size}\n'
        )

    def schedule(self, job: Job):
        """Метод добавляет задачу в очередь"""
        self.__jobs_queue.put(job)
        save_status(f'add job {job} to scheduler {self}')

    def __get_job_from_queue(self):
        """Пока не получена команда остановиться
        и не опустела очередь задач метод
        запускает задачи, все время проверяя состояние
        статусов стоп и рестарт.
        В случае рестарта перезапускается последняя выполененная задача
        и выполнение продолжается"""
        while not self.__isStop:
            try:
                job = self.__jobs_queue.get(timeout=2)
                job.run()
                save_status(f'scheduler {self} run job {job}')

                if not self.__isRestart:
                    sleep(3)
                if self.__isRestart:
                    logging.info(f'restart {job}')
                    save_status(f'scheduler {self} restart job {job}')
                    job.run()
                    self.__isRestart = False

                if not self.__isStop:
                    sleep(3)
                if self.__isStop:
                    logging.info(f'stoped after {job}')
                    save_status('scheduler {self} stop job {job}')

            except queue.Empty:
                save_status('jobs queue is empty')
                break

    def run(self):
        """Метод запуска планировщика.
        Создается и запускается пул потоков,
        которые разбирают задачи из очереди"""
        for _ in range(self.__pool_size):
            thread = Thread(target=self.__get_job_from_queue)

            self.__threads.append(thread)
        for thread in self.__threads:
            thread.start()

    def restart(self):
        """Метод меняющий статус планировщика на рестарт"""
        self.__isRestart = True

    def stop(self):
        """Метод меняющий статус планировщика на стоп"""
        self.__isStop = True
