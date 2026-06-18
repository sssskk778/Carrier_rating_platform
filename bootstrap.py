"""
Заполнение базы данных начальными данными (пользователи и критерии).

Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
import os
from src import create_app, db

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    print('Таблицы пересозданы')
    from src.seed import seed_everything
    seed_everything()