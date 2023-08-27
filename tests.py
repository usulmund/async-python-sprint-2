"""Тесты работы задач"""
import unittest
import os.path

from job import Job
from job_types import (
    JobWithFiles,
    JobWithFS,
)

from settings_store import set_logging, clear_status_file


class AppTest(unittest.TestCase):
    """Класс с тестами"""
    def test_job_with_files_create_file(self):
        """Тест для проверки файловой задачи создания файла"""
        file_name = 'files_job_test_file.txt'
        create = Job(
            target=JobWithFiles().create_file,
            args=(file_name,),
            tries=3,
        )
        create.run()
        self.assertTrue(os.path.isfile(file_name))

    def test_job_with_files_write_file(self):
        """Тест для проверки файловой задачи записи в файл"""
        file_name = 'files_job_test_file.txt'
        data = 'data-data-data\n'
        write = Job(
            target=JobWithFiles().write_file,
            args=((file_name, data, 'w'),),
            tries=1,
        )
        write.run()

        with open(file_name) as file:
            text = file.read()
        self.assertEqual(data, text)

    def test_job_with_fs_create_file(self):
        """Тест для проверки ФС-задачи создания файла"""
        file_name = 'fs_job_file.txt'
        create_file_job = Job(
            target=JobWithFS().create_file,
            args=(file_name,)
        )
        create_file_job.run()
        self.assertTrue(os.path.isfile(file_name))

    def test_job_with_fs_create_dir(self):
        """Тест для проверки ФС-задачи создания директории"""
        dir_name = 'fs_job_TEST_DIR'
        create_dir_job = Job(
            target=JobWithFS().create_dir,
            args=(dir_name,)
        )
        create_dir_job.run()
        self.assertTrue(os.path.isdir(dir_name))

    def test_job_with_fs_delete(self):
        """Тест для проверки ФС-задачи удаления файла"""
        file = 'fs_job_file.txt'
        delete_job = Job(
            target=JobWithFS().delete,
            args=(file,)
        )
        delete_job.run()
        self.assertFalse(os.path.exists(file))


if __name__ == "__main__":
    set_logging()
    clear_status_file()
    unittest.main()
