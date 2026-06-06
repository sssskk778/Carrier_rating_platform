"""
Точка входа для Celery воркера.
Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""

from src import create_app
from src.extensions import celery
import src.tasks

src = create_app()