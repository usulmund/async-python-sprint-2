"""Пример использования задач и планировщика"""
from datetime import datetime, timedelta
from random import uniform
import logging
from typing import Iterable


from job import Job
from job_types import (
    JobWithFS,
    JobWithFiles,
    JobWithNet,

)
from scheduler import Scheduler
from settings_store import clear_status_file
from data import Data

data = Data()
DATA_DIR = data.data_dir
CITIES = data.cities


"""

Если вы запускаете под MacOS и у вас выдает ошибку,
запустите проект в Docker.

* Сборка в ручном режиме, чтобы проверить,
какие файлы создались:
docker build -t async2 . --build-arg arg=manual

* Сборка контейнера с тестированием:
docker build -t async2 . --build-arg arg=test

* Сборка контейнера с запуском примера использования:
docker build -t async2 . --build-arg arg=example

* Старт контейнера:
docker run -it async2

* В ручном режиме:
python3 tests.py
python3 using_example.py

"""


def read_data_from_file():
    """Заключительный этап конвейера: считываем результаты
    из файла и выводим их в консоль"""
    job_with_files = JobWithFiles()
    try:
        while True:
            data_chunk = (yield)

            read_file_job = Job(
                target=job_with_files.read_file,
                args=(f'{DATA_DIR}{data_chunk}_data.txt',),
                tries=3,
            )
            read_file_job.run()
    except GeneratorExit:
        logging.info('all data is read')


def get_data_and_analyze():
    """Третий этап конвейера: получаем данные по URL
    и заносим их в файл"""
    coro = read_data_from_file()
    coro.send(None)
    job_with_net = JobWithNet()
    try:
        while True:
            data_chunck = (yield)
            read_url_job = Job(
                target=job_with_net.read_url,
                args=(CITIES[data_chunck],)
            )
            read_url_job.run()
            coro.send(data_chunck)
    except GeneratorExit:
        logging.info('all data is ready')


def create_file():
    """Второй этап конвеера: на основе полученных данных
    создаются задачи для создания директории и выходных файлов"""
    coro = get_data_and_analyze()
    coro.send(None)

    job_with_fs = JobWithFS()
    create_dir_job = Job(
        target=job_with_fs.create_dir,
        args=(DATA_DIR,),
        tries=2
    )
    create_dir_job.run()

    try:
        while True:
            data_chunk = (yield)
            create_file_job = Job(
                target=job_with_fs.create_file,
                args=(f'{DATA_DIR}/{data_chunk}_data.txt',),
                dependencies=(create_dir_job,),
            )
            create_file_job.run()

            coro.send(data_chunk)
    except GeneratorExit:
        logging.info('all files are created')


def sent_data_to_pipeline(data: Iterable):
    """Входная точка в конвейер: отправляет данные,
    на основе которых будут формироваться URL-запросы
    и выходные файлы"""
    coro = create_file()
    coro.send(None)

    for data_chunck in data:
        logging.debug(f'sent_data_to_pipeline: {data_chunck}')
        coro.send(data_chunck)
    coro.close()
    return ('success', 0)


def run_jobs_with_fs():
    """Работа с файловой системой:
    создается директория и файлы внутри нее,
    просматривается содержимое директории, удаляется один файл.
    Задачи зависимы друг от друга.
    Первая задача запустится с задержкой в 5 секунд"""
    dir_name = 'NEW_DIR'
    file_name_1 = f'{dir_name}/some_file.txt'
    file_name_2 = f'{dir_name}/other_file.txt'
    file_name_3 = f'{dir_name}/file_for_delete.txt'
    job_with_fs = JobWithFS()

    create_dir_job = Job(
        target=job_with_fs.create_dir,
        args=(dir_name,),
        start_at=datetime.now() + timedelta(seconds=5),
        tries=2
    )
    create_dir_job.run()

    create_file_job = Job(
        target=job_with_fs.create_file,
        args=(file_name_1, file_name_2, file_name_3),
        dependencies=(create_dir_job,),
    )
    create_file_job.run()

    change_dir_job = Job(
        target=job_with_fs.change_dir,
        args=((dir_name, 'ls'),),
        max_working_time=uniform(0, 3),
        tries=3,
        dependencies=(create_dir_job,),
    )
    change_dir_job.run()

    delete_job = Job(
        target=job_with_fs.delete,
        args=(file_name_3,),
        dependencies=(create_dir_job, create_file_job,),
    )
    delete_job.run()


def run_jobs_with_files():
    """Работа с файлами:
    создается файл, в него записываются данные,
    которые затем считываются.
    С задержкой в 5 секунд файл удаляется"""
    file_name = 'new_file.txt'
    data = 'you see this text because create-, ' \
        'write- and read-jobs are succesfull.\n'

    job_with_files = JobWithFiles()
    create = Job(
        target=job_with_files.create_file,
        args=(file_name, ),
        tries=3,
    )
    create.run()

    write = Job(
        target=job_with_files.write_file,
        args=((file_name, data, 'w'),),
        tries=1,
        dependencies=(create,),
    )
    write.run()

    read = Job(
        target=job_with_files.read_file,
        args=(file_name,),
        dependencies=(create, write,),
    )
    read.run()

    delete_file_job = Job(
        target=job_with_files.delete_file,
        args=(file_name,),
        tries=3,
        start_at=datetime.now() + timedelta(seconds=5),
        dependencies=(create,),
    )
    delete_file_job.run()


def run_instruction(scheduler: Scheduler):
    """Пример инструкций для планировщика:
    запуск, рестарт, стоп"""
    scheduler.run()
    scheduler.restart()
    scheduler.stop()


def run_scheduler():
    """Запуск планировщика:
    создается объект планировщика,
    в который добавляются задачи."""
    scheduler = Scheduler(pool_size=5)

    try:
        while True:
            job = (yield)
            logging.info(f'add job {job}')
            scheduler.schedule(job)
    except GeneratorExit:
        run_instruction(scheduler)


def run_scheduler_test():
    """Пример организации задач в планировщике:
    создание файла,
    запись в файл,
    чтение файла,
    запуск конвейра с обработкой URL."""
    file_name = 'test_scheduler.txt'
    data = 'you see this text because scheduler worked succesfully.'

    scheduler = run_scheduler()
    scheduler.send(None)

    create = Job(
        target=JobWithFS().create_file,
        args=(file_name,),
        tries=3,
    )
    scheduler.send(create)

    write = Job(
        target=JobWithFiles().write_file,
        args=((file_name, data, 'w'),),
        tries=1,
        dependencies=(create,),
    )
    scheduler.send(write)

    read = Job(
        target=JobWithFiles().read_file,
        args=(file_name,),
        dependencies=(create, write),
        start_at=datetime.now() + timedelta(seconds=10),
    )
    scheduler.send(read)

    data = list(CITIES)
    pipeline = Job(
        target=sent_data_to_pipeline,
        args=(data,)
    )
    scheduler.send(pipeline)

    scheduler.close()


if __name__ == '__main__':
    clear_status_file()
    run_jobs_with_files()
    run_jobs_with_fs()
    run_scheduler_test()
