"""
Сценарий 3: Создание и настройка сценария.
Файл: tests/test_scenarios.py
"""
import json
from src import db

class TestScenario:

    def test_case8_create_scenario_success(self, admin_client):
        """
        TestCase8. POST /api/scenarios с корректными данными.
        Ожидание: статус 201, сценарий создан со статусом черновик.
        """
        with admin_client.application.app_context():
            from src.models import Criterion
            criterion_ids = [c.id for c in Criterion.query.all()[:2]]

        response = admin_client.post('/api/scenarios',
                                     data=json.dumps({
                                         'name': 'Новый сценарий',
                                         'description': 'Описание',
                                         'method': 'topsis',
                                         'criterion_ids': criterion_ids,
                                         'swara_config': {}
                                     }),
                                     content_type='application/json')
        assert response.status_code == 201
        data = response.get_json()
        assert data['ok'] is True
        assert 'id' in data['data']

    def test_case9_create_scenario_missing_fields(self, admin_client):
        """
        TestCase9. POST /api/scenarios без обязательных полей.
        Ожидание: статус 422, сообщение об ошибке валидации.
        """
        response = admin_client.post('/api/scenarios',
                                     data=json.dumps({}),
                                     content_type='application/json')
        assert response.status_code == 422
        data = response.get_json()
        assert data['ok'] is False

    def test_case10_set_swara_weights(self, admin_client, scenario_id):
        """
        TestCase10. PUT /api/scenarios/{sid}/weights/swara с корректными весами.
        Ожидание: статус 200, веса сохранены.
        """
        with admin_client.application.app_context():
            from src.models import Criterion, ScenarioCriterion
            links = ScenarioCriterion.query.filter_by(scenario_id=scenario_id).all()
            codes = []
            for link in links:
                c = db.session.get(Criterion, link.criterion_id)
                if c:
                    codes.append(c.code)

        response = admin_client.put(f'/api/scenarios/{scenario_id}/weights/swara',
                                    data=json.dumps({
                                        'ranking': codes,
                                        's_values': [0.2] * (len(codes) - 1)
                                    }),
                                    content_type='application/json')
        assert response.status_code == 200
        data = response.get_json()
        assert data['ok'] is True