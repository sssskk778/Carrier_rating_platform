# bootstrap.py
import os
from src import create_app, db

app = create_app()
with app.app_context():
    db.drop_all()
    db.create_all()
    print('Таблицы пересозданы')
    from src.seed import seed_everything
    seed_everything()