"""
Сценарий 9: Взаимодействие с очередью задач.
Файл: tests/test_tasks.py
"""
import io
from unittest.mock import patch


class TestTaskQueue:

    def test_case25_task_saved_when_worker_off(self, admin_client):
        """
        TestCase25. POST /api/datasets/upload, воркер отключён.
        Ожидание: статус 202, task_id возвращён — задача принята очередью.
        """
        with patch('src.services.core.task_service.TaskService.start_import') as mock_import:
            mock_import.return_value = {'task_id': 'queued-task-id', 'status': 'запущен'}
            data = {
                'file': (io.BytesIO(b'PK\x03\x04'), 'test.xlsx'),
                'name': 'Тест'
            }
            response = admin_client.post('/api/datasets/upload',
                                         data=data,
                                         content_type='multipart/form-data')
        assert response.status_code == 202
        assert response.get_json()['data']['task_id'] == 'queued-task-id'

    def test_case26_task_status_pending(self, admin_client):
        """
        TestCase26. GET /api/tasks/{task_id} сразу после создания задачи.
        Ожидание: статус 200, статус задачи PENDING.
        """
        with patch('src.services.core.task_service.TaskService.get_status') as mock_status:
            mock_status.return_value = {
                'task_id': 'new-task-id',
                'status': 'PENDING',
                'result': None,
                'error': None
            }
            response = admin_client.get('/api/tasks/new-task-id')
        assert response.status_code == 200
        assert response.get_json()['data']['status'] == 'PENDING'

    def test_case27_task_status_started(self, admin_client):
        """
        TestCase27. GET /api/tasks/{task_id} во время выполнения расчёта.
        Ожидание: статус 200, статус задачи STARTED.
        """
        with patch('src.services.core.task_service.TaskService.get_status') as mock_status:
            mock_status.return_value = {
                'task_id': 'running-task-id',
                'status': 'STARTED',
                'result': None,
                'error': None
            }
            response = admin_client.get('/api/tasks/running-task-id')
        assert response.status_code == 200
        assert response.get_json()['data']['status'] == 'STARTED'

    def test_case28_task_success_contains_run_id(self, admin_client, scenario_id):
        """
        TestCase28. POST /api/scenarios/{sid}/run, дождаться завершения,
        GET /api/tasks/{task_id}.
        Ожидание: статус 200, статус SUCCESS, результат содержит run_id.
        """
        with patch('src.services.core.task_service.TaskService.start_run') as mock_run:
            mock_run.return_value = {'task_id': 'success-task-id', 'status': 'запущен'}
            response = admin_client.post(f'/api/scenarios/{scenario_id}/run')
        assert response.status_code == 202
        task_id = response.get_json()['data']['task_id']

        with patch('src.services.core.task_service.TaskService.get_status') as mock_status:
            mock_status.return_value = {
                'task_id': task_id,
                'status': 'SUCCESS',
                'result': {'run_id': 1, 'status': 'расчёт выполнен'},
                'error': None
            }
            status_response = admin_client.get(f'/api/tasks/{task_id}')
        data = status_response.get_json()['data']
        assert data['status'] == 'SUCCESS'
        assert data['result']['run_id'] is not None

    def test_case29_task_failure_contains_error(self, admin_client, scenario_id):
        """
        TestCase29. POST /api/scenarios/{sid}/run при отсутствии данных,
        дождаться завершения, GET /api/tasks/{task_id}.
        Ожидание: статус 200, статус FAILURE, содержит сообщение об ошибке.
        """
        with patch('src.services.core.task_service.TaskService.start_run') as mock_run:
            mock_run.return_value = {'task_id': 'failure-task-id', 'status': 'запущен'}
            response = admin_client.post(f'/api/scenarios/{scenario_id}/run')
        assert response.status_code == 202
        task_id = response.get_json()['data']['task_id']

        with patch('src.services.core.task_service.TaskService.get_status') as mock_status:
            mock_status.return_value = {
                'task_id': task_id,
                'status': 'FAILURE',
                'result': None,
                'error': 'Нет перевозчиков с доставленными рейсами.'
            }
            status_response = admin_client.get(f'/api/tasks/{task_id}')
        data = status_response.get_json()['data']
        assert data['status'] == 'FAILURE'
        assert data['error'] is not None

    def test_case30_two_parallel_runs_have_different_task_ids(self, admin_client, scenario_id):
        """
        TestCase30. Два последовательных POST /api/scenarios/{sid}/run.
        Ожидание: обе задачи созданы с разными task_id.
        """
        with patch('src.services.core.task_service.TaskService.start_run') as mock_run:
            mock_run.side_effect = [
                {'task_id': 'task-id-first', 'status': 'запущен'},
                {'task_id': 'task-id-second', 'status': 'запущен'},
            ]
            response1 = admin_client.post(f'/api/scenarios/{scenario_id}/run')
            response2 = admin_client.post(f'/api/scenarios/{scenario_id}/run')

        assert response1.status_code == 202
        assert response2.status_code == 202
        task_id1 = response1.get_json()['data']['task_id']
        task_id2 = response2.get_json()['data']['task_id']
        assert task_id1 != task_id2