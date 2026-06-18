"""
Заполнение базы данных начальными данными (пользователи и критерии).

Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
from src import db
from src.models import User, Criterion


def seed_everything():

    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            full_name='Администратор системы',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)

    user = User.query.filter_by(username='user').first()
    if not user:
        user = User(
            username='user',
            full_name='Логист Иванов',
            role='user'
        )
        user.set_password('user123')
        db.session.add(user)

    db.session.commit()
    print('Пользователи готовы')

    if Criterion.query.count() == 0:
        criteria_list = [
            ('on_time_rate', 'Своевременность доставки', 'benefit'),
            ('cancellation_rate', 'Доля отменённых рейсов', 'cost'),
            ('cargo_safety_rate', 'Сохранность груза', 'benefit'),
            ('accident_rate', 'Аварийность', 'cost'),
            ('tracking_compliance', 'Отслеживание', 'benefit'),
            ('pod_rate', 'Документооборот', 'benefit'),
            ('feedback_score', 'Репутация', 'benefit'),
            ('rate_per_km', 'Стоимость', 'cost'),
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
        print(f'Создано {Criterion.query.count()} критериев')
        print('Список критериев:')
        for c in Criterion.query.order_by(Criterion.order_no).all():
            print(f'      {c.order_no}. {c.code} ({c.kind})')
    else:
        print(f'Критерии уже есть ({Criterion.query.count()} шт.)')


if __name__ == '__main__':
    from src import create_app

    app = create_app()
    with app.app_context():
        seed_everything()
