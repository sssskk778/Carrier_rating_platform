"""
Сценарий 4: Запуск расчёта рейтинга.
Файл: tests/test_run.py
"""
import json
from unittest.mock import patch


class TestRun:

    def test_case11_run_scenario_with_data(self, admin_client, scenario_id):
        """
        TestCase11. POST /api/scenarios/{sid}/run при наличии данных в БД.
        Ожидание: статус 202, задача создана, возвращён task_id.
        """
        with patch('src.services.core.task_service.TaskService.start_run') as mock_run:
            mock_run.return_value = {'task_id': 'run-task-id', 'status': 'запущен'}
            response = admin_client.post(f'/api/scenarios/{scenario_id}/run')
        assert response.status_code == 202
        data = response.get_json()
        assert data['ok'] is True
        assert 'task_id' in data['data']

    def test_case12_get_task_status_after_run(self, admin_client):
        """
        TestCase12. GET /api/tasks/{task_id} после завершения расчёта.
        Ожидание: статус 200, статус SUCCESS, результаты сохранены.
        """
        with patch('src.services.core.task_service.TaskService.get_status') as mock_status:
            mock_status.return_value = {
                'task_id': 'run-task-id',
                'status': 'SUCCESS',
                'result': {'run_id': 1, 'status': 'расчёт выполнен'},
                'error': None
            }
            response = admin_client.get('/api/tasks/run-task-id')
        assert response.status_code == 200
        data = response.get_json()
        assert data['data']['status'] == 'SUCCESS'

    def test_case13_run_scenario_no_data(self, admin_client, scenario_id):
        """
        TestCase13. POST /api/scenarios/{sid}/run при отсутствии данных в БД.
        Ожидание: статус 202, после выполнения статус FAILURE.
        """
        with patch('src.services.core.task_service.TaskService.start_run') as mock_run:
            mock_run.return_value = {'task_id': 'fail-task-id', 'status': 'запущен'}
            response = admin_client.post(f'/api/scenarios/{scenario_id}/run')
        assert response.status_code == 202

        with patch('src.services.core.task_service.TaskService.get_status') as mock_status:
            mock_status.return_value = {
                'task_id': 'fail-task-id',
                'status': 'FAILURE',
                'result': None,
                'error': 'Нет перевозчиков с доставленными рейсами.'
            }
            status_response = admin_client.get('/api/tasks/fail-task-id')
        assert status_response.get_json()['data']['status'] == 'FAILURE'
        assert status_response.get_json()['data']['error'] is not None