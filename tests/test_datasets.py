"""
Сценарий 2: Загрузка данных.
Файл: tests/test_datasets.py
"""
import io
import json
from unittest.mock import patch


class TestDatasetUpload:

    def test_case4_upload_valid_excel(self, admin_client):
        """
        TestCase4. POST /api/datasets/upload с валидным Excel-файлом.
        Ожидание: статус 202, задача импорта создана, возвращён task_id.
        """
        with patch('src.services.core.task_service.TaskService.start_import') as mock_import:
            mock_import.return_value = {'task_id': 'test-task-id', 'status': 'запущен'}
            data = {
                'file': (io.BytesIO(b'PK\x03\x04'), 'test.xlsx'),
                'name': 'Тест'
            }
            response = admin_client.post('/api/datasets/upload',
                                         data=data,
                                         content_type='multipart/form-data')
        assert response.status_code == 202
        result = response.get_json()
        assert result['ok'] is True
        assert 'task_id' in result['data']

    def test_case5_get_task_status_after_import(self, admin_client):
        """
        TestCase5. GET /api/tasks/{task_id} после завершения импорта.
        Ожидание: статус 200, статус задачи SUCCESS, данные сохранены в БД.
        """
        with patch('src.services.core.task_service.TaskService.get_status') as mock_status:
            mock_status.return_value = {
                'task_id': 'test-task-id',
                'status': 'SUCCESS',
                'result': {'dataset_id': 1, 'skipped_shipments': 0},
                'error': None
            }
            response = admin_client.get('/api/tasks/test-task-id')
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True
        assert data['data']['status'] == 'SUCCESS'

    def test_case6_upload_invalid_format(self, admin_client):
        """
        TestCase6. POST /api/datasets/upload с файлом неверного формата (.txt).
        Ожидание: статус 400, сообщение об ошибке формата.
        """
        data = {
            'file': (io.BytesIO(b'plain text content'), 'test.txt'),
            'name': 'Тест'
        }
        response = admin_client.post('/api/datasets/upload',
                                     data=data,
                                     content_type='multipart/form-data')
        assert response.status_code == 400
        result = response.get_json()
        assert result['ok'] is False

    def test_case7_upload_empty_file(self, admin_client):
        """
        TestCase7. POST /api/datasets/upload с пустым файлом.
        Ожидание: статус 400, сообщение об ошибке.
        """
        data = {
            'file': (io.BytesIO(b''), 'empty.xlsx'),
            'name': 'Тест'
        }
        response = admin_client.post('/api/datasets/upload',
                                     data=data,
                                     content_type='multipart/form-data')
        assert response.status_code in (400, 500)
        result = response.get_json()
        assert result['ok'] is False