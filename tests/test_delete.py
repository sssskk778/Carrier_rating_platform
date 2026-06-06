"""
Сценарий 6: Удаление данных.
Файл: tests/test_delete.py
"""


class TestDelete:

    def test_case17_delete_existing_dataset(self, admin_client):
        """
        TestCase17. DELETE /api/datasets/{did} для существующего датасета.
        Ожидание: статус 200, датасет удалён из БД.
        """
        with admin_client.application.app_context():
            from src.models import Dataset
            from src import db
            ds = Dataset(name='Тест', file_name='test.xlsx',
                         description='', records_count=0)
            db.session.add(ds)
            db.session.commit()
            did = ds.id

        response = admin_client.delete(f'/api/datasets/{did}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True

    def test_case18_delete_nonexistent_dataset(self, admin_client):
        """
        TestCase18. DELETE /api/datasets/{did} для несуществующего датасета.
        Ожидание: статус 404, сообщение об ошибке.
        """
        response = admin_client.delete('/api/datasets/99999')
        assert response.status_code == 404

    def test_case19_delete_existing_scenario(self, admin_client, scenario_id):
        """
        TestCase19. DELETE /api/scenarios/{sid} для существующего сценария.
        Ожидание: статус 200, сценарий удалён.
        """
        response = admin_client.delete(f'/api/scenarios/{scenario_id}')
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True

    def test_case31_delete_nonexistent_scenario(self, admin_client):
        """
        TestCase31. DELETE /api/scenarios/{sid} для несуществующего сценария.
        Ожидание: статус 404, сообщение об ошибке.
        """
        response = admin_client.delete('/api/scenarios/99999')
        assert response.status_code == 404