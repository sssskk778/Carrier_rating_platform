"""
Сценарий 7: Разграничение прав доступа.
Файл: tests/test_access.py
"""
import json


class TestAccessControl:

    def test_case20_user_cannot_create_scenario(self, user_client):
        """
        TestCase20. POST /api/scenarios от пользователя с ролью user.
        Ожидание: статус 403, доступ запрещён.
        """
        with user_client.application.app_context():
            from src.models import Criterion
            criterion_ids = [c.id for c in Criterion.query.all()[:2]]

        response = user_client.post('/api/scenarios',
                                    data=json.dumps({
                                        'name': 'Тест',
                                        'method': 'topsis',
                                        'criterion_ids': criterion_ids,
                                        'swara_config': {}
                                    }),
                                    content_type='application/json')
        assert response.status_code == 403

    def test_case21_user_cannot_run_scenario(self, user_client):
        """
        TestCase21. POST /api/scenarios/{sid}/run от пользователя с ролью user.
        Ожидание: статус 403, доступ запрещён.
        """
        with user_client.application.app_context():
            from src.models import Scenario, Criterion, ScenarioCriterion, User
            from src import db
            admin = User.query.filter_by(username='admin').first()
            criteria = Criterion.query.all()[:2]
            s = Scenario(
                name='Тест запуска',
                description='',
                method='topsis',
                status='черновик',
                created_by=admin.id
            )
            db.session.add(s)
            db.session.flush()
            for order, c in enumerate(criteria, 1):
                db.session.add(ScenarioCriterion(
                    scenario_id=s.id,
                    criterion_id=c.id,
                    order_no=order,
                    is_enabled=True
                ))
            db.session.commit()
            sid = s.id

        response = user_client.post(f'/api/scenarios/{sid}/run')
        assert response.status_code == 403