"""
Точка входа для Celery воркера.
"""
from src import create_app
from src.extensions import celery
import src.tasks

src = create_app()