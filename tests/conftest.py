"""
Общие фикстуры для интеграционного тестирования.
Файл: tests/conftest.py
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
import json
import pytest
import os
from src import create_app, db as _db

@pytest.fixture
def app():
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    application = create_app()
    application.config['TESTING'] = True
    application.config['CELERY_TASK_ALWAYS_EAGER'] = True
    application.config['CELERY_TASK_EAGER_PROPAGATES'] = False
    application.config['UPLOAD_FOLDER'] = '/tmp/test_uploads'

    with application.app_context():
        _db.create_all()

        from src.models import User, Criterion
        admin = User(username='admin', full_name='Admin', role='admin')
        admin.set_password('admin123')
        user = User(username='user1', full_name='User', role='user')
        user.set_password('user123')
        _db.session.add_all([admin, user])

        criteria = [
            ('on_time_rate', 'Своевременность доставки', 'benefit'),
            ('cancellation_rate', 'Доля отменённых рейсов', 'cost'),
            ('no_show_rate', 'Доля неявок на погрузку', 'cost'),
            ('damage_rate', 'Доля повреждений груза', 'cost'),
            ('loss_rate', 'Доля утрат груза', 'cost'),
            ('accident_rate', 'Доля рейсов с ДТП', 'cost'),
            ('tracking_compliance', 'Доля рейсов с GPS-трекингом', 'benefit'),
            ('pod_rate', 'Доля рейсов с POD', 'benefit'),
            ('feedback_score', 'Средняя оценка клиентов', 'benefit'),
            ('rate_per_km', 'Средняя ставка за километр', 'cost'),
        ]
        for order, (code, name, kind) in enumerate(criteria, 1):
            _db.session.add(Criterion(code=code, name=name, kind=kind, order_no=order))
        _db.session.commit()

        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_client(client):
    """Авторизованный клиент с правами администратора."""
    client.post('/api/auth/login',
                data=json.dumps({'username': 'admin', 'password': 'admin123'}),
                content_type='application/json')
    return client


@pytest.fixture
def user_client(client):
    """Авторизованный клиент с правами пользователя."""
    client.post('/api/auth/login',
                data=json.dumps({'username': 'user1', 'password': 'user123'}),
                content_type='application/json')
    return client


@pytest.fixture
def scenario_id(admin_client):
    """Создаёт сценарий и возвращает его ID."""
    with admin_client.application.app_context():
        from src.models import Criterion
        criterion_ids = [c.id for c in Criterion.query.all()[:2]]

    resp = admin_client.post('/api/scenarios',
                             data=json.dumps({
                                 'name': 'Тестовый сценарий',
                                 'description': 'Описание',
                                 'method': 'topsis',
                                 'criterion_ids': criterion_ids,
                                 'swara_config': {}
                             }),
                             content_type='application/json')
    return resp.get_json()['data']['id']