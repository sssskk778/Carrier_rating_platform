from app import db
from app.models import User, Criterion
from sqlalchemy import text


def seed_everything():
    # =========================================================================
    # 1. СОЗДАЕМ ПОЛЬЗОВАТЕЛЕЙ
    # =========================================================================
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            full_name='Администратор системы',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)

    user = User.query.filter_by(username='logist').first()
    if not user:
        user = User(
            username='logist',
            full_name='Логист Иванов',
            role='user'
        )
        user.set_password('logist123')
        db.session.add(user)

    db.session.commit()
    print('✅ Пользователи созданы: admin / admin123, logist / logist123')

    # =========================================================================
    # 2. УДАЛЯЕМ СТАРЫЕ КРИТЕРИИ И СОЗДАЕМ НОВЫЕ 8
    # =========================================================================
    db.session.execute(text('DELETE FROM scenario_criterion'))
    db.session.execute(text('DELETE FROM criterion'))
    db.session.commit()
    print('✅ Старые критерии удалены')

    criteria_list = [
        ('on_time_rate', 'Своевременность доставки', 'benefit'),
        ('cancellation_rate', 'Доля отменённых рейсов', 'cost'),
        ('cargo_safety_rate', 'Сохранность груза', 'benefit'),
        ('accident_rate', 'Аварийность', 'cost'),
        ('tracking_compliance', 'Доля рейсов с GPS-трекингом', 'benefit'),
        ('pod_rate', 'Доля рейсов с POD', 'benefit'),
        ('feedback_score', 'Средняя оценка клиентов', 'benefit'),
        ('rate_per_km', 'Средняя ставка за километр', 'cost'),
    ]

    for order, (code, name, kind) in enumerate(criteria_list, 1):
        criterion = Criterion(
            code=code,
            name=name,
            kind=kind,
            order_no=order
        )
        db.session.add(criterion)

    db.session.commit()
    print(f'✅ Создано {Criterion.query.count()} новых критериев')
    print('   Список критериев:')
    for c in Criterion.query.order_by(Criterion.order_no).all():
        print(f'      {c.order_no}. {c.code} ({c.kind})')


if __name__ == '__main__':
    from app import create_app

    app = create_app()
    with app.app_context():
        seed_everything()